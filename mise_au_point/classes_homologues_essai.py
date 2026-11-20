"""Mise au point (pas un verdict) : la classe homologue apporte-t-elle plus que la moyenne générale ? (0.10.385)

Accord de l'auteur, 2026-11-20, 12 h 29. Questions d'occurrence de l'échantillon de mise au point qui entrent dans une
classe homologue (classes_homologues.py) ayant au moins 30 questions PASSÉES à la date jugée. Trois calculs :
  A  calcul actuel (semblables) ;
  I  témoin : 80 % semblables + 20 % taux de base (moyenne générale, sans structure) — en log-cotes ;
  J  80 % semblables + 20 % taux de la classe homologue (même fiche, même nature d'acteur, même rapport
     fenêtre / vitesse), passé seulement, rétréci vers le taux de base (poids 5).
La question qui compte pour l'hypothèse : J fait-il mieux que I ?

    python mise_au_point/classes_homologues_essai.py   # écrit registre/mise-au-point/classes-homologues.json
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

import banc_jugement as bj
import brique_fenetre as bf
import classes_homologues as ch
import fenetre_variantes as fv

SORTIE = Path("registre") / "mise-au-point" / "classes-homologues.json"
MIN_N, M, POIDS = 30, 5.0, 0.2


def lg(p):
    p = min(0.98, max(0.02, p))
    return math.log(p / (1 - p))


def sig(z):
    return 1 / (1 + math.exp(-z))


def principal() -> int:
    xs = fv.charger()
    bj.calculer(xs)
    occ = [x for x in xs if x["structure"] in bf.OCCURRENCE]
    for x in occ:
        k = ch.classe(x["titre"], x["horizon"])
        x["classe"] = k["cle"] if k else None
    fin = np.array([max(x["resolue_le"], x.get("cloture", "")) for x in occ])
    ids = np.array([f'{x["source"]}:{x["id"]}' for x in occ])
    y = np.array([x["issue"] for x in occ], dtype=float)
    cl = np.array([x["classe"] or "" for x in occ])
    cibles = []
    for i, x in enumerate(occ):
        if not x["classe"]:
            continue
        ok = (fin < x["jeu"]) & (ids != ids[i]) & (cl == x["classe"])
        if ok.sum() < MIN_N:
            continue
        r = (y[ok].sum() + M * x["p_R1"]) / (ok.sum() + M)
        x["r_classe"], x["n_classe"] = float(r), int(ok.sum())
        x["p_I"] = sig((1 - POIDS) * lg(x["p_S"]) + POIDS * lg(x["p_R1"]))
        x["p_J"] = sig((1 - POIDS) * lg(x["p_S"]) + POIDS * lg(r))
        cibles.append(x)
    pl = bj.cb.pl
    groupes = {"registre ForecastBench 2024-2026 (le monde des fiches)": [x for x in cibles if not x["source"].startswith("fr_")],
               "Metaculus, GJOpen, CSET 2015-2024": [x for x in cibles if x["source"] in ("fr_metaculus", "fr_gjopen", "fr_cset")],
               "Manifold 2015-2024": [x for x in cibles if x["source"] == "fr_manifold"],
               "tout": cibles}
    r = {"questions_occurrence": len(occ), "dans_une_classe": sum(1 for x in occ if x["classe"]),
         "jugees (classe de 30 passées ou plus)": len(cibles), "groupes": {}}
    for g, s in groupes.items():
        if not s:
            continue
        pm = lambda k: round(sum(pl(x[k], x["issue"]) for x in s) / len(s), 4)
        e = [(f'{x["source"]}:{x["id"]}', pl(x["p_J"], x["issue"]) - pl(x["p_I"], x["issue"])) for x in s]
        bas, haut = bj.cb.bootstrap(e, 0.05)
        r["groupes"][g] = {"n": len(s), "questions_distinctes": len({k for k, _ in e}),
                           "pertes": {"A semblables": pm("p_S"), "I témoin moyenne générale": pm("p_I"), "J classe homologue": pm("p_J")},
                           "J_moins_I": {"moyenne": round(sum(v for _, v in e) / len(e), 4), "intervalle_90": [round(bas, 4), round(haut, 4)]}}
    par = {}
    for x in groupes["registre ForecastBench 2024-2026 (le monde des fiches)"] + groupes["Metaculus, GJOpen, CSET 2015-2024"]:
        par.setdefault(x["classe"], []).append(pl(x["p_J"], x["issue"]) - pl(x["p_I"], x["issue"]))
    r["par_classe_hors_manifold"] = {k: {"n": len(v), "J_moins_I": round(sum(v) / len(v), 4)} for k, v in sorted(par.items(), key=lambda kv: -len(kv[1]))}
    r["note"] = "mise au point, pas un verdict ; perte log, plus bas = mieux ; J − I < 0 : la classe homologue aide plus que la moyenne"
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in r.items() if k != "par_classe_hors_manifold"}, ensure_ascii=False, indent=1))
    for k, v in list(r["par_classe_hors_manifold"].items())[:25]:
        print(v["n"], v["J_moins_I"], k)
    return 0


if __name__ == "__main__":
    sys.exit(principal())
