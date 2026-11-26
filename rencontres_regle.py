"""Brique « rencontres » — fréquence des rencontres au sommet entre deux pays (COLT, Pardee/Université de Denver,
CC0, voyages des chefs d'État et de gouvernement 1990-2025). Décision de l'auteur, 2026-11-24 (16 h 52 « On commence »,
banc COLT lancé à 18 h 09). Procédure : preenregistrements/rencontres.md.

Rencontre entre les pays A et B (chefs d'État ou de gouvernement) : un dirigeant de A visite B et rencontre le chef
de l'hôte (MetHostHoGS = Yes), ou l'inverse, ou les dirigeants de A et de B sont dans le même pays visité avec des
dates qui se chevauchent. Rencontres distinctes : écart d'au moins 3 jours. Pour trois pays : les trois présents au
même endroit les mêmes jours.
Taux : (rencontres dans les 5 ans précédant min(date de la question, 2025-12-31) + 0,5) / 5 ans.
P = 1 − exp(−λ·h). Seulement quand le titre nomme des dirigeants ou des pays au niveau des chefs (meet in person,
trilateral meeting) ; « diplomatic meeting », envoyés ou ministres = abstention (niveau non couvert).
"""
from __future__ import annotations

import csv
import datetime as dt
import glob
import gzip
import math
import os
import re
from pathlib import Path

import accords_regle as ar

ICI = Path(__file__).resolve().parent
REG = Path(os.environ.get("ALPHABET_REGISTRE", ICI / "registre"))
FIN_COLT = dt.date(2025, 12, 31)
FENETRE_ANS = 5
NOMS = {"putin": "RUS", "zelensky": "UKR", "zelenskyy": "UKR", "trump": "USA", "xi jinping": "CHN", "xi": "CHN",
        "modi": "IND", "erdogan": "TUR", "erdoğan": "TUR", "netanyahu": "ISR", "kim jong": "PRK", "macron": "FRA",
        "russia": "RUS", "ukraine": "UKR", "india": "IND", "china": "CHN", "united states": "USA", "iran": "IRN"}


def _d(x: str):
    try:
        return dt.date.fromisoformat((x or "")[:10])
    except ValueError:
        return None


def voyages():
    f = glob.glob(str(REG / "colt" / "*-Data.csv.gz"))
    if not f:
        return []
    out = []
    for r in csv.DictReader(gzip.open(f[0], "rt", encoding="utf-8")):
        a, b = r.get("LeaderCountryISO"), r.get("CountryVisitedISO")
        s, e = _d(r.get("TripStartDate")), _d(r.get("TripEndDate"))
        if a and b and s:
            out.append((a, b, s, e or s, r.get("MetHostHoGS") == "Yes"))
    return out


def rencontres(V, pays: tuple[str, ...], jusqua: dt.date) -> list[dt.date]:
    P = set(pays)
    dates = []
    if len(P) == 2:
        a, b = sorted(P)
        for x, y, s, e, met in V:
            if s < jusqua and {x, y} == {a, b} and met:
                dates.append(s)
    par_lieu = {}
    for x, y, s, e, met in V:
        if x in P and s < jusqua:
            par_lieu.setdefault(y, []).append((x, s, e))
    for lieu, L in par_lieu.items():
        for x, s, e in L:
            presents = {x} | {lieu} & P                    # l'hôte est présent chez lui
            jours = [(z, s2) for z, s2, e2 in L if s2 <= e and e2 >= s]
            presents |= {z for z, _ in jours}
            if P <= presents:
                dates.append(max([s] + [s2 for _, s2 in jours]))
    dates.sort()
    out = []
    for d in dates:
        if not out or (d - out[-1]).days >= 3:
            out.append(d)
    return out


def pays_du_titre(titre: str) -> tuple[str, ...] | None:
    t = (titre or "").lower()
    if re.search(r"\b(diplomatic meeting|envoy|vance|kushner|witkoff|rubio|minister|attend)\b", t):
        return None
    if not re.search(r"\b(meet|meeting|summit|trilateral)\b", t) or re.search(r"\bnot meet\b", t):
        return None
    # Hors domaine (correction du 2026-11-26) : COLT ne compte que les rencontres en personne ; une question qui accepte
    # aussi un appel ou un échange à distance (« meet in person or talk on the phone ») n'est pas mesurée par cette
    # brique. Cas d'origine : Trump–Putin, Metaculus 46751, mesuré à 0,049 alors que les appels sont fréquents.
    if re.search(r"\b(phone|call|calls|talk|talks|speak|speaks|video|virtual|virtually|remote|remotely)\b", t):
        return None
    P = []
    for k, v in sorted(NOMS.items(), key=lambda z: -len(z[0])):
        if re.search(r"\b" + re.escape(k) + r"\b", t) and v not in P:
            P.append(v)
    return tuple(P) if len(P) in (2, 3) else None


def probabilite(titre: str, jeu: dt.date, V) -> float | None:
    P = pays_du_titre(titre)
    e = ar.echeance(titre, jeu)
    if P is None or e is None or e <= jeu:
        return None
    fin = min(jeu, FIN_COLT + dt.timedelta(days=1))
    debut = fin - dt.timedelta(days=int(365.25 * FENETRE_ANS))
    k = sum(1 for d in rencontres(V, P, fin) if d >= debut)
    lam = (k + 0.5) / (365.25 * FENETRE_ANS)
    return 1 - math.exp(-lam * (e - jeu).days)


def estimer(titre: str, jeu: dt.date | None = None) -> dict | None:
    import json
    try:
        if not json.loads((ICI / "ecosystemes" / "rencontres-branchee.json").read_text(encoding="utf-8"))["branchee"]:
            return None
        p = probabilite(titre, jeu or dt.date.today(), voyages())
    except (OSError, ValueError, KeyError):
        return None
    if p is None:
        return None
    return {"classe": "rencontre", "guerre": "-".join(pays_du_titre(titre)), "p": min(max(p, .01), .99)}
