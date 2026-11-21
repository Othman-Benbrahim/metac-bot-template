"""Niveau et tendance par filtre de Kalman contre le modèle actuel des indicateurs lents
(preenregistrements/kalman-indicateurs.md ; piste Learning Bayesian Statistics, épisode 124, décision de l'auteur du
2026-11-21, 12 h 53). Aucun appel de modèle. e-Stat : This service uses API functions from e-Stat, however its
contents are not guaranteed by government.

Modèle actuel : prochaine valeur = dernière + un des 36 derniers écarts (distribution empirique).
Concurrent : modèle « niveau et tendance locale » (deux états, trois variances estimées par maximum de vraisemblance
sur les 60 dernières valeurs), prévision gaussienne à un pas.
Comparaison : CRPS (score continu de probabilité classée, plus bas = mieux), règle propre qui juge toute la
distribution ; couverture des intervalles à 80 % et 60 % en description.

    python mise_au_point/kalman_indicateurs_essai.py
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SORTIE = Path("registre") / "mise-au-point" / "kalman-indicateurs.json"
FENETRE_KALMAN, FENETRE_EMPIRIQUE, DEBUT = 60, 36, 19


def filtre(y: np.ndarray, log_var: np.ndarray) -> tuple[float, float, float]:
    """Niveau et tendance locale. Rend (log-vraisemblance, moyenne prévue au pas suivant, variance prévue)."""
    h, q_niv, q_pente = np.exp(log_var)
    T = np.array([[1.0, 1.0], [0.0, 1.0]])
    Q = np.diag([q_niv, q_pente])
    a = np.array([y[0], 0.0])
    P = np.eye(2) * 1e6
    ll = 0.0
    for t, yt in enumerate(y):
        f = P[0, 0] + h
        v = yt - a[0]
        if t >= 2:                                  # les deux premières observations initialisent (diffus)
            ll += -0.5 * (math.log(2 * math.pi * f) + v * v / f)
        K = P[:, 0] / f
        a = a + K * v
        P = P - np.outer(K, P[0, :])
        a = T @ a
        P = T @ P @ T.T + Q
    return ll, float(a[0]), float(P[0, 0] + h)


def prevision_kalman(hist: list[float]) -> tuple[float, float]:
    y = np.asarray(hist[-FENETRE_KALMAN:], dtype=float)
    v0 = max(float(np.var(np.diff(y))), 1e-6)
    depart = np.log([v0 / 2, v0 / 2, v0 / 100])
    r = minimize(lambda lv: -filtre(y, lv)[0], depart, method="Nelder-Mead",
                 options={"maxiter": 400, "xatol": 1e-3, "fatol": 1e-4})
    _, m, var = filtre(y, r.x)
    return m, math.sqrt(max(var, 1e-12))


def crps_gauss(m: float, s: float, x: float) -> float:
    z = (x - m) / s
    return s * (z * (2 * norm.cdf(z) - 1) + 2 * norm.pdf(z) - 1 / math.sqrt(math.pi))


def crps_empirique(points: np.ndarray, x: float) -> float:
    """CRPS d'une distribution empirique : E|X − x| − ½ E|X − X'|."""
    p = np.sort(points)
    n = len(p)
    e1 = np.abs(p - x).mean()
    e2 = (2 * np.arange(1, n + 1) - n - 1) @ p / (n * n)       # ½ E|X − X'| sur échantillon trié
    return float(e1 - e2)


def _q(p: np.ndarray, a: float) -> float:
    i = a * (len(p) - 1)
    lo, hi = int(i), min(len(p) - 1, int(i) + 1)
    return float(p[lo] + (p[hi] - p[lo]) * (i - lo))


def comparer(x: list[float], garde=lambda t: True) -> list[dict]:
    out = []
    for t in range(max(DEBUT, FENETRE_KALMAN // 2), len(x) - 1):
        if not garde(t):
            continue
        v = x[max(0, t - FENETRE_EMPIRIQUE): t + 1]
        pas = np.diff(v)
        if len(pas) < FENETRE_EMPIRIQUE // 2:
            continue
        emp = np.sort(x[t] + pas)
        m, s = prevision_kalman(x[: t + 1])
        y = x[t + 1]
        out.append({"t": t, "crps_actuel": crps_empirique(emp, y), "crps_kalman": crps_gauss(m, s, y),
                    "c80_actuel": _q(emp, .1) <= y <= _q(emp, .9), "c80_kalman": abs(y - m) <= 1.2816 * s,
                    "c60_actuel": _q(emp, .2) <= y <= _q(emp, .8), "c60_kalman": abs(y - m) <= 0.8416 * s})
    return out


def resumer(ls: list[dict], blocs: list[int], tirages: int = 4000) -> dict:
    """Écart relatif de CRPS (Kalman/actuel − 1), intervalle à 90 % par bootstrap par blocs de 12 mois de chaque série."""
    a = np.array([l["crps_actuel"] for l in ls])
    k = np.array([l["crps_kalman"] for l in ls])
    b = np.asarray(blocs)
    ids = np.unique(b)
    rng = np.random.default_rng(sum(map(ord, "kalman-indicateurs")))
    boot = []
    for _ in range(tirages):
        tire = rng.choice(ids, len(ids))
        idx = np.concatenate([np.nonzero(b == i)[0] for i in tire])
        boot.append(k[idx].sum() / a[idx].sum() - 1)
    lo, hi = np.percentile(boot, [5, 95])
    n = len(ls)
    return {"n": n, "crps_actuel": round(float(a.mean()), 4), "crps_kalman": round(float(k.mean()), 4),
            "ecart_relatif": round(float(k.sum() / a.sum() - 1), 4), "intervalle_90": [round(float(lo), 4), round(float(hi), 4)],
            "adopte": bool(hi < 0),
            "couverture_80": {"actuel": round(sum(l["c80_actuel"] for l in ls) / n, 3), "kalman": round(sum(l["c80_kalman"] for l in ls) / n, 3)},
            "couverture_60": {"actuel": round(sum(l["c60_actuel"] for l in ls) / n, 3), "kalman": round(sum(l["c60_kalman"] for l in ls) / n, 3)}}


def principal() -> int:
    s = {}
    for r in csv.DictReader(open("registre/fred.csv", encoding="utf-8")):
        s.setdefault(r["serie"], []).append((r["jour"], float(r["valeur"])))
    series = {"UNRATE": [v for _, v in sorted(s["UNRATE"])], "UMCSENT": [v for _, v in sorted(s["UMCSENT"])]}
    for cle in ("CPIAUCSL", "CPILFESL"):
        x = [v for _, v in sorted(s[cle])]
        series[cle] = [100 * (x[i] / x[i - 12] - 1) for i in range(12, len(x))]
    tk = sorted((r["mois"], float(r["inflation_hors_frais_sur_un_an"]))
                for r in csv.DictReader(open("registre/estat-tokyo-cpi.csv", encoding="utf-8")) if r["base"] == "2025")
    mois = [m for m, _ in tk]
    tous, blocs, par = [], [], {}
    for j, (nom, x, garde) in enumerate([(k, v, lambda t: True) for k, v in series.items()] +
                                        [("TOKYO", [v for _, v in tk], lambda t: "2006-01" <= mois[t] <= "2026-09")]):
        ls = comparer(x, garde)
        par[nom] = resumer(ls, [l["t"] // 12 for l in ls]) if len(ls) > 24 else {"n": len(ls)}
        tous += ls
        blocs += [j * 10000 + l["t"] // 12 for l in ls]
    r = {"decision_ensemble": resumer(tous, blocs), "par_serie": par,
         "note": "écart relatif de CRPS Kalman/actuel − 1 (négatif = Kalman meilleur) ; adopté si l'intervalle à 90 % est entièrement sous 0 ; e-Stat : contenu non garanti par le gouvernement"}
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
