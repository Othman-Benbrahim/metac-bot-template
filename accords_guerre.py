"""Brique « accords selon l'état de la guerre » (décision de l'auteur, 2026-11-24, 16 h 28 : découpage « matriochka » ;
procédure : preenregistrements/accords-guerre.md, versée avant le calcul).

État à la date de la question, lu dans ecosystemes/guerres-suivies.csv (dates sourcées) pour la guerre que nomme le
titre : guerre en cours (dernier événement = début ou rupture) ou cessez-le-feu en vigueur ; type inter / interne.
Mesure : UCDP Conflict Termination Dataset v4-2024 (épisodes ; début = start_date2 de l'épisode, fin = c_ependdate,
issue = c_outcome : 1 accord de paix, 2 cessez-le-feu). Épisodes extra-systémiques exclus.
- cessez_le_feu (guerre en cours) : taux par jour des fins d'épisode par cessez-le-feu ou accord de paix (1, 2), par
  tranche d'âge de l'épisode (moins d'un an, un an et plus), pour le type de la guerre ; autres fins = sortie sans
  événement ; épisodes en cours = censurés. P = 1 − exp(−Σ λ_tranche · jours passés dans la tranche pendant h).
- accord_paix (guerre en cours) : même calcul, issue 1 seule.
- tenue (cessez-le-feu en vigueur) : après un épisode terminé par cessez-le-feu (2), reprise = début d'un épisode suivant
  du même conflit ; taux par tranche de temps depuis la fin ; tous types réunis. P(rupture) = 1 − exp(−…).
Abstention : guerre non trouvée, état contraire à la question (cessez-le-feu en vigueur pour « conclure »), échéance
illisible. Sans regard vers l'avant : épisodes et événements antérieurs à la date de la question.
"""
from __future__ import annotations

import csv
import datetime as dt
import math
import os
import re
from pathlib import Path

import accords_regle as ar

ICI = Path(__file__).resolve().parent
UCDP = Path(os.environ.get("ALPHABET_REGISTRE", ICI / "registre")) / "ucdp-fin-conflits.csv"
GUERRES = ICI / "ecosystemes" / "guerres-suivies.csv"
TRANCHE = 365
FIN_DONNEES = dt.date(2023, 12, 31)
J = dt.date.fromisoformat
_US = r"(\bU\.?S\.?A?\b|\bUnited States\b|\bAmerican?\b|\bTrump\b|\bRubio\b|\bVance\b|\bWitkoff\b|\bKushner\b)"
CORRESPONDANCE = (                                       # ordre : du plus précis au plus général
    ("israel_hamas", lambda t: re.search(r"\b(hamas|gaza)\b", t, re.I)),
    ("etats_unis_houthis", lambda t: re.search(r"houthi", t, re.I) and re.search(_US, t)),
    ("yemen_houthis", lambda t: re.search(r"houthi", t, re.I)),
    ("israel_iran", lambda t: re.search(r"\bisrael\b", t, re.I) and re.search(r"\biran\b", t, re.I)),
    ("etats_unis_iran", lambda t: re.search(r"\biran\b", t, re.I) and re.search(_US, t)),
    ("russie_ukraine", lambda t: re.search(r"\bukraine\b", t, re.I)),
)


def guerre(titre: str) -> str | None:
    for g, f in CORRESPONDANCE:
        if f(titre or ""):
            return g
    return None


def evenements(chemin: Path = GUERRES):
    E = {}
    for r in csv.DictReader(chemin.open(encoding="utf-8")):
        E.setdefault(r["guerre"], []).append((J(r["date"]), r["evenement"], r["type"]))
    return {g: sorted(L) for g, L in E.items()}


def etat(g: str, jeu: dt.date, E):
    L = [e for e in E.get(g, []) if e[0] < jeu]
    if not L:
        return None
    d, ev, ty = L[-1]
    return ("guerre" if ev in ("debut", "rupture") else "cessez"), (jeu - d).days, ty


