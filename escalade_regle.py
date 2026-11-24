"""Brique « échelle de l'escalade » branchée dans le bot (0.10.497 ; décision de l'auteur du 2026-11-24, 15 h 40).

Procédure fixée avant calcul et passée une fois : mise_au_point/echelle_escalade.py, résultat registre/echelle-escalade.json
(66 questions, 28 groupes de pays ; chaque groupe mis de côté : classe 0,494, référence 0,516, mélange plafonné 0,505 ;
critère de branchement atteint). Les mêmes règles de lecture qu'à l'évaluation.
Taux appris sur les 66 questions, tirés vers la moyenne (poids 5) : acte LOURD (invasion, opération terrestre, blocus,
quarantaine, occupation, guerre) 2 oui sur 26 ; acte LÉGER (frappe, attaque, action militaire, accrochage) 11 sur 40 ;
moyenne 13 sur 66. Mélange d'un quart avec la prévision du bot, déplacement plafonné à 15 points.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "mise_au_point"))
import evenements_regle as er  # noqa: E402
from echelle_escalade import CONFLIT, LOURD, FIN  # noqa: E402

MOY = 13 / 66
TAUX = {"lourd": (2 + 5 * MOY) / (26 + 5), "leger": (11 + 5 * MOY) / (40 + 5)}
POIDS, ECART_MAX = 0.25, 0.15


def classe(titre: str) -> str | None:
    if not CONFLIT.search(titre) or er.NON_ETATIQUES.search(titre) or FIN.search(titre) or not er.pays(titre):
        return None
    return "lourd" if LOURD.search(titre) else "leger"


def estimer(titre: str, p_bot: float) -> dict | None:
    c = classe(titre)
    if c is None:
        return None
    lg = lambda v: math.log(min(max(v, .01), .99) / (1 - min(max(v, .01), .99)))
    p = 1 / (1 + math.exp(-((1 - POIDS) * lg(p_bot) + POIDS * lg(TAUX[c]))))
    p = min(max(p, p_bot - ECART_MAX), p_bot + ECART_MAX)
    return {"classe": c, "p_regle": TAUX[c], "p_bot": p_bot, "p": p, "poids": POIDS, "ecart_max": ECART_MAX}
