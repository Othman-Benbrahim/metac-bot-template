"""JUGE VERROUILLÉ du banc du compte. Ne pas modifier pendant une boucle d'amélioration.

    uv run python banc/compte/juge.py            # partie de travail (graines 0 à 399)
    uv run python banc/compte/juge.py --cache    # partie cachée (graines 100000+) : vérification finale SEULEMENT

Cas simulés, de VRAIE probabilité connue, au format des relevés des puits ; seul alphabet_compte.compter est modifiable :
  E  événements (séismes, alertes, décrets…) : processus de Poisson, taux annuel de 0,2 à 30, historique de 3 à 30
     ans ; un tiers des cas avec une tendance (le taux final vaut 0,3 à 3 fois le taux initial). Question : « au
     moins un événement dans les W prochains jours ? » ; vérité 1 − exp(−λ_fin·W/365).
  N  niveaux (taux, prix, indices) : marche aléatoire mensuelle sur 3 à 30 ans ; seuil au-dessus de la dernière
     valeur. Question : « la série atteindra-t-elle le seuil dans les W prochains jours ? » ; vérité par 4 000
     simulations du même processus à partir de la dernière valeur (mode « atteint » ; « franchit » pour la moitié).
Score (à faire baisser) : divergence de Kullback-Leibler moyenne, en millinats, entre la vraie probabilité et
l'estimation (bornée à [0,001 ; 0,999]). Une abstention (fréquence None) compte comme 0,5 : ne rien dire coûte.
"""
import argparse
import json
import math
import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from alphabet_compte import compter  # noqa: E402

FIN = date(2026, 6, 1)
W_EVT = [7, 30, 90, 180, 365]
W_NIV = [30, 90, 180, 365]


def cas_evenements(rnd: random.Random) -> dict:
    lam0 = math.exp(rnd.uniform(math.log(0.2), math.log(30)))
    tendance = rnd.random() < 1 / 3
    lam1 = lam0 * (math.exp(rnd.uniform(math.log(0.3), math.log(3))) if tendance else 1.0)
    annees = rnd.uniform(3, 30)
    jours = int(annees * 365)
    debut = FIN - timedelta(days=jours)
    pts, t = [], 0.0
    while True:                                      # Poisson non homogène par amincissement
        lmax = max(lam0, lam1) / 365
        t += rnd.expovariate(lmax)
        if t >= jours:
            break
        lam_t = (lam0 + (lam1 - lam0) * t / jours) / 365
        if rnd.random() < lam_t / lmax:
            pts.append({"date": (debut + timedelta(days=int(t))).isoformat(), "valeur": None})
    W = rnd.choice(W_EVT)
    return {"genre": "E" + ("t" if tendance else ""), "releve": {"debut": debut.isoformat(), "date_limite": FIN.isoformat(),
            "points": pts}, "W": W, "mode": "evenement", "seuil": None, "sens": ">=", "nature": "evenements",
            "vrai": 1 - math.exp(-lam1 * W / 365)}


def cas_niveaux(rnd: random.Random) -> dict:
    mois = int(rnd.uniform(3, 30) * 12)
    sigma = rnd.uniform(0.5, 3)
    derive = rnd.choice([0.0, 0.0, rnd.uniform(-0.3, 0.3) * sigma])
    x, pts = rnd.uniform(-10, 10), []
    for k in range(mois):
        x += derive + rnd.gauss(0, sigma)
        d = FIN - timedelta(days=int((mois - 1 - k) * 30.44))
        pts.append({"date": d.isoformat(), "valeur": round(x, 4)})
    W = rnd.choice(W_NIV)
    pas = max(1, round(W / 30.44))
    seuil = x + rnd.uniform(0.2, 2.5) * sigma * math.sqrt(pas)
    sim = random.Random(rnd.random())
    hits = 0
    for _ in range(4000):
        y = x
        for _ in range(pas):
            y += derive + sim.gauss(0, sigma)
            if y >= seuil:
                hits += 1
                break
    mode = rnd.choice(["atteint", "franchit"])
    return {"genre": "N", "releve": {"debut": pts[0]["date"], "date_limite": FIN.isoformat(), "points": pts},
            "W": W, "mode": mode, "seuil": round(seuil, 4), "sens": ">=", "nature": "niveau",
            "vrai": (hits + 0.5) / 4001}


def generer(graine: int) -> dict:
    rnd = random.Random(graine)
    return cas_evenements(rnd) if graine % 2 == 0 else cas_niveaux(rnd)


def kl(p: float, q: float) -> float:
    q = min(0.999, max(0.001, q))
    p = min(0.999, max(0.001, p))
    return p * math.log(p / q) + (1 - p) * math.log((1 - p) / (1 - q))


def juger(graines) -> dict:
    tot, par = [], {}
    abst = 0
    for g in graines:
        c = generer(g)
        try:
            r = compter(c["releve"], c["W"], c["mode"], c["seuil"], c["sens"], None, fin=FIN, nature=c["nature"])
            q = r.get("frequence")
        except Exception:
            q = None
        if q is None:
            abst += 1
            q = 0.5
        d = 1000 * kl(c["vrai"], float(q))
        tot.append(d)
        par.setdefault(c["genre"], []).append(d)
    return {"score": round(sum(tot) / len(tot), 3), "cas": len(tot), "abstentions": abst,
            "par_genre": {k: round(sum(v) / len(v), 2) for k, v in sorted(par.items())}}


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--cache", action="store_true")
    args = a.parse_args()
    print(json.dumps(juger(range(100000, 100200) if args.cache else range(400)), ensure_ascii=False))
