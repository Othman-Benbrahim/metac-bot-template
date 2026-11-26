"""Passage unique : signal de crise pour la brique du maintien (preenregistrements/maintien-crise.md).
Données : peacesciencer (Archigos 4.1, UCDP/PRIO ACD), téléchargées par le workflow. Aucun modèle de langue."""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd
import pyreadr
from scipy.stats import chi2

ICI = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ICI))
import maintien_regle as mr  # noqa: E402

GW_COW = {260: 255, 340: 345, 678: 679, 817: 817}


def lire(f):
    return list(pyreadr.read_r(f).values())[0]


def principal(f_arch: str, f_acd: str):
    A, U = lire(f_arch), lire(f_acd)
    print("Archigos colonnes :", list(A.columns))
    print("UCDP colonnes :", list(U.columns))
    cc = next(c for c in ("ccode", "gwcode", "idacr") if c in A.columns)
    nais = next((c for c in ("yrborn", "born", "borndate") if c in A.columns), None)
    # signal pays-année
    sig = defaultdict(int)          # (code COW, année) -> intensité max
    for _, r in U.iterrows():
        for g in str(r["gwno_loc"]).split(","):
            g = g.strip()
            if not g or g.lower() == "nan":
                continue
            g = int(float(g))
            c = GW_COW.get(g, g)
            sig[(c, int(r["year"]))] = max(sig[(c, int(r["year"]))], int(r["intensity_level"]))
    risques, q = mr.risques(), mr.mortalite()
    lignes = []
    for _, r in A.iterrows():
        s, e = pd.Timestamp(r["startdate"]), pd.Timestamp(r["enddate"])
        for an in range(max(1990, s.year), min(2015, e.year) + 1):
            a, b = max(s, pd.Timestamp(f"{an}-01-01")), min(e, pd.Timestamp(f"{an}-12-31"))
            if b <= a:
                continue
            expo = (b - a).days / 365.25
            anc = (a - s).days / 365.25
            rk = risques[mr.tranche(anc)]
            h = rk["irregulier"] + rk["regulier"]
            mort = 0.0
            if nais and pd.notna(r[nais]):
                try:
                    yb = int(str(r[nais])[:4])
                    mort = -math.log(1 - q.get(min(max(an - yb, 40), 100), 0.37))
                except ValueError:
                    pass
            parti = int(e <= pd.Timestamp(f"{an}-12-31") and str(r["exit"]) != "Still in Office")
            niveau = sig.get((int(r[cc]), an - 1), 0)
            lignes.append({"an": an, "expo": expo, "h": h, "mort": mort, "y": parti, "niveau": niveau})
    D = pd.DataFrame(lignes)
    print(f"{len(D)} dirigeants-années ; départs {int(D.y.sum())} ; par niveau :", D.groupby("niveau").size().to_dict())
    app, test = D[D.an <= 2005], D[D.an >= 2006]
    M = {}
    for n in (1, 2):
        x = app[app.niveau == n]
        obs = x.y.sum()
        att = ((x.h) * x.expo).sum()          # attendu hors mortalité (le multiplicateur porte sur le politique)
        m = obs / att if att else float("nan")
        lo = chi2.ppf(0.05, 2 * obs) / 2 / att if obs > 0 else 0.0
        hi = chi2.ppf(0.95, 2 * (obs + 1)) / 2 / att
        M[n] = {"m": round(m, 3), "ic90": [round(lo, 3), round(hi, 3)], "departs": int(obs), "attendus": round(att, 1),
                "dirigeants_annees": int(len(x))}
    garde = {n: M[n]["ic90"][0] > 1 for n in M}

    def perte(df, mult):
        tot = 0.0
        for _, r in df.iterrows():
            k = mult.get(int(r.niveau), 1.0)
            p = 1 - math.exp(-(r.h * k + r.mort) * r.expo)
            p = min(max(p, 0.002), 0.998)
            tot += -math.log(p if r.y else 1 - p)
        return tot / len(df)
    mult = {n: M[n]["m"] for n in M if garde[n]}
    res = {"multiplicateurs_appris_1990_2005": M, "appliques": mult,
           "perte_test_tables": round(perte(test, {}), 5), "perte_test_avec_crise": round(perte(test, mult), 5),
           "test_par_niveau": {int(n): {"n": int(len(g)), "departs": int(g.y.sum()),
                                        "tables": round(perte(g, {}), 4), "crise": round(perte(g, mult), 4)}
                               for n, g in test.groupby("niveau")}}
    res["retenue"] = bool(garde.get(2)) and res["perte_test_avec_crise"] < res["perte_test_tables"]
    json.dump(res, open(ICI / "banc_maintien_crise.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    principal(sys.argv[1], sys.argv[2])
