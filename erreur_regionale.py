"""Erreur des sondages aux élections infranationales, mesurée sur Wikipédia (bot 0.10.376, ombre).

Décision d'auteur du 2026-11-20 : la base n'a pas de source publiée pour l'erreur des sondages aux élections régionales
et municipales ; on la MESURE, comme ParlGov pour les sièges : pour chaque élection passée d'une échelle, sondages de la
dernière semaine (tableaux de la page) contre résultat (encadré de la page). Règle inscrite seulement pour une échelle
qui réunit au moins 30 élections mesurées ; sinon abstention.

Échelles : États brésiliens (gouverneur, premier tour), Länder allemands, provinces canadiennes, grandes villes
américaines (maire), collectivités coréennes (maires des grandes villes et gouverneurs de province). Pages lues par l'API Wikimedia (api.wikimedia.org, permise par robots.txt), version actuelle :
les sondages d'une élection passée ne changent plus. Archive : registre/erreur-regionale/archives.jsonl (tableaux
extraits et lignes chiffrées de l'encadré, jamais le texte de la page).

`python erreur_regionale.py --collecter` (réseau, workflow) ; `python erreur_regionale.py` (hors réseau) écrit
registre/erreur-regionale/mesures.json et mesures.md.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import banc_scrutin as bs

DOSSIER = Path("registre") / "erreur-regionale"
ARCHIVES = DOSSIER / "archives.jsonl"
FENETRE = 7                      # dernière semaine, comme Jennings et Wlezien
PART_MIN = 5.0                   # partis ou candidats d'au moins 5 % au résultat
MINIMUM = 30                     # élections mesurées pour inscrire une règle

ETATS_BR = ["Acre", "Alagoas", "Amapá", "Amazonas", "Bahia", "Ceará", "Federal District", "Espírito Santo", "Goiás",
            "Maranhão", "Mato Grosso", "Mato Grosso do Sul", "Minas Gerais", "Pará", "Paraíba", "Paraná", "Pernambuco",
            "Piauí", "Rio de Janeiro", "Rio Grande do Norte", "Rio Grande do Sul", "Rondônia", "Roraima",
            "Santa Catarina", "São Paulo", "Sergipe", "Tocantins"]
LANDER = ["Baden-Württemberg", "Bavarian", "Berlin", "Brandenburg", "Bremen", "Hamburg", "Hessian", "Lower Saxony",
          "Mecklenburg-Vorpommern", "North Rhine-Westphalia", "Rhineland-Palatinate", "Saarland", "Saxony",
          "Saxony-Anhalt", "Schleswig-Holstein", "Thuringian"]
PROVINCES = ["Alberta", "British Columbia", "Manitoba", "New Brunswick", "Newfoundland and Labrador", "Nova Scotia",
             "Ontario", "Prince Edward Island", "Quebec", "Saskatchewan"]
VILLES = ["New York City", "Los Angeles", "Chicago", "Houston", "Philadelphia", "San Antonio", "San Diego", "Dallas",
          "San Jose", "Austin", "Boston", "Seattle", "Denver", "Washington, D.C.", "Atlanta", "Baltimore", "Detroit",
          "Minneapolis", "San Francisco", "Portland, Oregon"]


COREE_VILLES = ["Seoul", "Busan", "Daegu", "Incheon", "Gwangju", "Daejeon", "Ulsan", "Sejong"]
COREE_PROVINCES = ["Gyeonggi", "Gangwon", "North Chungcheong", "South Chungcheong", "North Jeolla", "South Jeolla",
                   "North Gyeongsang", "South Gyeongsang", "Jeju"]


def titres() -> list[tuple[str, str]]:
    t = [(f"{a} {e} {g} election", "bresil_etats") for a in (2014, 2018, 2022) for e in ETATS_BR
         for g in ("gubernatorial", "state")]           # 0.10.377 : beaucoup de pages s'appellent « 2022 Bahia state election »
    t += [(f"{a} {l} state election", "allemagne_lander") for a in range(2011, 2026) for l in LANDER]
    t += [(f"{a} {p} general election", "canada_provinces") for a in range(2011, 2026) for p in PROVINCES]
    t += [(f"{a} {v} mayoral election", "etats_unis_villes") for a in range(2009, 2026) for v in VILLES]
    t += [(f"{a} {v} mayoral election", "coree_collectivites") for a in (2014, 2018, 2022) for v in COREE_VILLES]
    t += [(f"{a} {p} gubernatorial election", "coree_collectivites") for a in (2014, 2018, 2022) for p in COREE_PROVINCES]
    return t


CHAMPS = re.compile(r"^\s*\|\s*((?:candidate|party|nominee|percentage|popular_vote|election_date|date|\d?blank|\d?data)\w*)\s*=\s*(.*)$", re.I)


def encadre(texte: str) -> dict[str, str]:
    """Lignes « | clé = valeur » de l'encadré utiles au résultat (candidat, parti, pourcentage, date)."""
    m = re.search(r"\{\{\s*Infobox (?:election|legislative election)", texte, re.I)
    if not m:
        return {}
    out = {}
    for ligne in texte[m.start(): m.start() + 20000].split("\n"):
        if ligne.startswith("}}"):
            break
        c = CHAMPS.match(ligne)
        if c and c.group(1).lower() not in out:
            out[c.group(1).lower()] = bs._texte_cellule(c.group(2))[:120]
    return out


