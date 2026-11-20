"""Calibrage de la prochaine publication de l'inflation de Tokyo (preenregistrements/inflation-tokyo.md).
This service uses API functions from e-Stat, however its contents are not guaranteed by government."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import indicateurs_lents as il

SORTIE = Path("registre") / "mise-au-point" / "inflation-tokyo.json"


def principal() -> int:
    s = sorted((r["mois"], float(r["inflation_hors_frais_sur_un_an"]))
               for r in csv.DictReader(open("registre/estat-tokyo-cpi.csv", encoding="utf-8")) if r["base"] == "2025")
    mois = [m for m, _ in s]
    v = [x for _, x in s]
    n = c80 = c60 = 0
    for t in range(len(v) - 1):
        if not ("2006-01" <= mois[t] <= "2026-09"):
            continue
        f = il.fourchette_suivante(v[: t + 1], h=1)
        if not f:
            continue
        q = dict(f)
        n += 1
        c80 += q[0.1] <= v[t + 1] <= q[0.9]
        c60 += q[0.2] <= v[t + 1] <= q[0.8]
    r = {"n": n, "couverture_80": round(c80 / n, 3), "couverture_60": round(c60 / n, 3),
         "note": "critère 0,75-0,85 et 0,55-0,65 ; e-Stat, contenu non garanti par le gouvernement"}
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
