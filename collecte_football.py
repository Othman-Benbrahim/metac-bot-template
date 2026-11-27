"""État courant des cinq grands championnats pour la brique « football : Elo, classement et matchs restants »
(décision de l'auteur du 2026-11-27, 12 h 34, option 2 ; méthode retenue par preenregistrements/football-championnats.md,
critère atteint : 0,066 contre 0,219 pour « un parmi N » sur 5 940 questions construites).

Sources :
- openfootball (domaine public) : historique des matchs, pour l'Elo (même calcul que le banc) ;
- Wikipédia (page brute /wiki/<titre>?action=raw, CC BY-SA 4.0, robots.txt respecté) : classement et résultats à jour
  de la saison en cours (gabarits « Sports table » et « Sports results »).

Sortie : registre/football/etat.json (petit : points, matchs restants, Elo, réglages, date de mise à jour du classement).

    python collecte_football.py              # collecte et écrit l'état
    python collecte_football.py --diagnostic # imprime ce qui a été lu, n'écrit rien
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import httpx

import politesse
import banc_football as bf

ICI = Path(__file__).resolve().parent
SORTIE = ICI / "registre" / "football" / "etat.json"
WIKI = "https://en.wikipedia.org/wiki/"
NOMS_WIKI = {"en.1": "Premier League", "es.1": "La Liga", "it.1": "Serie A", "de.1": "Bundesliga", "fr.1": "Ligue 1"}
MOIS_EN = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                       "september", "october", "november", "december"], 1)}


def saison_courante(j: date) -> int:
    return j.year if j.month >= 7 else j.year - 1


def titre_saison(a: int, div: str) -> str:
    return f"{a}–{(a + 1) % 100:02d} {NOMS_WIKI[div]}"


# ---- lecture du wikitexte --------------------------------------------------------------------------------------------
def corps_module(texte: str, module: str) -> list[str]:
    """Corps des appels {{#invoke:<module>|...}}, accolades appariées."""
    out, i = [], 0
    motif = re.compile(r"\{\{\s*#invoke:\s*" + re.escape(module) + r"\s*\|", re.I)
    while True:
        m = motif.search(texte, i)
        if not m:
            return out
        k, prof = m.start(), 0
        j = k
        while j < len(texte) - 1:
            if texte[j:j + 2] == "{{":
                prof += 1
                j += 2
                continue
            if texte[j:j + 2] == "}}":
                prof -= 1
                j += 2
                if prof == 0:
                    break
                continue
            j += 1
        out.append(texte[m.end():j - 2])
        i = j


def parametres(corps: str) -> dict[str, str]:
    """Paramètres nommés séparés par « | » au premier niveau (hors [[...]] et {{...}})."""
    P, cour, prof_l, prof_g, i = {}, [], 0, 0, 0
    morceaux = []
    while i < len(corps):
        d = corps[i:i + 2]
        if d == "[[":
            prof_l += 1; cour.append(d); i += 2; continue
        if d == "]]":
            prof_l -= 1; cour.append(d); i += 2; continue
        if d == "{{":
            prof_g += 1; cour.append(d); i += 2; continue
        if d == "}}":
            prof_g -= 1; cour.append(d); i += 2; continue
        if corps[i] == "|" and prof_l == 0 and prof_g == 0:
            morceaux.append("".join(cour)); cour = []; i += 1; continue
        cour.append(corps[i]); i += 1
    morceaux.append("".join(cour))
    for x in morceaux:
        if "=" in x:
            k, v = x.split("=", 1)
            P[k.strip()] = re.sub(r"<!--.*?-->", "", v, flags=re.S).strip()
    return P


def affiche(v: str) -> str:
    """[[Arsenal F.C.|Arsenal]] -> Arsenal ; retire gabarits et références."""
    v = re.sub(r"<ref[^>]*/>|<ref.*?</ref>", "", v or "", flags=re.S)
    v = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", v)
    v = re.sub(r"\{\{[^{}]*\}\}", "", v)
    return re.sub(r"\s+", " ", v).strip()


def entier(v: str) -> int:
    m = re.search(r"-?\d+", affiche(v or "0"))
    return int(m.group(0)) if m else 0


def date_maj(v: str) -> str | None:
    v = affiche(v).lower()
    m = re.search(r"(\d{1,2})\s+([a-z]+)\s+(\d{4})", v) or re.search(r"([a-z]+)\s+(\d{1,2}),?\s+(\d{4})", v)
    if not m:
        return None
    a, b, c = m.groups()
    j, mo = (int(a), MOIS_EN.get(b)) if a.isdigit() else (int(b), MOIS_EN.get(a))
    try:
        return date(int(c), mo, j).isoformat() if mo else None
    except ValueError:
        return None


def lire_tableau(texte: str) -> dict | None:
    for corps in corps_module(texte, "Sports table"):
        P = parametres(corps)
        codes = [P[k] for k in sorted((k for k in P if re.fullmatch(r"team\d+", k)), key=lambda k: int(k[4:]))]
        if len(codes) < 16:
            continue
        equipes = {}
        for c in codes:
            w, d_, l = entier(P.get(f"win_{c}", "0")), entier(P.get(f"draw_{c}", "0")), entier(P.get(f"loss_{c}", "0"))
            equipes[c] = {"nom": affiche(P.get(f"name_{c}", c)), "joues": w + d_ + l,
                          "points": 3 * w + d_ + entier(P.get(f"adjust_points_{c}", "0"))}
        return {"equipes": equipes, "mise_a_jour": date_maj(P.get("update", "")),
                "complete": "complete" in P.get("update", "").lower()}
    return None


def lire_resultats(texte: str, codes: set[str]) -> dict[tuple[str, str], tuple[int, int]]:
    out = {}
    for corps in corps_module(texte, "Sports results"):
        for k, v in parametres(corps).items():
            m = re.fullmatch(r"match_([A-Za-z0-9]+)_([A-Za-z0-9]+)", k)
            if not m or m.group(1) not in codes or m.group(2) not in codes:
                continue
            s = re.search(r"(\d+)\s*[–—-]\s*(\d+)", affiche(v))
            if s:
                out[(m.group(1), m.group(2))] = (int(s.group(1)), int(s.group(2)))
    return out


def brut(c: httpx.Client, titre: str) -> str | None:
    u = WIKI + titre.replace(" ", "_") + "?action=raw"
    if not politesse.autorise(c, u):
        print(f"refusé par robots.txt : {u}", flush=True)
        return None
    r = c.get(u)
    time.sleep(1)
    print(f"  « {titre} » : HTTP {r.status_code}, {len(r.text)} caractères", flush=True)
    if r.status_code != 200:
        return None
    m = re.match(r"\s*#REDIRECT\s*\[\[([^\]|#]+)", r.text, re.I)
    return brut(c, m.group(1).strip()) if m else r.text


def page_saison(c: httpx.Client, a: int, div: str) -> tuple[dict | None, dict]:
    """Classement et résultats ; si l'article transclut le tableau (gabarit « ... table »), on lit le gabarit."""
    texte = brut(c, titre_saison(a, div)) or ""
    tab = lire_tableau(texte)
    if tab is None:
        for t in re.findall(r"\{\{\s*([^{}|]*\btable\b[^{}|]*)\}\}", texte, re.I):
            g = brut(c, "Template:" + t.strip())
            tab = lire_tableau(g or "")
            if tab:
                texte += "\n" + (g or "")
                break
    res = lire_resultats(texte, set(tab["equipes"]) if tab else set())
    if tab and not res:
        for t in re.findall(r"\{\{\s*([^{}|]*\bresults\b[^{}|]*)\}\}", texte, re.I):
            g = brut(c, "Template:" + t.strip())
            res = lire_resultats(g or "", set(tab["equipes"]))
            if res:
                break
    return tab, res


# ---- état --------------------------------------------------------------------------------------------------------------
def etat(diag: bool = False) -> dict:
    auj = datetime.now(timezone.utc).date()
    a = saison_courante(auj)
    src = bf.Source()
    saisons = {(d, x): src.matchs(d, x) for d in bf.LIGUES for x in range(2015, a + 1)}
    out = {"calcule_le": auj.isoformat(), "saison": a, "ligues": {}}
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=60, follow_redirects=True) as c:
        for div in bf.LIGUES:
            tab, res = page_saison(c, a, div)
            if not tab:
                out["ligues"][div] = {"erreur": "classement illisible"}
                continue
            codes = list(tab["equipes"])
            n = len(codes)
            # Elo : openfootball jusqu'à aujourd'hui, puis résultats Wikipédia que openfootball n'a pas encore
            R = bf.elo_a(saisons, div, auj)
            of_joues = {(bf.cle(m["h"]), bf.cle(m["a"])) for m in saisons[(div, a)] if m["hg"] is not None}
            cles = {cd: (bf.trouver(tab["equipes"][cd]["nom"], {k: k for k in R}) or bf.cle(tab["equipes"][cd]["nom"]))
                    for cd in codes}
            init = min(R.values()) if R else bf.ELO0       # club absent d'openfootball (rare) : Elo le plus bas
            for cd in codes:
                R.setdefault(cles[cd], init)
            ajoutes = 0
            for (h, g), (sh, sg) in res.items():
                if (cles[h], cles[g]) in of_joues:
                    continue
                E = 1 / (1 + 10 ** (-(R[cles[h]] + bf.H_ELO - R[cles[g]]) / 400))
                S = 1.0 if sh > sg else (0.5 if sh == sg else 0.0)
                R[cles[h]] += bf.K_ELO * (S - E)
                R[cles[g]] -= bf.K_ELO * (S - E)
                ajoutes += 1
            restants = [[h, g] for h in codes for g in codes if h != g and (h, g) not in res]
            H, pn = bf.regler(saisons, div)
            joues = sum(e["joues"] for e in tab["equipes"].values()) // 2
            out["ligues"][div] = {
                "titre": titre_saison(a, div), "mise_a_jour": tab["mise_a_jour"], "complete": tab["complete"],
                "equipes": {cd: {**tab["equipes"][cd], "elo": round(R[cles[cd]], 1), "cle": cles[cd]} for cd in codes},
                "restants": restants, "H": H, "p_nul": round(pn, 4),
                "controle": {"matchs_classement": joues, "resultats_lus": len(res), "restants": len(restants),
                             "attendu_total": n * (n - 1), "resultats_ajoutes_elo": ajoutes},
            }
            if diag:
                L = out["ligues"][div]
                top = sorted(L["equipes"].values(), key=lambda e: -e["points"])[:5]
                print(div, L["titre"], "maj", L["mise_a_jour"], L["controle"],
                      [(e["nom"], e["points"], e["elo"]) for e in top], flush=True)
    return out


def principal() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--diagnostic", action="store_true")
    diag = ap.parse_args().diagnostic
    E = etat(diag)
    if diag:
        return 0
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(json.dumps(E, ensure_ascii=False, indent=1), encoding="utf-8")
    for d, v in E["ligues"].items():
        top = sorted((v.get("equipes") or {}).values(), key=lambda e: -e["points"])[:3]
        print(d, v.get("erreur") or "", v.get("mise_a_jour"), v.get("controle"), [(e["nom"], e["points"], e["elo"]) for e in top])
    print("écrit", SORTIE)
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
