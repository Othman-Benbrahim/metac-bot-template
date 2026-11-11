"""JUGE VERROUILLÉ du banc du compte, VERSION 2 (2026-11-11). Ne pas modifier pendant une boucle d'amélioration.

Le juge 1 (`juge.py`) reste tel quel. La version 2 garde ses deux familles (E, N) et ajoute les pièges repérés sur de
vraies séries le 2026-11-11 (question FYONET), chacun de VRAIE probabilité connue :
  C  croissance : série annuelle positive à croissance géométrique (1 à 8 % par an, bruit relatif 1 à 4 %), 15 à 40 ans ;
     seuil au-dessus de la dernière valeur ;
  R  rupture : marche aléatoire mensuelle avec UN choc ponctuel de 8 à 20 écarts-types dans l'historique, qui ne se
     reproduit pas ;
  M  retour à la moyenne : processus AR(1) mensuel (φ de 0,70 à 0,97), comme un taux ou un chômage ;
  B  bornée : pourcentage entre 0 et 100 (marche aléatoire sur l'échelle logit), seuil parfois près de la borne ; le
     relevé déclare ses bornes (bornes=(0, 100)), comme le fera le catalogue ou la demande du modèle.
Score : divergence de Kullback-Leibler moyenne (millinats) ; abstention = 0,5.

    uv run python banc/compte/juge2.py            # travail (graines 0 à 599)
    uv run python banc/compte/juge2.py --cache    # caché (graines 200000+) : vérification finale SEULEMENT
"""
import argparse
import json
import math
import random
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from alphabet_compte import compter  # noqa: E402
from juge import FIN, W_NIV, cas_evenements, cas_niveaux, kl  # noqa: E402

N_SIM = 4000


def _mensuel(valeurs: list[float]) -> list[dict]:
    n = len(valeurs)
    return [{"date": (FIN - timedelta(days=int((n - 1 - k) * 30.44))).isoformat(), "valeur": round(v, 6)}
            for k, v in enumerate(valeurs)]


def _vrai(sim, x0, pas, pas_fn, seuil) -> float:
    hits = 0
    for _ in range(N_SIM):
        y = x0
        for _ in range(pas):
            y = pas_fn(y, sim)
            if y >= seuil:
                hits += 1
                break
    return (hits + 0.5) / (N_SIM + 1)


def cas_croissance(rnd: random.Random) -> dict:
    ans = int(rnd.uniform(15, 40))
    g, s = rnd.uniform(0.01, 0.08), rnd.uniform(0.01, 0.04)
    x, vals = rnd.uniform(100, 5000), []
    for _ in range(ans):
        x *= math.exp(g + rnd.gauss(0, s))
        vals.append(x)
    pts = [{"date": (FIN - timedelta(days=int((ans - 1 - k) * 365.25))).isoformat(), "valeur": round(v, 4)}
           for k, v in enumerate(vals)]
    W = rnd.choice([365, 730, 1095])
    pas = round(W / 365.25)
    seuil = x * math.exp(g * pas * rnd.uniform(0.3, 2.0) + rnd.uniform(0, 1.5) * s * math.sqrt(pas))
    vrai = _vrai(random.Random(rnd.random()), x, pas, lambda y, r: y * math.exp(g + r.gauss(0, s)), seuil)
    return {"genre": "C", "releve": {"debut": pts[0]["date"], "date_limite": FIN.isoformat(), "points": pts},
            "W": W, "mode": "atteint", "seuil": round(seuil, 4), "sens": ">=", "nature": "niveau", "vrai": vrai}


