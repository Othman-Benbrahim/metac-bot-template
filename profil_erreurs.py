"""Profil des erreurs d'une prévision (bot 0.10.265) : d'où vient un gain, et ce qu'il coûte.

Décision d'auteur du 2026-11-18, 14 h 07 (« oui, et s'il y a des modifications à faire, fais-le »), après la lecture
de Zhang et al. (NeurIPS 2026 : le classement de deux modèles change selon que le score pèse les ratés ou les fausses
alertes) et une erreur de Claude le matin même : juger M sur les seules questions finies en « oui » (conditionner sur
l'issue). Règle en code : tout bilan de banc de jugement affiche, à côté de la perte log, les deux côtés à la fois.

Pour une liste de (p, issue) :
- perte log totale, puis sa part venue des « oui » et sa part venue des « non » (les deux s'additionnent) ;
- ratés : « oui » prévus sous 30 % ; fausses alertes : « non » prévus au-dessus de 50 % ;
- Brier et sa décomposition de Murphy (10 classes) : fiabilité (calibration, plus bas = mieux), résolution
  (discrimination, plus haut = mieux), incertitude (propre aux questions, la même pour tous).
"""
from __future__ import annotations

import math

SEUIL_RATE, SEUIL_ALERTE = 0.30, 0.50


def _pl(p: float, y: int) -> float:
    p = min(0.99, max(0.01, float(p)))
    return -math.log(p if y else 1 - p)


def profil(paires: list[tuple[float, int]]) -> dict:
    n = len(paires)
    if not n:
        return {"n": 0}
    oui = [p for p, y in paires if y == 1]
    non = [p for p, y in paires if y == 0]
    base = len(oui) / n
    classes: dict[int, list[tuple[float, int]]] = {}
    for p, y in paires:
        classes.setdefault(min(9, int(float(p) * 10)), []).append((float(p), y))
    fiab = sum(len(c) * (sum(p for p, _ in c) / len(c) - sum(y for _, y in c) / len(c)) ** 2 for c in classes.values()) / n
    resol = sum(len(c) * (sum(y for _, y in c) / len(c) - base) ** 2 for c in classes.values()) / n
    return {"n": n, "oui": len(oui),
            "perte_log": round(sum(_pl(p, y) for p, y in paires) / n, 4),
            "perte_venue_des_oui": round(sum(_pl(p, 1) for p in oui) / n, 4),
            "perte_venue_des_non": round(sum(_pl(p, 0) for p in non) / n, 4),
            "rates_oui_sous_30": sum(1 for p in oui if p < SEUIL_RATE),
            "fausses_alertes_non_sur_50": sum(1 for p in non if p > SEUIL_ALERTE),
            "brier": round(sum((float(p) - y) ** 2 for p, y in paires) / n, 4),
            "fiabilite_plus_bas_mieux": round(fiab, 4), "resolution_plus_haut_mieux": round(resol, 4),
            "incertitude": round(base * (1 - base), 4)}


def profils(lignes: list[dict], bras: dict[str, str]) -> dict:
    """{nom: profil} pour chaque bras (nom → clé de probabilité) sur les MÊMES questions (celles où tous existent)."""
    ok = [x for x in lignes if x.get("issue") in (0, 1) and all(x.get(k) is not None for k in bras.values())]
    return {nom: profil([(x[k], x["issue"]) for x in ok]) for nom, k in bras.items()}


def unites(lignes: list[dict]) -> dict:
    """0.10.267 : garde-fou automatique de tout bilan de jugement. Une même question peut revenir à plusieurs dates
    de jeu ; le nombre qui compte pour la preuve est celui des QUESTIONS DISTINCTES, pas des lignes. Erreur de Claude
    du 2026-11-17/18 : « 309 questions » qui n'étaient que 119, intervalles et examens des cartes gonflés."""
    qs = [":".join(str(x["question_id"]).split(":")[:2]) for x in lignes if x.get("question_id")]
    d = len(set(qs))
    oui = len({q for q, x in zip(qs, lignes) if x.get("issue") == 1})
    return {"lignes": len(lignes), "questions_distinctes": d, "questions_oui_distinctes": oui,
            "alerte": (f"{len(lignes)} lignes pour {d} questions distinctes : la preuve repose sur {d}, pas sur "
                       f"{len(lignes)} (intervalles par question)") if d and len(lignes) > 1.1 * d else None}
