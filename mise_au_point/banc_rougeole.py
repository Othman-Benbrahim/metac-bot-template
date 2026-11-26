"""Passage unique : épidémies de rougeole, cycle + couverture + âge + connectivité (preenregistrements/epidemies-rougeole.md).
Téléchargements : OMS (GHO OData) et Banque mondiale (API). Aucun modèle de langue."""
from __future__ import annotations

import json
import math
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

import httpx
import numpy as np
from sklearn.linear_model import LogisticRegression

ICI = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ICI))
import politesse  # noqa: E402

GHO = "https://ghoapi.azureedge.net/api/{ind}"
WB = "https://api.worldbank.org/v2/country/all/indicator/{ind}?format=json&per_page=20000&date=1995:2025"
KS = (0.5, 1, 2, 5)


def gho(c, ind):
    u = GHO.format(ind=ind)
    if not politesse.autorise(c, u):
        print("refusé par robots.txt :", u)
        return {}
    out = {}
    while u:
        r = c.get(u, timeout=120)
        r.raise_for_status()
        j = r.json()
        for x in j.get("value", []):
            if x.get("SpatialDimType") == "COUNTRY" and x.get("NumericValue") is not None:
                out[(x["SpatialDim"], int(x["TimeDim"]))] = float(x["NumericValue"])
        u = j.get("@odata.nextLink")
    print(f"OMS {ind} : {len(out)} valeurs")
    return out


def wb(c, ind):
    u = WB.format(ind=ind)
    if not politesse.autorise(c, u):
        print("refusé par robots.txt :", u)
        return {}
    r = c.get(u, timeout=120)
    r.raise_for_status()
    out = {}
    for x in r.json()[1] or []:
        if x.get("value") is not None and x.get("countryiso3code"):
            out[(x["countryiso3code"], int(x["date"]))] = float(x["value"])
    print(f"Banque mondiale {ind} : {len(out)} valeurs")
    time.sleep(1)
    return out


def principal():
    with httpx.Client(headers={"User-Agent": politesse.UA}, follow_redirects=True) as c:
        cas, mcv1, mcv2 = gho(c, "WHS3_62"), gho(c, "WHS8_110"), gho(c, "MCV2")
        arr, nat, pop, jeunes = (wb(c, i) for i in ("ST.INT.ARVL", "SP.DYN.CBRT.IN", "SP.POP.TOTL", "SP.POP.0014.TO.ZS"))
    pays = sorted({p for p, _ in cas})
    lignes = []
    for p in pays:
        for t in range(2001, 2026):
            c1 = cas.get((p, t - 1))
            ct = cas.get((p, t))
            if c1 is None or ct is None or c1 < 10:
                continue
            hist = [cas.get((p, a)) for a in range(t - 11, t)]
            # dernier pic : année dont les cas dépassent le double de la médiane des 10 années précédentes
            depuis = 10
            for a in range(t - 1, t - 11, -1):
                prev = [cas.get((p, b)) for b in range(a - 10, a) if cas.get((p, b)) is not None]
                if prev and cas.get((p, a)) is not None and cas[(p, a)] > 2 * float(np.median(prev)):
                    depuis = t - a
                    break
            max5 = max([cas.get((p, a)) or 0 for a in range(t - 6, t - 1)] + [c1])
            m1 = mcv1.get((p, t - 1))
            m2 = mcv2.get((p, t - 1))
            ar, po = arr.get((p, t - 1)), pop.get((p, t - 1))
            for k in KS:
                lignes.append({"pays": p, "t": t, "k": k, "y": int(ct > k * c1), "logc": math.log(c1), "depuis": depuis,
                               "logmax": math.log(max5 / c1), "m1": m1, "m2": m2, "nat": nat.get((p, t - 1)),
                               "jeunes": jeunes.get((p, t - 1)),
                               "arr": math.log(ar / po) if ar and po else None})
    app = [l for l in lignes if 2001 <= l["t"] <= 2018]
    epr = [l for l in lignes if 2022 <= l["t"] <= 2025]
    def med(cle):
        v = [l[cle] for l in app if l[cle] is not None]
        return float(np.median(v)) if v else 0.0
    M = {c_: med(c_) for c_ in ("m1", "m2", "nat", "jeunes", "arr")}
    def X(l, complet):
        ks = [1.0 if l["k"] == k else 0.0 for k in KS]
        base = ks + [l["logc"], l["depuis"], l["logmax"]]
        if not complet:
            return base
        m1 = l["m1"] if l["m1"] is not None else M["m1"]
        m2 = l["m2"] if l["m2"] is not None else m1
        return base + [m1 / 100, m2 / 100, float(l["m2"] is None), (l["nat"] if l["nat"] is not None else M["nat"]) / 10,
                       (l["jeunes"] if l["jeunes"] is not None else M["jeunes"]) / 10,
                       l["arr"] if l["arr"] is not None else M["arr"], float(l["arr"] is None)]
    y_app = np.array([l["y"] for l in app]); y_epr = np.array([l["y"] for l in epr])
    taux = {k: np.mean([l["y"] for l in app if l["k"] == k]) for k in KS}
    pa = np.array([taux[l["k"]] for l in epr])
    res_modeles = {}
    preds = {"a": pa}
    for nom, complet in (("b", False), ("c", True)):
        m = LogisticRegression(max_iter=2000, C=1.0, fit_intercept=False)
        m.fit(np.array([X(l, complet) for l in app]), y_app)
        preds[nom] = m.predict_proba(np.array([X(l, complet) for l in epr]))[:, 1]
        res_modeles[nom] = [round(float(w), 3) for w in m.coef_[0]]
    clip = lambda p: np.clip(p, 0.02, 0.98)
    perte = {k: -(y_epr * np.log(clip(v)) + (1 - y_epr) * np.log(1 - clip(v))) for k, v in preds.items()}
    moy = {k: round(float(v.mean()), 4) for k, v in perte.items()}
    parp = defaultdict(list)
    for i, l in enumerate(epr):
        parp[l["pays"]].append(perte["b"][i] - perte["c"][i])
    P = list(parp)
    rnd = random.Random(20261126)
    boot = []
    for _ in range(1000):
        tir = [rnd.choice(P) for _ in P]
        v = [x for p in tir for x in parp[p]]
        boot.append(sum(v) / len(v))
    boot.sort()
    res = {"n_apprentissage": len(app), "n_epreuve": len(epr), "pays_epreuve": len(P), "pertes_epreuve": moy,
           "gain_c_sur_b": round(moy["b"] - moy["c"], 4), "ic90_gain_c_sur_b": [round(boot[50], 4), round(boot[949], 4)],
           "gain_c_sur_a": round(moy["a"] - moy["c"], 4),
           "coefficients_c": dict(zip(["k0.5", "k1", "k2", "k5", "log_cas", "depuis_pic", "log_max5", "couv1", "couv2",
                                       "couv2_absente", "natalite", "part_0_14", "arrivees_par_hab", "arrivees_absentes"],
                                      res_modeles["c"]))}
    res["retenue"] = res["gain_c_sur_b"] >= 0.005 and res["gain_c_sur_a"] >= 0.005 and res["ic90_gain_c_sur_b"][0] > 0
    json.dump(res, open(ICI / "banc_rougeole.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    principal()
