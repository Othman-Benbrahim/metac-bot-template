"""Calibrage des fourchettes d'indicateurs lents sur les séries mensuelles FRED (preenregistrements/indicateurs-lents.md)."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import indicateurs_lents as il

SORTIE = Path("registre") / "mise-au-point" / "indicateurs-lents.json"


def principal() -> int:
    s = {}
    for r in csv.DictReader(open("registre/fred.csv", encoding="utf-8")):
        s.setdefault(r["serie"], []).append((r["jour"], float(r["valeur"])))
    series = {"chômage (UNRATE)": [v for _, v in sorted(s["UNRATE"])],
              "confiance des ménages (UMCSENT)": [v for _, v in sorted(s["UMCSENT"])]}
    for nom, cle in (("inflation sur un an (CPIAUCSL)", "CPIAUCSL"), ("inflation sous-jacente sur un an (CPILFESL)", "CPILFESL")):
        x = [v for _, v in sorted(s[cle])]
        series[nom] = [100 * (x[i] / x[i - 12] - 1) for i in range(12, len(x))]
    res, tot = {}, [0, 0, 0]
    for nom, x in series.items():
        n = c80 = c60 = 0
        for t in range(19, len(x) - 1):
            f = il.fourchette_suivante(x[: t + 1])
            if not f:
                continue
            q = dict(f)
            n += 1
            c80 += q[0.1] <= x[t + 1] <= q[0.9]
            c60 += q[0.2] <= x[t + 1] <= q[0.8]
        res[nom] = {"n": n, "couverture_80": round(c80 / n, 3), "couverture_60": round(c60 / n, 3)}
        tot = [tot[0] + n, tot[1] + c80, tot[2] + c60]
    r = {"ensemble": {"n": tot[0], "couverture_80": round(tot[1] / tot[0], 3), "couverture_60": round(tot[2] / tot[0], 3)},
         "series": res, "note": "attendu 0,80 et 0,60 ; critère 0,75-0,85 et 0,55-0,65 sur l'ensemble"}
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
