"""Prévisions de température GFS (NOAA) aux points météo des écosystèmes (bot 0.10.355).

Décision de l'auteur du 2026-11-19 (15 h 57), après le tri des sources citées par Agentic Earth : on n'avait que la
météo OBSERVÉE (collecte_meteo.py, GHCN-Daily) ; on ajoute la météo ANNONCÉE. Source : le modèle GFS de la NOAA,
publié en données ouvertes sur AWS (bucket public noaa-gfs-bdp-pds, sans clé), grille à 1°.

On ne télécharge pas les fichiers entiers : l'index (.idx) de chaque échéance donne la position du seul champ
« TMP:2 m above ground », lu par une requête partielle (Range). Run de 00 h UTC du jour (sinon de la veille) ;
pour chaque jour cible J+1 à J+ECHEANCES, moyenne des quatre instants 00, 06, 12, 18 h UTC ; valeur au point de
grille le plus proche de chaque point de collecte_meteo.POINTS. Décodage GRIB2 par pygrib, installé seulement par
le workflow de cette collecte (uv run --with pygrib), pour ne pas alourdir les autres.

Registre : registre/gfs-previsions.csv (run, point, jour, echeance, t_moy en °C), complété à chaque passage.
"""
from __future__ import annotations

import csv
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import httpx

import collecte_meteo as cm
import politesse

REG = Path(os.environ.get("ALPHABET_REGISTRE", "registre"))
SORTIE = REG / "gfs-previsions.csv"
BASE = "https://noaa-gfs-bdp-pds.s3.amazonaws.com"
FICHIER = BASE + "/gfs.{run}/00/atmos/gfs.t00z.pgrb2.1p00.f{h:03d}"
CHAMP = ":TMP:2 m above ground:"
ECHEANCES = 7
PAUSE = 0.5
COLONNES = ["run", "point", "jour", "echeance", "t_moy"]


def plage(idx: str, champ: str = CHAMP) -> tuple[int, int | None] | None:
    """Index GRIB (« n:octet:d=…:VAR:niveau:échéance: ») → (début, fin incluse ou None si dernier message)."""
    lignes = [l for l in idx.splitlines() if l.strip()]
    for i, l in enumerate(lignes):
        if champ in l:
            debut = int(l.split(":")[1])
            fin = int(lignes[i + 1].split(":")[1]) - 1 if i + 1 < len(lignes) else None
            return debut, fin
    return None


def valeurs_aux_points(grib: bytes) -> dict[str, float]:
    """Champ GRIB2 de température (K) → °C au point de grille le plus proche de chaque point."""
    import numpy as np
    import pygrib
    m = pygrib.fromstring(grib)
    vals = m.values
    lats, lons = m.latlons()
    out = {}
    for p, (la, lo, _) in cm.POINTS.items():
        d = (lats - la) ** 2 + ((lons - lo % 360 + 180) % 360 - 180) ** 2
        i = np.unravel_index(np.argmin(d), d.shape)
        out[p] = round(float(vals[i]) - 273.15, 2)
    return out


def moyennes(instants: dict[int, dict[str, float]]) -> list[tuple[str, int, float]]:
    """{heure d'échéance: {point: °C}} → [(point, échéance en jours, moyenne des quatre instants du jour)]."""
    out = []
    for e in range(1, ECHEANCES + 1):
        hs = [24 * e + k for k in (0, 6, 12, 18)]
        if not all(h in instants for h in hs):
            continue
        for p in cm.POINTS:
            out.append((p, e, round(sum(instants[h][p] for h in hs) / 4, 2)))
    return out


def lire() -> list[dict]:
    return list(csv.DictReader(SORTIE.open(encoding="utf-8"))) if SORTIE.exists() else []


def principal() -> int:
    lignes = lire()
    faits = {r["run"] for r in lignes}
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=120) as c:
        if not politesse.autorise(c, BASE + "/gfs."):
            print("::warning::GFS : refusé par robots.txt ; rien collecté.")
            return 0
        run = None
        for d in (date.today(), date.today() - timedelta(days=1)):
            r = c.get(FICHIER.format(run=d.strftime("%Y%m%d"), h=24 * ECHEANCES + 18) + ".idx")
            if r.status_code == 200:
                run = d
                break
        if run is None:
            print("::warning::GFS : aucun run de 00 h complet aujourd'hui ni hier ; rien collecté.")
            return 0
        if run.isoformat() in faits:
            print(f"GFS : run du {run} déjà enregistré.")
            return 0
        instants = {}
        for e in range(1, ECHEANCES + 1):
            for k in (0, 6, 12, 18):
                h = 24 * e + k
                url = FICHIER.format(run=run.strftime("%Y%m%d"), h=h)
                try:
                    ri = c.get(url + ".idx")
                    ri.raise_for_status()
                    pl = plage(ri.text)
                    if pl is None:
                        continue
                    rng = f"bytes={pl[0]}-" + ("" if pl[1] is None else str(pl[1]))
                    rg = c.get(url, headers={"Range": rng})
                    rg.raise_for_status()
                    instants[h] = valeurs_aux_points(rg.content)
                except Exception as ex:
                    print(f"::warning::GFS f{h:03d} : {type(ex).__name__}", flush=True)
                time.sleep(PAUSE)
    neuves = [{"run": run.isoformat(), "point": p, "jour": (run + timedelta(days=e)).isoformat(), "echeance": e, "t_moy": t}
              for p, e, t in moyennes(instants)]
    if not neuves:
        print("::warning::GFS : aucune journée complète ; rien écrit.")
        return 0
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with SORTIE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLONNES)
        w.writeheader()
        w.writerows(lignes + neuves)
    print(f"GFS : run du {run}, {len(neuves)} prévisions ({len(instants)} champs lus).")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
