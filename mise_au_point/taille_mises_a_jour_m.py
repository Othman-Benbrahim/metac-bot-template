"""Taille des mises à jour de M (preenregistrements/taille-mises-a-jour-m.md, piste « reverse Bayes » de Learning
Bayesian Statistics, décision de l'auteur du 2026-11-21, 12 h 53). Aucun appel de modèle : banc de M existant.

M part du taux des semblables p_B et s'en écarte. On demande si cet écart est trop grand ou trop petit :
    p_k = σ( logit(p_B) + k · (logit(p_M) − logit(p_B)) )
k = 1 : M tel quel ; k < 1 : M bouge trop ; k > 1 : pas assez. Un seul nombre, appris sur les questions passées
(fenêtre qui s'élargit, verification_a_priori.blocs_chronologiques), jugé sur les suivantes ; une ligne par question
(son premier jeu), pour qu'une question ne soit jamais à la fois apprise et jugée.

    python mise_au_point/taille_mises_a_jour_m.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import banc_jugement_alphabet as bja
import score_registre as sr
import verification_a_priori as va

SORTIE = Path("registre") / "mise-au-point" / "taille-mises-a-jour-m.json"
GRILLE = np.round(np.arange(0.0, 2.01, 0.05), 2)
K_TRANCHES, MIN_APPRENTISSAGE = 5, 20


def _logit(p: float) -> float:
    p = min(0.99, max(0.01, p))
    return math.log(p / (1 - p))


def p_k(x: dict, k: float) -> float:
    z = _logit(x["p_B"]) + k * (_logit(x["p_M"]) - _logit(x["p_B"]))
    return 1 / (1 + math.exp(-z))


def meilleur_k(xs: list[dict]) -> float:
    pertes = [sum(sr.log_score(p_k(x, k), x["issue"]) for x in xs) for k in GRILLE]
    return float(GRILLE[int(np.argmin(pertes))])


def une_par_question(ls: list[dict]) -> list[dict]:
    par = {}
    for x in sorted(ls, key=lambda x: x["jeu"]):
        if x.get("p_M") is None or x.get("p_B") is None or x.get("exclue") or x.get("issue") not in (0, 1):
            continue
        par.setdefault(x["question_id"].split(":")[1], x)          # le premier jeu de chaque question
    return list(par.values())


def evaluer(xs: list[dict], tirages: int = 5000) -> dict:
    blocs = va.blocs_chronologiques([x["jeu"] for x in xs], K_TRANCHES, MIN_APPRENTISSAGE)
    juges, ks = [], []
    for appris, juge in blocs:
        k = meilleur_k([xs[i] for i in appris])
        ks.append({"jusqu_au": max(xs[i]["jeu"] for i in appris), "k": k, "n_appris": len(appris), "n_juge": len(juge)})
        for i in juge:
            juges.append((sr.log_score(p_k(xs[i], k), xs[i]["issue"]), sr.log_score(xs[i]["p_M"], xs[i]["issue"])))
    if not juges:
        return {"n_juge": 0}
    d = np.array([a - b for a, b in juges])
    rng = np.random.default_rng(sum(map(ord, "taille-mises-a-jour-m")))
    boot = np.array([d[rng.integers(0, len(d), len(d))].mean() for _ in range(tirages)])
    lo, hi = np.percentile(boot, [5, 95])
    return {"n_juge": len(d), "perte_k": round(float(np.mean([a for a, _ in juges])), 4),
            "perte_M": round(float(np.mean([b for _, b in juges])), 4), "ecart": round(float(d.mean()), 4),
            "intervalle_90": [round(float(lo), 4), round(float(hi), 4)], "adopte": bool(hi < 0), "k_par_tranche": ks,
            "puissance": va.puissance(d.tolist())}


def principal() -> int:
    xs = une_par_question(bja.lignes())
    r = {"questions": len(xs), "jugement": evaluer(xs),
         "descriptif_k_sur_tout": meilleur_k(xs),
         "note": "écart = perte avec k − perte de M (négatif = k aide) ; adopté si l'intervalle à 90 % est entièrement sous 0"}
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
