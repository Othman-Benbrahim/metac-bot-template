"""Brique « justice » — Cour suprême des États-Unis (Supreme Court Database 2026_01, affaires 1946-2025). Décision de
l'auteur, 2026-11-24, 18 h 19 (« la suite ? »). Procédure : preenregistrements/justice.md, versée avant le calcul.

- « rule in favor of X in X v. Y » : X est le demandeur (premier nommé) ; P = part des affaires tranchées au fond
  (decisionType 1, 6 ou 7) gagnées par le demandeur (partyWinning = 1), sur les 20 sessions (terms) closes avant la
  question.
- « any justice announce their retirement before <date> » : taux annuel des départs de juges (dernière session siégée,
  hors juges encore en fonction à la dernière session) de 1946 à la dernière session close ; tout motif de départ
  (la base ne dit pas le motif : décès compris, déclaré) ; P = 1 − exp(−λ·h).
Abstention ailleurs (camp du « oui » non lisible mécaniquement, acceptation d'une affaire, autre tribunal).
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
REG = Path(os.environ.get("ALPHABET_REGISTRE", ICI / "registre"))
FAVEUR = re.compile(r"rule in favou?r of ([\w .,&'-]+?) in \1[\w .,&'-]* v\. ", re.I)
RETRAITE = re.compile(r"\bjustice\b.*\bannounce\w* (their|his|her) retirement\b", re.I)


def _lire(nom):
    return list(csv.DictReader((REG / nom).open(encoding="utf-8")))


def taux_demandeur(A, jeu: dt.date, sessions: int = 20):
    der = jeu.year - 1 if jeu.month < 7 else jeu.year          # une session close fin juin
    T = [a for a in A if a["decisionType"] in ("1", "6", "7") and a["partyWinning"] in ("0", "1")
         and der - sessions < int(a["term"]) <= der]
    return (sum(a["partyWinning"] == "1" for a in T) + 0.5) / (len(T) + 1), len(T)


def taux_departs(J, jeu: dt.date):
    der = jeu.year - 1 if jeu.month < 7 else jeu.year
    dern = {}
    for r in J:
        t = int(r["term"])
        if t <= der:
            dern[r["justice"]] = max(dern.get(r["justice"], 0), t)
    fin = max(dern.values())
    departs = [t for t in dern.values() if t < fin and t >= 1946]
    annees = fin - 1946 + 1
    return (len(departs) + 0.5) / annees, len(departs), annees


def probabilite(titre: str, jeu: dt.date, A, J) -> float | None:
    t = titre or ""
    if re.search(r"\bnot\b", t, re.I):
        return None
    if FAVEUR.search(t):
        return taux_demandeur(A, jeu)[0]
    if RETRAITE.search(t):
        e = ar.echeance(t, jeu)
        if e is None or e <= jeu:
            return None
        return 1 - math.exp(-taux_departs(J, jeu)[0] * (e - jeu).days / 365.25)
    return None


def estimer(titre: str, jeu: dt.date | None = None) -> dict | None:
    import json
    try:
        if not json.loads((ICI / "ecosystemes" / "justice-branchee.json").read_text(encoding="utf-8"))["branchee"]:
            return None
        p = probabilite(titre, jeu or dt.date.today(), _lire("scdb-affaires.csv"), _lire("scdb-juges.csv"))
    except (OSError, ValueError, KeyError):
        return None
    return None if p is None else {"classe": "justice", "guerre": "Cour suprême", "p": min(max(p, .01), .99)}
