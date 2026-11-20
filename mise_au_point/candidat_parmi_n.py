"""Mise au point (pas un verdict) : « un candidat parmi N », partir de 1/N (préenregistrement candidat-parmi-n.md).

Accord de l'auteur, 2026-11-20, 15 h 52. Groupes de questions sœurs Metaculus (même titre hors parenthèse finale, N ≥ 2) ;
exclusif ou non décidé sur le seul titre (EXCLUSIF). Témoin I des classes homologues (80 % semblables + 20 % taux de base,
en log-cotes) ; K = 1/N ; K½ = moyenne des log-cotes de 1/N et du témoin. Intervalle à 90 % par rééchantillonnage des
groupes. Manifold : descriptif à part.

    python mise_au_point/candidat_parmi_n.py   # écrit registre/mise-au-point/candidat-parmi-n.json
"""
from __future__ import annotations

import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

import banc_jugement as bj
import fenetre_variantes as fv

SORTIE = Path("registre") / "mise-au-point" / "candidat-parmi-n.json"
PAREN = re.compile(r"^(.*\S)\s*\(([^()]*)\)\s*$")
EXCLUSIF = re.compile(r"\bwho will win\b|\bwho will be\b|\bwhich (?:party|parties|team|country|candidate|company)\b.*\b(?:win|control)\b", re.I)
SAUF = re.compile(r"\bthese\b", re.I)
POIDS = 0.2


def lg(p):
    p = min(0.98, max(0.02, p))
    return math.log(p / (1 - p))


def sig(z):
    return 1 / (1 + math.exp(-z))


def borne(p):
    return min(0.99, max(0.01, p))


def perte(p, y):
    p = borne(p)
    return -math.log(p if y else 1 - p)


def exclusif(titre: str) -> bool:
    return bool(EXCLUSIF.search(titre)) and not SAUF.search(titre)


def groupes(xs: list[dict], source: str) -> dict:
    g = defaultdict(list)
    for x in xs:
        if x["source"] != source:
            continue
        m = PAREN.match(x["titre"])
        if m:
            g[m.group(1)].append(x)
    return {k: v for k, v in g.items() if len(v) >= 2}


def mesurer(g: dict, graine: int = 0) -> dict:
    ex = {k: v for k, v in g.items() if exclusif(k)}
    lignes = []                                    # (groupe, écart K − I, écart K½ − I, pertes)
    for k, v in ex.items():
        n = len(v)
        for x in v:
            pi = sig((1 - POIDS) * lg(x["p_S"]) + POIDS * lg(x["p_R1"]))
            pk = 1 / n
            pkd = sig(0.5 * lg(pk) + 0.5 * lg(pi))
            y = x["issue"]
            lignes.append((k, perte(pk, y) - perte(pi, y), perte(pkd, y) - perte(pi, y), perte(pi, y), perte(pk, y), perte(pkd, y)))
    if not lignes:
        return {"groupes_exclusifs": 0}
    cles = sorted(ex)
    par = defaultdict(list)
    for l in lignes:
        par[l[0]].append(l)
    rng = np.random.default_rng(graine)
    def ic(j):
        moy = []
        for _ in range(2000):
            tir = rng.choice(len(cles), len(cles), replace=True)
            vals = [l[j] for t in tir for l in par[cles[t]]]
            moy.append(sum(vals) / len(vals))
        return [round(float(np.quantile(moy, 0.05)), 4), round(float(np.quantile(moy, 0.95)), 4)]
    m = lambda j: round(sum(l[j] for l in lignes) / len(lignes), 4)
    un_oui = sum(1 for v in ex.values() if sum(x["issue"] for x in v) == 1)
    zero_oui = sum(1 for v in ex.values() if sum(x["issue"] for x in v) == 0)
    return {"groupes_exclusifs": len(ex), "questions": len(lignes),
            "groupes_non_exclusifs (non jugés)": len(g) - len(ex),
            "pertes": {"I témoin": m(3), "K 1/N": m(4), "K½": m(5)},
            "K_moins_I": {"moyenne": m(1), "intervalle_90": ic(1)},
            "Kdemi_moins_I": {"moyenne": m(2), "intervalle_90": ic(2)},
            "diagnostic": {"groupes avec exactement un OUI": un_oui, "groupes sans OUI (N incomplet ?)": zero_oui,
                           "groupes avec plusieurs OUI (expression fautive ?)": len(ex) - un_oui - zero_oui}}


def principal() -> int:
    xs = fv.charger()
    bj.calculer(xs)
    r = {"metaculus (jugé)": mesurer(groupes(xs, "fr_metaculus")),
         "manifold (descriptif)": mesurer(groupes(xs, "fr_manifold")),
         "note": "mise au point, pas un verdict ; perte log, plus bas = mieux ; K − I < 0 : partir de 1/N aide"}
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
