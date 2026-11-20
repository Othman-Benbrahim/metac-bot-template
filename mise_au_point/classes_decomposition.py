"""Mise au point (pas un verdict) : décomposition de la classe homologue en ses éléments (0.10.386).

Accord de l'auteur, 2026-11-20, 13 h 00 (« l'état précède l'essence » : les règles révèlent, elles ne contraignent
pas). Ensemble FIXE de questions : celles que la classe complète (fiche × nature × rapport, même époque de 730 jours)
sait juger (au moins 30 questions passées). Sur ce même ensemble, chaque variante remplace la classe par une partie de
ses éléments ; si la variante n'a pas 30 questions passées pour une question, elle retombe sur le taux de base (= I).
Mesure : perte de la variante moins perte du témoin I (80 % semblables + 20 % taux de base), plus bas = mieux.
Plus l'état observé : part de « oui » par rapport fenêtre / vitesse dans chaque écosystème (sans modèle).

    python mise_au_point/classes_decomposition.py   # écrit registre/mise-au-point/classes-decomposition.json
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

import banc_jugement as bj
import brique_fenetre as bf
import classes_homologues as ch
import fenetre_variantes as fv

SORTIE = Path("registre") / "mise-au-point" / "classes-decomposition.json"
MIN_N, M, POIDS, EPOQUE = 30, 5.0, 0.2, 730
VARIANTES = {"écosystème seul": ("fiche",), "nature seule": ("organisation",), "rapport seul": ("rapport",),
             "époque seule (taux récent, sans structure)": (),
             "écosystème + nature": ("fiche", "organisation"), "écosystème + rapport": ("fiche", "rapport"),
             "nature + rapport": ("organisation", "rapport"), "classe complète": ("fiche", "organisation", "rapport")}


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
        x["k"] = ch.classe(x["titre"], x["horizon"])
    dans = [x for x in occ if x["k"]]                     # toutes les variantes puisent dans les questions classées
    fin = np.array([max(x["resolue_le"], x.get("cloture", "")) for x in dans])
    ids = np.array([f'{x["source"]}:{x["id"]}' for x in dans])
    y = np.array([x["issue"] for x in dans], dtype=float)
    cols = {c: np.array([x["k"][c] for x in dans]) for c in ("fiche", "organisation", "rapport")}

    def taux(i, x, champs):
        ok = (fin < x["jeu"]) & (ids != ids[i]) & (fin >= (date.fromisoformat(x["jeu"]) - timedelta(days=EPOQUE)).isoformat())
        for c in champs:
            ok &= cols[c] == x["k"][c]
        return None if ok.sum() < MIN_N else float((y[ok].sum() + M * x["p_R1"]) / (ok.sum() + M))

    fixes = []
    for i, x in enumerate(dans):
        if taux(i, x, ("fiche", "organisation", "rapport")) is None:
            continue
        x["p_I"] = sig((1 - POIDS) * lg(x["p_S"]) + POIDS * lg(x["p_R1"]))
        for v, champs in VARIANTES.items():
            r = taux(i, x, champs)
            x["p_" + v] = sig((1 - POIDS) * lg(x["p_S"]) + POIDS * lg(r)) if r is not None else x["p_I"]
        fixes.append(x)
    pl = bj.cb.pl
    groupes = {"Metaculus, GJOpen, CSET 2015-2024": [x for x in fixes if x["source"] in ("fr_metaculus", "fr_gjopen", "fr_cset")],
               "ForecastBench 2024-2026": [x for x in fixes if not x["source"].startswith("fr_")],
               "Manifold 2015-2024": [x for x in fixes if x["source"] == "fr_manifold"]}
    r = {"ensemble_fixe": len(fixes), "groupes": {}}
    for g, s in groupes.items():
        if not s:
            continue
        r["groupes"][g] = {"n": len(s), "questions_distinctes": len({f'{x["source"]}:{x["id"]}' for x in s}), "variante_moins_I": {}}
        for v in VARIANTES:
            e = [(f'{x["source"]}:{x["id"]}', pl(x["p_" + v], x["issue"]) - pl(x["p_I"], x["issue"])) for x in s]
            bas, haut = bj.cb.bootstrap(e, 0.05)
            r["groupes"][g]["variante_moins_I"][v] = {"moyenne": round(sum(d for _, d in e) / len(e), 4),
                                                       "intervalle_90": [round(bas, 4), round(haut, 4)]}
    # état observé : part de « oui » par rapport fenêtre / vitesse, par écosystème (questions classées, hors Manifold)
    etat = defaultdict(lambda: defaultdict(list))
    for x in dans:
        if x["source"] != "fr_manifold":
            etat[x["k"]["fiche"]][x["k"]["rapport"]].append(x["issue"])
    r["etat_observe_part_oui"] = {f: {rp: {"n": len(v), "part_oui": round(sum(v) / len(v), 3)}
                                      for rp, v in sorted(d.items())} for f, d in sorted(etat.items())}
    r["note"] = "mise au point, pas un verdict ; variante − I < 0 : la variante aide plus que la moyenne générale"
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    for g, v in r["groupes"].items():
        print("==", g, v["n"], v["questions_distinctes"])
        for k, w in v["variante_moins_I"].items():
            print(f"   {w['moyenne']:+.4f} {w['intervalle_90']}  {k}")
    print("== état observé (part de oui)")
    for f, d in r["etat_observe_part_oui"].items():
        print("  ", f, {rp: (w["n"], w["part_oui"]) for rp, w in d.items()})
    return 0


if __name__ == "__main__":
    sys.exit(principal())
