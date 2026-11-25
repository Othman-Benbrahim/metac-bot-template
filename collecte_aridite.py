"""Aridité par pays (2026-11-25, source validée par l'auteur à 14 h 36) : Global Aridity Index v3.1, Zomer, Xu et
Trabucco (2022), Scientific Data 9, 409 ; figshare doi 10.6084/m9.figshare.7504448 (CC BY 4.0). Contours des pays :
Natural Earth 1:50 m (domaine public).

L'indice est une moyenne climatique (1970-2000), fixe : on le calcule une fois (et à la main si la source change).
Le raster mondial (30 secondes d'arc) est lu à une résolution réduite (pas de 0,1°), puis chaque cellule est rattachée à
un pays. Par pays : indice moyen, part des terres arides ou hyperarides (indice < 0,2) et part des terres sèches au sens
de l'ONU (indice < 0,65). Écrit registre/aridite/aridite-pays.csv et registre/aridite/etat.json (fichiers trouvés).
    uv run --with rasterio --with numpy python collecte_aridite.py
"""
from __future__ import annotations

import csv
import io
import json
import sys
import tempfile
import zipfile
from pathlib import Path

import httpx

import politesse

API = "https://api.figshare.com/v2/articles/7504448"
PAYS = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson"
DOSSIER = Path("registre") / "aridite"
PAS = 0.1


def principal() -> int:
    import numpy as np
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.features import rasterize
    from rasterio.transform import from_origin

    DOSSIER.mkdir(parents=True, exist_ok=True)
    etat = {}
    with httpx.Client(headers={"User-Agent": politesse.UA}, follow_redirects=True, timeout=1800) as c:
        meta = c.get(API).json()
        fichiers = [(f["name"], f["size"], f["download_url"]) for f in meta.get("files", [])]
        etat["fichiers"] = [(n, s) for n, s, _ in fichiers]
        cand = [f for f in fichiers if "ai" in f[0].lower() and "annual" in f[0].lower()] or \
               [f for f in fichiers if "ai" in f[0].lower().replace("et0", "")]
        if not cand:
            etat["erreur"] = "aucun fichier d'indice annuel"
            (DOSSIER / "etat.json").write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")
            print(json.dumps(etat, ensure_ascii=False, indent=1))
            return 0
        nom, taille, url = min(cand, key=lambda f: f[1])
        etat["lu"] = nom
        if not politesse.autorise(c, url):
            etat["erreur"] = "refuse_robots"
            return 0
        with tempfile.TemporaryDirectory() as d:
            arch = Path(d) / nom
            with c.stream("GET", url) as r, arch.open("wb") as h:
                r.raise_for_status()
                for b in r.iter_bytes(1 << 20):
                    h.write(b)
            if nom.lower().endswith(".zip"):
                z = zipfile.ZipFile(arch)
                tifs = [n for n in z.namelist() if n.lower().endswith(".tif") and "ai" in Path(n).name.lower()]
                etat["tifs"] = tifs
                tif = max(tifs, key=lambda n: z.getinfo(n).file_size)
                z.extract(tif, d)
                chemin = Path(d) / tif
            else:
                chemin = arch
            largeur, hauteur = int(360 / PAS), int(180 / PAS)
            with rasterio.open(chemin) as src:
                nodata = src.nodata
                ai = src.read(1, out_shape=(hauteur, largeur), resampling=Resampling.average, boundless=True,
                              fill_value=nodata if nodata is not None else -1,
                              window=src.window(-180, -90, 180, 90)).astype("float64")
            if nodata is not None:
                ai[ai == nodata] = np.nan
            ai[ai < 0] = np.nan
            if np.nanmax(ai) > 100:           # v3 : indice stocké × 10 000
                ai = ai / 10000.0
            geo = c.get(PAYS).json()
    tr = from_origin(-180, 90, PAS, PAS)
    codes, formes = {}, []
    for i, f in enumerate(geo["features"], start=1):
        p = f["properties"]
        iso2 = p.get("ISO_A2_EH") if p.get("ISO_A2_EH") not in (None, "-99") else p.get("ISO_A2")
        if not iso2 or iso2 == "-99":
            continue
        codes[i] = (iso2, p.get("NAME_FR") or p.get("NAME"))
        formes.append((f["geometry"], i))
    grille = rasterize(formes, out_shape=ai.shape, transform=tr, fill=0, dtype="int32")
    lat = 90 - (np.arange(ai.shape[0]) + 0.5) * PAS
    poids = np.cos(np.radians(lat))[:, None] * np.ones_like(ai)        # aire d'une cellule
    lignes = []
    for i, (iso2, nom_p) in codes.items():
        m = (grille == i) & ~np.isnan(ai)
        if m.sum() < 3:
            continue
        w, v = poids[m], ai[m]
        lignes.append((iso2, nom_p, round(float((w * v).sum() / w.sum()), 4), round(float(100 * w[v < 0.2].sum() / w.sum()), 1),
                       round(float(100 * w[v < 0.65].sum() / w.sum()), 1), int(m.sum())))
    with (DOSSIER / "aridite-pays.csv").open("w", encoding="utf-8", newline="") as f:
        f.write("# Global Aridity Index v3.1 (Zomer, Xu, Trabucco 2022 ; CC BY 4.0), moyenne 1970-2000, par pays (Natural Earth) ; collecte_aridite.py\n")
        w = csv.writer(f)
        w.writerow(["iso2", "pays", "indice_moyen", "part_aride_pct", "part_seche_pct", "cellules"])
        w.writerows(sorted(lignes))
    etat["pays"] = len(lignes)
    (DOSSIER / "etat.json").write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(etat, ensure_ascii=False, indent=1)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(principal())
