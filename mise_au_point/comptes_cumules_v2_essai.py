"""Comptes cumulés, version 2, sur des données NEUVES pour ce modèle (preenregistrements/comptes-cumules.md, partie v2) :
manifestations GDELT par pays et séismes M4,5+ mondiaux (USGS). UCDP rapporté à titre descriptif."""
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

SORTIE = Path("registre") / "mise-au-point" / "comptes-cumules-v2.json"


def couverture(series: dict[str, dict[str, float]], debut: date, fin: date) -> dict:
    tot = {1: [0, 0, 0], 2: [0, 0, 0]}
    for _, jours in sorted(series.items()):
        def somme(a, b):
            d, s = a, 0.0
            while d < b:
                s += jours.get(d.isoformat(), 0.0)
                d += timedelta(days=1)
            return s
        d0 = debut
        while d0 + timedelta(days=14) <= fin:
            inc = [somme(d0 - timedelta(days=7 * (k + 1)), d0 - timedelta(days=7 * k)) for k in range(53)][::-1]
            total = somme(date(d0.year, 1, 1), d0)
            for h in (1, 2):
                f = cc.fourchette_cumul_v2(inc, total, h)
                if f:
                    q = dict(f)
                    reel = total + somme(d0, d0 + timedelta(days=7 * h))
                    tot[h][0] += 1
                    tot[h][1] += q[0.1] <= reel <= q[0.9]
                    tot[h][2] += q[0.2] <= reel <= q[0.8]
            d0 += timedelta(days=7)
    return {f"{7*h} j": {"n": v[0], "couverture_80": round(v[1] / v[0], 3) if v[0] else None,
                         "couverture_60": round(v[2] / v[0], 3) if v[0] else None} for h, v in tot.items()}


def principal() -> int:
    g = defaultdict(dict)
    for r in csv.DictReader(open("registre/gdelt-manifestations.csv", encoding="utf-8")):
        g[r["pays"]][r["jour"]] = float(r["manifestations"] or 0)
    s = {"monde": {r["jour"]: float(r["m45"] or 0) for r in csv.DictReader(open("registre/seismes-usgs.csv", encoding="utf-8"))}}
    u = defaultdict(lambda: defaultdict(float))
    for r in csv.DictReader(gzip.open("registre/ucdp-cellules.csv.gz", "rt", encoding="utf-8")):
        u[r["pays"]][r["jour"]] += float(r["evenements"] or 0)
    fin_g = date.fromisoformat(max(j for v in g.values() for j in v))
    fin_s = date.fromisoformat(max(s["monde"]))
    r = {"jugé : manifestations GDELT (par pays, depuis 2025-07)": couverture(g, date(2025, 7, 7), fin_g),
         "jugé : séismes M4,5+ mondiaux (USGS, depuis 2001)": couverture(s, date(2001, 1, 8), fin_s),
         "descriptif : UCDP (données du calibrage v1)": couverture(u, date(2017, 1, 1), date(2026, 9, 30)),
         "note": "attendu 0,80 et 0,60 ; critère : 0,75-0,85 et 0,55-0,65 aux deux échéances, sur chaque source jugée"}
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