def lire_page(c, source, titre: str, texte: str) -> dict:
    annee = int(titre[:4])
    tabs = bs.tableaux(texte, annee)
    sond = source(c, f"Opinion polling for the {titre}")
    if sond:
        tabs += bs.tableaux(sond, annee)
    return {"encadre": encadre(texte), "date_scrutin": bs._date_scrutin(texte), "page_sondages": bool(sond),
            "tableaux": [{"colonnes": t["colonnes"], "lignes": [(d_.isoformat(), v) for d_, v in t["lignes"]]} for t in tabs]}


def collecter() -> int:
    import httpx
    import politesse
    from urllib.parse import quote
    DOSSIER.mkdir(parents=True, exist_ok=True)
    deja = {json.loads(l)["titre"] for l in ARCHIVES.read_text(encoding="utf-8").splitlines() if l.strip()} \
        if ARCHIVES.exists() else set()
    todo = [(t, e) for t, e in titres() if t not in deja]
    print(f"{len(todo)} pages à lire ({len(deja)} déjà archivées).", flush=True)

    def source(c, titre: str) -> str | None:
        for essai in range(3):
            r = c.get(bs.CORE + f"/page/{quote(titre.replace(' ', '_'), safe='')}")
            if r.status_code == 429:
                time.sleep(10 * (essai + 1))
                continue
            time.sleep(0.2)
            if r.status_code != 200:
                return None
            d = r.json()
            if d.get("redirect_target"):
                return None
            return d.get("source")
        return None

    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=60, follow_redirects=True) as c, \
            ARCHIVES.open("a", encoding="utf-8") as f:
        if not politesse.autorise(c, bs.CORE + "/page/Test"):
            print("::warning::API Wikimedia refusée par robots.txt ; rien collecté.")
            return 0
        lus = 0
        for titre, echelle in todo:
            texte = source(c, titre)
            rec = {"titre": titre, "echelle": echelle, "existe": texte is not None}
            if texte:
                try:
                    rec.update(lire_page(c, source, titre, texte))
                    lus += 1
                except Exception as x:                       # 0.10.377 : une page illisible n'arrête pas la collecte
                    rec["erreur"] = f"{type(x).__name__}: {x}"[:200]
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
        print(f"{lus} pages existantes archivées.", flush=True)
    return 0


def _pct(x: str) -> float | None:
    m = re.search(r"(\d{1,2}(?:[.,]\d+)?)\s*%?", x or "")
    return float(m.group(1).replace(",", ".")) if m else None


def resultats(enc: dict[str, str]) -> list[tuple[str, float]]:
    """(nom, part) depuis l'encadré : candidateN / nomineeN / partyN avec percentageN (premier tour s'il y en a deux)."""
    out = []
    for k, v in enc.items():
        m = re.fullmatch(r"percentage(\d+)", k)
        if not m:
            continue
        i = m.group(1)
        nom = enc.get(f"candidate{i}") or enc.get(f"nominee{i}") or enc.get(f"party{i}")
        p = _pct(v)
        if nom and p is not None:
            out.append((nom, p))
    if not out:                                   # encadré à deux tours : « 1blank = First round », « 1data1 = … (45.2%) »
        rang = next((k[0] for k, v in enc.items() if re.fullmatch(r"\dblank", k) and "first" in v.lower()), None)
        if rang:
            for k, v in enc.items():
                m = re.fullmatch(rf"{rang}data(\d+)", k)
                pc = re.search(r"(\d{1,2}(?:[.,]\d+)?)\s*%", v or "")
                nom = m and (enc.get(f"candidate{m.group(1)}") or enc.get(f"nominee{m.group(1)}") or enc.get(f"party{m.group(1)}"))
                if nom and pc:
                    out.append((nom, float(pc.group(1).replace(",", "."))))
    return out


def tours(enc: dict[str, str]) -> tuple[str, str] | None:
    """Encadré à deux tours : (premier du premier tour, vainqueur du second) ; None sans second tour lisible."""
    num = {}
    for k, v in enc.items():
        if re.fullmatch(r"\dblank", k):
            num["1" if "first" in v.lower() else "2" if "second" in v.lower() else "?"] = k[0]
    if "1" not in num or "2" not in num:
        return None
    def premier(t):
        xs = []
        for k, v in enc.items():
            m = re.fullmatch(rf"{num[t]}data(\d+)", k)
            pc = re.search(r"(\d{1,2}(?:[.,]\d+)?)\s*%", v or "")
            if m and pc:
                xs.append((float(pc.group(1).replace(",", ".")), m.group(1)))
        return max(xs)[1] if xs else None
    a, b = premier("1"), premier("2")
    return (a, b) if a and b else None


