"""Passage unique : questionneur × délai (preenregistrements/questionneur-delai.md). Aucun modèle de langue."""
from __future__ import annotations

import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

ICI = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ICI))
import structures_questions as sq  # noqa: E402

COUPURE = "2025-11-01"


def tranche(h) -> str:
    h = float(h)
    return "<=7" if h <= 7 else "8-30" if h <= 30 else "31-90" if h <= 90 else "91-365" if h <= 365 else ">365"


def borne(p):
    return min(max(p, 0.02), 0.98)


def ll(p, y):
    return -math.log(p if y else 1 - p)


def principal():
    Q = []
    for l in open(ICI / "registre/jugement-questions.jsonl", encoding="utf-8"):
        d = json.loads(l)
        if d.get("issue") in (0, 1) and d.get("horizon") not in (None, ""):
            Q.append({**d, "forme": sq.structure(d["titre"]), "tr": tranche(d["horizon"])})
    app = [q for q in Q if q["jeu"] < COUPURE]
    test = [q for q in Q if q["jeu"] >= COUPURE]
    f, c = defaultdict(list), defaultdict(list)
    for q in app:
        f[q["forme"]].append(q["issue"])
        c[(q["forme"], q["tr"])].append(q["issue"])
    glob = sum(q["issue"] for q in app) / len(app)
    def p_forme(q):
        v = f.get(q["forme"])
        return borne(sum(v) / len(v)) if v else borne(glob)
    def p_case(q):
        base = p_forme(q)
        v = c.get((q["forme"], q["tr"]), [])
        w = len(v) / (len(v) + 20)
        return borne(w * (sum(v) / len(v) if v else base) + (1 - w) * base)
    def pertes(L):
        return [ll(p_forme(q), q["issue"]) - ll(p_case(q), q["issue"]) for q in L], \
               sum(ll(p_forme(q), q["issue"]) for q in L) / len(L), sum(ll(p_case(q), q["issue"]) for q in L) / len(L)
    res = {}
    for nom, L in (("ensemble", test), ("metaculus", [q for q in test if q["source"] == "metaculus"])):
        d, pf, pc = pertes(L)
        rnd = random.Random(20261126)
        boot = sorted(sum(rnd.choice(d) for _ in d) / len(d) for _ in range(1000))
        res[nom] = {"n": len(L), "oui": sum(q["issue"] for q in L), "forme_seule": round(pf, 4), "forme_x_delai": round(pc, 4),
                    "gain": round(pf - pc, 4), "ic90_gain": [round(boot[50], 4), round(boot[949], 4)]}
    # tableau descriptif (apprentissage) : part de oui par tranche, toutes formes
    t = defaultdict(list)
    for q in app:
        t[q["tr"]].append(q["issue"])
    res["part_oui_par_tranche_apprentissage"] = {k: [len(v), round(sum(v) / len(v), 3)] for k, v in sorted(t.items())}
    res["n_apprentissage"] = len(app)
    e, m = res["ensemble"], res["metaculus"]
    res["retenue"] = e["gain"] >= 0.005 and m["gain"] >= 0.005 and e["ic90_gain"][0] > 0
    json.dump(res, open(ICI / "registre/questionneur-delai.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    principal()
