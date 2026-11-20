"""Calibrage des fourchettes de comptes cumulés sur les événements UCDP (preenregistrements/comptes-cumules.md)."""
from __future__ import annotations

import csv
import gzip
import json
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import comptes_cumules as cc

SORTIE = Path("registre") / "mise-au-point" / "comptes-cumules.json"


def principal() -> int:
    par = defaultdict(lambda: defaultdict(float))
    for r in csv.DictReader(gzip.open("registre/ucdp-cellules.csv.gz", "rt", encoding="utf-8")):
        par[r["pays"]][r["jour"]] += float(r["evenements"] or 0)
    fin_donnees = date(2026, 9, 30)
    tot = {1: [0, 0, 0], 2: [0, 0, 0]}
    res = {}
    for pays, jours in sorted(par.items()):
        def somme(a, b):
            d, s = a, 0.0
            while d < b:
                s += jours.get(d.isoformat(), 0.0)
                d += timedelta(days=1)
            return s
        loc = {1: [0, 0, 0], 2: [0, 0, 0]}
        d0 = date(2017, 1, 1)
        while d0 + timedelta(days=14) <= fin_donnees:
            inc = [somme(d0 - timedelta(days=7 * (k + 1)), d0 - timedelta(days=7 * k)) for k in range(56)][::-1]
            debut_annee = date(d0.year, 1, 1)
            total = somme(debut_annee, d0)
            for h in (1, 2):
                f = cc.fourchette_cumul(inc, total, h)
                if not f:
                    continue
                q = dict(f)
                reel = total + somme(d0, d0 + timedelta(days=7 * h))
                loc[h][0] += 1
                loc[h][1] += q[0.1] <= reel <= q[0.9]
                loc[h][2] += q[0.2] <= reel <= q[0.8]
            d0 += timedelta(days=7)
        res[pays] = {f"{7*h} j": {"n": v[0], "couverture_80": round(v[1] / v[0], 3), "couverture_60": round(v[2] / v[0], 3)}
                     for h, v in loc.items() if v[0]}
        for h in (1, 2):
            tot[h] = [a + b for a, b in zip(tot[h], loc[h])]
    r = {"ensemble": {f"{7*h} j": {"n": v[0], "couverture_80": round(v[1] / v[0], 3), "couverture_60": round(v[2] / v[0], 3)}
                      for h, v in tot.items()}, "pays": res,
         "note": "attendu 0,80 et 0,60 ; plus bas = trop étroit ; plus haut = trop large"}
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(r["ensemble"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
