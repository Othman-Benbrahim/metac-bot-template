"""Test de la propagation dans le réseau d'acteurs sur des questions neuves (préenregistrement
preenregistrements/reseau-propagation.md, 2026-11-20).

    python mise_au_point/reseau_propagation_essai.py   # écrit registre/mise-au-point/reseau-propagation.json
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import banc_jugement as bj
import couverture_reseau as cr
import fenetre_variantes as fv
import reseau_observation as ro

SORTIE = Path("registre") / "mise-au-point" / "reseau-propagation.json"
POIDS, PAS, FEN, MIN_LIEN = 0.2, 0.3, 180, 3
RESERVOIR = {"fr_metaculus", "fr_gjopen", "fr_cset", "metaculus", "infer"}
DESCRIPTIF = {"polymarket", "manifold"}


def lg(p):
    p = min(0.98, max(0.02, p))
    return math.log(p / (1 - p))


def sig(z):
    return 1 / (1 + math.exp(-z))


def lies(i, q, pool):
    d0 = q["jeu"]
    deb = (date.fromisoformat(d0) - timedelta(days=FEN)).isoformat()
    liens = Counter()
    for p in pool:
        if p["jeu"] >= d0:
            break
        if p["fin"] < d0 and len(p["a"]) > 1 and p["a"] & q["a"]:
            for z in p["a"]:
                liens[z] += 1
    vo = {z for z, n in liens.items() if n >= MIN_LIEN} - q["a"]
    ys = [p["y"] for p in pool if p["jeu"] < d0 and deb <= p["fin"] < d0 and not (p["a"] & q["a"]) and p["a"] & vo]
    return sum(ys) / len(ys) if len(ys) >= 3 else None


def principal() -> int:
    xs = fv.charger()
    bj.calculer(xs)
    pool = []
    for x in xs:
        a = ro.acteurs(x["titre"])
        if a and x["source"] in RESERVOIR:
            pool.append({"jeu": x["jeu"], "fin": max(x["resolue_le"], x.get("cloture", "")), "y": int(x["issue"]), "a": a})
    pool.sort(key=lambda p: p["jeu"])
    groupes = {"jugé (Metaculus, INFER)": [], "descriptif (Polymarket, Manifold)": []}
    for x in xs:
        if x["source"] not in ({"metaculus", "infer"} | DESCRIPTIF) or x["jeu"] < "2024-01-01":
            continue
        a = ro.acteurs(x["titre"])
        if not a:
            continue
        t, voie = cr.type_question(x["titre"], x.get("horizon"))
        if t not in ("conflit", "politique"):
            continue
        q = {"jeu": x["jeu"], "a": a}
        v = lies(None, q, pool)
        b = 0 if v is None else (1 if v < 0.2 else -1 if v >= 0.4 else 0)
        s = 1 if t == "conflit" else -1
        z = (1 - POIDS) * lg(x["p_S"]) + POIDS * lg(x["p_R1"])
        x.update(p_I=sig(z), p_P=sig(z + s * PAS * b), _type=t, _voie=voie, _b=b)
        groupes["jugé (Metaculus, INFER)" if x["source"] in ("metaculus", "infer") else "descriptif (Polymarket, Manifold)"].append(x)
    pl = bj.cb.pl
    def bilan(s):
        if not s:
            return None
        e = [(f'{x["source"]}:{x["id"]}', pl(x["p_P"], x["issue"]) - pl(x["p_I"], x["issue"])) for x in s]
        bas, haut = bj.cb.bootstrap(e, 0.05)
        return {"n": len(s), "ajustees (b ≠ 0)": sum(1 for x in s if x["_b"]),
                "pertes": {"I": round(sum(pl(x["p_I"], x["issue"]) for x in s) / len(s), 4),
                           "P": round(sum(pl(x["p_P"], x["issue"]) for x in s) / len(s), 4)},
                "P_moins_I": {"moyenne": round(sum(v for _, v in e) / len(e), 4), "intervalle_90": [round(bas, 4), round(haut, 4)]},
                "part_oui_par_b": {str(b): (round(sum(x["issue"] for x in s if x["_b"] == b) / max(1, sum(1 for x in s if x["_b"] == b)), 3),
                                            sum(1 for x in s if x["_b"] == b)) for b in (1, 0, -1)}}
    j = groupes["jugé (Metaculus, INFER)"]
    r = {"critere (jugé, tout)": bilan(j),
         "conflit seul": bilan([x for x in j if x["_type"] == "conflit"]),
         "politique seul": bilan([x for x in j if x["_type"] == "politique"]),
         "extension UCDP seule": bilan([x for x in j if x["_voie"] == "extension UCDP"]),
         "descriptif Polymarket et Manifold": bilan(groupes["descriptif (Polymarket, Manifold)"]),
         "note": "perte log, plus bas = mieux ; P − I < 0 : la propagation aide ; b = +1 : peu de oui liés récents"}
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
