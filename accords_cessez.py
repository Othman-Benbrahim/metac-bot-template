"""Cessez-le-feu conclus en pleine guerre et leur tenue — ETH/PRIO (décision de l'auteur, 2026-11-24, 16 h 38 : « ne les
éludes pas. Cherche ETH/PRIO »). Procédure : preenregistrements/accords-cessez.md, versée avant le calcul.

Données : registre/cessez-le-feu-declarations.csv (ETH/PRIO, une ligne par déclaration dirigée ; un cessez-le-feu =
uniq_id) ; registre/ucdp-fin-conflits.csv (années de conflit actif, épisodes) pour l'exposition.
- cessez_le_feu (guerre en cours, âge a) : λ par tranche d'âge de l'épisode (moins d'un an, un an et plus) = cessez-le-feu
  bilatéraux ou multilatéraux (side 2 ou 3) déclarés pendant une année active du même conflit UCDP / jours d'année
  active ; années 1989-2020 seulement (couverture ETH/PRIO). Tous types de guerre (ETH/PRIO : guerres civiles).
- tenue (cessez-le-feu en vigueur depuis a jours) : cessez-le-feu bilatéraux ou multilatéraux ; début = entrée en
  vigueur, sinon déclaration ; échec = ended 2 à la date de fin ; fin sans échec (1, 4, ou -1 avec date) = sortie
  censurée ; toujours en cours (0) = censuré au 2020-12-31 ; jamais entré en vigueur (3) ou date de fin inconnue = exclu.
  λ par tranche d'âge : moins de 90 jours, 90 à 364, 365 et plus.
P = 1 − exp(−Σ λ·jours parcourus dans chaque tranche pendant h). État de la guerre : accords_guerre.etat.
"""
from __future__ import annotations

import csv
import datetime as dt
import math
import os
import re
from pathlib import Path

import accords_guerre as ag
import accords_regle as ar

ICI = Path(__file__).resolve().parent
REG = Path(os.environ.get("ALPHABET_REGISTRE", ICI / "registre"))
DECL = REG / "cessez-le-feu-declarations.csv"
FIN_CF = dt.date(2020, 12, 31)
TR_GUERRE = (365,)
TR_TENUE = (90, 365)


def _date(a, m, j):
    try:
        a, m, j = int(a), int(m), int(j)
    except (TypeError, ValueError):
        return None
    if a <= 0 or m <= 0:
        return None
    try:
        return dt.date(a, m, j if j > 0 else 15)
    except ValueError:
        return None


def cessez(chemin: Path = DECL):
    U = {}
    for r in csv.DictReader(chemin.open(encoding="utf-8")):
        if r["uniq_id"] not in U and r["side"] in ("2", "3"):
            U[r["uniq_id"]] = r
    out = []
    for r in U.values():
        dec = _date(r["cf_dec_yr"], r["cf_dec_month"], r["cf_dec_day"])
        if dec is None:
            continue
        eff = _date(r["cf_effect_yr"], r["cf_effect_month"], r["cf_effect_day"]) or dec
        fin = _date(r["end_yr"], r["end_month"], r["end_day"])
        out.append({"conflit": r["ucdp_acd_id"], "dec": dec, "eff": eff, "fin": fin, "ended": r["ended"]})
    return out


def _tranches(age0: int, duree: int, bornes) -> list[int]:
    """Jours d'une période [age0, age0+duree) répartis dans les tranches définies par `bornes`."""
    lim = [0, *bornes, 10 ** 9]
    return [max(0, min(age0 + duree, lim[i + 1]) - max(age0, lim[i])) for i in range(len(lim) - 1)]


def taux_conclusion(CF, EP, jeu: dt.date):
    borne = min(jeu, FIN_CF + dt.timedelta(days=1))
    ev = [0] * (len(TR_GUERRE) + 1)
    ex = [0] * (len(TR_GUERRE) + 1)
    actives = {}
    for e in EP:
        fin = e["fin"] or dt.date(2023, 12, 31)
        for a in range(max(e["debut"].year, 1989), min(fin.year, 2020) + 1):
            d0 = max(dt.date(a, 1, 1), e["debut"])
            d1 = min(dt.date(a, 12, 31), fin, borne - dt.timedelta(days=1))
            if d1 < d0:
                continue
            actives.setdefault(e["conflit"], []).append((d0, d1, e["debut"]))
            for i, j in enumerate(_tranches((d0 - e["debut"]).days, (d1 - d0).days + 1, TR_GUERRE)):
                ex[i] += j
    for c in CF:
        if c["dec"] >= borne:
            continue
        for d0, d1, deb in actives.get(c["conflit"], []):
            if d0 <= c["dec"] <= d1:
                age = (c["dec"] - deb).days
                ev[sum(age >= b for b in TR_GUERRE)] += 1
                break
    return [ev[i] / ex[i] if ex[i] else 0.0 for i in range(len(ev))], ev, ex


def taux_echec(CF, jeu: dt.date):
    borne = min(jeu, FIN_CF)
    ev = [0] * (len(TR_TENUE) + 1)
    ex = [0] * (len(TR_TENUE) + 1)
    for c in CF:
        if c["eff"] >= borne or c["ended"] == "3":
            continue
        if c["ended"] == "0" or (c["fin"] and c["fin"] >= borne):
            fin, echec = borne, False
        elif c["fin"] is None:
            continue
        else:
            fin, echec = c["fin"], c["ended"] == "2"
        d = max(0, (fin - c["eff"]).days)
        for i, j in enumerate(_tranches(0, d, TR_TENUE)):
            ex[i] += j
        if echec:
            ev[sum(d >= b for b in TR_TENUE)] += 1
    return [ev[i] / ex[i] if ex[i] else 0.0 for i in range(len(ev))], ev, ex


def _cumul(lam, age: int, h: int, bornes) -> float:
    return sum(l * j for l, j in zip(lam, _tranches(age, h, bornes)))


def probabilite(cl: str, titre: str, jeu: dt.date, CF, EP, E, releves: bool = False) -> float | None:
    g = ag.guerre(titre, releves)
    if g is None:
        return None
    s = ag.etat(g, jeu, E)
    e = ar.echeance(titre, jeu)
    if s is None or e is None or e <= jeu:
        return None
    st, age, _ = s
    h = (e - jeu).days
    if cl == "cessez_le_feu" and st == "guerre":
        lam, _, _ = taux_conclusion(CF, EP, jeu)
        return 1 - math.exp(-_cumul(lam, age, h, TR_GUERRE))
    if cl == "tenue" and st == "cessez":
        lam, _, _ = taux_echec(CF, jeu)
        r = 1 - math.exp(-_cumul(lam, age, h, TR_TENUE))
        return r if re.search(r"\bbroken\b", titre, re.I) else 1 - r
    return None
