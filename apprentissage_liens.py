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

Découpage dans le temps : les jeux les plus récents, pris EN ENTIER jusqu'à couvrir au moins le tiers des lectures,
servent au jugement ; les jeux plus anciens à l'apprentissage (décision d'auteur du 2026-11-14, voir `decouper`).

Statut de chaque lien (apprentissage) : intervalle à 90 % (approximation de Laplace) ; « pousse » s'il est au-dessus
de 0, « retient » s'il est au-dessous, « ne dit rien » s'il contient 0 avec au moins 30 cas, « indéterminé » sinon.

Critère d'adoption (jugement) : le « C empirique » ne remplace la matrice que si, sur le tiers de jugement, sa perte
log est inférieure à celle de B ET que l'intervalle à 90 % de l'écart apparié (bootstrap, 2 000 tirages, graine 0)
reste au-dessous de 0, avec au moins 100 lectures de jugement. Même alors, il entre en ombre ; le remplacement est une
décision d'auteur datée. Rien n'est écrit au registre ; rien n'est posté.

Stabilité (ajout du 2026-11-14, EN OMBRE ; Al Mamun, « From Data to Decision », §32.5 ; Meinshausen et Bühlmann 2010) :
pour chaque lien qui « pousse » ou « retient », le modèle est réajusté sur 200 tirages bootstrap des lectures
d'apprentissage (graine 0) ; « stabilite » est la part des tirages où l'intervalle à 90 % reste du même côté de 0.
Au-dessous de 80 %, le lien est dit « limite ». Le statut du protocole ne change pas : la stabilité est rapportée à côté,
parce que 36 liens testés chacun à 90 % laissent attendre quelques statuts par hasard (inférence après sélection).

Blocs (ajout du 2026-11-14, EN OMBRE ; dépôt calibrain-harness : des décisions qui se recouvrent valent moins que
leur nombre). Les questions d'un même jeu et d'une même source partagent la même semaine du monde (mêmes chocs) : elles
ne sont pas indépendantes. Le bootstrap officiel tire les lectures une par une ; l'ombre tire des BLOCS « jeu × source »
entiers, pour l'intervalle du critère d'adoption et pour la stabilité. Le critère officiel ne change pas ; le rapport
donne les deux, et le nombre de blocs (avec peu de blocs, l'intervalle par blocs est lui-même grossier).

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
             "bootstrap": 2000, "niveau": 0.90,
             # décision d'auteur du 2026-11-14 (0.10.89) : le jugement prend des JEUX ENTIERS, les plus récents
             "decoupage": "jeux_entiers", "decoupage_decide_le": "2026-11-14"}
