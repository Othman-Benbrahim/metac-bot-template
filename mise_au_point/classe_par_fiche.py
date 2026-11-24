"""Essai préenregistré : preenregistrements/classe-par-fiche.md (2026-11-24)."""
import json, math, random, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lecture_mecanique import Carte, ICI

COUPURE, K, B_MIN, B_MAX = "2025-11-01", 20, 0.02, 0.98


def ll(p, y):
    p = min(max(p, B_MIN), B_MAX)
    return -math.log(p if y else 1 - p)


def principal():
    c = Carte()
    vus, Q = set(), []
    for l in (ICI / "registre/jugement-questions.jsonl").read_text(encoding="utf-8").splitlines():
        q = json.loads(l)
        if q["titre"] in vus or str(q.get("issue")) not in ("0", "1") or not q.get("jeu"):
            continue
        vus.add(q["titre"])
        comps, _ = c.rattacher(q["titre"])
        Q.append({"jeu": q["jeu"], "y": int(q["issue"]), "src": q["source"], "fiches": sorted({x.split(":")[0] for x in comps})})
    A = [q for q in Q if q["jeu"] < COUPURE]
    T = [q for q in Q if q["jeu"] >= COUPURE]
    B = sum(q["y"] for q in A) / len(A)
    s = defaultdict(lambda: [0, 0])
    for q in A:
        for f in q["fiches"]:
            s[f][0] += q["y"]; s[f][1] += 1
    def F(q):
        ps = [(K * B + s[f][0]) / (K + s[f][1]) for f in q["fiches"]]
        return sum(ps) / len(ps) if ps else B
    res = {"apprentissage": len(A), "essai": len(T), "B": round(B, 4)}
    for nom, S in [("toutes", T), ("metaculus", [q for q in T if q["src"] == "metaculus"])]:
        d = [ll(F(q), q["y"]) - ll(B, q["y"]) for q in S]
        random.seed(1)
        bs = sorted(sum(random.choice(d) for _ in d) / len(d) for _ in range(2000))
        res[nom] = {"n": len(S), "perte_B": round(sum(ll(B, q["y"]) for q in S) / len(S), 4),
                    "perte_F": round(sum(ll(F(q), q["y"]) for q in S) / len(S), 4),
                    "ecart_F_moins_B": round(sum(d) / len(d), 4), "ic90": [round(bs[100], 4), round(bs[1899], 4)]}
    res["verdict"] = "adoptée comme repère" if res["toutes"]["ic90"][1] < 0 else "critère non atteint"
    (ICI / "registre/classe-par-fiche.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))


principal()
