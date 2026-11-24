"""Brique du maintien (bot 0.10.495, décision de l'auteur du 2026-11-24, 15 h 21-15 h 23 ; sources validées à 15 h 23).

Question reconnue : un dirigeant de ecosystemes/dirigeants-maintien.csv, et une forme de maintien (« cease to be »,
« out as », « remain », « still be », « leave office », « resign », « step down »). Abstention : mécanisme précis nommé
(25th Amendment, impeachment, arrest…), ou élection nationale du pays dans l'horizon (la question relève de la course).
Risque annuel de départ : irrégulier + régulier selon l'ancienneté (Archigos 4.1, 1990-2015) + mortalité selon l'âge
(SSA 2023, hommes) ; pape : mortalité seule. P(départ avant l'échéance) = 1 − exp(−Σ risques × durée), la mortalité
étant cumulée année par année. Mélange d'un quart avec la prévision du bot, déplacement plafonné à 15 points, comme la
règle des événements comptés.
"""
from __future__ import annotations

import csv
import math
import re
from datetime import date
from pathlib import Path

ICI = Path(__file__).resolve().parent
POIDS, ECART_MAX = 0.25, 0.15
DEPART = re.compile(r"\b(cease[sd]? to be|out as|leave[s]? office|resign|step[s]? down|ousted|no longer)\b", re.I)
RESTE = re.compile(r"\b(remain|still be|stay|be the (president|prime minister|supreme leader|leader|pope))\b", re.I)
PRECIS = re.compile(r"\b(25th amendment|impeach\w*|arrest\w*|indict\w*|convicted|assassinat\w*|coup|removed via|elections?)\b", re.I)
NATIONALES = re.compile(r"(presidential|general|parliamentary|legislative|federal) election", re.I)


def _lignes(nom: str) -> list[list[str]]:
    return [[x.strip() for x in l.split("|")] if "|" in l else l.split(",")
            for l in (ICI / "ecosystemes" / nom).read_text(encoding="utf-8").splitlines() if l and not l.startswith("#")]


def dirigeants() -> list[dict]:
    return [{"motifs": l[0].split("/"), "poste": l[1], "iso3": l[2], "naissance": int(l[3]), "debut": l[4], "source": l[5]}
            for l in _lignes("dirigeants-maintien.csv")]


def mortalite() -> dict[int, float]:
    return {int(a): float(q) for a, q in _lignes("mortalite-ssa-2023.csv")[1:]}


def risques() -> dict[str, dict]:
    return {l[0]: {"irregulier": float(l[2]), "regulier": float(l[3])} for l in _lignes("archigos-risques.csv")[1:]}


def tranche(ans: float) -> str:
    return "0-2" if ans < 2 else "2-5" if ans < 5 else "5-10" if ans < 10 else "10+"


def election_dans(iso3: str, jour: str, echeance: str) -> bool:
    import adaptateurs  # noqa: F401  (registre)
    f = Path("registre") / "elections.csv"
    if not f.exists():
        return False
    iso2 = {r["iso3"]: r["iso2"] for r in csv.DictReader(
        l for l in (ICI / "ecosystemes/codes-pays-fips.csv").read_text(encoding="utf-8").splitlines() if l and not l.startswith("#"))}.get(iso3)
    return any(r["pays"] == iso2 and jour <= r["date"] <= echeance and NATIONALES.search(r.get("nom") or "")
               for r in csv.DictReader(f.open(encoding="utf-8")))


def reconnaitre(titre: str) -> dict | None:
    if PRECIS.search(titre) or not (DEPART.search(titre) or RESTE.search(titre)):
        return None
    for d in dirigeants():
        if any(re.search(r"(?<![\w-])" + re.escape(m) + r"(?![\w-])", titre) for m in d["motifs"]):
            return {**d, "sens": "reste" if RESTE.search(titre) and not DEPART.search(titre) else "depart"}
    return None


def p_depart(d: dict, jour: str, echeance: str) -> float:
    j0, j1 = date.fromisoformat(jour), date.fromisoformat(echeance)
    t = (j1 - j0).days / 365.25
    if t <= 0:
        return 0.0
    q = mortalite()
    survie, age, reste = 1.0, j0.year - d["naissance"], t
    while reste > 0:                                   # mortalité cumulée par année (ou fraction d'année)
        pas = min(1.0, reste)
        survie *= (1 - q.get(min(max(age, 40), 100), 0.37)) ** pas
        age, reste = age + 1, reste - pas
    if d["poste"] == "pape":
        return 1 - survie
    r = risques()[tranche((j0 - date.fromisoformat(d["debut"])).days / 365.25)]
    return 1 - survie * math.exp(-(r["irregulier"] + r["regulier"]) * t)


def melanger(p_bot: float, p_regle: float) -> float:
    lg = lambda p: math.log(min(max(p, .01), .99) / (1 - min(max(p, .01), .99)))
    p = 1 / (1 + math.exp(-((1 - POIDS) * lg(p_bot) + POIDS * lg(p_regle))))
    return min(max(p, p_bot - ECART_MAX), p_bot + ECART_MAX)


def estimer(titre: str, jour: str, echeance: str, p_bot: float, verifier_elections: bool = True) -> dict | None:
    d = reconnaitre(titre)
    if d is None or (verifier_elections and d["poste"] != "pape" and election_dans(d["iso3"], jour, echeance)):
        return None
    pd_ = p_depart(d, jour, echeance)
    p_regle = pd_ if d["sens"] == "depart" else 1 - pd_
    return {"dirigeant": d["motifs"][0], "poste": d["poste"], "sens": d["sens"], "p_depart": pd_, "p_regle": p_regle,
            "p_bot": p_bot, "p": melanger(p_bot, p_regle), "poids": POIDS, "ecart_max": ECART_MAX, "source": d["source"]}
