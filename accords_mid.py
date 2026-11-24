"""Tenue des trêves entre États — couche MID 5.0, affrontements commencés à partir de 1946 (décision de l'auteur,
2026-11-24, 16 h 46). Procédure : preenregistrements/accords-mid.md, versée avant le calcul.

Affrontement retenu : dispute MID de niveau d'hostilité 4 (emploi de la force) ou 5 (guerre), commencée en 1946 ou après.
Pour chaque paire d'États opposés (camp A / camp B, fichier MIDB) : trêve = fin de l'affrontement (fin de dispute,
MIDA) ; échec = début d'un nouvel affrontement retenu entre les deux mêmes États ; sinon censure au 2014-12-31 (ou à la
date de la question). Taux par tranche de temps depuis la trêve : < 90 jours, 90-364, ≥ 365.
Guerre interne : tenue ETH/PRIO (accords_cessez) inchangée.
"""
from __future__ import annotations

import csv
import datetime as dt
import math
import os
import re
from pathlib import Path

import accords_cessez as ac
import accords_guerre as ag
import accords_regle as ar

ICI = Path(__file__).resolve().parent
REG = Path(os.environ.get("ALPHABET_REGISTRE", ICI / "registre"))
FIN_MID = dt.date(2014, 12, 31)


def _d(j, m, a):
    try:
        j, m, a = int(j), int(m), int(a)
    except (TypeError, ValueError):
        return None
    if a < 0 or m < 1:
        return None
    try:
        return dt.date(a, m, j if j > 0 else 15)
    except ValueError:
        return None


def affrontements(a: Path = REG / "mid-a.csv", b: Path = REG / "mid-b.csv"):
    D = {}
    for r in csv.DictReader(a.open(encoding="utf-8")):
        if r["hostlev"] not in ("4", "5"):
            continue
        s, e = _d(r["stday"], r["stmon"], r["styear"]), _d(r["endday"], r["endmon"], r["endyear"])
        if s is None or s.year < 1946:
            continue
        D[r["dispnum"]] = {"debut": s, "fin": e if r.get("ongo2014") != "1" else None, "A": set(), "B": set()}
    for r in csv.DictReader(b.open(encoding="utf-8")):
        d = D.get(r["dispnum"])
        if d is not None:
            d["A" if r["sidea"] == "1" else "B"].add(r["ccode"])
    return D


def taux_reprise(D, jeu: dt.date):
    borne = min(jeu, FIN_MID)
    debuts = {}
    for d in D.values():
        for x in d["A"]:
            for y in d["B"]:
                debuts.setdefault(frozenset((x, y)), []).append(d["debut"])
    ev, ex = [0, 0, 0], [0, 0, 0]
    for d in D.values():
        if d["fin"] is None or d["fin"] >= borne:
            continue
        for k in {frozenset((x, y)) for x in d["A"] for y in d["B"]}:
            suiv = [s for s in debuts[k] if s > d["fin"]]
            r = min(suiv) if suiv else None
            if r and r < borne:
                duree, echec = (r - d["fin"]).days, True
            else:
                duree, echec = (borne - d["fin"]).days, False
            for i, j in enumerate(ac._tranches(0, duree, ac.TR_TENUE)):
                ex[i] += j
            if echec:
                ev[sum(duree >= t for t in ac.TR_TENUE)] += 1
    return [ev[i] / ex[i] if ex[i] else 0.0 for i in range(3)], ev, ex


def probabilite(titre: str, jeu: dt.date, D, CF, E, releves: bool = False) -> float | None:
    g = ag.guerre(titre, releves)
    if g is None:
        return None
    s = ag.etat(g, jeu, E)
    if s is None:
        return None
    if s[2] != "inter":
        return ac.probabilite("tenue", titre, jeu, CF, None, E, releves)
    e = ar.echeance(titre, jeu)
    if e is None or e <= jeu or s[0] != "cessez":
        return None
    lam, _, _ = taux_reprise(D, jeu)
    r = 1 - math.exp(-ac._cumul(lam, s[1], (e - jeu).days, ac.TR_TENUE))
    return r if re.search(r"\bbroken\b", titre, re.I) else 1 - r


def estimer(titre: str, jeu: dt.date | None = None) -> dict | None:
    import json
    try:
        B = json.loads((ICI / "ecosystemes" / "accords-mid-branchees.json").read_text(encoding="utf-8"))["branchees"]
        if ar.classe(titre) != "tenue" or "tenue" not in B:
            return None
        p = probabilite(titre, jeu or dt.date.today(), affrontements(), ac.cessez(), ag.evenements(releves=True), True)
    except (OSError, ValueError, KeyError):
        return None
    if p is None:
        return None
    return {"classe": "tenue", "guerre": ag.guerre(titre, True), "p": min(max(p, .01), .99)}
