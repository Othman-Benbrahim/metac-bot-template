"""Passage unique : fréquence de franchissement commune, épreuve dans le temps (preenregistrements/seuil-statistique-commun.md)."""
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
COUPE = "2022-01"


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def ll(p, y):
    p = min(max(p, 0.02), 0.98)
    return -math.log(p if y else 1 - p)


def charger():
    S = defaultdict(dict)
    for r in csv.DictReader(open(ICI / "registre/fred.csv", encoding="utf-8")):
        try:
            S[r["serie"]][r["jour"][:7]] = float(r["valeur"])
        except ValueError:
            pass
    out = {}
    m = sorted(S["UNRATE"])
    out["UNRATE"] = ("taux", m, [S["UNRATE"][k] for k in m])
    for s, nom in (("CPIAUCSL", "inflation_cpi"), ("CPILFESL", "inflation_core"), ("CES0500000003", "salaires_an")):
        k = sorted(S[s])
        v = [S[s][x] for x in k]
        out[nom] = ("taux", k[12:], [100 * (v[i] / v[i - 12] - 1) for i in range(12, len(v))])
    for s in NIVEAUX:
        k = [x for x in sorted(S[s]) if S[s][x] > 0]
        out[s] = ("niveau", k, [math.log(S[s][x]) for x in k])
    return out


def principal():
    Q = []
    for nom, (nature, mois, v) in charger().items():
        for t in range(36, len(v)):
            for h in H_:
                if t + h - 1 >= len(v):
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
                    p_rw = phi((x0 - T) / sig) if haut else phi((T - x0) / sig)
                    y = int(xh > T) if haut else int(xh < T)
                    Q.append({"serie": nom, "cle": (nature, cran, h), "depart": mois[t], "cible": mois[t + h - 1],
                              "p_rw": p_rw, "y": y})
    app = [q for q in Q if q["cible"] < COUPE]
    epr = [q for q in Q if q["depart"] >= COUPE]
    tab = defaultdict(lambda: defaultdict(list))
    for q in app:
        tab[q["cle"]][q["serie"]].append(q["y"])
    const = sum(q["y"] for q in app) / len(app)
    for q in epr:
        autres = [y for s, ys in tab[q["cle"]].items() if s != q["serie"] for y in ys]
        q["p_commun"] = sum(autres) / len(autres) if autres else const
        q["p_const"] = const
    par = defaultdict(list)
    for q in epr:
        par[q["serie"]].append(q)
    M = ("p_commun", "p_rw", "p_const")
    lignes = {s: {k: round(sum(ll(q[k], q["y"]) for q in L) / len(L), 4) for k in M} | {"n": len(L)} for s, L in par.items()}
    ens = {k: round(sum(ll(q[k], q["y"]) for q in epr) / len(epr), 4) for k in M} | {"n": len(epr), "n_apprentissage": len(app)}
    gagne = sum(v["p_commun"] < v["p_rw"] and v["p_commun"] < v["p_const"] for v in lignes.values())
    out = {"epreuve_ensemble": ens, "par_serie": lignes, "series_gagnees_par_commun": gagne, "n_series": len(lignes),
           "retenue": ens["p_commun"] < ens["p_rw"] and ens["p_commun"] < ens["p_const"] and gagne >= math.ceil(2 * len(lignes) / 3)}
    json.dump(out, open(ICI / "registre/seuil-statistique-commun.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    principal()
