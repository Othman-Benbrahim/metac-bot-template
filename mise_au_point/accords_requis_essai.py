"""Mise au point (pas un verdict) : accords requis, question par question, questions « procédure » (préenregistrement
preenregistrements/accords-requis.md, plan B). Accord de l auteur, 2026-11-20, 17 h 08.

    python mise_au_point/accords_requis_essai.py   # écrit registre/mise-au-point/accords-requis.json
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

import accords_requis as ar
import acteurs_de_veto as av
import banc_jugement as bj
import fenetre_variantes as fv

SORTIE = Path("registre") / "mise-au-point" / "accords-requis.json"
MIN_N, M, POIDS = 30, 5.0, 0.2


def lg(p):
    p = min(0.98, max(0.02, p))
    return math.log(p / (1 - p))


def sig(z):
    return 1 / (1 + math.exp(-z))


def principal() -> int:
    xs = fv.charger()
    bj.calculer(xs)
    proc = [x for x in xs if x["source"] in ("fr_metaculus", "fr_gjopen") and str(x["structure"]).startswith("procédure")]
    for x in proc:
        x["tranche"] = ar.accords(x["titre"])
    fin = np.array([max(x["resolue_le"], x.get("cloture", "")) for x in proc])
    y = np.array([x["issue"] for x in proc], dtype=float)
    tr = np.array([x["tranche"] or "" for x in proc])
    ids = np.array([f'{x["source"]}:{x["id"]}' for x in proc])
    cibles, avec_classe = [], 0
    for i, x in enumerate(proc):
        if not x["tranche"]:
            continue
        x["p_I"] = sig((1 - POIDS) * lg(x["p_S"]) + POIDS * lg(x["p_R1"]))
        ok = (fin < x["jeu"]) & (tr == x["tranche"]) & (ids != ids[i])
        if ok.sum() >= MIN_N:
            r = (y[ok].sum() + M * x["p_R1"]) / (ok.sum() + M)
            x["p_V"] = sig((1 - POIDS) * lg(x["p_S"]) + POIDS * lg(r))
            avec_classe += 1
        else:
            x["p_V"] = x["p_I"]
        cibles.append(x)
    pl = bj.cb.pl
    e = [(f'{x["source"]}:{x["id"]}', pl(x["p_V"], x["issue"]) - pl(x["p_I"], x["issue"])) for x in cibles]
    bas, haut = bj.cb.bootstrap(e, 0.05)
    desc = {}
    for t in ("1", "2", "3+"):
        s = [x for x in cibles if x["tranche"] == t]
        desc[t] = {"n": len(s), "part_oui": round(sum(x["issue"] for x in s) / len(s), 3) if s else None}
    sans_usa = [x for x in cibles if av.pays(x["titre"]) != {"USA"}]
    desc_sans_usa = {t: {"n": len(s), "part_oui": round(sum(x["issue"] for x in s) / len(s), 3) if s else None}
                     for t in ("1", "2", "3+") for s in [[x for x in sans_usa if x["tranche"] == t]]}
    r = {"questions_procedure": len(proc), "jugees": len(cibles), "avec_classe_de_30": avec_classe,
         "pertes": {"I témoin": round(sum(pl(x["p_I"], x["issue"]) for x in cibles) / len(cibles), 4),
                    "V accords requis": round(sum(pl(x["p_V"], x["issue"]) for x in cibles) / len(cibles), 4)},
         "V_moins_I": {"moyenne": round(sum(v for _, v in e) / len(e), 4), "intervalle_90": [round(bas, 4), round(haut, 4)]},
         "descriptif_part_oui_par_tranche": desc, "descriptif_sans_etats_unis": desc_sans_usa,
         "note": "mise au point, pas un verdict ; perte log, plus bas = mieux ; Tsebelis prédit une part de oui décroissante"}
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
