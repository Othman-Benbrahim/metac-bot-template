"""Position des compartiments dans le réseau d'influence des fiches (MICMAC adapté) (bot 0.10.386, ombre).

Accord de l'auteur, 2026-11-20, 13 h 16 : première sonde « influence et réseau », par étapes. Le réseau est celui que
les fiches DÉCLARENT : relations entre compartiments (de → vers, avec la force écrite, et le retour s'il est écrit)
et ponts entre fiches (depuis → fiche:compartiment). Ce sont des hypothèses, presque toutes « à vérifier ».

Influence d'un compartiment : ce qu'il atteint ; dépendance : ce qui l'atteint ; chacune en direct et par ricochet
d'un pas (MICMAC de Godet : matrice M, puis M + M²/2 ; forces forte 3, moyenne 2, faible 1). Quadrants par rapport aux
médianes de tous les compartiments : moteur (influent, peu dépendant), relais (influent et dépendant), dépendant,
autonome.

    python position_reseau.py      # écrit registre/position-reseau.json
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import numpy as np
import yaml

SORTIE = Path("registre") / "position-reseau.json"
FORCE = {"forte": 3.0, "moyenne": 2.0, "faible": 1.0}


def reseau() -> tuple[list[str], np.ndarray]:
    fiches = {}
    for f in sorted(glob.glob("ecosystemes/*.yaml")):
        d = yaml.safe_load(open(f, encoding="utf-8")) or {}
        if "theme" in d:
            fiches[Path(f).stem] = d
    noeuds = [f"{t}:{c['id']}" for t, d in fiches.items() for c in d.get("compartiments") or []]
    idx = {n: i for i, n in enumerate(noeuds)}
    M = np.zeros((len(noeuds), len(noeuds)))
    for t, d in fiches.items():
        for r in d.get("relations") or []:
            a, b = idx.get(f"{t}:{r.get('de')}"), idx.get(f"{t}:{r.get('vers')}")
            if a is None or b is None:
                continue
            w = FORCE.get(r.get("force"), 1.0)
            M[a, b] += w
            if r.get("retour") not in (None, "", "0", "aucun"):
                M[b, a] += w
        for p in d.get("ponts") or []:
            a, b = idx.get(f"{t}:{p.get('depuis')}"), idx.get(str(p.get("vers")))
            if a is not None and b is not None:
                M[a, b] += 1.0
    return noeuds, M


def positions() -> dict[str, dict]:
    noeuds, M = reseau()
    T = M + (M @ M) / 2
    inf, dep = T.sum(axis=1), T.sum(axis=0)
    mi, md = float(np.median(inf)), float(np.median(dep))
    out = {}
    for i, n in enumerate(noeuds):
        q = ("moteur" if inf[i] > mi and dep[i] <= md else "relais" if inf[i] > mi else
             "dependant" if dep[i] > md else "autonome")
        out[n] = {"influence": round(float(inf[i]), 2), "dependance": round(float(dep[i]), 2), "quadrant": q}
    return out


def principal() -> int:
    p = positions()
    SORTIE.write_text(json.dumps(p, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    print(len(p), "compartiments ;", dict(Counter(v["quadrant"] for v in p.values())))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
