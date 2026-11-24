"""Couche « guerres entre États » des cessez-le-feu et de leur tenue — COW Inter-State War v4.0, guerres commencées à
partir de 1946 (décision de l'auteur, 2026-11-24, 16 h 46 : « 1817-2007, c'est un peu vieux comme série »).
Procédure : preenregistrements/accords-etats.md, versée avant le calcul.

Guerre inter (type de la table ou du relevé) : mesure COW ; guerre interne : mesure ETH/PRIO (accords_cessez).
- cessez_le_feu, guerre entre États en cours depuis a jours : une guerre COW s'arrête (fin du dernier combat de tous ses
  participants, toutes issues confondues) ; taux de fin par tranche d'âge (< 365 jours, ≥ 365), guerres commencées en
  1946 ou après, terminées avant la date de la question ; guerres en cours censurées.
- tenue, trêve entre États en vigueur depuis a jours : après la fin d'une période de combat (fin du 1er épisode d'un
  participant, ou fin de guerre), échec = reprise (2e épisode de la même guerre, ou nouvelle guerre COW entre deux mêmes
  États) ; sinon censure au 2007-12-31 ; tranches < 90 jours, 90-364, ≥ 365. Une paire d'États par trêve.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import math
import os
import re
from pathlib import Path

import accords_cessez as ac
import accords_guerre as ag
import accords_regle as ar

ICI = Path(__file__).resolve().parent
COW = Path(os.environ.get("ALPHABET_REGISTRE", ICI / "registre")) / "cow-guerres-etats.csv"
DEBUT_MIN = 1946
FIN_COW = dt.date(2007, 12, 31)


def _d(m, j, a):
    try:
        m, j, a = int(m), int(j), int(a)
    except (TypeError, ValueError):
        return None
    if a < 0 or m < 0:
        return None
    try:
        return dt.date(a, m, j if j > 0 else 15)
    except ValueError:
        return None


def guerres(chemin: Path = COW):
    t = chemin.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    W = {}
    for r in csv.DictReader(io.StringIO(t)):
        W.setdefault(r["WarNum"], []).append(r)
    out = []
    for num, L in W.items():
        part = []
        for r in L:
            s1, e1 = _d(r["StartMonth1"], r["StartDay1"], r["StartYear1"]), _d(r["EndMonth1"], r["EndDay1"], r["EndYear1"])
            s2, e2 = _d(r["StartMonth2"], r["StartDay2"], r["StartYear2"]), _d(r["EndMonth2"], r["EndDay2"], r["EndYear2"])
            if s1 is None:
                continue
            part.append({"etat": r["ccode"], "camp": r["Side"], "s1": s1, "e1": e1, "s2": s2, "e2": e2})
        if not part:
            continue
        debut = min(p["s1"] for p in part)
        if debut.year < DEBUT_MIN:
            continue
        fins = [p["e2"] or p["e1"] for p in part]
        fin = None if any(f is None for f in fins) else max(fins)
        out.append({"num": num, "debut": debut, "fin": fin, "part": part})
    return sorted(out, key=lambda g: g["debut"])


def taux_fin(G, jeu: dt.date):
    borne = min(jeu, FIN_COW)
    D = []
    for g in G:
        if g["debut"] >= borne:
            continue
        if g["fin"] and g["fin"] < borne:
            D.append(((g["fin"] - g["debut"]).days, True))
        else:
            D.append(((borne - g["debut"]).days, False))
    ev, ex = [0, 0], [0, 0]
    for d, e in D:
        for i, j in enumerate(ac._tranches(0, d, (365,))):
            ex[i] += j
        if e:
            ev[0 if d < 365 else 1] += 1
    return [ev[i] / ex[i] if ex[i] else 0.0 for i in (0, 1)], ev, ex


def taux_reprise(G, jeu: dt.date):
    borne = min(jeu, FIN_COW)
    paires = {}                                           # paire d'États → débuts de guerre
    for g in G:
        A = {p["etat"] for p in g["part"] if p["camp"] == "1"}
        B = {p["etat"] for p in g["part"] if p["camp"] == "2"}
        for a in A:
            for b in B:
                paires.setdefault(frozenset((a, b)), []).append(g["debut"])
    D = []
    for g in G:
        A = [p for p in g["part"] if p["camp"] == "1"]
        B = [p for p in g["part"] if p["camp"] == "2"]
        vues = set()
        for a in A:
            for b in B:
                k = frozenset((a["etat"], b["etat"]))
                if k in vues:
                    continue
                vues.add(k)
                # première trêve de la paire : fin du 1er épisode commun ; reprise : 2e épisode ou guerre suivante
                f1 = min(x for x in (a["e1"], b["e1"]) if x) if (a["e1"] or b["e1"]) else None
                if f1 is None or f1 >= borne:
                    continue
                rep = [x for x in (a["s2"], b["s2"]) if x and x > f1]
                rep += [d for d in paires.get(k, []) if d > f1]
                r = min(rep) if rep else None
                if r and r < borne:
                    D.append(((r - f1).days, True))
                else:
                    D.append(((borne - f1).days, False))
    ev, ex = [0, 0, 0], [0, 0, 0]
    for d, e in D:
        for i, j in enumerate(ac._tranches(0, d, ac.TR_TENUE)):
            ex[i] += j
        if e:
            ev[sum(d >= b for b in ac.TR_TENUE)] += 1
    return [ev[i] / ex[i] if ex[i] else 0.0 for i in range(3)], ev, ex


def probabilite(cl: str, titre: str, jeu: dt.date, G, CF, EP, E, releves: bool = False) -> float | None:
    g = ag.guerre(titre, releves)
    if g is None:
        return None
    s = ag.etat(g, jeu, E)
    if s is None:
        return None
    if s[2] != "inter":                                   # guerre interne : couche ETH/PRIO
        return ac.probabilite(cl, titre, jeu, CF, EP, E, releves)
    e = ar.echeance(titre, jeu)
    if e is None or e <= jeu:
        return None
    st, age, _ = s
    h = (e - jeu).days
    if cl == "cessez_le_feu" and st == "guerre":
        lam, _, _ = taux_fin(G, jeu)
        return 1 - math.exp(-ac._cumul(lam, age, h, (365,)))
    if cl == "tenue" and st == "cessez":
        lam, _, _ = taux_reprise(G, jeu)
        r = 1 - math.exp(-ac._cumul(lam, age, h, ac.TR_TENUE))
        return r if re.search(r"\bbroken\b", titre, re.I) else 1 - r
    return None


def estimer(titre: str, jeu: dt.date | None = None) -> dict | None:
    import json
    try:
        B = json.loads((ICI / "ecosystemes" / "accords-etats-branchees.json").read_text(encoding="utf-8"))["branchees"]
        cl = ar.classe(titre)
        if cl not in B:
            return None
        jeu = jeu or dt.date.today()
        p = probabilite(cl, titre, jeu, guerres(), ac.cessez(), ag.episodes(), ag.evenements(releves=True), True)
    except (OSError, ValueError, KeyError):
        return None
    if p is None:
        return None
    return {"classe": cl, "guerre": ag.guerre(titre, True), "p": min(max(p, .01), .99)}
