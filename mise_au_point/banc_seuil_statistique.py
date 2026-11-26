"""Passage unique : seuil d'une statistique officielle (preenregistrements/seuil-statistique.md)."""
from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import pstdev

ICI = Path(__file__).resolve().parent.parent
NIVEAUX = ["UMCSENT", "PFOODINDEXM", "PCOPPUSDM", "PNICKUSDM", "PURANUSDM", "PALUMUSDM", "PIORECRUSDM", "PZINCUSDM",
           "PWHEAMTUSDM", "PMAIZMTUSDM"]
H_ = (1, 3, 6, 12)
DELTAS = (0.1, 0.3, 0.5, 1.0)
RS = (0.02, 0.05, 0.10, 0.20)


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def ll(p, y):
    return -math.log(p if y else 1 - p)


def charger():
    S = defaultdict(dict)
    for r in csv.DictReader(open(ICI / "registre/fred.csv", encoding="utf-8")):
        try:
            S[r["serie"]][r["jour"][:7]] = float(r["valeur"])
        except ValueError:
            pass
    out = {}
    def suite(d):
        return [d[k] for k in sorted(d)]
    out["UNRATE"] = ("taux", suite(S["UNRATE"]))
    for s, nom in (("CPIAUCSL", "inflation_cpi"), ("CPILFESL", "inflation_core"), ("CES0500000003", "salaires_an")):
        v = suite(S[s])
        out[nom] = ("taux", [100 * (v[i] / v[i - 12] - 1) for i in range(12, len(v))])
    for s in NIVEAUX:
        out[s] = ("niveau", [math.log(x) for x in suite(S[s]) if x > 0])
    return out


def principal():
    Q = []
    for nom, (nature, v) in charger().items():
        for t in range(36, len(v)):
            for h in H_:
                if t + h - 1 >= len(v) - 0:
                    continue
                pas = [v[i] - v[i - h] for i in range(max(h, t - 36), t) if i - h >= 0]
                if len(pas) < 24:
                    continue
                sig = max(pstdev(pas), 1e-6)
                x0, xh = v[t - 1], v[t + h - 1]
                crans = [(d, x0 + d) for d in DELTAS] + [(-d, x0 - d) for d in DELTAS] if nature == "taux" else \
                        [(r, x0 + math.log(1 + r)) for r in RS] + [(-r, x0 + math.log(1 - r)) for r in RS]
                for cran, T in crans:
                    haut = cran > 0
                    p = phi((x0 - T) / sig) if haut else phi((T - x0) / sig)
                    p = min(max(p, 0.02), 0.98)
                    y = int(xh > T) if haut else int(xh < T)
                    Q.append({"serie": nom, "nature": nature, "cran": cran, "h": h, "p": p, "y": y})
    cle = lambda q: (q["nature"], q["cran"], q["h"])
    groupes = defaultdict(lambda: defaultdict(list))
    for q in Q:
        groupes[cle(q)][q["serie"]].append(q["y"])
    for q in Q:
        autres = [y for s, ys in groupes[cle(q)].items() if s != q["serie"] for y in ys]
        q["ref"] = min(max(sum(autres) / len(autres), 0.02), 0.98) if autres else 0.5
    par = defaultdict(list)
    for q in Q:
        par[q["serie"]].append(q)
    lignes = {s: {"n": len(L), "regle": round(sum(ll(q["p"], q["y"]) for q in L) / len(L), 4),
                  "reference": round(sum(ll(q["ref"], q["y"]) for q in L) / len(L), 4)} for s, L in par.items()}
    ens = {"n": len(Q), "regle": round(sum(ll(q["p"], q["y"]) for q in Q) / len(Q), 4),
           "reference": round(sum(ll(q["ref"], q["y"]) for q in Q) / len(Q), 4)}
    gagnes = sum(v["regle"] < v["reference"] for v in lignes.values())
    cal = defaultdict(lambda: [0, 0])
    for q in Q:
        b = min(int(q["p"] * 5), 4)
        cal[b][0] += 1
        cal[b][1] += q["y"]
    out = {"ensemble": ens, "par_serie": lignes, "series_gagnees": gagnes, "n_series": len(lignes),
           "retenue": ens["regle"] < ens["reference"] and gagnes >= math.ceil(2 * len(lignes) / 3),
           "calibration": {f"{b/5:.1f}-{(b+1)/5:.1f}": {"n": n, "part_oui": round(o / n, 3)} for b, (n, o) in sorted(cal.items())}}
    json.dump(out, open(ICI / "registre/seuil-statistique.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    principal()
