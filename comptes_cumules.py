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
