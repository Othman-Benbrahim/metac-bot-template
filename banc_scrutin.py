"""Brique « scrutin » : étalons de l'écosystème électoral (bot 0.10.364, ombre).

Préenregistrement : preenregistrements/etalon-scrutin.md (essai etalon_scrutin). Aucun modèle de langue.

Deux temps, pour que le test soit reproductible :
1. `python banc_scrutin.py --collecter` (réseau, workflow) : pour chaque question électorale de la cohorte, cherche la
   page Wikipédia des sondages, lit sa VERSION à la date de la question et archive au registre l'identifiant de version
   et le tableau extrait (registre/scrutins/archives.jsonl). Une page déjà archivée pour cette date n'est pas relue.
2. `python banc_scrutin.py` (hors réseau) : calcule la probabilité de la brique à partir des seules archives, la compare
   aux semblables (p_S) et écrit registre/banc-scrutin.json, avec l'empreinte SHA-256 des probabilités.

Une question hors brique, ou sans sondage lisible dans les 30 jours avant sa date, est une ABSTENTION (publiée).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import time
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

REG = Path("registre")
ARCHIVES = REG / "scrutins" / "archives.jsonl"
SORTIE = REG / "banc-scrutin.json"
API = "https://en.wikipedia.org/w/api.php"
CORE = "https://api.wikimedia.org/core/v1/wikipedia/en"
FENETRE = 30            # jours de sondages avant la date de la question (E2)
SIGMA0 = 2.5            # points, erreur habituelle à la veille du vote (E3)
TIRAGES = 20_000
GRAINE = 0
DEUX_TOURS = {"brazil", "brazilian", "peru", "peruvian", "chile", "chilean", "colombia", "colombian", "ecuador",
              "ecuadorian", "bolivia", "bolivian", "portugal", "portuguese", "romania", "romanian", "france", "french",
              "poland", "polish", "costa rica", "argentina", "argentine", "congo", "uruguay", "guatemala", "dominican",
              "georgia", "louisiana", "texas", "mississippi", "minas gerais", "bahia", "rio de janeiro", "sao paulo",
              "são paulo"}
HORS_FORME = re.compile(r"\bby \d+%? or more|\d+\s*-\s*\d+ seats|\bby \d+-\d+%|popular vote|rounds or fewer|majority of seats|every region|if trump|before "
                        r"september|electoral votes|margin", re.I)


# ---------------------------------------------------------------- 1. rattachement (règles écrites)

def _norm(x: str) -> str:
    x = unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]+", " ", x).strip()


def forme(titre: str) -> dict | None:
    """Forme de la question → {sujet, evenement (gagne|qualifie|rang), rang, election, classe} ; None = hors brique."""
    t = titre.strip().rstrip("?").replace("’", "'")
    if HORS_FORME.search(t):
        return None
    m = re.match(r"^(?:\[[^\]]+\]\s*)?Will (.+?) (win|finish in|place|qualify for|advance to|be nominated|win the nomination)(.*)$", t, re.I)
    if not m:
        return None
    sujet, verbe, reste = m.group(1).strip(), m.group(2).lower(), m.group(3).strip()
    rang = {"first": 1, "second": 2, "third": 3, "fourth": 4, "1st": 1, "2nd": 2, "3rd": 3, "4th": 4}
    s_ = (verbe + " " + reste).lower()
    r = (re.search(r"\b(first|second|third|fourth|1st|2nd|3rd|4th)(?:[ -]place|[ -]most)", s_)
         or re.search(r"^(?:place|finish in|finish) (first|second|third|fourth|1st|2nd|3rd|4th)\b", s_))
    if verbe in ("qualify for", "advance to"):
        ev, k = "qualifie", 2
    elif r:
        ev, k = "rang", rang[r.group(1)]
    elif re.search(r"most (seats|votes)", s_):
        ev, k = "rang", 1
    else:
        ev, k = "gagne", 1
    reste = re.sub(r"^(?:in |at )?(?:the )?(?:\d+(?:st|nd|rd|th)|first|second|third|fourth)?(?:[ -](?:place|most \w+))?\s*"
                   r"(?:in |of )?(?:the )?(?:(?:1st|2nd|first|second) round of (?:the )?)?", "", reste, flags=re.I)
    el = re.search(r"((?:the )?(?:\d{4} |next )?[A-Z0-9][^?]*?(?:election|primary|nomination|elections|runoff))", reste)
    election = (el.group(1) if el else reste).strip()
    election = re.sub(r"^(the )?(most seats|most votes|second[- ]most seats|third[- ]most seats)( in| at)?( the)?\s*", "", election, flags=re.I)
    election = re.sub(r"^(in|at|of) (the )?", "", election, flags=re.I)
    e = _norm(election)
    if "primary" in e or "nomination" in e:
        classe = "S1" if any(w in e for w in ("texas", "georgia", "mississippi", "alabama", "south dakota", "louisiana")) else "S3"
    elif any(w in e for w in DEUX_TOURS) and ("president" in e or "governor" in e or "gubernatorial" in e):
        classe = "S1"
    else:
        classe = "S2"
    if ev == "qualifie" and classe != "S1":
        return None
    return {"sujet": sujet, "evenement": ev, "rang": k, "election": election, "classe": classe}


# ---------------------------------------------------------------- 2. lecture d'un tableau de sondages (wikitexte)

MOIS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def _texte_cellule(c: str) -> str:
    c = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", c, flags=re.S)
    c = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", c)
    c = re.sub(r"\{\{(?:nowrap|small|nobr)\|([^{}]*)\}\}", r"\1", c, flags=re.I)
    c = re.sub(r"\{\{dts\|(\d{4})\|(\d{1,2})\|(\d{1,2})[^}]*\}\}", r"\1-\2-\3", c, flags=re.I)
    c = re.sub(r"\{\{[^{}]*\}\}", " ", c)
    c = re.sub(r"<[^>]+>", " ", c).replace("'''", "").replace("''", "")
    if "|" in c and not c.strip().startswith("|"):
        c = c.split("|")[-1]                                  # attributs de style : « style=... | 34 »
    return re.sub(r"\s+", " ", c).strip()


def _date(texte: str, annee_defaut: int) -> date | None:
    t = texte.lower()
    iso = re.findall(r"(\d{4})-(\d{1,2})-(\d{1,2})", t)
    if iso:
        a, m, j = iso[-1]
        return date(int(a), int(m), int(j))
    dm = re.findall(r"(\d{1,2})\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?(?:\s*,?\s*(\d{4}))?", t)
    md = re.findall(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*(\d{1,2})(?:\s*,?\s*(\d{4}))?", t)
    try:
        if dm:
            j, m, a = dm[-1]
            return date(int(a or annee_defaut), MOIS[m], int(j))
        if md:
            m, j, a = md[-1]
            return date(int(a or annee_defaut), MOIS[m], int(j))
    except ValueError:
        return None
    return None


def _nombre(texte: str) -> float | None:
    texte = re.sub(r"\[[^\]]*\]|[*†‡]", "", texte).strip().lstrip("|").strip()
    m = re.fullmatch(r"\s*(\d{1,2}(?:[.,]\d+)?)\s*%?\s*", texte)
    return float(m.group(1).replace(",", ".")) if m else None


ECARTER = re.compile(r"poll|firm|pollster|date|field|sample|size|lead|margin|other|undecided|none|blank|null|abst|"
                     r"don|n/a|ref|source|mode|link|\bdk\b", re.I)


def tableaux(wikitexte: str, annee_defaut: int) -> list[dict]:
    """Chaque tableau de sondages : {colonnes: [noms], lignes: [(date, [valeurs])]}. Heuristique ; un tableau illisible
    est ignoré."""
    out = []
    annee = annee_defaut
    for bloc in re.split(r"\n\{\|", "\n" + wikitexte):
        avant, _, corps = bloc.partition("\n|}")
        lignes_t = avant.split("\n|-")
        if len(lignes_t) < 3:
            for h in re.findall(r"^=+\s*(\d{4})\s*=+", avant, re.M):
                annee = int(h)
            continue
        entetes: list[str] = []
        lignes = []
        for lt in lignes_t:
            lt = "\n".join(l for l in lt.strip().split("\n") if l.startswith(("!", "|")))
            if lt.startswith("|+"):
                continue
            cellules_h = [x for x in re.split(r"\n!|!!", "\n" + lt) if x.strip()] if lt.startswith("!") else []
            if cellules_h and not entetes:
                entetes = [_texte_cellule(x) for x in cellules_h]
                continue
            cells = [x for x in re.split(r"\n\||\|\|", "\n" + lt) if x.strip()]
            if not cells or not entetes:
                continue
            textes = [_texte_cellule(x) for x in cells]
            d = None
            for x in textes[:3]:
                d = _date(x, annee) or d
            if not d:
                continue
            lignes.append((d, textes))
        if entetes and lignes:
            out.append({"colonnes": entetes, "lignes": lignes})
        for h in re.findall(r"^=+\s*(\d{4})\s*=+", corps, re.M):
            annee = int(h)
    return out


def moyenne_sondages(tabs: list[dict], jour: date, sujet: str) -> dict | None:
    """Moyenne, sur les sondages des FENETRE jours avant `jour`, de chaque colonne de candidat du premier tableau qui
    contient le sujet. Rend {nom: part} avec la clé « __sujet__ » pour la colonne du sujet ; None si rien."""
    cle = [w for w in _norm(sujet).split() if len(w) >= 3 and w not in ("the", "and", "del", "dos", "das")]
    if not cle:
        return None
    meilleur_resultat, meilleur_n = None, 0
    for tab in tabs:
        cols = tab["colonnes"]
        scores = []
        for i, c in enumerate(cols):
            n = set(_norm(c).split())
            sc = 3 if n and set(cle) <= n else 2 if cle[-1] in n else 1 if any(len(w) >= 4 and w in n for w in cle) else 0
            scores.append(sc)
        meilleur = max(scores) if scores else 0
        if meilleur == 0 or scores.count(meilleur) > 1:          # aucun ou plusieurs candidats possibles : on s'abstient
            continue
        idx_sujet = scores.index(meilleur)
        candidats = [i for i, c in enumerate(cols) if c and not ECARTER.search(c)]
        if idx_sujet not in candidats:
            candidats.append(idx_sujet)
        somme = {i: [] for i in candidats}
        for d, textes in tab["lignes"]:
            if not (jour - timedelta(days=FENETRE) <= d <= jour):
                continue
            decal = len(cols) - len(textes)                        # cellules fusionnées en tête de ligne
            for i in candidats:
                j = i - decal
                if 0 <= j < len(textes):
                    v = _nombre(textes[j])
                    if v is not None:
                        somme[i].append(v)
        parts = {cols[i]: float(np.mean(v)) for i, v in somme.items() if v}
        n_sujet = len(somme.get(idx_sujet) or [])
        if cols[idx_sujet] in parts and len(parts) >= 2 and n_sujet > meilleur_n:
            # 0.10.370 : le tableau qui compte le plus de sondages du sujet dans la fenêtre, et non le premier venu
            parts["__sujet__"] = cols[idx_sujet]
            meilleur_resultat, meilleur_n = parts, n_sujet
    return meilleur_resultat


# ---------------------------------------------------------------- 3. calcul (déterministe)

def probabilite(parts: dict, f: dict, jours_restants: int, sigma0: float = SIGMA0) -> float:
    noms = [k for k in parts if k != "__sujet__"]
    mu = np.array([parts[k] for k in noms], dtype=float)
    i = noms.index(parts["__sujet__"])
    sigma = sigma0 * math.sqrt(1 + max(jours_restants, 0) / 30)
    g = np.random.default_rng(GRAINE)
    x = np.clip(mu + g.normal(0, sigma, size=(TIRAGES, len(mu))), 0.01, None)
    x = 100 * x / x.sum(axis=1, keepdims=True)
    rang = (x > x[:, [i]]).sum(axis=1) + 1                       # rang du sujet dans chaque tirage
    if f["evenement"] == "rang":
        p = float((rang == f["rang"]).mean())
    elif f["evenement"] == "qualifie":
        p = float((rang <= 2).mean())
    elif f["classe"] == "S1":
        # gagne au premier tour (> 50 %), sinon au second tour : le mieux placé des deux premiers (approximation écrite)
        p = float(((x[:, i] > 50) | (rang == 1)).mean())
    else:
        p = float((rang == 1).mean())
    return min(0.98, max(0.02, p))


# ---------------------------------------------------------------- 4. questions

def questions() -> list[dict]:
    import banc_jugement as bj
    import banc_proxemie as bp
    xs = [json.loads(l) for l in bj.REGISTRE.read_text(encoding="utf-8").splitlines() if l.strip()]
    xs = [x for x in xs if not bp.COMBINEE.search(x.get("titre") or "")]
    xs = bj.cohorte_complete(xs)
    bj.calculer(xs)
    out = []
    for x in xs:
        if not re.search(r"election|primary|nomination|runoff", x["titre"], re.I):
            continue
        x["forme"] = forme(x["titre"])
        out.append(x)
    return out


def lire_archives() -> dict[tuple[str, str], dict]:
    if not ARCHIVES.exists():
        return {}
    out = {}
    for l in ARCHIVES.read_text(encoding="utf-8").splitlines():
        if l.strip():
            a = json.loads(l)
            if a.get("revision"):
                out[(a["election"], a["jour"])] = a
    return out


# ---------------------------------------------------------------- 5. collecte (réseau)

GENERIQUES = {"the", "next", "election", "elections", "presidential", "parliamentary", "general", "state", "primary",
              "governor", "gubernatorial", "mayoral", "runoff", "republican", "democratic", "nomination", "of", "in"}


def _titre_plausible(titre: str, election: str) -> bool:
    """La page trouvée doit porter un mot distinctif de l'élection (pays, État, ville, année)."""
    mots = [w for w in _norm(election).split() if w not in GENERIQUES and len(w) >= 3]
    t = _norm(titre)
    return bool(mots) and any(w[:5] in t for w in mots)