# noms des partis dans l'encadré → sigle des colonnes de sondages (nomenclature, pas une règle)
SIGLES = [("christian democratic union", "CDU"), ("christian social union", "CSU"), ("social democratic party of germany", "SPD"),
          ("alliance 90", "Grüne"), ("alliance '90", "Grüne"), ("greens", "Grüne"), ("the left", "Linke"), ("left party", "Linke"),
          ("free democratic", "FDP"), ("alternative for germany", "AfD"), ("free voters", "FW"), ("pirate", "Piraten"),
          ("national democratic party of germany", "NPD"), ("sahra wagenknecht", "BSW"), ("south schleswig", "SSW"),
          ("new democratic", "NDP"), ("progressive conservative", "PC"), ("coalition avenir", "CAQ"),
          ("parti québécois", "PQ"), ("québec solidaire", "QS"), ("united conservative", "UCP"), ("saskatchewan party", "SKP"),
          ("green party", "Green"), ("liberal party", "Liberal"), ("people's party", "PPC")]


def sigle(nom: str) -> str:
    n = nom.lower()
    return next((s_ for k, s_ in SIGLES if k in n), nom)


def mesurer() -> dict:
    if not ARCHIVES.exists():
        return {}
    par = defaultdict(list)
    vus = set()
    for l in ARCHIVES.read_text(encoding="utf-8").splitlines():
        r = json.loads(l) if l.strip() else {}
        if not r.get("existe") or r["titre"] in vus or not r.get("date_scrutin"):
            continue
        vus.add(r["titre"])
        jour = date.fromisoformat(r["date_scrutin"])
        tabs = [{"colonnes": t["colonnes"],
                 "lignes": [(date.fromisoformat(d), v) for d, v in t["lignes"]
                            if jour - timedelta(days=FENETRE) <= date.fromisoformat(d) < jour]} for t in r["tableaux"]]
        tabs = [t for t in tabs if t["lignes"]]
        erreurs = []
        for nom, res in resultats(r.get("encadre") or {}):
            if res < PART_MIN:
                continue
            parts = bs.moyenne_sondages(tabs, jour, nom) or (bs.moyenne_sondages(tabs, jour, sigle(nom)) if sigle(nom) != nom else None)
            if parts:
                erreurs.append(abs(parts[parts["__sujet__"]] - res))
        if len(erreurs) >= 2:
            par[r["echelle"]].append({"titre": r["titre"], "erreur_moyenne": statistics.mean(erreurs), "n_parts": len(erreurs)})
    retour = defaultdict(lambda: [0, 0])
    for l in ARCHIVES.read_text(encoding="utf-8").splitlines():
        r = json.loads(l) if l.strip() else {}
        t = r.get("existe") and tours(r.get("encadre") or {})
        if t:
            retour[r["echelle"]][0] += 1
            retour[r["echelle"]][1] += t[0] != t[1]
    out = {}
    for e, xs in sorted(par.items()):
        es = [x["erreur_moyenne"] for x in xs]
        out[e] = {"elections": len(xs), "erreur_absolue_moyenne": round(statistics.mean(es), 2),
                  "mediane": round(statistics.median(es), 2), "sigma": round(statistics.mean(es) / 0.8, 2),
                  "statut": "mesurable" if len(xs) >= MINIMUM else "insuffisant",
                  "seconds_tours": retour[e][0], "retournements": retour[e][1],
                  "taux_retournement": round(retour[e][1] / retour[e][0], 3) if retour[e][0] >= MINIMUM else None,
                  "detail": xs}
    return out


def principal() -> int:
    m = mesurer()
    (DOSSIER / "mesures.json").write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    L = ["# Erreur des sondages aux élections infranationales (mesurée sur Wikipédia)", "",
         f"Sondages des {FENETRE} derniers jours contre résultat de l'encadré ; partis ou candidats d'au moins {PART_MIN:g} % ; "
         f"règle inscrite à partir de {MINIMUM} élections.", "",
         "| Échelle | Élections | Erreur absolue moyenne (points) | Médiane | σ (÷ 0,8) | Statut | Seconds tours (retournements) |",
         "|---|---|---|---|---|---|---|"]
    L += [f"| {e} | {v['elections']} | {v['erreur_absolue_moyenne']} | {v['mediane']} | {v['sigma']} | {v['statut']} | {v['seconds_tours']} ({v['retournements']}) |"
          for e, v in m.items()]
    (DOSSIER / "mesures.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--collecter", action="store_true")
    sys.exit(collecter() if a.parse_args().collecter else principal())
