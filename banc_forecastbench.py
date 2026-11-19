"""Banc ForecastBench (bot 0.10.43 ; décision d'auteur du 2026-11-11) : jouer B et C sur des questions ForecastBench
DÉJÀ résolues, à leur date d'information, pour avoir vite assez d'issues (biais de C, λ appris, C contre B).

Source : forecastingresearch/forecastbench-datasets (Forecasting Research Institute ; CC BY-SA 4.0). Toutes les deux
semaines, un jeu de 500 questions (date D) ; le jeu de résolutions du même D les résout à plusieurs horizons, le premier
à D + 7 jours.

Garde-fous contre la fuite (§26), les mêmes que les tests rétrospectifs, plus deux :
  - seules les questions tirées de SÉRIES (fred, dbnomics, yfinance, acled, wikipedia) sont jouées : les questions de
    marchés (Metaculus, Manifold, Polymarket, Kalshi) portent la cote de la foule au gel, interdite avant scellement ;
  - jeux postérieurs à la date de connaissance du modèle (--apres) ; recherche Exa bornée à D (pages datées seulement) ;
  - sonde : si le modèle dit connaître l'issue et a raison, la question est exclue ;
  - la dernière valeur de la série au gel (`freeze_datetime_value`) est donnée : c'est un fait daté, pas une prévision.
Les lignes vont dans registre/retro.jsonl (type « retro », banc « forecastbench ») : le score des tests rétrospectifs
(biais de C, correction, C contre B) les compte avec les autres. Rien n'est posté.

    uv run python banc_forecastbench.py --n 20 [--jeu 2026-10-25] [--sources fred,dbnomics,yfinance,acled,wikipedia]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import os
import random
import sys
from datetime import date, datetime, timedelta, timezone

import math

import httpx

import alphabet_pipeline as ap
import alphabet_retro as ar

DEPOT = "https://raw.githubusercontent.com/forecastingresearch/forecastbench-datasets/main/datasets"
SOURCES_SERIES = ("fred", "dbnomics", "yfinance", "acled", "wikipedia")
MARCHES = ("metaculus", "manifold", "polymarket", "kalshi", "infer")


async def _json(url: str) -> dict:
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as c:
        r = await c.get(url)
        r.raise_for_status()
        return r.json()


def jeux_candidats(aujourdhui: date, apres: date, n_max: int = 12) -> list[str]:
    """Les dates D (tous les 14 jours, ancrées sur 2026-10-25) dont la première résolution (D + 7) est passée."""
    d, out = date(2026, 10, 25), []
    while d + timedelta(days=14) + timedelta(days=7) <= aujourdhui:
        d += timedelta(days=14)
    while d > apres and len(out) < n_max:
        if d + timedelta(days=7) <= aujourdhui:
            out.append(d.isoformat())
        d -= timedelta(days=14)
    return out


def apparier(questions: dict, resolutions: dict, sources=SOURCES_SERIES) -> list[dict]:
    """Une entrée par question de série résolue (0 ou 1), à son PREMIER horizon résolu. Les questions combinées
    (identifiant en liste) et toutes les questions de marché sont écartées."""
    qs = {(q["source"], q["id"]): q for q in questions.get("questions", [])
          if q.get("source") in sources and isinstance(q.get("id"), str)}
    garde: dict = {}
    for r in resolutions.get("resolutions", []):
        if not isinstance(r.get("id"), str):
            continue
        cle = (r.get("source"), r.get("id"))
        if cle not in qs or not r.get("resolved") or r.get("resolved_to") not in (0, 1, 0.0, 1.0):
            continue
        if cle not in garde or r["resolution_date"] < garde[cle]["resolution_date"]:
            garde[cle] = r
    out = []
    for cle, r in garde.items():
        q = qs[cle]
        out.append({"question": q, "resolution_date": r["resolution_date"], "issue": int(r["resolved_to"])})
    return sorted(out, key=lambda x: (x["question"]["source"], x["question"]["id"]))


def construire(item: dict, jeu: str) -> dict:
    q, rd = item["question"], item["resolution_date"]
    sub = lambda s: str(s or "").replace("{forecast_due_date}", jeu).replace("{resolution_date}", rd)
    contexte = sub(q.get("background"))
    if q.get("freeze_datetime_value") not in (None, "", "N/A") and q.get("source") in SOURCES_SERIES:
        contexte += (f"\n\nDernière valeur connue au {str(q.get('freeze_datetime', ''))[:10]} : "
                     f"{q['freeze_datetime_value']} ({q.get('freeze_datetime_value_explanation', '')}).")
    return {"qid": f"fb:{jeu}:{q['source']}:{q['id']}:{rd}", "titre": sub(q["question"]), "contexte": contexte,
            "criteres": sub(q.get("resolution_criteria")), "url": q.get("url") or "", "resolution": rd,
            "source": q["source"], "issue": item["issue"], "_q": q}


# --------------------------------------------------------------------------- 0.10.44 : B calculé par le code

EMETTEURS = {"acled": "ACLED", "fred": "FRED (Federal Reserve Bank of St. Louis)", "dbnomics": "DBnomics",
             "yfinance": "Yahoo Finance", "wikipedia": "Wikipedia"}


def _vue(f: float, classe: str, source: str, periode: str, disponible: str, calcul: str, x: dict | None = None,
         ecart: str = "identique : même série, même comparaison, même horizon que le critère de résolution") -> dict:
    v = {"frequence": min(0.999, max(0.001, f)), "compte_calcule": True, "classe_de_reference": classe,
         "source": source, "periode": periode, "disponible_le": disponible, "calcul": calcul, "ecart_critere": ecart,
         "classe_alternative": None, "motif_sans_alternative": "classe fixée par la forme de la question ForecastBench"}
    if x:   # 0.10.46 : la résolution vient de la question (sans elle, le dossier était refusé)
        v["resolution"] = x.get("criteres") or x.get("titre")
        v["source_resolution"] = {"emetteur": EMETTEURS.get(x.get("source"), str(x.get("source"))),
                                  "document": x.get("url") or "jeu de résolutions ForecastBench",
                                  "regle_ambiguite": "la résolution publiée par ForecastBench fait foi"}
    return v


def b_acled(m: float, facteur: float = 1.0) -> float:
    """« Plus d'événements dans les 30 jours avant R que la moyenne sur 30 jours des 360 jours avant D » (m, valeur au
    gel). Compte total K = 12·m sur 12 fenêtres ; taux a posteriori Gamma(K + ½, 12) (Jeffreys) ; compte d'une nouvelle
    fenêtre : binomiale négative (r = K + ½, p = 12/13). P(N > m) = 1 − Σ_{n ≤ ⌊m⌋} P(N = n). Ne voit pas la
    surdispersion des conflits (rafales) : pour les morts, la vraie probabilité est plutôt plus basse.

    0.10.127 (erreur trouvée le 2026-11-15) : pour les questions « plus de DIX FOIS plus … que UN PLUS la moyenne »,
    la valeur au gel est m = 1 + moyenne et le seuil est 10·m. Avant, le code calculait P(N > m) comme pour la forme
    simple : environ 40 % annoncés là où la vraie probabilité est quasi nulle (0 oui sur 74 questions)."""
    if facteur != 1.0:
        moyenne, seuil = max(m - 1.0, 0.0), facteur * m
    else:
        moyenne, seuil = max(m, 0.0), m
    r, q = 12 * moyenne + 0.5, 1 / 13
    cdf = sum(math.exp(math.lgamma(n + r) - math.lgamma(r) - math.lgamma(n + 1) + r * math.log(1 - q) + n * math.log(q))
              for n in range(int(math.floor(seuil)) + 1))
    return 1 - cdf


def facteur_acled(texte: str) -> float:
    """0.10.127 : 10 pour la forme « more than ten times as many … compared to one plus the 30-day average »."""
    return 10.0 if "ten times" in (texte or "").lower() else 1.0


def b_hausse(points: list[dict], h: int, avant: date, annees: int = 5) -> tuple[float, int, int] | None:
    """Part des intervalles de h jours (sur les `annees` dernières années avant D) où la série a MONTÉ : (k + ½)/(n + 1)."""
    pts = sorted((date.fromisoformat(p["date"][:10]), float(p["valeur"])) for p in points
                 if p.get("date") and p.get("valeur") is not None and p["date"][:10] < avant.isoformat())
    pts = [p for p in pts if p[0] >= avant - timedelta(days=365 * annees)]
    if len(pts) < 20:
        return None
    k = n = 0
    j = 0
    for i, (t, v) in enumerate(pts):
        cible = t + timedelta(days=h)
        while j < len(pts) and pts[j][0] < cible:
            j += 1
        if j >= len(pts):
            break
        n += 1
        k += pts[j][1] > v
    if n < 10:
        return None
    return (k + 0.5) / (n + 1), k, n


# 0.10.362 (décision d'auteur du 2026-11-19, 18 h 58, EN OMBRE) : B À L'ÉCHÉANCE. La règle de résolution de ForecastBench
# prend, pour une date sans observation, la DERNIÈRE observation antérieure (report). b_hausse compare chaque point au
# PREMIER point postérieur à t + h : pour une série mensuelle à 7 jours, il compare deux mois successifs, alors qu'à la
# résolution la valeur n'a souvent pas bougé (aucune observation datée dans la fenêtre) → « non ». Règle fixée AVANT
# toute mesure (préenregistrement preenregistrements/echeance.md) :
#   - mêmes points que B (5 ans strictement avant D) ; valeur d'un jour = dernière observation datée ≤ ce jour ;
#   - calendrier des observations déduit de l'écart médian s : ≤ 4 j quotidien (jours de semaine observés), 5-10 hebdo
#     (jour de semaine), 25-35 mensuel (jour du mois), 80-100 trimestriel (mois mod 3, jour), 170-190 semestriel,
#     350-380 annuel (mois, jour) ; clés relevées sur les 2 dernières années ; autre écart → None ;
#   - classe de la fenêtre (D, D + h] : contient-elle au moins une date d'observation attendue ?
#   - historique : chaque jour civil d des 5 ans tel que d + h ≤ dernière observation ; « hausse » = valeur(d + h) >
#     valeur(d), comptée dans la classe de SA fenêtre ; P = (k + ½)/(n + 1) dans la classe de la fenêtre à D.
def _cle_calendrier(s: float):
    if s <= 4 or 5 <= s <= 10:
        return lambda d: d.weekday()
    if 25 <= s <= 35:
        return lambda d: d.day
    if 80 <= s <= 100:
        return lambda d: (d.month % 3, d.day)
    if 170 <= s <= 190:
        return lambda d: (d.month % 6, d.day)
    if 350 <= s <= 380:
        return lambda d: (d.month, d.day)
    return None


def b_echeance(points: list[dict], h: int, avant: date, annees: int = 5) -> dict | None:
    import bisect
    import statistics as st_
    pts = sorted((date.fromisoformat(p["date"][:10]), float(p["valeur"])) for p in points
                 if p.get("date") and p.get("valeur") is not None and p["date"][:10] < avant.isoformat())
    pts = [p for p in pts if p[0] >= avant - timedelta(days=365 * annees)]
    if len(pts) < 20 or h <= 0:
        return None
    jours = [p[0] for p in pts]
    s = st_.median((b - a).days for a, b in zip(jours, jours[1:]))
    cle = _cle_calendrier(s)
    if cle is None:
        return None
    cles = {cle(d) for d in jours if d >= jours[-1] - timedelta(days=730)}

    def obs_dans(a: date, b: date) -> bool:
        return any(cle(a + timedelta(days=i)) in cles for i in range(1, (b - a).days + 1))

    def valeur(d: date):
        i = bisect.bisect_right(jours, d) - 1
        return pts[i][1] if i >= 0 else None

    compte = {True: [0, 0], False: [0, 0]}
    d = jours[0]
    while d + timedelta(days=h) <= jours[-1]:
        v0, v1 = valeur(d), valeur(d + timedelta(days=h))
        if v0 is not None and v1 is not None:
            c = compte[obs_dans(d, d + timedelta(days=h))]
            c[1] += 1
            c[0] += v1 > v0
        d += timedelta(days=1)
    classe = obs_dans(avant, avant + timedelta(days=h))
    k, n = compte[classe]
    if n < 10:
        return None
    return {"p": (k + 0.5) / (n + 1), "k": k, "n": n, "fenetre_avec_observation": classe, "ecart_median_jours": s,
            "regle": "report de la dernière observation ; classe de la fenêtre selon le calendrier des observations"}


# 0.10.92 (décision d'auteur du 2026-11-14, EN OMBRE) : un second taux de base pour les séries, par un modèle
# autorégressif. Le but n'est pas de battre C mais de trouver la meilleure prévision ; B par comptage est-il le meilleur
# B possible ? Règle fixée AVANT toute mesure, jamais ajustée sur les issues :
#   - mêmes points que B (5 ans avant D, strictement avant D) ;
#   - pas = observations natives ; k = nombre de pas dans l'horizon = arrondi de h / écart médian entre observations ;
#   - AR(1) sur les différences, avec constante, par moindres carrés : d_t = c + φ·d_(t−1) + e, φ borné à ±0,95 ;
#   - somme des k différences à venir, gaussienne : moyenne Σ [μ + φ^m (d_T − μ)], μ = c/(1−φ) ;
#     variance σ² Σ_m (Σ_(j<k−m+1) φ^j)² ;
#   - P(hausse) = (1 − part des intervalles de h jours sans changement, comptés comme B) × Φ(moyenne / écart-type) ;
#   - bornée à 0,001–0,999. Rien n'est posté ; comparé à B par la perte log sur les mêmes questions.
def b_ar(points: list[dict], h: int, avant: date, annees: int = 5) -> dict | None:
    import math
    import statistics as st_
    pts = sorted((date.fromisoformat(p["date"][:10]), float(p["valeur"])) for p in points
                 if p.get("date") and p.get("valeur") is not None and p["date"][:10] < avant.isoformat())
    pts = [p for p in pts if p[0] >= avant - timedelta(days=365 * annees)]
    if len(pts) < 30 or h <= 0:
        return None
    ecarts = [(b[0] - a[0]).days for a, b in zip(pts, pts[1:])]
    pas = st_.median(ecarts) or 1
    k = max(1, round(h / pas))
    v = [p[1] for p in pts]
    d = [b - a for a, b in zip(v, v[1:])]
    x_, y_ = d[:-1], d[1:]
    mx, my = st_.fmean(x_), st_.fmean(y_)
    sxx = sum((a - mx) ** 2 for a in x_)
    phi = 0.0 if sxx == 0 else sum((a - mx) * (b - my) for a, b in zip(x_, y_)) / sxx
    phi = max(-0.95, min(0.95, phi))
    c = my - phi * mx
    res = [b - c - phi * a for a, b in zip(x_, y_)]
    sigma = math.sqrt(sum(e * e for e in res) / max(1, len(res) - 2))
    mu = c / (1 - phi)
    moyenne = sum(mu + phi ** m * (d[-1] - mu) for m in range(1, k + 1))
    var = sigma ** 2 * sum(sum(phi ** j for j in range(k - m + 1)) ** 2 for m in range(1, k + 1))
    # part des intervalles de h jours sans changement (même appariement que b_hausse)
    n = egal = 0
    j = 0
    for t, val in pts:
        cible = t + timedelta(days=h)
        while j < len(pts) and pts[j][0] < cible:
            j += 1
        if j >= len(pts):
            break
        n += 1
        egal += pts[j][1] == val
    p_egal = egal / n if n else 0.0
    if var <= 0:
        p_haut = 1.0 if moyenne > 0 else 0.0
    else:
        p_haut = 0.5 * (1 + math.erf(moyenne / math.sqrt(2 * var)))
    p = max(0.001, min(0.999, (1 - p_egal) * p_haut))
    return {"p": p, "phi": round(phi, 4), "pas_jours": pas, "k": k, "moyenne": moyenne, "ecart_type": math.sqrt(max(var, 0)),
            "part_sans_changement": round(p_egal, 4), "points": len(pts)}


# 0.10.283 (décision d'auteur du 2026-11-18, 19 h 08, « on teste, c'est gratuit » ; EN OMBRE ; préenregistrement
# preenregistrements/b-ou.md) : retour vers la moyenne (Ornstein-Uhlenbeck discret) autour d'une tendance linéaire.
# b_ar travaille sur les VARIATIONS (marche aléatoire, sans rappel) ; aucun B ne regarde l'écart du NIVEAU à son
# équilibre. Règle fixée AVANT toute mesure, jamais ajustée sur les issues :
#   - mêmes points que B (5 ans, strictement avant D) ; pas natif, k = arrondi de h / écart médian ;
#   - moindres carrés v_t = a + b·t + φ·v_(t−1) + e (t = rang de l'observation), φ borné à [0 ; 0,999] ;
#   - espérance itérée sur k pas : E_m = a + b·(T+m) + φ·E_(m−1), E_0 = v_T ; variance σ²(1 − φ^(2k))/(1 − φ²) ;
#   - P(hausse) = (1 − part des intervalles sans changement, comme b_ar) × Φ((E_k − v_T) / écart-type) ;
#   - bornée à 0,001–0,999. Rien n'est posté ; comparé à B par la perte log (essai b_ou).
def b_ou(points: list[dict], h: int, avant: date, annees: int = 5) -> dict | None:
    import math
    import statistics as st_

    import numpy as np
    pts = sorted((date.fromisoformat(p["date"][:10]), float(p["valeur"])) for p in points
                 if p.get("date") and p.get("valeur") is not None and p["date"][:10] < avant.isoformat())
    pts = [p for p in pts if p[0] >= avant - timedelta(days=365 * annees)]
    if len(pts) < 30 or h <= 0:
        return None
    pas = st_.median([(b[0] - a[0]).days for a, b in zip(pts, pts[1:])]) or 1
    k = max(1, round(h / pas))
    v = np.array([p[1] for p in pts], dtype=float)
    t = np.arange(1, len(v), dtype=float)
    X = np.column_stack([np.ones(len(t)), t, v[:-1]])
    coef, *_ = np.linalg.lstsq(X, v[1:], rcond=None)
    a, b, phi = (float(c) for c in coef)
    if phi < 0 or phi > 0.999:                    # bornes : refaire l'ajustement avec φ fixé à la borne
        phi = min(max(phi, 0.0), 0.999)
        X2 = np.column_stack([np.ones(len(t)), t])
        (a, b), *_ = np.linalg.lstsq(X2, v[1:] - phi * v[:-1], rcond=None)
        a, b = float(a), float(b)
    res = v[1:] - (a + b * t + phi * v[:-1])
    sigma = math.sqrt(float(res @ res) / max(1, len(res) - 3))
    # 0.10.285 (amendement b-ou.md, décision d'auteur du 2026-11-18, 19 h 30) : BIC gaussien, sur l'historique seul,
    # du modèle de rappel (a, b, φ, σ : 4 paramètres) contre la marche aléatoire avec dérive (Δv = c + e : 2).
    nb = len(res)
    dv = v[1:] - v[:-1]
    rss_m = float(((dv - dv.mean()) ** 2).sum())
    rss_r = float(res @ res)
    bic = lambda rss, k_: nb * math.log(max(rss, 1e-300) / nb) + k_ * math.log(nb)
    bic_ecart = bic(rss_m, 2) - bic(rss_r, 4)        # > 0 : le rappel est préféré
    T = len(v) - 1
    e = float(v[-1])
    for m in range(1, k + 1):
        e = a + b * (T + m) + phi * e
    var = sigma ** 2 * (k if phi >= 0.999999 else (1 - phi ** (2 * k)) / (1 - phi ** 2))
    n = egal = 0
    j = 0
    for tt, val in pts:
        cible = tt + timedelta(days=h)
        while j < len(pts) and pts[j][0] < cible:
            j += 1
        if j >= len(pts):
            break
        n += 1
        egal += pts[j][1] == val
    p_egal = egal / n if n else 0.0
    ecart = e - float(v[-1])
    p_haut = (1.0 if ecart > 0 else 0.0) if var <= 0 else 0.5 * (1 + math.erf(ecart / math.sqrt(2 * var)))
    p = max(0.001, min(0.999, (1 - p_egal) * p_haut))
    return {"p": p, "phi": round(phi, 4), "bic_ecart": round(bic_ecart, 2), "pas_jours": pas, "k": k, "ecart_attendu": ecart,
            "ecart_type": math.sqrt(max(var, 0)), "part_sans_changement": round(p_egal, 4), "points": len(pts)}


# 0.10.131 (décision d'auteur du 2026-11-15, EN OMBRE ; pré-enregistrement b-tendance.md) : B qui pèse davantage les
# semaines récentes. Constat du garde-fou sur B (audit_b.py) : écarts de crédit FRED, B 40 % annoncés, 75 % observés,
# même sens dans 7 jeux sur 9 ; B compte les hausses sur 5 ans et ne voit pas la tendance en cours. Règle fixée AVANT
# toute mesure :
#   - mêmes intervalles de h jours que B (5 ans, strictement avant D, même appariement) ;
#   - chaque intervalle pèse 2^(−âge / 90), âge = jours entre la fin de l'intervalle et D (demi-vie de 90 jours) ;
#   - P(hausse) = (Σ poids × hausse + ½) / (Σ poids + 1) (Jeffreys sur les comptes pondérés) ;
#   - appliqué seulement si Σ poids ≥ 20 (séries fréquentes : quotidiennes, hebdomadaires) ; sinon rien (B reste).
DEMI_VIE_TENDANCE = 90
POIDS_MIN_TENDANCE = 20.0


def b_tendance(points: list[dict], h: int, avant: date, annees: int = 5, demi_vie: int = DEMI_VIE_TENDANCE) -> dict | None:
    pts = sorted((date.fromisoformat(p["date"][:10]), float(p["valeur"])) for p in points
                 if p.get("date") and p.get("valeur") is not None and p["date"][:10] < avant.isoformat())
    pts = [p for p in pts if p[0] >= avant - timedelta(days=365 * annees)]
    if len(pts) < 20 or h <= 0:
        return None
    k = w = 0.0
    j = 0
    for t, v in pts:
        cible = t + timedelta(days=h)
        while j < len(pts) and pts[j][0] < cible:
            j += 1
        if j >= len(pts):
            break
        poids = 2.0 ** (-(avant - pts[j][0]).days / demi_vie)
        w += poids
        k += poids * (pts[j][1] > v)
    if w < POIDS_MIN_TENDANCE:
        return None
    return {"p": (k + 0.5) / (w + 1), "poids": round(w, 1), "hausses_ponderees": round(k, 1), "demi_vie": demi_vie}


# 0.10.233 (décision d'auteur du 2026-11-17, « Let's go », EN OMBRE ; pré-enregistrement classe-reference.md, partie
# « autre domaine ») : B par classe de référence pondérée par la RESSEMBLANCE. Mêmes intervalles de h jours que B (5 ans,
# strictement avant D, même appariement) ; chaque intervalle commençant en t pèse selon la ressemblance de la série en t
# avec la série en D, sur deux nombres connus à la date :
#   z(t) = (v_t − moyenne des valeurs des 365 jours avant t) / écart-type de ces valeurs ;
#   m(t) = (v_t − valeur au dernier point à t − h ou avant) / même écart-type ;
#   w = max(0,005 ; exp(−½ Δz² − ½ Δm²)) ; P(hausse) = (Σ w × hausse + ½) / (Σ w + 1) (Jeffreys, comme B).
# Au moins 10 points dans l'année avant t et un écart-type non nul ; au moins 20 intervalles pondérables, sinon rien.
def b_noyau(points: list[dict], h: int, avant: date, annees: int = 5, hz: float = 1.0, hm: float = 1.0) -> dict | None:
    import bisect
    import math
    if h <= 0:
        return None
    pts = sorted((date.fromisoformat(p["date"][:10]), float(p["valeur"])) for p in points
                 if p.get("date") and p.get("valeur") is not None and p["date"][:10] < avant.isoformat())
    pts = [p for p in pts if p[0] >= avant - timedelta(days=365 * (annees + 1) + h)]
    if len(pts) < 30:
        return None
    ts = [p[0] for p in pts]
    vs = [p[1] for p in pts]
    s1, s2 = [0.0], [0.0]
    for v in vs:
        s1.append(s1[-1] + v)
        s2.append(s2[-1] + v * v)

    def etat(i: int) -> tuple[float, float] | None:
        a = bisect.bisect_left(ts, ts[i] - timedelta(days=365))
        n = i - a
        if n < 10:
            return None
        moy = (s1[i] - s1[a]) / n
        var = (s2[i] - s2[a]) / n - moy * moy
        if var <= 1e-12:
            return None
        sd = math.sqrt(var)
        j = bisect.bisect_right(ts, ts[i] - timedelta(days=h)) - 1
        if j < 0:
            return None
        return (vs[i] - moy) / sd, (vs[i] - vs[j]) / sd

    present = etat(len(pts) - 1)
    if present is None:
        return None
    debut = avant - timedelta(days=365 * annees)
    k = w = 0.0
    n = 0
    j = 0
    for i, (t, v) in enumerate(pts):
        if t < debut:
            continue
        cible = t + timedelta(days=h)
        while j < len(pts) and pts[j][0] < cible:
            j += 1
        if j >= len(pts):
            break
        e = etat(i)
        if e is None:
            continue
        poids = max(0.005, math.exp(-0.5 * ((e[0] - present[0]) / hz) ** 2 - 0.5 * ((e[1] - present[1]) / hm) ** 2))
        w += poids
        k += poids * (pts[j][1] > v)
        n += 1
    if n < 20:
        return None
    return {"p": (k + 0.5) / (w + 1), "poids": round(w, 1), "intervalles": n, "z": round(present[0], 3),
            "m": round(present[1], 3)}


# 0.10.104 (décision d'auteur du 2026-11-15, EN OMBRE ; pré-enregistrement b-saisonnier.md) : un troisième taux de base
# pour les séries, SAISONNIER. Constat : sur DBnomics (surtout des températures Météo-France), B annonce ~50 % alors que
# ~26 % des questions se résolvent OUI ; B compte les hausses sur toute l'année. Règle fixée AVANT toute mesure :
#   - points strictement avant D, sur les 10 dernières années ;
#   - intervalles de h jours qui COMMENCENT à ±15 jours de la même date du calendrier que D, dans une année passée, et
#     qui finissent avant D ; même appariement que B (premier point à t + h ou après) ;
#   - P(hausse) = (hausses + ½) / (intervalles + 1) (Jeffreys) ; au moins 5 intervalles, sinon rien.
def b_saison(points: list[dict], h: int, avant: date, annees: int = 10, fenetre: int = 15) -> dict | None:
    if h <= 0:
        return None
    pts = sorted((date.fromisoformat(p["date"][:10]), float(p["valeur"])) for p in points
                 if p.get("date") and p.get("valeur") is not None and p["date"][:10] < avant.isoformat())
    pts = [p for p in pts if p[0] >= avant - timedelta(days=365 * annees + 3)]
    k = n = 0
    j = 0
    for t, v in pts:
        cible = t + timedelta(days=h)
        if cible >= avant:
            break
        ecart = abs((t - avant).days) % 365.2425
        if min(ecart, 365.2425 - ecart) > fenetre or (avant - t).days < 300:
            continue
        while j < len(pts) and pts[j][0] < cible:
            j += 1
        if j >= len(pts):
            break
        jj = j
        n += 1
        k += pts[jj][1] > v
    if n < 5:
        return None
    return {"p": (k + 0.5) / (n + 1), "hausses": k, "intervalles": n, "fenetre_jours": fenetre, "annees": annees}


async def vue_calculee(x: dict, q: dict, jeu: str) -> dict | None:
    """Le taux de base calculé par le code quand la forme de la question le permet ; None sinon (vues du modèle)."""
    d0 = date.fromisoformat(jeu)
    h = (date.fromisoformat(x["resolution"]) - d0).days
    gel = str(q.get("freeze_datetime") or jeu)[:10]
    src = q.get("source")
    try:
        if src == "acled":
            m = float(q.get("freeze_datetime_value"))
            fa = facteur_acled(q.get("question") or x.get("titre", ""))
            return _vue(b_acled(m, fa), "fenêtres de 30 jours du même pays et du même type d'événement (ACLED)",
                        "ForecastBench, valeur de référence au gel (moyenne ACLED sur 30 jours, 360 jours)",
                        f"360 jours avant {gel}", gel,
                        (f"binomiale négative, r = 12·{m:.4g} + 0,5, p = 12/13 ; P(N > {m:.4g}) (Jeffreys)" if fa == 1.0 else
                         f"binomiale négative, r = 12·({m:.4g} − 1) + 0,5, p = 12/13 ; P(N > 10·{m:.4g}) (Jeffreys)"), x,
                        "la classe suppose un taux stable (Poisson-gamma) ; le critère compare la fenêtre de 30 jours qui "
                        "finit à la résolution à la moyenne des 360 jours avant le gel, et les conflits arrivent en rafales")
        if src == "yfinance" and "higher rate of return than" in q.get("question", ""):
            return _vue(0.5, "paires d'actions, rendement relatif sur le même intervalle", "symétrie de la paire",
                        jeu, jeu, "0,5 : les deux actions sont échangeables a priori (aucune ne domine sans information)", x,
                        "identique : le critère compare les deux rendements sur le même intervalle")
        if src in ("fred", "dbnomics") and h > 0:
            import alphabet_puits as apz
            if src == "fred":
                try:
                    r = await apz.fred(q["id"], avant=d0)
                except Exception:
                    r = {}
                ok_millesime = len(r.get("points") or []) >= 20 and not r.get("millesime")
                if ok_millesime:
                    x["_provenance"] = "ALFRED (millésime à la date d'information)"
                elif marche_non_revise(q["id"]):
                    # 0.10.46 : séries de marché sans millésimes ALFRED (SP500…) ; valeurs actuelles bornées à D par
                    # b_hausse. 0.10.189 (audit ALFRED) : seulement pour les cotations de marché de la liste
                    # MARCHES_NON_REVISES (jamais révisées) ; une série révisable sans millésime n'a plus de B.
                    if len(r.get("points") or []) < 20 or r.get("millesime"):
                        r = await apz.fred(q["id"])
                    x["_provenance"] = "FRED actuel borné à la date (cotation de marché non révisée, exception vérifiée)"
                else:
                    x["_provenance"] = "refusé : série révisable sans millésime ALFRED"
                    return None
            else:
                r = await apz.dbnomics(q["url"].split("db.nomics.world/", 1)[1], avant=d0)
            b = b_hausse(r.get("points") or [], h, d0)
            try:                                      # 0.10.92 : second taux de base, autorégressif, en ombre
                x["_b_ar"] = b_ar(r.get("points") or [], h, d0)
            except Exception as e:
                x["_b_ar"] = {"erreur": f"{type(e).__name__}: {e}"[:200]}
            try:                                      # 0.10.104 : taux de base saisonnier, en ombre
                x["_b_saison"] = b_saison(r.get("points") or [], h, d0)
            except Exception as e:
                x["_b_saison"] = {"erreur": f"{type(e).__name__}: {e}"[:200]}
            try:                                      # 0.10.233 : classe de référence pondérée, en ombre
                x["_b_noyau"] = b_noyau(r.get("points") or [], h, d0)
            except Exception as e:
                x["_b_noyau"] = {"erreur": f"{type(e).__name__}: {e}"[:200]}
            try:                                      # 0.10.283 : retour vers la moyenne (OU), en ombre
                x["_b_ou"] = b_ou(r.get("points") or [], h, d0)
            except Exception as e:
                x["_b_ou"] = {"erreur": f"{type(e).__name__}: {e}"[:200]}
            try:                                      # 0.10.362 : B à l'échéance (report, calendrier), en ombre
                x["_b_echeance"] = b_echeance(r.get("points") or [], h, d0)
            except Exception as e:
                x["_b_echeance"] = {"erreur": f"{type(e).__name__}: {e}"[:200]}
            try:                                      # 0.10.131 : taux de base récent (tendance), en ombre
                x["_b_tendance"] = b_tendance(r.get("points") or [], h, d0)
            except Exception as e:
                x["_b_tendance"] = {"erreur": f"{type(e).__name__}: {e}"[:200]}
            # 0.10.78 : la série téléchargée ici sert aussi à l'ombre « ancrage par les séries » (au banc, le puits du
            # bot n'est pas appelé pour ces questions) ; bornée STRICTEMENT avant la date d'information
            x["_releve"] = dict(r, points=[p for p in r.get("points") or [] if str(p.get("date", ""))[:10] < jeu])
            if b:
                f, k, n = b
                return _vue(f, f"intervalles de {h} jours de la même série, 5 ans avant {jeu}",
                            f"{r.get('source')} : {r.get('titre')}", f"5 ans avant {jeu}", jeu,
                            f"({k} hausses + 0,5) / ({n} intervalles + 1) (Jeffreys)", x)
    except Exception:
        return None
    return None


from alphabet_puits import MARCHES_NON_REVISES, marche_non_revise  # noqa: E402,F401  (0.10.189)


def sans_b_code(x: dict) -> bool:
    """0.10.86 : une source pour laquelle le banc ne calcule aucun B par le code (voir vue_code)."""
    q = x.get("_q") or {}
    return x["source"] == "wikipedia" or (x["source"] == "yfinance"
                                          and "higher rate of return than" not in (q.get("question") or ""))


async def un_test(x: dict, jeu: str, llm, deja: set[str]) -> dict | None:
    if x["qid"] in deja:
        return None
    info = datetime.fromisoformat(jeu).replace(tzinfo=timezone.utc)
    issue = "yes" if x["issue"] == 1 else "no"
    ligne = {"type": "retro", "banc": "forecastbench", "jeu": jeu, "source_question": x["source"],
             "version_bot": ap.VERSION_BOT, "version_skill": ap.version_skill(), "question_id": x["qid"],
             "modeles": ap.modeles_actifs(), "url": x["url"], "titre": x["titre"], "date_information": jeu,
             "resolution": x["resolution"], "issue": x["issue"],
             "licence": "ForecastBench, Forecasting Research Institute, CC BY-SA 4.0"}
    # 0.10.79 (décision d'auteur du 2026-11-14) : les duels d'actions (« X a-t-elle un meilleur rendement que Y sur une
    # semaine ? ») ne sont plus lus. B = 0,5 par symétrie ; la lecture y ancrait de l'information publique déjà dans
    # les cours (avis d'analystes) et C y faisait moins bien que B (rejeu du 2026-11-14 : 22 lectures, perte log 0,83
    # contre 0,69). Aucun appel de modèle ; ALPHABET_FB_DUELS=1 les fait relire (test multi-lecteurs, par exemple).
    if (x["source"] == "yfinance" and "higher rate of return than" in (x["_q"].get("question") or "")
            and os.environ.get("ALPHABET_FB_DUELS", "0") != "1"):
        return None              # ni écrite ni comptée : le budget n va aux questions que l'alphabet lit
    # 0.10.86 (banc du 2026-11-14, jeu 2026-09-27) : actions seules (« clôture de GD plus haute dans 7 jours ? ») et
    # questions Wikipedia (Elo d'échecs, vaccins) : le banc n'a pas de B calculé par le code pour ces sources, et la vue
    # extérieure du modèle refuse de l'estimer (13 « sans_vue » sur 14, aucune lecture, 0,10 $ chacune, comptées dans
    # n). Elles ne sont plus jouées tant qu'aucun B par le code n'existe pour elles ; ALPHABET_FB_SANS_B=1 les rouvre.
    if (sans_b_code(x) and os.environ.get("ALPHABET_FB_SANS_B", "0") != "1"):
        return None
    try:
        sonde = ap.extraire_json(await llm(ar.consigne_sonde(x["titre"], x["criteres"])))
    except Exception as e:
        sonde = {"erreur": str(e)[:200]}
    ligne["sonde"] = sonde
    if sonde.get("connait") is True and str(sonde.get("issue") or "").lower() == issue:
        ligne["statut"] = "exclue_connue"
        return ligne
    q = ap.Question(id=x["qid"], url=x["url"], titre=x["titre"], contexte=x["contexte"], criteres=x["criteres"],
                    precisions="", resolution=date.fromisoformat(x["resolution"]))
    jours = max(1, (date.fromisoformat(x["resolution"]) - info.date()).days)

    async def chercher(req: str) -> str:
        return await ar.chercher_avant(req, info)
    vue = await vue_calculee(x, x["_q"], jeu)
    ligne["b_calcule"] = bool(vue)
    ligne["vue_calculee"] = vue     # 0.10.47 : gardée au registre, pour vérifier la cohérence de B
    c = await ap.alphabet(q, "", llm, chercher, True, jeu, jours, ar.historique_avant, vue_fixee=vue)
    p_b = c.get("p_B")
    if p_b is None and vue and vue.get("frequence") is not None:
        # 0.10.61 : B est calculé par le code AVANT la lecture ; une question jugée hors alphabet (ou refusée au plan)
        # garde son B, comme la pipeline le fixe (trace["p_B"] = fréquence de la vue)
        p_b = float(vue["frequence"])
    ligne.update(statut=c.get("statut"), p_B=p_b, p_C=c.get("p_C"), motif=c.get("motif"),
                 evenement=c.get("evenement"), etat=c.get("etat"), vues=c.get("vues"), classe_statut=c.get("classe_statut"),
                 nature_etat_nul=c.get("nature_etat_nul"), puits=c.get("puits"),
                 compte_calcule=bool((c.get("vue") or {}).get("compte_calcule")),
                 exploratoire=c.get("exploratoire"), symetrique=c.get("symetrique"),
                 ombre_causale=c.get("ombre_causale"), rejeu=c.get("_rejeu"),
                 empreintes_passages=c.get("empreintes_passages"),
                 tiers_polarite=c.get("tiers_polarite") or (c.get("exploratoire") or {}).get("tiers_polarite"),
                 attribution=ap.controle_attribution(c.get("dossier"), c.get("_textes")))
    # 0.10.70 : ombre « absence » (hypothèse enregistrée le 2026-11-13), état nul posté ou exploratoire
    for k_ in ("ombre_filtrage", "ombre_series", "ombre_nouveau_depart", "ombre_sans_matrice"):      # 0.10.73 : tâches refaites par le code, en ombre
        ligne[k_] = c.get(k_) or (c.get("exploratoire") or {}).get(k_)
    if x.get("_b_ar") is not None:
        ligne["ombre_b_ar"] = x["_b_ar"]
    if x.get("_b_saison") is not None:
        ligne["ombre_b_saison"] = x["_b_saison"]
    try:                                         # 0.10.118 : type, régime et régimes lus dans les cartes, en ombre
        ligne["aiguillage"] = ap.aiguillage_ombre(x["titre"], x.get("criteres") or "", c, None)
    except Exception as e:
        ligne["aiguillage"] = {"erreur": f"{type(e).__name__}: {e}"[:200]}
    if not ligne.get("ombre_series") and x.get("_releve"):       # 0.10.78 : série du banc, bornée à D
        try:
            import ombres_auto as oa
            mots_ = (((c.get("_rejeu") or {}).get("lectures") or [{}])[-1] or {}).get("mots")
            ligne["ombre_series"] = oa.comparer_series([x["_releve"]], None, mots_)
        except Exception as e:
            ligne["ombre_series"] = {"erreur": f"{type(e).__name__}: {e}"[:200]}
    ligne["ombre_absence"] = ap.ombre_absence(p_b, c.get("nature_etat_nul")
                                              or (c.get("exploratoire") or {}).get("nature_etat_nul"))
    if c.get("statut") == "refuse" and c.get("dossier"):     # 0.10.55 : en strate 7 aussi, le dossier refusé est gardé
        d_ = c["dossier"]
        ligne["dossier_refuse"] = {k: d_.get(k) for k in ("candidats", "contre_candidate", "mots", "rejets", "liaisons",
                                                          "questions", "_reparations") if k in d_}
    if (c.get("exploratoire") or {}).get("statut") == "panne":      # 0.10.54 : la panne de la lecture exploratoire
        ligne.update(statut="panne", motif=c["exploratoire"].get("motif"))
    return ligne


def questions_de(version: str) -> tuple[list[str], set[str]]:
    """0.10.58 : les questions (identifiants et jeux) jouées par une version du bot : pour qu'un autre codeur lise les
    MÊMES questions (test multi-lecteurs). Les pannes ne comptent pas."""
    f = ap.REGISTRE / ar.RETRO
    lignes = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()] if f.is_file() else []
    qids = {x["question_id"] for x in lignes if x.get("banc") == "forecastbench" and x.get("version_bot") == version
            and x.get("statut") != "panne"}
    return sorted({q.split(":")[1] for q in qids}), qids


def deja_par(modele: str) -> set[str]:
    """0.10.58 : les questions du banc déjà lues par CE modèle principal (un autre codeur peut les relire)."""
    f = ap.REGISTRE / ar.RETRO
    lignes = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()] if f.is_file() else []
    return {x["question_id"] for x in lignes if x.get("banc") == "forecastbench" and x.get("statut") != "panne"
            and (x.get("modeles") or {}).get("principal") == modele}


def depasse(cumul: float, pire: float, budget: float) -> bool:
    """0.10.85 : la prochaine question, au pire coût déjà vu, ferait-elle passer le plafond ? (0 = sans plafond)"""
    return budget > 0 and cumul + pire > budget


async def principal(n: int, apres: str, jeu: str | None, sources: tuple[str, ...], graine: int,
                    memes_que: str | None = None, budget: float = 0.0) -> int:
    import alphabet_bot as ab
    import alphabet_modeles as am
    if not ar.recherche_bornee_disponible():
        print("Banc ForecastBench : il faut une recherche bornable dans le temps (EXA_API_KEY ou TINYFISH_API_KEY). "
              "Rien n'est lancé.")
        return 1
    choix, essais = await am.choisir()
    if not choix["principal"]:
        print("Aucun modèle principal disponible. Rien n'est lancé.")
        for e_ in essais:                          # 0.10.58 : pourquoi (modèle inconnu, clé, réponse sans JSON…)
            print(f"  essai {e_.get('role')} {e_.get('modele')} : {e_.get('erreur')}")
        return 1
    am.appliquer(choix)
    am.installer_traceur()                       # 0.10.100 : version exacte du modèle servi, par question
    am.servis_et_vider()
    modele = ab.configuration().get("default")

    delai_appel = float(os.environ.get("ALPHABET_APPEL_DELAI") or "600")

    async def llm(consigne: str) -> str:
        # 0.10.59 : aucun appel ne peut bloquer le banc au-delà de ce délai ; le dépassement est une PANNE (harnais)
        try:
            return await asyncio.wait_for(modele.invoke(consigne), delai_appel)
        except asyncio.TimeoutError:
            raise TimeoutError(f"appel au modèle sans réponse en {delai_appel:.0f} s") from None
    jeux = [jeu] if jeu else jeux_candidats(date.today(), date.fromisoformat(apres))
    deja, faites, pannes_suite = ar.deja_faites(), 0, 0
    # 0.10.85 : plafond en dollars par passage (billet « eval harness », 2026-11-14). Le banc s'arrêtait au nombre de
    # questions, jamais au coût : un lecteur qui boucle ou un prix qui change n'étaient arrêtés par rien. Avant chaque
    # question, on s'arrête si le coût cumulé PLUS la question la plus chère vue jusqu'ici dépasserait le plafond
    # (pire cas connu, pannes comprises). 0 = sans plafond.
    cumul, pire = 0.0, 0.0
    cibles = None
    if memes_que:
        os.environ["ALPHABET_FB_DUELS"] = "1"     # 0.10.79 : une relecture compare les lecteurs sur les MÊMES questions
        os.environ["ALPHABET_FB_SANS_B"] = "1"    # 0.10.86 : idem pour les sources sans B par le code
        # 0.10.58 : test multi-lecteurs : les questions d'une version passée, relues par le codeur de ce passage
        jeux, cibles = questions_de(memes_que)
        deja = deja_par(choix["principal"])
        print(f"Mêmes questions que la version {memes_que} : {len(cibles)} ; codeur {choix['principal']} ; "
              f"{len(cibles & deja)} déjà lue(s) par lui.")
        if not cibles:
            print("Aucune question pour cette version. Rien n'est lancé.")
            return 1
    rnd = random.Random(graine)
    from forecasting_tools import MonetaryCostManager
    for j in jeux:
        if faites >= n or pannes_suite >= 3:
            break
        try:
            qs = await _json(f"{DEPOT}/question_sets/{j}-llm.json")
            rs = await _json(f"{DEPOT}/resolution_sets/{j}_resolution_set.json")
        except Exception as e:
            print(f"Jeu {j} indisponible : {type(e).__name__}")
            continue
        items = [construire(i, j) for i in apparier(qs, rs, sources)]
        if cibles is not None:
            items = [x for x in items if x["qid"] in cibles]
        rnd.shuffle(items)
        print(f"Jeu {j} : {len(items)} questions de séries résolues.")
        for x in items:
            if faites >= n:
                break
            if depasse(cumul, pire, budget):
                print(f"Plafond atteint : {cumul:.2f} $ dépensés + {pire:.2f} $ (question la plus chère) > {budget:.2f} $. "
                      "Arrêt du banc.")
                n = faites
                break
            avant_m = ar.moteurs_utilises()
            with MonetaryCostManager() as cm:
                try:
                    ligne = await un_test(x, j, llm, deja)
                except Exception as e:
                    # 0.10.54 : une exception du banc est une panne du HARNAIS (code ou service), pas un refus
                    ligne = {"type": "retro", "banc": "forecastbench", "version_bot": ap.VERSION_BOT,
                             "question_id": x["qid"], "statut": "panne", "motif": f"{type(e).__name__}: {e}"[:300]}
                cout = cm.current_usage
            if ligne is None:
                continue
            ligne["cout_usd"] = round(float(cout or 0), 4)
            ligne["modeles_servis"] = am.servis_et_vider()
            cumul += ligne["cout_usd"]
            pire = max(pire, ligne["cout_usd"])
            apres_m = ar.moteurs_utilises()      # 0.10.50 : quels moteurs ont servi pour CETTE question
            ligne["moteurs_recherche"] = {k: v - avant_m.get(k, 0) for k, v in apres_m.items() if v - avant_m.get(k, 0)}
            ar.ecrire(ligne)
            if ligne.get("statut") == "panne":
                # 0.10.54 : écrite pour le diagnostic, mais ni comptée ni marquée faite : un prochain passage la refera.
                # Trois pannes de suite : le service est tombé, on s'arrête plutôt que de brûler la liste.
                pannes_suite += 1
                print(f"{ligne['question_id'][:60]} : PANNE (non comptée) · {ligne.get('motif', '')[:120]}")
                if pannes_suite >= 3:
                    print("Trois pannes de suite : arrêt du banc.")
                    break
                continue
            pannes_suite = 0
            deja.add(ligne["question_id"])
            faites += 1
            print(f"{ligne['question_id'][:60]} : {ligne.get('statut')} · B {ligne.get('p_B')} · C {ligne.get('p_C')} · "
                  f"issue {ligne.get('issue')} · {ligne['cout_usd']} $")
    print(f"{faites} question(s) ForecastBench écrite(s) dans registre/{ar.RETRO} ; coût {cumul:.2f} $"
          + (f" (plafond {budget:.2f} $)." if budget > 0 else "."))
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--n", type=int, default=int(os.environ.get("ALPHABET_FB_N") or 20))
    a.add_argument("--apres", default=os.environ.get("ALPHABET_RETRO_APRES") or "2026-07-01",
                   help="jeux postérieurs à cette date (après la date de connaissance du modèle)")
    a.add_argument("--jeu", default=None, help="date d'un jeu (AAAA-MM-JJ) ; sinon les plus récents résolus")
    a.add_argument("--sources", default=",".join(SOURCES_SERIES))
    a.add_argument("--graine", type=int, default=0)
    a.add_argument("--memes-que", default=os.environ.get("ALPHABET_FB_MEMES") or None,
                   help="version du bot dont on relit les mêmes questions (test multi-lecteurs)")
    a.add_argument("--budget", type=float, default=float(os.environ.get("ALPHABET_FB_BUDGET") or 15),
                   help="plafond en dollars pour ce passage (0 = sans plafond)")
    args = a.parse_args()
    srcs = tuple(s for s in args.sources.split(",") if s in SOURCES_SERIES)
    sys.exit(asyncio.run(principal(args.n, args.apres, args.jeu, srcs, args.graine, args.memes_que, args.budget)))
