"""Influence × connexion : une population en réseau, des propriétaires de médias, des plateformes (bot 0.10.347, ombre).

Demande de l'auteur du 2026-11-19, 13 h 44 : simuler qui interagit avec qui et à quel niveau (proches, connaissances,
connaissances de connaissances), avec des forces de lien selon le statut ou l'influence, et relier cela à l'influence
des masses par convergence éditoriale (peu de propriétaires) et algorithmique (peu de plateformes). C'est un MODÈLE
SYNTHÉTIQUE : aucune personne réelle n'y figure ; ses paramètres viennent de la littérature (sources dans
lectures/reseaux-influence.md) et sont faits pour être recalibrés.

Construction
- N individus répartis en communautés de 150 (Dunbar) posées sur un anneau.
- Liens par couches emboîtées de Dunbar (5, 15, 50, 150 ; rapport ≈ 3), de poids décroissant (1 ; 0,5 ; 0,25 ; 0,1).
  Les trois premières couches sont prises dans la communauté ; la dernière (connaissances) l'est aussi, sauf une part
  p_loin de liens lointains tirés au hasard dans toute la population (liens faibles de Granovetter, petit monde de
  Watts et Strogatz).
- Statut : loi de Pareto (α = 2) ; il multiplie le poids de ce que dit un individu (influence) à la puissance gamma.
- Médias : des titres possédés par quelques propriétaires, d'audience très inégale ; chaque individu suit quelques
  titres, choisis selon l'audience. La CONVERGENCE ÉDITORIALE est le nombre de propriétaires (les plus gros d'abord)
  dont tous les titres portent le même message.
- Plateformes : l'AMPLIFICATION ALGORITHMIQUE a multiplie le poids des liens faibles (couches 3 et 4) et des individus
  de haut statut quand le message circule (Huszár et al. 2022 : des contenus atteignent 1,5 à 2,7 fois plus de
  monde avec le fil algorithmique qu'avec le fil chronologique).

Dynamique (seuils de Granovetter, de Schelling et de Watts et Dodds)
- Chacun adopte quand l'exposition dépasse son seuil (seuils distribués, loi normale mu, sigma). Exposition = part
  pondérée de ses liens qui ont adopté (poids × statut^gamma, amplifiés) + beta × part de ses titres qui portent le
  message. On itère jusqu'à l'arrêt. Sortie : part finale d'adoptants, nombre de tours, part due aux médias seuls.

    python reseau_influence.py            # grille influence × connexion → registre/influence-connexion.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy import sparse

SORTIE = Path("registre") / "influence-connexion.json"
COUCHES = (5, 10, 35, 100)          # tailles des couches successives (cumul 5, 15, 50, 150)
POIDS = (1.0, 0.5, 0.25, 0.1)
COMMUNAUTE = 150


def construire(n: int = 20000, p_loin: float = 0.2, gamma: float = 1.0, graine: int = 0) -> dict:
    """Réseau synthétique : matrice des liens (poids de couche), couche de chaque lien, statut."""
    rng = np.random.default_rng(graine)
    statut = rng.pareto(2.0, n) + 1.0
    lignes, cols, poids, couche = [], [], [], []
    for i in range(n):
        debut = (i // COMMUNAUTE) * COMMUNAUTE
        membres = np.arange(debut, min(debut + COMMUNAUTE, n))
        membres = membres[membres != i]
        ordre = rng.permutation(membres)
        k = 0
        for c, (taille, w) in enumerate(zip(COUCHES, POIDS)):
            pris = ordre[k:k + taille]
            k += taille
            if c == len(COUCHES) - 1 and p_loin > 0:   # connaissances : une part de liens lointains
                loin = rng.random(len(pris)) < p_loin
                pris = np.where(loin, rng.integers(0, n, len(pris)), pris)
            pris = pris[pris != i]
            lignes += [i] * len(pris)
            cols += pris.tolist()
            poids += [w] * len(pris)
            couche += [c] * len(pris)
    A = sparse.csr_matrix((poids, (lignes, cols)), shape=(n, n))
    C = sparse.csr_matrix((np.array(couche) + 1, (lignes, cols)), shape=(n, n))   # couche + 1 (0 = pas de lien)
    return {"n": n, "A": A, "C": C, "statut": statut, "gamma": gamma, "p_loin": p_loin}


def degres(res: dict, echantillon: int = 200, graine: int = 1) -> dict:
    """Part de la population atteinte en 1, 2, 3, 4 pas (proches, connaissances, connaissances de connaissances…)
    et distance moyenne estimée, sur un échantillon de départs (liens rendus non orientés)."""
    rng = np.random.default_rng(graine)
    G = ((res["A"] + res["A"].T) > 0).astype(np.int8).tocsr()
    n = res["n"]
    parts = {1: [], 2: [], 3: [], 4: []}
    dist = []
    for s in rng.choice(n, min(echantillon, n), replace=False):
        vu = np.zeros(n, bool)
        vu[s] = True
        front = np.zeros(n, bool)
        front[s] = True
        d = 0
        somme, nb = 0, 0
        while front.any():
            d += 1
            nouv = (G[front].sum(axis=0).A1 > 0) & ~vu
            if not nouv.any():
                break
            vu |= nouv
            somme += d * nouv.sum()
            nb += nouv.sum()
            if d in parts:
                parts[d].append(vu.sum() / n)
            front = nouv
        for k in parts:
            if len(parts[k]) < len(dist) + 1:
                parts[k].append(vu.sum() / n)
        dist.append(somme / max(nb, 1))
    return {"part_atteinte": {f"{k}_pas": round(float(np.mean(v)), 4) for k, v in parts.items()},
            "distance_moyenne": round(float(np.mean(dist)), 2)}


def medias(n: int, n_titres: int = 50, n_proprietaires: int = 25, suivis: int = 3, graine: int = 2) -> dict:
    """Titres d'audience très inégale (Zipf), répartis entre propriétaires (les gros en possèdent plusieurs)."""
    rng = np.random.default_rng(graine)
    audience = 1 / np.arange(1, n_titres + 1)
    audience /= audience.sum()
    prop_poids = 1 / np.arange(1, n_proprietaires + 1) ** 1.2
    proprietaire = rng.choice(n_proprietaires, n_titres, p=prop_poids / prop_poids.sum())
    lecteurs = np.array([rng.choice(n_titres, suivis, replace=False, p=audience) for _ in range(n)])
    part_prop = np.array([audience[proprietaire == o].sum() for o in range(n_proprietaires)])
    return {"proprietaire": proprietaire, "lecteurs": lecteurs, "part_audience_proprietaire": part_prop,
            "hhi": round(float((part_prop ** 2).sum()), 4)}


