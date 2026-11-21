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


# ---------------------------------------------------------------------------------------------------------------
# Taille d'échantillon nécessaire (décision de l'auteur du 2026-11-21, 12 h 53, d'après la fiche Risk Data Lab n° 06 :
# l'erreur de modèle croît comme N, le bruit d'échantillonnage comme √N ; au-delà de N* = (σ/|Δ|)², l'écart se voit).
# Lu pour un test : pour qu'un écart moyen Δ de perte log par question sorte de son intervalle, il faut environ
# ((z_niveau + z_puissance)·σ/Δ)² questions, σ étant l'écart-type de la différence de perte PAR QUESTION.
Z_90 = 1.6449      # intervalle à 90 % bilatéral (lecture principale à la manière de Metaculus)
Z_80 = 0.8416      # puissance 80 %


def sigma_par_question(differences: list[float]) -> float:
    """Écart-type de la différence de perte log par question (une valeur par question distincte)."""
    d = np.asarray(differences, dtype=float)
    return float(d.std(ddof=1)) if len(d) > 1 else float("nan")


def taille_necessaire(sigma: float, ecart: float, z: float = Z_90, z_puissance: float = Z_80) -> int:
    """Nombre de questions pour voir un écart moyen `ecart` (perte log) avec 80 % de chances, intervalle à 90 %."""
    return int(math.ceil(((z + z_puissance) * sigma / abs(ecart)) ** 2))


def ecart_detectable(sigma: float, n: int, z: float = Z_90, z_puissance: float = Z_80) -> float:
    """Plus petit écart moyen que n questions voient avec 80 % de chances."""
    return float((z + z_puissance) * sigma / math.sqrt(n))


def puissance(differences: list[float], ecarts=(0.005, 0.01, 0.02, 0.04)) -> dict:
    """Bilan pour un banc : σ mesuré, écart détectable à sa taille, questions nécessaires pour chaque écart visé."""
    s, n = sigma_par_question(differences), len(differences)
    return {"n": n, "sigma_par_question": round(s, 4), "ecart_detectable": round(ecart_detectable(s, n), 4),
            "questions_necessaires": {str(e): taille_necessaire(s, e) for e in ecarts}}


# ---------------------------------------------------------------------------------------------------------------
# Découpage temporel (piste LBS du 2026-11-21 ; déjà demandé par la référence Decker et Tresp) : un outil qui apprend
# des poids apprend sur le passé et se juge sur la suite, comme le tournoi. Fenêtre qui s'élargit.
def blocs_chronologiques(dates: list[str], k: int = 5, min_apprentissage: int = 20) -> list[tuple[list[int], list[int]]]:
    """Découpe les indices en k tranches chronologiques ; la tranche j est jugée par un modèle appris sur toutes les
    tranches antérieures (rien d'antérieur ou trop peu : tranche non jugée). Égalités de dates : même tranche."""
    ordre = sorted(range(len(dates)), key=lambda i: (dates[i], i))
    taille = math.ceil(len(ordre) / k) if ordre else 0
    tranches, cur = [], []
    for i in ordre:
        if len(cur) >= taille and dates[i] != dates[cur[-1]]:
            tranches.append(cur)
            cur = []
        cur.append(i)
    if cur:
        tranches.append(cur)
    out = []
    for j in range(1, len(tranches)):
        appris = [i for t in tranches[:j] for i in t]
        if len(appris) >= min_apprentissage:
            out.append((appris, tranches[j]))
    return out


def _decision_institution() -> dict:
    import decision_institution as di
    f = Path("registre") / "banc-decision-institution.jsonl"
    ls = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    ok = [x for x in ls if x.get("issue") in (0, 1) and x.get("x") is not None and not x.get("exclue")]
    X = np.array([[x["x"][i] for i in di.INDICATEURS] for x in ok], dtype=float)
    return simuler(X, np.array([x["p_S"] for x in ok]), sd=1.0)


def _puissances() -> dict:
    """σ par question mesuré sur nos bancs déjà passés (perte log, une ligne par question)."""
    import score_registre as sr
    import banc_jugement_alphabet as bja
    import decision_institution as di
    out = {}
    f = Path("registre") / "banc-decision-institution.jsonl"
    if f.exists():
        ls = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
        ok = [x for x in ls if x.get("issue") in (0, 1) and x.get("x") is not None and not x.get("exclue")]
        p = di.validation_croisee(ok)
        out["decision_institution_contre_semblables"] = puissance(
            [sr.log_score(q, x["issue"]) - sr.log_score(x["p_S"], x["issue"]) for x, q in zip(ok, p)])
    par_q = {}
    for x in bja.lignes():
        if x.get("p_M") is not None and x.get("p_A") is not None and not x.get("exclue") and x.get("issue") in (0, 1):
            par_q.setdefault(x["question_id"].split(":")[1], []).append(
                sr.log_score(x["p_M"], x["issue"]) - sr.log_score(x["p_A"], x["issue"]))
    if par_q:
        out["M_contre_A"] = puissance([float(np.mean(v)) for v in par_q.values()])
    return out


if __name__ == "__main__":
    r = _decision_institution()
    print(json.dumps(r, ensure_ascii=False, indent=1))
    print(json.dumps({"puissance": _puissances()}, ensure_ascii=False, indent=1))
    sys.exit(0)
