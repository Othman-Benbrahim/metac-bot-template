"""Outils communs aux deux bancs « correction finale à porte » (idée de GraFT, 0.10.305).

p' = σ(logit(base) + α·signal), α appris sur une grille SANS la question jugée (toutes ses lignes écartées).
À égalité de perte, le plus petit |α| l'emporte (retour vers la base).
"""
from __future__ import annotations

import banc_attention_gdelt as ba


def q(qid: str) -> str:
    return ":".join(qid.split(":")[:2])


def loo_porte(ls: list[dict], base: str, signal: str, grille: list[float]) -> tuple[list[float], float, dict]:
    """(p' par ligne, α appris sur tout, α appris par question écartée)."""
    pertes = [[ba._pl(ba.ajuste_tendance(x[base], x[signal], a), x["issue"]) for a in grille] for x in ls]
    tot = [sum(col) for col in zip(*pertes)]
    par_q: dict[str, list[float]] = {}
    for x, pq in zip(ls, pertes):
        acc = par_q.setdefault(q(x["question_id"]), [0.0] * len(grille))
        for i, v in enumerate(pq):
            acc[i] += v
    alpha_q = {k: grille[min(range(len(grille)), key=lambda i: (tot[i] - v[i], abs(grille[i])))] for k, v in par_q.items()}
    out = [ba.ajuste_tendance(x[base], x[signal], alpha_q[q(x["question_id"])]) for x in ls]
    return out, grille[min(range(len(grille)), key=lambda i: (tot[i], abs(grille[i])))], alpha_q


def perte(ls: list[dict], cle: str | None = None, ps: list[float] | None = None) -> float | None:
    if not ls:
        return None
    vals = ps if ps is not None else [x[cle] for x in ls]
    return round(sum(ba._pl(p, x["issue"]) for x, p in zip(ls, vals)) / len(ls), 4)