def cas_rupture(rnd: random.Random) -> dict:
    mois = int(rnd.uniform(5, 30) * 12)
    sigma = rnd.uniform(0.5, 3)
    choc = rnd.choice([-1, 1]) * rnd.uniform(8, 20) * sigma
    quand = rnd.randrange(mois // 5, mois - 3)
    x, vals = rnd.uniform(-10, 10), []
    for k in range(mois):
        x += rnd.gauss(0, sigma) + (choc if k == quand else 0.0)
        vals.append(x)
    W = rnd.choice(W_NIV)
    pas = max(1, round(W / 30.44))
    seuil = x + rnd.uniform(0.2, 2.5) * sigma * math.sqrt(pas)
    vrai = _vrai(random.Random(rnd.random()), x, pas, lambda y, r: y + r.gauss(0, sigma), seuil)
    pts = _mensuel(vals)
    return {"genre": "R", "releve": {"debut": pts[0]["date"], "date_limite": FIN.isoformat(), "points": pts},
            "W": W, "mode": "atteint", "seuil": round(seuil, 4), "sens": ">=", "nature": "niveau", "vrai": vrai}


def cas_retour(rnd: random.Random) -> dict:
    mois = int(rnd.uniform(5, 30) * 12)
    phi, sigma, mu = rnd.uniform(0.70, 0.97), rnd.uniform(0.1, 0.5), rnd.uniform(2, 10)
    x = mu + rnd.gauss(0, sigma / math.sqrt(1 - phi * phi))
    vals = []
    for _ in range(mois):
        x = mu + phi * (x - mu) + rnd.gauss(0, sigma)
        vals.append(x)
    W = rnd.choice(W_NIV)
    pas = max(1, round(W / 30.44))
    sd = sigma / math.sqrt(1 - phi * phi)
    seuil = max(x, mu) + rnd.uniform(0.2, 2.0) * sd
    vrai = _vrai(random.Random(rnd.random()), x, pas, lambda y, r: mu + phi * (y - mu) + r.gauss(0, sigma), seuil)
    pts = _mensuel(vals)
    return {"genre": "M", "releve": {"debut": pts[0]["date"], "date_limite": FIN.isoformat(), "points": pts},
            "W": W, "mode": "atteint", "seuil": round(seuil, 4), "sens": ">=", "nature": "niveau", "vrai": vrai}


def cas_bornee(rnd: random.Random) -> dict:
    mois = int(rnd.uniform(3, 20) * 12)
    sigma = rnd.uniform(0.05, 0.3)
    z, vals = rnd.uniform(-1, 3.5), []
    for _ in range(mois):
        z += rnd.gauss(0, sigma)
        vals.append(100 / (1 + math.exp(-z)))
    W = rnd.choice(W_NIV)
    pas = max(1, round(W / 30.44))
    x = vals[-1]
    seuil = min(99.9, x + rnd.uniform(0.2, 1.0) * (100 - x))
    vrai = _vrai(random.Random(rnd.random()), z, pas, lambda y, r: y + r.gauss(0, sigma),
                 math.log((seuil / 100) / (1 - seuil / 100)))
    pts = _mensuel(vals)
    return {"genre": "B", "releve": {"debut": pts[0]["date"], "date_limite": FIN.isoformat(), "points": pts},
            "W": W, "mode": "atteint", "seuil": round(seuil, 4), "sens": ">=", "nature": "niveau", "vrai": vrai,
            "bornes": (0.0, 100.0)}


GENRES = [cas_evenements, cas_niveaux, cas_croissance, cas_rupture, cas_retour, cas_bornee]


def generer(graine: int) -> dict:
    return GENRES[graine % len(GENRES)](random.Random(graine))


def juger(graines) -> dict:
    tot, par, abst = [], {}, 0
    for g in graines:
        c = generer(g)
        try:
            kw = {"bornes": c["bornes"]} if c.get("bornes") else {}
            r = compter(c["releve"], c["W"], c["mode"], c["seuil"], c["sens"], None, fin=FIN, nature=c["nature"], **kw)
            q = r.get("frequence")
        except TypeError:
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
    print(json.dumps(juger(range(200000, 200300) if args.cache else range(600)), ensure_ascii=False))