def collecter(tout: bool = False) -> int:
    """Archive, pour chaque (élection, date), la version de la page de sondages en vigueur à cette date. Passe par
    l'API Wikimedia (api.wikimedia.org, permise par robots.txt ; l'API MediaWiki de en.wikipedia.org est refusée)."""
    import httpx
    import politesse
    from urllib.parse import quote
    deja = lire_archives()
    import banc_jugement as bj
    qs = [x for x in questions() if x["forme"] and (tout or x["jeu"] >= bj.COUPURE)]   # --tout : aussi 2024-2025
    cles = sorted({(x["forme"]["election"], x["jeu"]) for x in qs} - set(deja))
    print(f"{len(qs)} questions dans la brique ; {len(cles)} couples (élection, date) à archiver.", flush=True)
    ARCHIVES.parent.mkdir(parents=True, exist_ok=True)

    def get(c, url, **kw):
        for essai in range(3):
            r = c.get(url, **kw)
            if r.status_code == 429:
                time.sleep(10 * (essai + 1))
                continue
            time.sleep(0.2)
            return r.json() if r.status_code == 200 else {}
        return {}

    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=60, follow_redirects=True) as c, \
            ARCHIVES.open("a", encoding="utf-8") as f:
        if not politesse.autorise(c, CORE + "/search/page"):
            print("::warning::API Wikimedia refusée par robots.txt ; rien collecté.")
            return 0
        titres: dict[str, str | None] = {}
        for election, _ in cles:
            if election in titres:
                continue
            titres[election] = None
            for q in (f"Opinion polling for the {election}", election):
                pages = (get(c, CORE + "/search/page", params={"q": q, "limit": 5}) or {}).get("pages") or []
                bons = [p["title"] for p in pages if _titre_plausible(p["title"], election)]
                bons.sort(key=lambda t: "polling" not in t.lower())
                if bons:
                    titres[election] = bons[0]
                    break
        par_titre: dict[str, list[tuple[str, str]]] = {}
        for election, jour in cles:
            if titres[election]:
                par_titre.setdefault(titres[election], []).append((election, jour))
            else:
                f.write(json.dumps({"election": election, "jour": jour, "titre": None, "revision": None,
                                    "tableaux": []}, ensure_ascii=False) + "\n")
        for titre, besoins in par_titre.items():
            plus_ancien = min(j for _, j in besoins)
            revs, url, n = [], CORE + f"/page/{quote(titre.replace(' ', '_'), safe='')}/history", 0
            while url and n < 200:                                   # 20 versions par page d'historique
                d = get(c, url)
                lot = d.get("revisions") or []
                revs += [(x["timestamp"], x["id"]) for x in lot]
                n += 1
                if not lot or lot[-1]["timestamp"][:10] < plus_ancien:
                    break
                url = d.get("older")
            revs.sort()
            textes: dict[int, str] = {}
            for election, jour in besoins:
                avant = [r for r in revs if r[0][:10] <= jour]
                rec = {"election": election, "jour": jour, "titre": titre, "revision": None, "horodatage": None,
                       "tableaux": []}
                if avant:
                    ts, rid = avant[-1]
                    if rid not in textes:
                        textes[rid] = (get(c, CORE + f"/revision/{rid}") or {}).get("source") or ""
                    texte = textes[rid]
                    rec.update(revision=rid, horodatage=ts, date_scrutin=_date_scrutin(texte),
                               tableaux=[{"colonnes": t["colonnes"], "lignes": [(d_.isoformat(), v) for d_, v in t["lignes"]]}
                                         for t in tableaux(texte, int(jour[:4]))])
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush()
                print(f"{election[:60]} @ {jour} : {titre} rév. {rec['revision']} · {len(rec['tableaux'])} tableau(x) "
                      f"({len(revs)} versions lues)", flush=True)
    return 0


