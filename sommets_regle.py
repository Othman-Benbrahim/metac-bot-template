"""Brique « présence du président américain à un sommet de l'OTAN » (décision de l'auteur, 2026-11-24, 18 h 15 : « Tu
peux faire l'OTAN »). Procédure : preenregistrements/sommets-otan.md, versée avant le calcul.

Sommets : ecosystemes/sommets-otan.csv (liste officielle, nato.int ; virtuel exclu). Présence : sommet aux États-Unis
= présent (hôte) ; sinon voyage du président américain (COLT) dans le pays hôte pendant le sommet (± 3 jours), ou, à
défaut, la même année (trois dates de la page officielle ne concordent pas avec les voyages : Londres 1990, Rome 1991,
Madrid 1997). P = (présences + 0,5) / (sommets + 1), sommets antérieurs à la date de la question et couverts par COLT.
"""
from __future__ import annotations

import csv
import datetime as dt
import re
from pathlib import Path

import rencontres_regle as rr

ICI = Path(__file__).resolve().parent
SOMMETS = ICI / "ecosystemes" / "sommets-otan.csv"
RECONNAIT = re.compile(r"\b(trump|us president|president of the united states|biden)\b.*\battend\w*\b.*\bnato summit\b", re.I)


def presences(V, jeu: dt.date):
    out = []
    for s in csv.DictReader(SOMMETS.open(encoding="utf-8")):
        d0, d1 = dt.date.fromisoformat(s["debut"]), dt.date.fromisoformat(s["fin"])
        if s["virtuel"] == "1" or d1 >= jeu or d1 > rr.FIN_COLT:
            continue
        if s["pays_iso"] == "USA":
            out.append((s["debut"], True))
            continue
        T = [1 for a, b, x, y, _ in V if a == "USA" and b == s["pays_iso"]
             and x <= d1 + dt.timedelta(3) and y >= d0 - dt.timedelta(3)]
        if not T:
            T = [1 for a, b, x, y, _ in V if a == "USA" and b == s["pays_iso"] and x.year == d0.year]
        out.append((s["debut"], bool(T)))
    return out


def probabilite(titre: str, jeu: dt.date, V) -> float | None:
    if not RECONNAIT.search(titre or "") or re.search(r"\bnot\b", titre or "", re.I):
        return None
    P = presences(V, jeu)
    if not P:
        return None
    return (sum(1 for _, x in P if x) + 0.5) / (len(P) + 1)


def estimer(titre: str, jeu: dt.date | None = None) -> dict | None:
    import json
    try:
        if not json.loads((ICI / "ecosystemes" / "sommets-otan-branchee.json").read_text(encoding="utf-8"))["branchee"]:
            return None
        p = probabilite(titre, jeu or dt.date.today(), rr.voyages())
    except (OSError, ValueError, KeyError):
        return None
    return None if p is None else {"classe": "rencontre", "guerre": "sommet OTAN", "p": min(max(p, .01), .99)}
