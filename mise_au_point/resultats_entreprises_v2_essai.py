"""Version 2 des fourchettes de chiffre d'affaires trimestriel (preenregistrements/resultats-entreprises.md, v2) :
modèle saisonnier de Foster (1977) avec φ = 1, jugé sur les 25 entreprises jamais vues (NOUVELLES_V2)."""
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
from collecte_edgar import NOUVELLES_V2

SORTIE = Path("registre") / "mise-au-point" / "resultats-entreprises-v2.json"
PS = (0.1, 0.2, 0.8, 0.9)


def _q(pas: list[float], p: float) -> float:
    pas = sorted(pas)
    i = p * (len(pas) - 1)
    lo, hi = int(i), min(len(pas) - 1, int(i) + 1)
    return pas[lo] + (pas[hi] - pas[lo]) * (i - lo)


def fourchette_v2(x: list[float], fenetre: int = 20, minimum: int = 12) -> dict | None:
    """x : logarithmes de trimestres consécutifs, jusqu'au dernier publié. Rend {p: quantile} du trimestre suivant."""
    g = [x[s] - x[s - 4] for s in range(4, len(x))]
    eps = [b - a for a, b in zip(g[:-1], g[1:])][-fenetre:]
    if len(eps) < minimum:
        return None
    centre = x[len(x) - 4] + g[-1]   # x(t−3) + g(t), t = dernier indice
    return {p: centre + _q(eps, p) for p in PS}


def blocs_consecutifs(pts):
    blocs, cur = [], [pts[0]]
    for a, b in zip(pts[:-1], pts[1:]):
        if 80 <= (date.fromisoformat(b[0]) - date.fromisoformat(a[0])).days <= 100:
            cur.append(b)
        else:
            blocs.append(cur)
            cur = [b]
    blocs.append(cur)
    return blocs


def evaluer(par: dict, entreprises, modele: str) -> dict:
    n = c80 = c60 = 0
    detail = {}
    for e in sorted(entreprises):
        if e not in par:
            continue
        ne = ce80 = ce60 = 0
        for bl in blocs_consecutifs(sorted(par[e])):
            x = [math.log(v) for _, v in bl]
            for t in range(1, len(x) - 1):
                if modele == "v2":
                    q = fourchette_v2(x[: t + 1])
                else:
                    if t < 8:
                        continue
                    f = il.fourchette_suivante(x[: t + 1], fenetre=12)
                    q = dict(f) if f else None
                if not q:
                    continue
                ne += 1
                ce80 += q[0.1] <= x[t + 1] <= q[0.9]
                ce60 += q[0.2] <= x[t + 1] <= q[0.8]
        if ne:
            detail[e] = {"n": ne, "couverture_80": round(ce80 / ne, 3), "couverture_60": round(ce60 / ne, 3)}
        n, c80, c60 = n + ne, c80 + ce80, c60 + ce60
    return {"n": n, "couverture_80": round(c80 / n, 3) if n else None,
            "couverture_60": round(c60 / n, 3) if n else None, "entreprises": detail}


def principal() -> int:
    par = defaultdict(list)
    for r in csv.DictReader(open("registre/edgar-trimestres.csv", encoding="utf-8")):
        if r["mesure"] == "chiffre_affaires" and float(r["valeur"]) > 0:
            par[r["entreprise"]].append((r["fin"], float(r["valeur"])))
    anciennes = [e for e in par if e not in NOUVELLES_V2]
    r = {"decision_v2_nouvelles": evaluer(par, NOUVELLES_V2, "v2"),
         "descriptif_v1_nouvelles": evaluer(par, NOUVELLES_V2, "v1"),
         "descriptif_v2_anciennes": evaluer(par, anciennes, "v2"),
         "note": "critère sur decision_v2_nouvelles : 0,75-0,85 (80 %) et 0,55-0,65 (60 %)"}
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    for k in ("decision_v2_nouvelles", "descriptif_v1_nouvelles", "descriptif_v2_anciennes"):
        print(k, {a: r[k][a] for a in ("n", "couverture_80", "couverture_60")})
    return 0


if __name__ == "__main__":
    sys.exit(principal())
