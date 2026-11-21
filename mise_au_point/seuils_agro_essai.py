"""Essai de cohérence des seuils agroclimatiques sur nos propres mesures (préenregistrement :
preenregistrements/seuils-agro.md). Aucun appel de modèle ; lancé une fois, après la première collecte ERA5-Land.

Pour chaque couple (point, culture, période sensible, seuil) et chaque année de 2005 à 2025 :
- exposition : somme sur la période des degrés au-dessus du seuil de la température maximale du jour (ERA5-Land,
  registre/era5land-points.csv) ;
- écart de rendement : rendement national de l'année (USDA PSD, fichier public psd_grains_pulses_csv.zip) rapporté à
  sa tendance linéaire 1990-2025 estimée SANS l'année elle-même, en pourcentage.
Statistique : corrélation de Spearman ; intervalle à 90 % par bootstrap sur les années (5 000 tirages).

    python mise_au_point/seuils_agro_essai.py
"""
from __future__ import annotations

import csv
import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ERA5 = Path("registre") / "era5land-points.csv"
SORTIE = Path("registre") / "mise-au-point" / "seuils-agro.json"
PSD = "https://apps.fas.usda.gov/psdonline/downloads/psd_grains_pulses_csv.zip"
ANNEES = range(2005, 2026)
COUPLES = [   # (nom, point, pays PSD, culture PSD, mois de début, mois de fin, seuil °C)
    ("maïs américain", "iowa", "United States", "Corn", 6, 8, 29.0),
    ("blé américain", "kansas", "United States", "Wheat", 5, 6, 34.0),
    ("blé indien", "pendjab", "India", "Wheat", 3, 4, 34.0),
]


def expositions(point: str, m1: int, m2: int, seuil: float) -> dict[int, float]:
    par: dict[int, float] = {}
    jours: dict[int, int] = {}
    with ERA5.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["point"] != point or not r["tmax"]:
                continue
            a, m = int(r["jour"][:4]), int(r["jour"][5:7])
            if m1 <= m <= m2:
                par[a] = par.get(a, 0.0) + max(0.0, float(r["tmax"]) - seuil)
                jours[a] = jours.get(a, 0) + 1
    attendu = {a: sum((31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)[m - 1] for m in range(m1, m2 + 1)) for a in par}
    return {a: round(v, 2) for a, v in par.items() if jours[a] >= 0.95 * attendu[a]}   # années complètes seulement


def rendements(contenu_zip: bytes, pays: str, culture: str) -> dict[int, float]:
    with zipfile.ZipFile(io.BytesIO(contenu_zip)) as z:
        texte = z.read(next(n for n in z.namelist() if n.lower().endswith(".csv"))).decode("utf-8", "replace")
    out = {}
    for r in csv.DictReader(io.StringIO(texte)):
        if r.get("Country_Name") == pays and r.get("Commodity_Description") == culture \
                and r.get("Attribute_Description") == "Yield":
            try:
                out[int(r["Market_Year"])] = float(r["Value"])
            except (KeyError, ValueError):
                pass
    return out


def ecarts_tendance(rdt: dict[int, float]) -> dict[int, float]:
    ans = [a for a in sorted(rdt) if 1990 <= a <= 2025]
    out = {}
    for a in ans:
        x = np.array([b for b in ans if b != a], float)
        y = np.array([rdt[b] for b in ans if b != a])
        pente, origine = np.polyfit(x, y, 1)
        out[a] = round(100 * (rdt[a] / (pente * a + origine) - 1), 2)
    return out


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    rx, ry = np.argsort(np.argsort(x)), np.argsort(np.argsort(y))
    return float(np.corrcoef(rx, ry)[0, 1])


def principal() -> int:
    import httpx
    import politesse
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=120, follow_redirects=True) as c:
        if not politesse.autorise(c, PSD):
            print("USDA PSD : robots.txt refuse ; essai impossible")
            return 1
        zp = c.get(PSD).content
    res = {}
    rng = np.random.default_rng(sum(map(ord, "seuils-agro")))
    for nom, point, pays, cul, m1, m2, seuil in COUPLES:
        ex = expositions(point, m1, m2, seuil)
        ec = ecarts_tendance(rendements(zp, pays, cul))
        ans = [a for a in ANNEES if a in ex and a in ec]
        if len(ans) < 10:
            res[nom] = {"n": len(ans), "statut": "données insuffisantes"}
            continue
        x, y = np.array([ex[a] for a in ans]), np.array([ec[a] for a in ans])
        rho = spearman(x, y)
        b = []
        for _ in range(5000):
            i = rng.integers(0, len(ans), len(ans))
            if len(set(x[i])) > 1 and len(set(y[i])) > 1:
                b.append(spearman(x[i], y[i]))
        ic = [round(float(v), 3) for v in np.percentile(b, [5, 95])]
        res[nom] = {"n": len(ans), "point": point, "periode_mois": [m1, m2], "seuil": seuil, "spearman": round(rho, 3),
                    "intervalle_90": ic, "confirme": bool(ic[1] < 0),
                    "annees": {a: {"exposition": ex[a], "ecart_rendement_pct": ec[a]} for a in ans}}
    r = {"couples": res, "note": "confirmé si l'intervalle à 90 % de la corrélation de Spearman est entièrement sous 0 "
                                 "(plus de chaleur au-dessus du seuil, rendement sous la tendance)"}
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "annees"} for k, v in res.items()}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
