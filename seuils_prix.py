"""Seuils de prix : probabilités log-normales sans dérive (référence preenregistrements/seuils-de-prix-reference.md).

Aucune cote de marché ni volatilité implicite : seulement l'historique des prix. Rien n'entre dans le bot à ce stade.
"""
from __future__ import annotations

import csv
import math
import re
from datetime import date
from functools import lru_cache
from pathlib import Path

FRED = Path("registre") / "fred.csv"
ACTIFS = {  # motif du titre → (série FRED, jours de cotation par an)
    "CBBTCUSD": (re.compile(r"\b(bitcoin|btc)\b", re.I), 365),
    "CBETHUSD": (re.compile(r"\b(ethereum|ether|eth)\b", re.I), 365),
    "DCOILBRENTEU": (re.compile(r"\bbrent\b", re.I), 252),
    "NASDAQCOM": (re.compile(r"\bnasdaq\b", re.I), 252),
    "SP500": (re.compile(r"\b(s&p ?500|spx)\b", re.I), 252),
    "DJIA": (re.compile(r"\bdow jones\b|\bdjia\b", re.I), 252),
}


def phi(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def p_a_la_date(s0: float, k: float, sigma: float, t_ans: float, au_dessus: bool = True) -> float:
    """Probabilité d'être au-dessus (ou au-dessous) de k à la date, marche log-normale sans dérive."""
    if t_ans <= 0 or sigma <= 0:
        return 1.0 if (s0 > k) == au_dessus else 0.0
    p = phi(math.log(s0 / k) / (sigma * math.sqrt(t_ans)))
    return p if au_dessus else 1 - p


def p_atteint_avant(s0: float, k: float, sigma: float, t_ans: float) -> float:
    """Probabilité de toucher k avant la date (principe de réflexion) ; 1 si k est déjà franchi."""
    if s0 == k:
        return 1.0
    if t_ans <= 0 or sigma <= 0:
        return 0.0
    return min(1.0, 2 * phi(-abs(math.log(k / s0)) / (sigma * math.sqrt(t_ans))))


@lru_cache(maxsize=1)
def series() -> dict[str, list[tuple[str, float]]]:
    out: dict[str, list[tuple[str, float]]] = {}
    if FRED.exists():
        for r in csv.DictReader(FRED.open(encoding="utf-8")):
            out.setdefault(r["serie"], []).append((r["jour"], float(r["valeur"])))
    for v in out.values():
        v.sort()
    return out


def etat(serie: str, avant: str, fenetre: int = 30) -> tuple[float, float] | None:
    """(dernier prix connu strictement avant la date, volatilité annualisée sur `fenetre` rendements)."""
    pts = [v for j, v in series().get(serie, []) if j < avant and v > 0]
    if len(pts) < fenetre + 1:
        return None
    r = [math.log(b / a) for a, b in zip(pts[-fenetre - 1:-1], pts[-fenetre:])]
    m = sum(r) / len(r)
    sd = math.sqrt(sum((x - m) ** 2 for x in r) / (len(r) - 1))
    return pts[-1], sd * math.sqrt(ACTIFS[serie][1])


def actif(titre: str) -> str | None:
    trouves = [s for s, (rx, _) in ACTIFS.items() if rx.search(titre or "")]
    return trouves[0] if len(trouves) == 1 else None


def annees(debut: str, fin: str) -> float:
    return (date.fromisoformat(fin[:10]) - date.fromisoformat(debut[:10])).days / 365.0
