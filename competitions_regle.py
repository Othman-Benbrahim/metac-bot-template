"""Brique « un parmi N » pour les questions « X gagnera-t-il <compétition> ? » (décision de l'auteur, 2026-11-24, 15 h 48).

Mécanisme (carte, competitions-culture : règles d'attribution, classements de force) : une compétition n'a qu'un vainqueur
parmi N concurrents ; une question posée sur un concurrent donné vaut 1/N en l'absence d'autre information. N est fixé
par le règlement de la compétition (nombre d'équipes ou de nommés), saisi de mémoire par Claude, à vérifier : c'est un
fait de règlement, pas une estimation.
Seule la forme « gagner » est traitée ; « finir 2e », « atteindre la finale », « meilleur buteur », « participer » :
abstention.
"""
from __future__ import annotations

import math
import re

GAGNER = re.compile(r"\bwins?\b|\bwin the\b|\bbe the (winner|champion)\b", re.I)
AUTRES_FORMES = re.compile(r"\b(conference finals|finish|reach|make it|advance|qualify|top goalscorer|top scorer|participate|repeat|place|runner-up|second|score|record|h2h|vs\.?|iff|if )\b", re.I)
# (motif de l'événement, N concurrents) — de la plus précise à la plus générale
EVENEMENTS = [
    (r"FIFA World Cup", 48), (r"Super Bowl|NFL championship", 32), (r"NBA Finals|NBA champion", 30),
    (r"Stanley Cup", 32), (r"World Series", 30), (r"Champions League|Europa League", 36),
    (r"Western Conference|Eastern Conference|National League Championship|American League Championship", 15),
    (r"Premier League|La ?Liga|Serie A", 20), (r"Bundesliga|Ligue 1", 18),
    (r"NBA .*Division|Southwest Division|Southeast Division|Northwest Division|Atlantic Division|Central Division|Pacific Division", 5),
    (r"Metropolitan Division", 8),
    (r"Eurovision", 37),
    (r"Best Picture", 10), (r"Academy Awards|Oscar", 5), (r"Emmy.*Outstanding (Comedy|Drama|Limited) Series", 8), (r"Emmy", 6),
    (r"Australian Open|French Open|Roland Garros|Wimbledon|US Open", 128),
]
MOTIFS = [(re.compile(m, re.I), n) for m, n in EVENEMENTS]
POIDS, ECART_MAX = 0.25, 0.15
# 0.10.498 : saillance par famille, retenue sur le développement (questions jouées avant 2026) et confirmée une fois sur
# les questions de 2026 (registre/un-parmi-n-saillance.json) : sports d'équipe k = 2, récompenses et tennis k = 1.
SAILLANCE = {"equipe": 2.0, "recompense": 1.0, "tennis": 1.0}


def famille(n: int) -> str:
    return "recompense" if n in (5, 6, 8, 10) else ("tennis" if n == 128 else "equipe")


def n_concurrents(titre: str) -> int | None:
    if not GAGNER.search(titre) or AUTRES_FORMES.search(titre):
        return None
    for m, n in MOTIFS:
        if m.search(titre):
            return n
    return None


def estimer(titre: str, p_bot: float) -> dict | None:
    n = n_concurrents(titre)
    if n is None:
        return None
    k = SAILLANCE[famille(n)]
    pr = 1 - (1 - 1 / n) ** k
    lg = lambda v: math.log(min(max(v, .01), .99) / (1 - min(max(v, .01), .99)))
    p = 1 / (1 + math.exp(-((1 - POIDS) * lg(p_bot) + POIDS * lg(pr))))
    p = min(max(p, p_bot - ECART_MAX), p_bot + ECART_MAX)
    return {"n": n, "saillance": k, "p_regle": pr, "p_bot": p_bot, "p": p, "poids": POIDS, "ecart_max": ECART_MAX}