def diffuser(res: dict, med: dict, aligne: int = 0, ampli: float = 1.0, beta: float = 0.3, mu: float = 0.35,
             sigma: float = 0.12, part_graines: float = 0.005, graines_influentes: bool = False, graine: int = 3,
             tours_max: int = 200) -> dict:
    """Diffusion à seuils. aligne : nombre de propriétaires (par audience décroissante) dont les titres portent le
    message. ampli : amplification algorithmique des liens faibles et des hauts statuts."""
    rng = np.random.default_rng(graine)
    n = res["n"]
    C = res["C"]
    W = res["A"].copy().astype(float)
    # amplification : couches 3 et 4 (liens faibles) multipliées par ampli ; le statut de l'émetteur, à la puissance
    # gamma, et doublement amplifié pour les hauts statuts (le fil met en avant ce qui engage)
    faibles = (C.data >= 3)
    W.data = W.data * np.where(faibles, ampli, 1.0)
    s = res["statut"] ** res["gamma"]
    s_amp = s * np.where(res["statut"] > np.quantile(res["statut"], 0.9), ampli, 1.0)
    W = W @ sparse.diags(s_amp)
    tot = np.asarray(W.sum(axis=1)).ravel() + 1e-12
    seuil = np.clip(rng.normal(mu, sigma, n), 0.01, None)
    ordre_prop = np.argsort(-med["part_audience_proprietaire"])
    porteurs = np.isin(med["proprietaire"], ordre_prop[:aligne])
    expo_media = porteurs[med["lecteurs"]].mean(axis=1) if aligne else np.zeros(n)
    k = max(1, int(part_graines * n))
    graines = np.argsort(-res["statut"])[:k] if graines_influentes else rng.choice(n, k, replace=False)
    adopte = np.zeros(n, bool)
    adopte[graines] = True
    seul_media = (beta * expo_media >= seuil)
    for t in range(1, tours_max + 1):
        pair = (W @ adopte.astype(float)) / tot
        nouv = (pair + beta * expo_media >= seuil) & ~adopte
        if not nouv.any():
            break
        adopte |= nouv
    return {"part_adoptants": round(float(adopte.mean()), 4), "tours": t,
            "part_par_les_medias_seuls": round(float(seul_media.mean()), 4)}


PLANETE = 8.1e9


def grille(n: int = 20000) -> dict:
    """Grille influence × connexion. Le seuil moyen mu règle la « résistance » de la population : sans lui, tout bascule
    ou rien ne bouge, et l'on ne voit rien ; c'est la frontière entre les deux qui est l'objet."""
    out = {"n": n, "parametres": {"couches": COUCHES, "poids": POIDS, "communaute": COMMUNAUTE, "beta_medias": 0.3},
           "reseaux": {}, "essais": []}
    med = medias(n)
    out["medias"] = {"hhi_audience_proprietaires": med["hhi"],
                     "part_audience_3_premiers": round(float(np.sort(med["part_audience_proprietaire"])[::-1][:3].sum()), 3)}
    for p_loin in (0.0, 0.2):
        res = construire(n, p_loin=p_loin)
        d = degres(res)
        k = res["A"].nnz / n
        d["degre_moyen"] = round(k, 1)
        d["distance_extrapolee_planete"] = round(float(np.log(PLANETE) / np.log(k)), 2) if p_loin > 0 else None
        out["reseaux"][str(p_loin)] = d
        for mu in (0.35, 0.5, 0.65):
            for aligne in (0, 1, 3):
                for ampli in (1.0, 2.7):
                    for infl in (False, True):
                        r = diffuser(res, med, aligne=aligne, ampli=ampli, mu=mu, graines_influentes=infl)
                        out["essais"].append({"p_loin": p_loin, "seuil_moyen": mu, "proprietaires_alignes": aligne,
                                              "amplification": ampli, "graines": "influentes" if infl else "au hasard", **r})
    return out


def principal() -> int:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    r = grille(n)
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in r.items() if k != "essais"}, ensure_ascii=False, indent=1))
    print(f"{'loin':>5} {'seuil':>5} {'alignés':>7} {'ampli':>5} {'graines':>11} {'adoptants':>9} {'médias seuls':>12} tours")
    for e in r["essais"]:
        print(f"{e['p_loin']:>5} {e['seuil_moyen']:>5} {e['proprietaires_alignes']:>7} {e['amplification']:>5} {e['graines']:>11} "
              f"{e['part_adoptants']:>9} {e['part_par_les_medias_seuls']:>12} {e['tours']}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
