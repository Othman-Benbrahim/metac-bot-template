"""Étape 2 (cohérence) : les calculs du moteur et du bot, recoupés par des bibliothèques indépendantes (0.10.69).

Rien n'est corrigé ici et rien n'est écrit au registre : chaque calcul maison est mis en face de son équivalent publié,
sur les MÊMES entrées, et l'écart est rapporté. Un écart n'est pas forcément une erreur (convention différente) ; il
est listé pour décision d'auteur.

  1. Scores : Brier et perte log (score_registre, moteur.perte_log) contre scikit-learn et properscoring.
  2. Décomposition de Murphy (moteur.murphy, score_registre.partition_murphy) contre un calcul sur les bacs de
     scikit-learn (calibration_curve).
  3. Intervalles : Wilson (moteur) contre statsmodels ; quantiles Beta (moteur, bissection sur ibeta) contre scipy.
  4. Recalibration logistique (ajuster_recalibration, ajuster_decalage) contre statsmodels (Logit, GLM à offset).
  5. AR(1) du compte de taux de base (alphabet_compte._ar1) contre statsmodels (OLS, Dickey-Fuller) et arch (ARX) ;
     seuils −2,5 / −3,5 du compte contre les valeurs critiques de Dickey-Fuller.
  6. Inférence séquentielle (e_valeur, intervalle_sequentiel, moteur.sequence_confiance) contre confseq
     (betting_cs, Waudby-Smith et Ramdas) : couverture simulée à tout instant, largeur comparée.

Dépendances (hors du bot, à installer à part) : scikit-learn, properscoring, statsmodels, arch, scipy, confseq.
confseq 0.0.x ne se compile plus tel quel (pybind11 ~2.6 et np.float_ de NumPy 1) : depuis ses sources, remplacer
pybind11~=2.6.0 par pybind11>=2.11 dans pyproject.toml et np.float_ par np.float64 dans src/confseq/*.py.

    python verif_moteur.py [--simulations 400] [--json sortie.json]
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import warnings

import numpy as np

import alphabet_compte as ac
import alphabet_pipeline as ap
import alphabet_retro as ar
import score_registre as sr

warnings.filterwarnings("ignore")
TOL = 1e-6


def paires_registre() -> dict[str, list[tuple[float, int]]]:
    f = ap.REGISTRE / ar.RETRO
    L = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()] if f.is_file() else []
    out = {"B": [], "C": []}
    for x in L:
        y = x.get("issue")
        if y not in (0, 1):
            continue
        if x.get("p_B") is not None:
            out["B"].append((float(x["p_B"]), int(y)))
        pc = x.get("p_C") if x.get("p_C") is not None else (x.get("exploratoire") or {}).get("p_C")
        if pc is not None:
            out["C"].append((float(pc), int(y)))
    return out


def ecart(a, b) -> float:
    return float(np.max(np.abs(np.asarray(a, float) - np.asarray(b, float))))


def verdict(e: float, tol: float = TOL) -> str:
    return "identique" if e <= tol else "ÉCART"


# 1. Scores ---------------------------------------------------------------------------------------------------------
def scores(paires: dict) -> dict:
    from properscoring import brier_score
    from sklearn.metrics import brier_score_loss, log_loss
    M = ap._moteur()
    out = {}
    for bras, L in paires.items():
        if not L:
            continue
        p = np.array([a for a, _ in L])
        y = np.array([b for _, b in L])
        b_maison = np.mean([sr.brier(a, b) for a, b in L])
        b_sk = brier_score_loss(y, p)
        b_ps = float(np.mean(brier_score(y, p)))
        l_maison = np.mean([sr.log_score(a, b) for a, b in L])
        pb = np.array([ap.borner(a) for a in p])           # même bornage que le bot
        l_sk = log_loss(y, pb, labels=[0, 1])
        # moteur.perte_log : une question à la fois (forme « items »)
        l_mot = np.mean([M.perte_log([{"id": 1, "x": a}], "x", {1: {"issue": b}}) for a, b in L])
        l_mot_ref = np.mean([-math.log(a if b == 1 else 1 - a) for a, b in L])
        out[bras] = {"n": len(L),
                     "brier": {"maison": b_maison, "sklearn": b_sk, "properscoring": b_ps,
                               "verdict": verdict(max(abs(b_maison - b_sk), abs(b_maison - b_ps)))},
                     "log_bot": {"maison": l_maison, "sklearn": l_sk, "verdict": verdict(abs(l_maison - l_sk))},
                     "log_moteur": {"maison": l_mot, "reference_non_bornee": l_mot_ref,
                                    "verdict": verdict(abs(l_mot - l_mot_ref))}}
    return out


# 2. Murphy ---------------------------------------------------------------------------------------------------------
def murphy_ref(L: list[tuple[float, int]], bacs: int) -> dict:
    """Décomposition sur bacs de largeur égale, bacs et fréquences pris à scikit-learn (calibration_curve)."""
    from sklearn.calibration import calibration_curve
    p = np.array([a for a, _ in L])
    y = np.array([b for _, b in L])
    # calibration_curve classe par np.searchsorted sur des bords [0, 1/bacs, …, 1] : même partition que int(p·bacs)
    # sauf aux bords exacts ; on recompte les effectifs avec la même règle que scikit-learn
    vrai, pred = calibration_curve(y, p, n_bins=bacs, strategy="uniform")
    bords = np.linspace(0.0, 1.0, bacs + 1)
    ids = np.searchsorted(bords[1:-1], p)
    cnt = np.bincount(ids, minlength=bacs)
    cnt = cnt[cnt > 0]
    n, o = len(y), y.mean()
    return {"fiabilite": float(np.sum(cnt * (pred - vrai) ** 2) / n),
            "resolution": float(np.sum(cnt * (vrai - o) ** 2) / n), "incertitude": float(o * (1 - o))}


def murphy(paires: dict) -> dict:
    M = ap._moteur()
    out = {}
    for bras, L in paires.items():
        if len(L) < 5:
            continue
        m = M.murphy(L)
        r10 = murphy_ref(L, 10)
        s5 = sr.partition_murphy(L, 5)
        r5 = murphy_ref(L, 5)
        e10 = max(abs(m["fiabilite"] - r10["fiabilite"]), abs(m["resolution"] - r10["resolution"]),
                  abs(m["incertitude"] - r10["incertitude"]))
        e5 = max(abs(s5["fiabilite"] - r5["fiabilite"]), abs(s5["resolution"] - r5["resolution"]))
        # convention des bords : le moteur met p = 0,5 dans [0,5 ; 0,6[ (int(p·10)), scikit-learn dans [0,4 ; 0,5] ;
        # on rejoue scikit-learn avec la règle du moteur (p décalé d'un epsilon vers le haut)
        p = np.array([a for a, _ in L])
        sur_bord = int(np.sum(np.minimum(9, (p * 10).astype(int)) != np.searchsorted(np.linspace(0, 1, 11)[1:-1], p)))
        r10b = murphy_ref([(min(1.0, a + 1e-12), b) for a, b in L], 10)
        e10b = max(abs(m["fiabilite"] - r10b["fiabilite"]), abs(m["resolution"] - r10b["resolution"]))
        out[bras] = {"moteur_10_bacs": {k: m[k] for k in ("fiabilite", "resolution", "incertitude")},
                     "sklearn_10_bacs": r10, "verdict_moteur_brut": verdict(e10),
                     "p_sur_un_bord": sur_bord, "sklearn_10_bacs_regle_du_moteur": r10b,
                     "verdict_moteur_meme_regle": verdict(e10b),
                     "score_registre_5_bacs": {k: s5[k] for k in ("fiabilite", "resolution")},
                     "sklearn_5_bacs": r5, "verdict_score_registre": verdict(e5, 5e-5)}   # arrondi à 4 décimales
    return out


# 3. Intervalles ----------------------------------------------------------------------------------------------------
def intervalles() -> dict:
    from scipy.stats import beta
    from statsmodels.stats.proportion import proportion_confint
    M = ap._moteur()
    ew = 0.0
    for n in (1, 2, 5, 10, 30, 100, 1000):
        for k in range(0, n + 1, max(1, n // 10)):
            a = M.wilson(k, n)
            lo, hi = proportion_confint(k, n, alpha=0.05, method="wilson")
            ew = max(ew, ecart(a, [lo, hi]))
    eb = eq = 0.0
    for a_ in (0.3, 0.5, 1.0, 2.5, 7.0, 40.0):
        for b_ in (0.3, 0.5, 1.0, 2.5, 7.0, 40.0):
            for x in (0.01, 0.1, 0.37, 0.5, 0.82, 0.99):
                eb = max(eb, abs(M.ibeta(a_, b_, x) - beta.cdf(x, a_, b_)))
            for q in (0.025, 0.1, 0.5, 0.9, 0.975):
                eq = max(eq, abs(M.beta_quantile(a_, b_, q) - beta.ppf(q, a_, b_)))
    k_, niv = M.P["k"], M.P["intervalle"]
    ei = 0.0
    for nE, nA, p0 in ((0, 3, 0.2), (2, 5, 0.4), (7, 10, 0.5), (1, 40, 0.05)):
        iv = M.intervalle_beta(nE, nA, p0)
        a_, b_ = nE + k_ * p0, nA - nE + k_ * (1 - p0)
        q = (1 - niv) / 2
        ei = max(ei, ecart(iv, [beta.ppf(q, a_, b_), beta.ppf(1 - q, a_, b_)]))
    return {"wilson_vs_statsmodels": {"ecart_max": ew, "verdict": verdict(ew)},
            "ibeta_vs_scipy": {"ecart_max": eb, "verdict": verdict(eb, 1e-8)},
            "beta_quantile_vs_scipy": {"ecart_max": eq, "verdict": verdict(eq, 1e-8)},
            "intervalle_beta_vs_scipy": {"ecart_max": ei, "verdict": verdict(ei, 1e-6),
                                        "note": "proba() du moteur borne le résultat : un écart aux extrêmes vient de là"}}


# 4. Recalibration --------------------------------------------------------------------------------------------------
def recalibration(paires: dict) -> dict:
    import statsmodels.api as sm
    out = {}
    for bras, L in paires.items():
        if len(L) < 10:
            continue
        x = np.array([sr._logit(p) for p, _ in L])
        y = np.array([b for _, b in L])
        a, b = sr.ajuster_recalibration(L, rappel=1e-9)            # rappel ~0 : maximum de vraisemblance pur
        fit = sm.Logit(y, sm.add_constant(x)).fit(disp=0)
        e1 = max(abs(a - fit.params[1]), abs(b - fit.params[0]))
        d = sr.ajuster_decalage(L, rappel=1e-9)
        g = sm.GLM(y, np.ones((len(y), 1)), family=sm.families.Binomial(), offset=x).fit()
        e2 = abs(d - g.params[0])
        # avec le rappel réel (1.0) : statsmodels pénalisé L2 centré sur (1, 0) n'existe pas tel quel ; on reformule
        # en pénalisant (a − 1, b) via un décalage de variable : logit = (a−1)·x + b + x, offset = x
        a1, b1 = sr.ajuster_recalibration(L, rappel=1.0)
        g2 = sm.GLM(y, sm.add_constant(x), family=sm.families.Binomial(), offset=x).fit_regularized(
            alpha=1.0 / len(y), L1_wt=0.0)  # objectif −llf/n + alpha/2·‖β‖² ⇒ rappel/2·‖β‖² en somme
        e3 = max(abs((a1 - 1) - g2.params[1]), abs(b1 - g2.params[0]))
        out[bras] = {"n": len(L),
                     "pente_et_constante": {"maison": [a, b], "statsmodels_Logit": [fit.params[1], fit.params[0]],
                                            "verdict": verdict(e1, 1e-5)},
                     "decalage_seul": {"maison": d, "statsmodels_GLM_offset": g.params[0], "verdict": verdict(e2, 1e-5)},
                     "avec_rappel_1": {"maison": [a1, b1], "statsmodels_ridge": [1 + g2.params[1], g2.params[0]],
                                       "verdict": verdict(e3, 1e-3)}}
    return out


# 5. AR(1) du taux de base --------------------------------------------------------------------------------------------
def ar1(simulations: int) -> dict:
    import statsmodels.api as sm
    from arch.univariate import ARX
    from statsmodels.tsa.stattools import adfuller
    rnd = np.random.default_rng(7)
    ecarts_b, ecarts_t, ecarts_arch = [], [], []
    for phi in (0.5, 0.8, 0.95):
        for _ in range(5):
            y = [0.0]
            for _ in range(200):
                y.append(1.0 + phi * y[-1] + rnd.normal())
            y = list(np.array(y) - 0)
            garde = list(range(len(y) - 1))
            # _ar1 rend None si t ≥ −2,5 ; on lit la régression elle-même par la même formule
            xs = np.array(y[:-1])
            ds = np.diff(y)
            ols = sm.OLS(ds, sm.add_constant(xs)).fit()
            r = ac._ar1(y, garde)
            if r is not None:
                ecarts_b.append(abs(r[1] - ols.params[1]))
                ecarts_t.append(abs(r[3] - ols.tvalues[1]))
            am = ARX(np.array(y), lags=1, constant=True).fit(disp="off")
            ecarts_arch.append(abs((am.params.iloc[1] - 1) - ols.params[1]))
    # seuils du compte contre Dickey-Fuller (constante, sans tendance), n ≈ 25, 100, 500
    crit = {}
    for n in (25, 100, 500):
        z = np.cumsum(rnd.normal(size=n))
        crit[n] = {k: round(v, 3) for k, v in adfuller(z, maxlag=0, regression="c", autolag=None)[4].items()}
    # taux de fausses alarmes : marche aléatoire pure, part des séries où _ar1 retient un AR(1) (t < −2,5) et où le
    # compte le retient seul (t < −3,5)
    fa25 = fa35 = 0
    for _ in range(simulations):
        z = list(np.cumsum(rnd.normal(size=120)))
        r = ac._ar1(z, list(range(len(z) - 1)))
        fa25 += r is not None
        fa35 += r is not None and r[3] < -3.5
    return {"pente_vs_statsmodels_OLS": {"ecart_max": max(ecarts_b) if ecarts_b else None,
                                         "verdict": verdict(max(ecarts_b), 1e-9) if ecarts_b else "non testé"},
            "t_vs_statsmodels_OLS": {"ecart_max": max(ecarts_t) if ecarts_t else None,
                                     "verdict": verdict(max(ecarts_t), 1e-6) if ecarts_t else "non testé"},
            "statsmodels_vs_arch_ARX": {"ecart_max": max(ecarts_arch), "verdict": verdict(max(ecarts_arch), 1e-4)},
            "valeurs_critiques_dickey_fuller": crit,
            "marche_aleatoire_120_points": {"simulations": simulations,
                                            "melange_declenche_t_sous_-2.5": fa25 / simulations,
                                            "ar1_seul_t_sous_-3.5": fa35 / simulations,
                                            "lecture": "part des marches aléatoires prises pour un retour à la moyenne"}}


# 6. Inférence séquentielle -----------------------------------------------------------------------------------------
def sequentiel(simulations: int) -> dict:
    from confseq.betting import betting_cs
    M = ap._moteur()
    m = sr.borne_gain_C_B()
    rnd = random.Random(11)
    T = 60
    cov_maison = cov_moteur = cov_cs = 0
    larg_maison, larg_moteur, larg_cs = [], [], []
    fa_e = 0
    for s in range(simulations):
        mu = rnd.uniform(-0.3, 0.3) * m
        # gains bornés dans [−m, m], moyenne mu : mélange de deux masses (cas le plus dur pour la variance)
        q = (mu / m + 1) / 2
        g = [m if rnd.random() < q else -m for _ in range(T)]
        lo, hi = sr.intervalle_sequentiel(g, m)
        cov_maison += lo <= mu <= hi
        larg_maison.append(hi - lo)
        # moteur.sequence_confiance travaille sur d ∈ [−2, 2] (Brier − référence) : on y ramène les gains
        d = [-x / m * 2 for x in g]
        r = M.sequence_confiance(d)
        lo2, hi2 = r["intervalle"]
        cov_moteur += lo2 <= -mu / m * 2 <= hi2
        larg_moteur.append((hi2 - lo2) / 2 * m)
        u = np.array([(x + m) / (2 * m) for x in g])
        l3, h3 = betting_cs(u, alpha=0.05, running_intersection=True)
        l3, h3 = l3[-1] * 2 * m - m, h3[-1] * 2 * m - m
        cov_cs += l3 <= mu <= h3
        larg_cs.append(h3 - l3)
        if s < simulations // 2:            # H0 vraie (mu ≤ 0) : e_valeur franchit-il 1/α à un instant quelconque ?
            g0 = [m if rnd.random() < 0.5 else -m for _ in range(T)]
            fa_e += any(sr.e_valeur(g0[:t], m) >= 1 / sr.ALPHA for t in range(1, T + 1))
    n = simulations
    return {"episodes": T, "simulations": n,
            "couverture_finale": {"score_registre": cov_maison / n, "moteur": cov_moteur / n, "confseq": cov_cs / n,
                                  "attendu": "≥ 0,95"},
            "largeur_mediane_en_points": {"score_registre": float(np.median(larg_maison)),
                                          "moteur": float(np.median(larg_moteur)), "confseq": float(np.median(larg_cs))},
            "e_valeur_fausse_alarme_a_tout_instant": {"taux": fa_e / (n // 2), "attendu": f"≤ {sr.ALPHA}"}}


def principal(simulations: int, sortie: str | None) -> int:
    paires = paires_registre()
    rapport = {"paires_resolues": {k: len(v) for k, v in paires.items()}}
    for nom, f in (("1_scores", lambda: scores(paires)), ("2_murphy", lambda: murphy(paires)),
                   ("3_intervalles", intervalles), ("4_recalibration", lambda: recalibration(paires)),
                   ("5_ar1", lambda: ar1(simulations)), ("6_sequentiel", lambda: sequentiel(simulations))):
        try:
            rapport[nom] = f()
        except Exception as e:
            rapport[nom] = {"erreur": f"{type(e).__name__}: {e}"}
        print(nom, json.dumps(rapport[nom], ensure_ascii=False, default=float), flush=True)
    if sortie:
        with open(sortie, "w", encoding="utf-8") as fh:
            json.dump(rapport, fh, ensure_ascii=False, indent=1, default=float)
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--simulations", type=int, default=400)
    a.add_argument("--json")
    args = a.parse_args()
    sys.exit(principal(args.simulations, args.json))