def _date_scrutin(texte: str) -> str | None:
    m = re.search(r"\|\s*election_date\s*=\s*([^\n]+)", texte)
    if not m:
        return None
    d = _date(_texte_cellule(m.group(1)), 2000)
    return d.isoformat() if d and d.year > 2000 else None


# ---------------------------------------------------------------- 6. évaluation (hors réseau, reproductible)

def evaluer() -> int:
    import banc_jugement as bj
    import essais as es
    cb = bj.cb
    arch = lire_archives()
    xs = questions()
    lignes = []
    for x in xs:
        f, p = x["forme"], None
        motif = None
        if not f:
            motif = "hors brique (forme)"
        else:
            a = arch.get((f["election"], x["jeu"]))
            if not a or not a.get("tableaux"):
                motif = "pas d'archive ou de tableau"
            else:
                tabs = [{"colonnes": t["colonnes"], "lignes": [(date.fromisoformat(d), v) for d, v in t["lignes"]]}
                        for t in a["tableaux"]]
                parts = moyenne_sondages(tabs, date.fromisoformat(x["jeu"]), f["sujet"])
                if not parts:
                    motif = "aucun sondage du sujet dans les 30 jours"
                else:
                    fin = a.get("date_scrutin") or x.get("resolue_le") or x["jeu"]
                    jr = (date.fromisoformat(fin[:10]) - date.fromisoformat(x["jeu"])).days
                    p = probabilite(parts, f, jr)
        lignes.append({"id": f'{x["source"]}:{x["id"]}', "jeu": x["jeu"], "titre": x["titre"], "issue": x["issue"],
                       "p_S": x["p_S"], "p_E": p, "classe": (f or {}).get("classe"), "abstention": motif})
    conf = [l for l in lignes if l["jeu"] >= bj.COUPURE]
    jug = [l for l in conf if l["p_E"] is not None]
    pm = lambda s, k: round(sum(cb.pl(l[k], l["issue"]) for l in s) / len(s), 4) if s else None
    ec = [(l["id"], cb.pl(l["p_E"], l["issue"]) - cb.pl(l["p_S"], l["issue"])) for l in jug]
    bas = haut = None
    if len(ec) >= 30:
        bas, haut = cb.bootstrap(ec, es.risque_corrige(1))
    empreinte = hashlib.sha256(json.dumps([(l["id"], l["jeu"], l["p_E"]) for l in lignes], sort_keys=True).encode()).hexdigest()
    r = {"questions_electorales": len(lignes), "confirmation": len(conf), "jugees": len(jug),
         "abstentions": {m: sum(1 for l in conf if l["abstention"] == m) for m in sorted({l["abstention"] for l in conf if l["abstention"]})},
         "perte": {"semblables": pm(jug, "p_S"), "brique": pm(jug, "p_E")},
         "ecart_brique_moins_semblables": round(sum(e for _, e in ec) / len(ec), 4) if ec else None,
         "intervalle_corrige": [round(bas, 4), round(haut, 4)] if bas is not None else None,
         "verdict": ("la brique aide" if haut is not None and haut < 0 else "la brique nuit" if bas is not None and bas > 0
                     else "non tranché" if bas is not None else "trop peu de questions jugées"),
         "par_classe": {c: {"n": len(v), "semblables": pm(v, "p_S"), "brique": pm(v, "p_E")}
                        for c in ("S1", "S2", "S3") for v in [[l for l in jug if l["classe"] == c]] if v},
         "empreinte_sha256": empreinte, "risque_corrige": es.risque_corrige(1),
         "note": "perte log, plus bas = mieux ; aucune donnée lue hors des archives ; ombre"}
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    (REG / "scrutins" / "detail.jsonl").parent.mkdir(parents=True, exist_ok=True)
    (REG / "scrutins" / "detail.jsonl").write_text("\n".join(json.dumps(l, ensure_ascii=False) for l in lignes) + "\n",
                                                   encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--collecter", action="store_true")
    a.add_argument("--tout", action="store_true", help="archiver aussi les questions d'avant 2026 (registre des briques)")
    o = a.parse_args()
    sys.exit(collecter(o.tout) if o.collecter else evaluer())
