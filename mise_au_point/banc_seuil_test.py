"""Passage unique : brique « seuil d'un test de référence avant une date » (preenregistrements/seuil-test-reference.md)."""
from __future__ import annotations

import csv
import datetime as dt
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ICI = Path(__file__).resolve().parent.parent
DOS = ICI / "registre" / "epoch-bancs"
TESTS = {"gpqa_diamond": "Best score (across scorers)", "frontiermath": "Best score (across scorers)",
         "otis_mock_aime_2024_2025": "Best score (across scorers)", "swe_bench_verified": "Best score (across scorers)",
         "simpleqa_verified": "Best score (across scorers)", "terminalbench_external": "Accuracy mean",
         "metr_time_horizons_external": "Time horizon"}
H_ = (3, 6, 12)
DELTAS = (0.02, 0.05, 0.10, 0.20)
KS = (1.5, 2.0, 4.0)


def mois(d: dt.date, k: int) -> dt.date:
    m = d.month - 1 + k
    return dt.date(d.year + m // 12, m % 12 + 1, 1)


def phi(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def serie(nom: str):
    L = list(csv.DictReader(open(DOS / f"{nom}.csv", encoding="utf-8")))
    pts = []
    for x in L:
        try:
            pts.append((dt.date.fromisoformat(x["Release date"][:10]), float(x[TESTS[nom]])))
        except (ValueError, KeyError, TypeError):
            pass
    if nom != "metr_time_horizons_external" and max(v for _, v in pts) > 1.5:
        pts = [(d, v / 100) for d, v in pts]
    return sorted(pts)


def record(pts, t):
    v = [s for d, s in pts if d < t]
    return max(v) if v else None


def echelle(nom, v):
    if nom == "metr_time_horizons_external":
        return math.log(max(v, 1e-3))
    v = min(max(v, 0.005), 0.995)
    return math.log(v / (1 - v))


def regle(nom, pts, t, H, T):
    xs, ys = [], []
    for k in range(-24, 0):
        m = mois(t, k)
        r = record(pts, m)
        if r is not None:
            xs.append(k / 12)
            ys.append(echelle(nom, r))
    if len(xs) < 6:
        return None
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx else 0.0
    a = my - b * mx
    res = [y - (a + b * x) for x, y in zip(xs, ys)]
    sig = math.sqrt(sum(r * r for r in res) / max(1, len(res) - 2))
    mu = max(echelle(nom, record(pts, t)), a + b * (H / 12))
    s = max(0.1, sig * math.sqrt(1 + H / 12))
    p = 1 - phi((echelle(nom, T) - mu) / s)
    return min(max(p, 0.02), 0.98)


def ll(p, y):
    return -math.log(p if y else 1 - p)


def principal():
    Qs = []
    for nom in TESTS:
        pts = serie(nom)
        debut, fin = pts[0][0], pts[-1][0]
        t = mois(dt.date(debut.year, debut.month, 1), 9)
        while t <= fin:
            R = record(pts, t)
            if R is not None:
                for H in H_:
                    if mois(t, H) > fin:
                        continue
                    crans = [(f"d{d}", R + d) for d in DELTAS if R + d < 1] if nom != "metr_time_horizons_external" \
                        else [(f"k{k}", R * k) for k in KS]
                    for cran, T in crans:
                        p = regle(nom, pts, t, H, T)
                        if p is None:
                            continue
                        y = int(record(pts, mois(t, H)) is not None and record(pts, mois(t, H)) >= T)
                        Qs.append({"test": nom, "t": t.isoformat(), "H": H, "cran": cran, "p": p, "y": y})
            t = mois(t, 1)
    # référence : même H et même cran, autres tests
    for q in Qs:
        autres = [x["y"] for x in Qs if x["test"] != q["test"] and x["H"] == q["H"] and x["cran"] == q["cran"]]
        if not autres:   # METR (crans k) : même H, tous crans des autres tests de même nature absente -> même H
            autres = [x["y"] for x in Qs if x["test"] != q["test"] and x["H"] == q["H"]]
        q["ref"] = min(max(sum(autres) / len(autres), 0.02), 0.98)
    par = defaultdict(list)
    for q in Qs:
        par[q["test"]].append(q)
    lignes = {}
    for nom, L in par.items():
        lignes[nom] = {"n": len(L), "oui": sum(q["y"] for q in L), "regle": round(sum(ll(q["p"], q["y"]) for q in L) / len(L), 4),
                       "reference": round(sum(ll(q["ref"], q["y"]) for q in L) / len(L), 4)}
    ens = {"n": len(Qs), "regle": round(sum(ll(q["p"], q["y"]) for q in Qs) / len(Qs), 4),
           "reference": round(sum(ll(q["ref"], q["y"]) for q in Qs) / len(Qs), 4)}
    gagnes = sum(v["regle"] < v["reference"] for v in lignes.values())
    retenue = ens["regle"] < ens["reference"] and gagnes >= math.ceil(2 * len(lignes) / 3)
    # calibration grossière
    cal = defaultdict(lambda: [0, 0])
    for q in Qs:
        b = min(int(q["p"] * 5), 4)
        cal[b][0] += 1
        cal[b][1] += q["y"]
    out = {"ensemble": ens, "par_test": lignes, "tests_gagnes": gagnes, "n_tests": len(lignes), "retenue": retenue,
           "calibration": {f"{b/5:.1f}-{(b+1)/5:.1f}": {"n": n, "part_oui": round(o / n, 3)} for b, (n, o) in sorted(cal.items())}}
    json.dump(out, open(ICI / "registre/seuil-test-reference.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    principal()
