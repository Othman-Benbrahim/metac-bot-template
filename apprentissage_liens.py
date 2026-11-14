"""Apprentissage empirique des liens carte → événement (0.10.80 ; protocole enregistré le 2026-11-14, décision
d'auteur : le sens et la portée d'un lien se mesurent sur les issues, ils ne se décident pas).

Données : lignes du banc ForecastBench écrites À PARTIR de la version PROTOCOLE["depuis_version"], lues par le SEUL
lecteur PROTOCOLE["lecteur"], avec issue et B. Les lectures plus anciennes ou d'un autre lecteur ont servi à formuler
le protocole : elles ne comptent pas.

Variables (fixées avant toute lecture d'apprentissage) :
  - événement « apparaît » : un indicateur par lien « CARTE ancrée dans la strate de l'événement → CARTE de
    l'événement » (une carte ancrée hors de cette strate n'entre pas : trop rare pour être apprise) ;
  - événement « persiste » ou « disparaît » : un indicateur « persiste:CARTE » (ou « disparait:CARTE »).
Modèle : logit P(OUI) = logit(B) + Σ β_lien · présence ; régularisation L2 (loi a priori normale centrée sur 0,
écart-type 0,5 sur chaque β : un lien ne déplace pas la cote de plus d'un facteur 2,7 sans données) ; Newton.

Découpage dans le temps : les lectures sont ordonnées par date de jeu ; le dernier tiers (jeux les plus récents) sert
au jugement, les deux premiers tiers à l'apprentissage.

Statut de chaque lien (apprentissage) : intervalle à 90 % (approximation de Laplace) ; « pousse » s'il est au-dessus
de 0, « retient » s'il est au-dessous, « ne dit rien » s'il contient 0 avec au moins 30 cas, « indéterminé » sinon.

Critère d'adoption (jugement) : le « C empirique » ne remplace la matrice que si, sur le tiers de jugement, sa perte
log est inférieure à celle de B ET que l'intervalle à 90 % de l'écart apparié (bootstrap, 2 000 tirages, graine 0)
reste au-dessous de 0, avec au moins 100 lectures de jugement. Même alors, il entre en ombre ; le remplacement est une
décision d'auteur datée. Rien n'est écrit au registre ; rien n'est posté.

    python apprentissage_liens.py [--json]
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys

import alphabet_pipeline as ap
import alphabet_retro as ar

PROTOCOLE = {"enregistre_le": "2026-11-14", "depuis_version": "0.10.80", "lecteur": "mistral/mistral-medium-latest",
             "ecart_type_a_priori": 0.5, "part_jugement": 1 / 3, "n_min_lien": 30, "n_min_jugement": 100,
             "bootstrap": 2000, "niveau": 0.90}


def _v(v) -> tuple:
    try:
        return tuple(int(x) for x in str(v).split("."))
    except ValueError:
        return (0,)


def _logit(p: float) -> float:
    p = min(max(p, 1e-3), 1 - 1e-3)
    return math.log(p / (1 - p))


def variables(x: dict) -> list[str]:
    """Les liens présents dans la DERNIÈRE lecture de la ligne (rejeu), selon les règles du protocole."""
    r = x.get("rejeu") or {}
    ev = (r.get("plan") or {}).get("evenement") or {}
    try:
        c_ev = ap.code_carte(ev.get("carte"))
    except Exception:
        return []
    typ, s_ev = ev.get("type"), str(ev.get("strate"))
    if typ != "apparait":
        return [f"{typ}:{c_ev}"]
    out = set()
    for m in ((r.get("lectures") or [{}])[-1] or {}).get("mots") or []:
        if not isinstance(m, dict) or str(m.get("strate")) != s_ev:
            continue
        try:
            out.add(f"{ap.code_carte(m.get('carte'))}→{c_ev}")
        except Exception:
            continue
    return sorted(out)


def donnees(lignes: list[dict]) -> list[dict]:
    out = []
    for x in lignes:
        if (x.get("banc") != "forecastbench" or x.get("issue") not in (0, 1) or x.get("p_B") is None
                or _v(x.get("version_bot")) < _v(PROTOCOLE["depuis_version"])
                or (x.get("modeles") or {}).get("principal") != PROTOCOLE["lecteur"]
                or not (x.get("rejeu") or {}).get("lectures")):
            continue
        out.append({"q": x["question_id"], "jeu": x.get("jeu") or x["question_id"].split(":")[1], "y": int(x["issue"]),
                    "B": float(x["p_B"]), "x": variables(x)})
    return sorted(out, key=lambda d: (d["jeu"], d["q"]))


def ajuster(D: list[dict], noms: list[str]) -> tuple[dict, dict]:
    """β (MAP, a priori normal) et leur écart-type de Laplace."""
    k = len(noms)
    idx = {n: i for i, n in enumerate(noms)}
    lam = 1 / PROTOCOLE["ecart_type_a_priori"] ** 2
    b = [0.0] * k
    H = None
    for _ in range(50):
        g = [lam * bi for bi in b]
        H = [[lam if i == j else 0.0 for j in range(k)] for i in range(k)]
        for d in D:
            ii = [idx[n] for n in d["x"] if n in idx]
            z = _logit(d["B"]) + sum(b[i] for i in ii)
            p = 1 / (1 + math.exp(-z))
            for i in ii:
                g[i] += p - d["y"]
                for j in ii:
                    H[i][j] += p * (1 - p)
        pas = _resoudre(H, g)
        b = [bi - si for bi, si in zip(b, pas)]
        if max((abs(s) for s in pas), default=0) < 1e-9:
            break
    inv = _inverse(H) if k else []
    return ({n: b[idx[n]] for n in noms}, {n: math.sqrt(max(inv[idx[n]][idx[n]], 0)) for n in noms})


def _resoudre(A: list[list[float]], y: list[float]) -> list[float]:
    n = len(y)
    M = [row[:] + [y[i]] for i, row in enumerate(A)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(M[r][c]))
        M[c], M[piv] = M[piv], M[c]
        for r in range(n):
            if r != c and M[c][c]:
                f = M[r][c] / M[c][c]
                M[r] = [a - f * b for a, b in zip(M[r], M[c])]
    return [M[i][n] / M[i][i] if M[i][i] else 0.0 for i in range(n)]


def _inverse(A: list[list[float]]) -> list[list[float]]:
    n = len(A)
    cols = [_resoudre(A, [1.0 if i == j else 0.0 for i in range(n)]) for j in range(n)]
    return [[cols[j][i] for j in range(n)] for i in range(n)]


def predire(d: dict, beta: dict) -> float:
    z = _logit(d["B"]) + sum(beta.get(n, 0.0) for n in d["x"])
    return 1 / (1 + math.exp(-z))


def perte(p: float, y: int) -> float:
    p = min(max(p, 1e-3), 1 - 1e-3)
    return -math.log(p if y else 1 - p)


def principal(en_json: bool) -> int:
    f = ap.REGISTRE / ar.RETRO
    L = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()] if f.is_file() else []
    D = donnees(L)
    jeux = sorted({d["jeu"] for d in D})
    coupe = len(D) - int(round(len(D) * PROTOCOLE["part_jugement"]))
    A, J = D[:coupe], D[coupe:]
    noms = sorted({n for d in A for n in d["x"]})
    beta, et = ajuster(A, noms) if A else ({}, {})
    zq = 1.6449
    liens = {}
    for n in noms:
        cas = [d for d in A if n in d["x"]]
        lo, hi = beta[n] - zq * et[n], beta[n] + zq * et[n]
        statut = ("pousse" if lo > 0 else "retient" if hi < 0 else
                  "ne dit rien" if len(cas) >= PROTOCOLE["n_min_lien"] else "indéterminé")
        liens[n] = {"n": len(cas), "oui": sum(d["y"] for d in cas), "beta": round(beta[n], 3),
                    "facteur_de_cote": round(math.exp(beta[n]), 2), "intervalle_90": [round(lo, 3), round(hi, 3)],
                    "statut": statut}
    jug = None
    if J:
        ec = [perte(predire(d, beta), d["y"]) - perte(d["B"], d["y"]) for d in J]
        rnd = random.Random(0)
        boots = sorted(sum(rnd.choice(ec) for _ in ec) / len(ec) for _ in range(PROTOCOLE["bootstrap"]))
        q = (1 - PROTOCOLE["niveau"]) / 2
        bas, haut = boots[int(q * len(boots))], boots[int((1 - q) * len(boots)) - 1]
        jug = {"n": len(J), "perte_B": sum(perte(d["B"], d["y"]) for d in J) / len(J),
               "perte_C_empirique": sum(perte(predire(d, beta), d["y"]) for d in J) / len(J),
               "ecart_moyen": sum(ec) / len(ec), "intervalle_90_ecart": [bas, haut],
               "critere_atteint": len(J) >= PROTOCOLE["n_min_jugement"] and sum(ec) < 0 and haut < 0}
    rap = {"protocole": PROTOCOLE, "lectures": len(D), "jeux": jeux, "apprentissage": len(A), "jugement": jug,
           "liens": dict(sorted(liens.items(), key=lambda t: -t[1]["n"]))}
    print(json.dumps(rap, ensure_ascii=False, indent=1 if en_json else None))
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--json", action="store_true")
    sys.exit(principal(a.parse_args().json))
