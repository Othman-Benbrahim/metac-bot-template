"""Calibrage des fourchettes de prix (préenregistrement preenregistrements/fourchettes-de-prix.md, 2026-11-20).

Pour chaque actif et chaque date d'ancrage (tous les 7 jours), fourchettes du modèle log-normal (σ sur 30 rendements)
pour la clôture à 7 et 14 jours calendaires ; on compte la part des clôtures réelles dans l'intervalle central 80 %
(percentiles 10-90) et 60 % (20-80). Aucune cote de marché ; actions : cours non ajustés lus chez Twelve Data.

    python mise_au_point/fourchettes_essai.py [--actions]   # écrit registre/mise-au-point/fourchettes[-actions].json
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import seuils_prix as sp

ACTIONS = "--actions" in sys.argv
SORTIE = Path("registre") / "mise-au-point" / ("fourchettes-actions.json" if ACTIONS else "fourchettes.json")
ACTIFS = list(sp.ACTIONS) if ACTIONS else ["CBBTCUSD", "CBETHUSD", "DCOILBRENTEU", "NASDAQCOM", "SP500", "DJIA"]


def principal() -> int:
    res = {}
    tout = {7: [0, 0, 0], 14: [0, 0, 0]}
    for a in ACTIFS:
        pts = sp.points(a)
        if len(pts) < 60:
            continue
        idx = {j: v for j, v in pts}
        jours = [j for j, _ in pts]
        par = {7: [0, 0, 0], 14: [0, 0, 0]}
        d = date.fromisoformat(max(jours[31], "2018-01-01"))
        fin_serie = date.fromisoformat(jours[-1])
        while d + timedelta(days=15) <= fin_serie:
            e = sp.etat(a, d.isoformat(), 30)
            if e:
                s0, sig = e
                for h in (7, 14):
                    cible = d + timedelta(days=h)
                    reel = next((idx[x] for x in jours if x >= cible.isoformat()), None)  # première clôture à l'échéance
                    if reel is None:
                        continue
                    q = dict(sp.quantiles(s0, sig, h / 365))
                    par[h][0] += 1
                    par[h][1] += q[0.1] <= reel <= q[0.9]
                    par[h][2] += q[0.2] <= reel <= q[0.8]
            d += timedelta(days=7)
        res[a] = {f"{h} j": {"n": v[0], "couverture_80": round(v[1] / v[0], 3) if v[0] else None,
                             "couverture_60": round(v[2] / v[0], 3) if v[0] else None} for h, v in par.items()}
        for h in (7, 14):
            tout[h] = [x + y for x, y in zip(tout[h], par[h])]
    r = {"actifs": res, "ensemble": {f"{h} j": {"n": v[0], "couverture_80": round(v[1] / v[0], 3) if v[0] else None,
                                                  "couverture_60": round(v[2] / v[0], 3) if v[0] else None} for h, v in tout.items()},
         "note": "attendu : 0,80 et 0,60 ; plus bas = fourchettes trop étroites ; plus haut = trop larges"}
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
