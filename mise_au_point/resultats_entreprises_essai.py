"""Calibrage des fourchettes de chiffre d'affaires trimestriel (preenregistrements/resultats-entreprises.md) : prochain
trimestre = dernier trimestre × variations logarithmiques empiriques d'un trimestre à l'autre (12 dernières), sur les
données EDGAR (registre/edgar-trimestres.csv)."""
from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import indicateurs_lents as il

SORTIE = Path("registre") / "mise-au-point" / "resultats-entreprises.json"


def principal() -> int:
    par = defaultdict(list)
    for r in csv.DictReader(open("registre/edgar-trimestres.csv", encoding="utf-8")):
        if r["mesure"] == "chiffre_affaires" and float(r["valeur"]) > 0:
            par[r["entreprise"]].append((r["fin"], float(r["valeur"])))
    n = c80 = c60 = 0
    detail = {}
    for e, pts in sorted(par.items()):
        pts.sort()
        # trimestres consécutifs seulement (écart de 80 à 100 jours entre deux fins de trimestre)
        blocs, cur = [], [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]):
            if 80 <= (date.fromisoformat(b[0]) - date.fromisoformat(a[0])).days <= 100:
                cur.append(b)
            else:
                blocs.append(cur)
                cur = [b]
        blocs.append(cur)
        ne = ce80 = ce60 = 0
        for bl in blocs:
            x = [math.log(v) for _, v in bl]
            for t in range(8, len(x) - 1):
                f = il.fourchette_suivante(x[: t + 1], fenetre=12)
                if not f:
                    continue
                q = dict(f)
                ne += 1
                ce80 += q[0.1] <= x[t + 1] <= q[0.9]
                ce60 += q[0.2] <= x[t + 1] <= q[0.8]
        if ne:
            detail[e] = {"n": ne, "couverture_80": round(ce80 / ne, 3), "couverture_60": round(ce60 / ne, 3)}
        n, c80, c60 = n + ne, c80 + ce80, c60 + ce60
    r = {"ensemble": {"n": n, "couverture_80": round(c80 / n, 3) if n else None, "couverture_60": round(c60 / n, 3) if n else None},
         "entreprises": detail, "note": "attendu 0,80 et 0,60 ; critère 0,75-0,85 et 0,55-0,65 sur l'ensemble"}
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(r["ensemble"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