STABILITE = {"ajoute_le": "2026-11-14", "tirages": 200, "graine": 0, "seuil": 0.80, "statut": "ombre"}


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
        jeu_ = x.get("jeu") or x["question_id"].split(":")[1]
        out.append({"q": x["question_id"], "jeu": jeu_, "bloc": f"{jeu_}:{x['question_id'].split(':')[2]}",
                    "y": int(x["issue"]),
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


def decouper(D: list[dict]) -> tuple[list[dict], list[dict]]:
    """0.10.89 (décision d'auteur du 2026-11-14). Le jugement prend les jeux les plus récents EN ENTIER, ajoutés un par un
    jusqu'à couvrir au moins le tiers des lectures ; l'apprentissage, les jeux plus anciens. Un jeu n'est jamais coupé
    en deux : l'apprentissage et le jugement ne partagent pas la même semaine du monde. Avant 0.10.89, la coupe se
    faisait au nombre de lignes, triées par identifiant : le dernier tiers était presque entièrement les questions FRED
    du dernier jeu (calculée en ombre, `ombre_ancien_decoupage`). Avec un seul jeu, pas de jugement."""
    jeux = sorted({d["jeu"] for d in D})
    if len(jeux) < 2:
        return D, []
    juge: list[str] = []
    n_j = 0
    for j in reversed(jeux[1:]):                  # le jeu le plus ancien reste toujours à l'apprentissage
        juge.append(j)
        n_j += sum(1 for d in D if d["jeu"] == j)
        if n_j >= len(D) * PROTOCOLE["part_jugement"]:
            break
    return [d for d in D if d["jeu"] not in juge], [d for d in D if d["jeu"] in juge]


def tirer_blocs(D: list[dict], rnd: random.Random) -> list[dict]:
    """Un tirage bootstrap par blocs : autant de blocs que dans D, tirés avec remise, chacun avec toutes ses lectures."""
    blocs: dict[str, list[dict]] = {}
    for d in D:
        blocs.setdefault(d.get("bloc") or d["q"], []).append(d)
    cles = sorted(blocs)
    return [d for _ in cles for d in blocs[rnd.choice(cles)]]


def stabilite(A: list[dict], statuts: dict[str, str], par_blocs: bool = False) -> dict[str, float]:
    """Part des tirages bootstrap où l'intervalle à 90 % du lien reste du côté de son statut (ombre, 2026-11-14).
    par_blocs : tirage par blocs « jeu × source » (ombre)."""
    if not statuts:
        return {}
    zq = 1.6449
    rnd = random.Random(STABILITE["graine"])
    compte = {n: 0 for n in statuts}
    for _ in range(STABILITE["tirages"]):
        S = tirer_blocs(A, rnd) if par_blocs else [rnd.choice(A) for _ in A]
        nb = sorted({n for d in S for n in d["x"]})
        be, es = ajuster(S, nb)
        for n, st in statuts.items():
            if n in be:
                compte[n] += (be[n] - zq * es[n] > 0) if st == "pousse" else (be[n] + zq * es[n] < 0)
    return {n: c / STABILITE["tirages"] for n, c in compte.items()}


def principal(en_json: bool) -> int:
    f = ap.REGISTRE / ar.RETRO
    L = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()] if f.is_file() else []
    D = donnees(L)
    jeux = sorted({d["jeu"] for d in D})
    A, J = decouper(D)
    coupe_ancienne = len(D) - int(round(len(D) * PROTOCOLE["part_jugement"]))
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
    # stabilité (ombre) : seulement pour les liens qui sortent
    for n, st_ in stabilite(A, {n: v["statut"] for n, v in liens.items() if v["statut"] in ("pousse", "retient")}).items():
        liens[n]["stabilite"] = round(st_, 3)
        liens[n]["stable"] = st_ >= STABILITE["seuil"]
    for n, st_ in stabilite(A, {n: v["statut"] for n, v in liens.items() if v["statut"] in ("pousse", "retient")},
                            par_blocs=True).items():
        liens[n]["stabilite_blocs"] = round(st_, 3)
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
        # ombre : même intervalle, tirage par blocs « jeu × source »
        ecb = [dict(d, e=e_) for d, e_ in zip(J, ec)]
        rnd_b = random.Random(0)
        boots_b = []
        for _ in range(PROTOCOLE["bootstrap"]):
            S = tirer_blocs(ecb, rnd_b)
            boots_b.append(sum(d["e"] for d in S) / len(S))
        boots_b.sort()
        bas_b, haut_b = boots_b[int(q * len(boots_b))], boots_b[int((1 - q) * len(boots_b)) - 1]
        jug["ombre_blocs"] = {"blocs": len({d["bloc"] for d in J}), "intervalle_90_ecart": [bas_b, haut_b],
                              "critere_atteint": len(J) >= PROTOCOLE["n_min_jugement"] and sum(ec) < 0 and haut_b < 0}
    ancien = None
    A0, J0 = D[:coupe_ancienne], D[coupe_ancienne:]
    if A0 and J0:
        n0 = sorted({n for d in A0 for n in d["x"]})
        b0, _ = ajuster(A0, n0)
        ancien = {"apprentissage": len(A0), "jugement": len(J0),
                  "perte_B": sum(perte(d["B"], d["y"]) for d in J0) / len(J0),
                  "perte_C_empirique": sum(perte(predire(d, b0), d["y"]) for d in J0) / len(J0)}
    rap = {"protocole": PROTOCOLE, "ombre_ancien_decoupage": ancien, "stabilite_ombre": STABILITE, "lectures": len(D), "jeux": jeux, "apprentissage": len(A), "jugement": jug,
           "liens": dict(sorted(liens.items(), key=lambda t: -t[1]["n"]))}
    print(json.dumps(rap, ensure_ascii=False, indent=1 if en_json else None))
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--json", action="store_true")
    sys.exit(principal(a.parse_args().json))
