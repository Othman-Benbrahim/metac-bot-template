"""Simulation a priori d'un outil qui apprend des poids, AVANT tout banc payant (décision de l'auteur du 2026-11-21,
12 h 31 : « ça ne coûte rien de l'appliquer... Fais-le »). Aucun appel de modèle : quelques tirages en Python.

Idée (démarche bayésienne, Gelman et al. ; exposé d'A. Andorra, Princeton, sept. 2026) : on tire des poids dans l'a
priori, AVANT d'avoir vu une seule issue, et on regarde quelles prévisions l'outil produirait. Un a priori qui semble
prudent (normal (0, 1) sur chaque poids) peut, une fois les indicateurs additionnés, déplacer la prévision très loin du
taux de départ sans aucune donnée. Avec une centaine de questions, ce déplacement non justifié devient du bruit.

Cas d'origine : l'outil « décision d'institution » (6 indicateurs, a priori normal (0, 1), 94 questions) a fait pire que
le taux des semblables (0,649 contre 0,622). Cette vérification l'aurait signalé avant le run (voir __main__).

Ce que la fonction rend, pour un a priori donné :
- `decalage_median` : déplacement typique du logit par rapport au taux de départ (0,5 logit ≈ ±12 points autour de 50 %) ;
- `extremes` : part des prévisions sous 5 % ou au-dessus de 95 %, contre la même part pour le taux de départ seul ;
- `sd_conseille` : le plus grand écart-type a priori qui garde le déplacement médian sous la cible.
Alerte si le déplacement médian dépasse la cible ou si les extrêmes gagnent plus de 10 points.

    python verification_a_priori.py            # appliqué au banc « décision d'institution »
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

CIBLE_LOGIT = 0.5          # déplacement médian toléré sans donnée (≈ ±12 points autour de 50 %)
HAUSSE_EXTREMES = 0.10     # hausse tolérée de la part des prévisions sous 5 % ou au-dessus de 95 %
_Z_MEDIANE = 0.6745        # médiane de |N(0, 1)|


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 0.02, 0.98)
    return np.log(p / (1 - p))


def sd_conseille(X: np.ndarray, cible: float = CIBLE_LOGIT) -> float:
    """Plus grand sd tel que la médiane (sur les questions) du déplacement médian |x·β| reste sous la cible.
    Pour une question, x·β ~ N(0, sd²‖x‖²) : déplacement médian = 0,6745·sd·‖x‖."""
    normes = np.linalg.norm(np.asarray(X, dtype=float), axis=1)
    normes = normes[normes > 0]
    if not len(normes):
        return float("inf")
    return float(cible / (_Z_MEDIANE * np.median(normes)))


def simuler(X: np.ndarray, p_depart: np.ndarray, sd: float = 1.0, tirages: int = 4000, graine: int = 0,
            cible: float = CIBLE_LOGIT) -> dict:
    """X : indicateurs (questions × indicateurs), réels ou supposés ; p_depart : taux de départ par question."""
    X = np.asarray(X, dtype=float)
    d = _logit(np.asarray(p_depart, dtype=float))
    rng = np.random.default_rng(graine)
    B = rng.normal(0.0, sd, size=(tirages, X.shape[1]))
    dec = X @ B.T                                          # questions × tirages
    p = 1 / (1 + np.exp(-(d[:, None] + dec)))
    ext = lambda q: float(np.mean((q < 0.05) | (q > 0.95)))
    med = float(np.median(np.abs(dec)))
    e0, e1 = ext(1 / (1 + np.exp(-d))), ext(p)
    sdc = sd_conseille(X, cible)
    alerte = med > cible or (e1 - e0) > HAUSSE_EXTREMES
    return {"sd": sd, "questions": int(X.shape[0]), "indicateurs": int(X.shape[1]),
            "decalage_median_logit": round(med, 3), "extremes_depart": round(e0, 3), "extremes_outil": round(e1, 3),
            "sd_conseille": round(sdc, 3) if math.isfinite(sdc) else None, "alerte": bool(alerte),
            "lecture": (f"sans aucune donnée, l'a priori déplace la prévision de {med:.2f} logit en médiane "
                        f"(cible {cible}) ; extrêmes {e0:.0%} → {e1:.0%}. "
                        + (f"ALERTE : a priori trop large pour ce nombre d'indicateurs ; sd conseillé ≈ {sdc:.2f}."
                           if alerte else "A priori acceptable."))}


def _decision_institution() -> dict:
    import decision_institution as di
    f = Path("registre") / "banc-decision-institution.jsonl"
    ls = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    ok = [x for x in ls if x.get("issue") in (0, 1) and x.get("x") is not None and not x.get("exclue")]
    X = np.array([[x["x"][i] for i in di.INDICATEURS] for x in ok], dtype=float)
    return simuler(X, np.array([x["p_S"] for x in ok]), sd=1.0)


if __name__ == "__main__":
    r = _decision_institution()
    print(json.dumps(r, ensure_ascii=False, indent=1))
    sys.exit(0)
