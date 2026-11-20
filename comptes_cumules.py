"""Comptes cumulés : fourchettes du total à une ou deux semaines (préenregistrement preenregistrements/comptes-cumules.md).
Modèle « baseline » des centres de prévision du CDC (Cramer et al., PNAS 2022), adapté au cumul. Rien dans le bot.
"""
from __future__ import annotations

import random


def fourchette_cumul(incidences: list[float], dernier_total: float, h: int, ps=(0.1, 0.2, 0.4, 0.6, 0.8, 0.9),
                     tirages: int = 2000, graine: int = 0) -> list[tuple[float, float]] | None:
    """`incidences` : incidences par période, de la plus ancienne à la plus récente (au moins 8)."""
    if len(incidences) < 8 or h < 1:
        return None
    base = sum(incidences[-4:]) / 4
    rapports = []
    hist = incidences[-56:]
    for i in range(4, len(hist)):
        m = sum(hist[i - 4:i]) / 4
        if m > 0:
            rapports.append(hist[i] / m)
    if not rapports:
        rapports = [1.0]
    rnd = random.Random(graine)
    totaux = sorted(dernier_total + sum(base * rnd.choice(rapports) for _ in range(h)) for _ in range(tirages))
    return [(p, totaux[min(tirages - 1, int(p * tirages))]) for p in ps]


def fourchette_cumul_v2(incidences: list[float], dernier_total: float, h: int, ps=(0.1, 0.2, 0.4, 0.6, 0.8, 0.9),
                        tirages: int = 2000, graine: int = 0) -> list[tuple[float, float]] | None:
    """Version 2 (2026-11-20, 20 h 30, décision d'auteur « corriger le modèle ») : la baseline publiée des centres de
    prévision du CDC telle qu'elle est décrite (Cramer et al., PNAS 2022) — médiane = DERNIÈRE incidence observée ;
    l'incidence suit une marche au hasard dont les pas sont tirés dans les variations d'une période à l'autre des 52
    dernières périodes, rendues symétriques (± chaque variation) ; incidence bornée à 0. Les pas s'additionnent d'une
    période à l'autre, ce qui élargit la fourchette avec l'échéance (la v1 tirait des rapports indépendants)."""
    if len(incidences) < 8 or h < 1:
        return None
    hist = incidences[-53:]
    pas = [b - a for a, b in zip(hist[:-1], hist[1:])]
    pas = pas + [-x for x in pas]
    rnd = random.Random(graine)
    totaux = []
    for _ in range(tirages):
        y, s = incidences[-1], 0.0
        for _ in range(h):
            y = max(0.0, y + rnd.choice(pas))
            s += y
        totaux.append(dernier_total + s)
    totaux.sort()
    return [(p, totaux[min(tirages - 1, int(p * tirages))]) for p in ps]


# ---- 0.10.403 : pari d'auteur du 2026-11-20 (20 h 44) sur la version 1, branchée dans le bot ; version 2 conservée
import csv as _csv
import re as _re
from datetime import date as _date, timedelta as _td
from pathlib import Path as _Path

ROUGEOLE = _Path("registre") / "rougeole-cdc.csv"
MOTIF_ROUGEOLE = _re.compile(r"\bmeasles\b.*\b(cdc|confirmed)\b|\b(cdc|confirmed)\b.*\bmeasles\b", _re.I)


def totaux_hebdomadaires(f: _Path | None = None) -> list[tuple[str, float]]:
    f = f or ROUGEOLE
    if not f.exists():
        return []
    return sorted((x["jour"], float(x["total"])) for x in _csv.DictReader(f.open(encoding="utf-8")))


def fourchette_rougeole(titre: str, jour: str, fin: str | None) -> dict | None:
    """Percentiles du total CDC de rougeole à l'échéance (version 1). None tant qu'il n'y a pas 9 relevés hebdomadaires
    consécutifs (8 incidences), ou si la question n'est pas une question de total CDC."""
    if not MOTIF_ROUGEOLE.search(titre or "") or not fin:
        return None
    t = [(j, v) for j, v in totaux_hebdomadaires() if j < jour]
    if len(t) < 9:
        return None
    t = t[-57:]
    # relevés hebdomadaires seulement (écart de 6 à 8 jours), sinon on ne calcule pas
    if any(not 6 <= (_date.fromisoformat(b[0]) - _date.fromisoformat(a[0])).days <= 8 for a, b in zip(t[:-1], t[1:])):
        return None
    inc = [b[1] - a[1] for a, b in zip(t[:-1], t[1:])]
    h = max(1, round((_date.fromisoformat(fin) - _date.fromisoformat(t[-1][0])).days / 7))
    f = fourchette_cumul(inc, t[-1][1], h)
    return {"dernier_total": t[-1][1], "date_total": t[-1][0], "periodes": h, "percentiles": f} if f else None