def episodes(chemin: Path = UCDP):
    ep = {}
    for r in csv.DictReader(chemin.open(encoding="utf-8")):
        k = r["c_epid"]
        if not k:
            continue
        e = ep.setdefault(k, {"conflit": r["conflict_id"], "no": int(r["c_epno"] or 0), "type": r["type_of_conflict"],
                              "debut": r["start_date2"], "fin": None, "issue": None})
        if r["c_epterm"] == "1":
            e["fin"], e["issue"] = r["c_ependdate"] or None, r["c_outcome"] or None
    out = []
    for e in ep.values():
        try:
            debut = J(e["debut"])
            fin = J(e["fin"]) if e["fin"] else None
        except ValueError:
            continue
        if e["type"] == "1":
            continue
        out.append({"conflit": e["conflit"], "no": e["no"], "type": "inter" if e["type"] == "2" else "interne",
                    "debut": debut, "fin": fin, "issue": e["issue"]})
    return out


def _taux(durees: list[tuple[int, bool]]):
    """durées (jours, événement ?) → taux par jour pour [0, TRANCHE) et [TRANCHE, ∞)."""
    ev, ex = [0, 0], [0, 0]
    for d, e in durees:
        ex[0] += min(d, TRANCHE)
        ex[1] += max(0, d - TRANCHE)
        if e:
            ev[0 if d < TRANCHE else 1] += 1
    return [ev[i] / ex[i] if ex[i] else 0.0 for i in (0, 1)], ev, ex


def taux_fin(EP, jeu: dt.date, ty: str, issues: tuple[str, ...]):
    borne = min(jeu, FIN_DONNEES)
    D = []
    for e in EP:
        if e["type"] != ty or e["debut"] >= borne:
            continue
        if e["fin"] and e["fin"] < borne:
            D.append(((e["fin"] - e["debut"]).days, e["issue"] in issues))
        else:
            D.append(((borne - e["debut"]).days, False))
    return _taux(D)


def taux_reprise(EP, jeu: dt.date):
    borne = min(jeu, FIN_DONNEES)
    par = {}
    for e in EP:
        par.setdefault(e["conflit"], []).append(e)
    D = []
    for L in par.values():
        L.sort(key=lambda z: z["debut"])
        for i, e in enumerate(L):
            if e["issue"] != "2" or not e["fin"] or e["fin"] >= borne:
                continue
            suiv = L[i + 1]["debut"] if i + 1 < len(L) else None
            if suiv and suiv < borne:
                D.append((max(0, (suiv - e["fin"]).days), True))
            else:
                D.append(((borne - e["fin"]).days, False))
    return _taux(D)


def _cumul(lam, age: int, h: int) -> float:
    a1 = max(0, min(age + h, TRANCHE) - min(age, TRANCHE))
    return lam[0] * a1 + lam[1] * (h - a1)


def probabilite(cl: str, titre: str, jeu: dt.date, EP, E) -> float | None:
    g = guerre(titre)
    if g is None:
        return None
    s = etat(g, jeu, E)
    e = ar.echeance(titre, jeu)
    if s is None or e is None or e <= jeu:
        return None
    st, age, ty = s
    h = (e - jeu).days
    if cl in ("cessez_le_feu", "accord_paix"):
        if st != "guerre":
            return None
        lam, _, _ = taux_fin(EP, jeu, ty, ("1", "2") if cl == "cessez_le_feu" else ("1",))
        return 1 - math.exp(-_cumul(lam, age, h))
    if cl == "tenue":
        if st != "cessez":
            return None
        lam, _, _ = taux_reprise(EP, jeu)
        r = 1 - math.exp(-_cumul(lam, age, h))
        return r if re.search(r"\bbroken\b", titre, re.I) else 1 - r
    return None


def estimer(titre: str, jeu: dt.date | None = None) -> dict | None:
    """Dans le bot : seules les sous-familles branchées (ecosystemes/accords-guerre-branchees.json) s'appliquent."""
    import json
    try:
        B = json.loads((ICI / "ecosystemes" / "accords-guerre-branchees.json").read_text(encoding="utf-8"))["branchees"]
        cl = ar.classe(titre)
        if cl not in B:
            return None
        jeu = jeu or dt.date.today()
        p = probabilite(cl, titre, jeu, episodes(), evenements())
    except (OSError, ValueError, KeyError):
        return None
    if p is None:
        return None
    return {"classe": cl, "guerre": guerre(titre), "p": min(max(p, .01), .99)}
