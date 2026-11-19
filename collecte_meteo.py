"""Collecte des températures quotidiennes en quelques points clés des écosystèmes — 0.10.318, source changée en 0.10.322
puis en 0.10.334.

0.10.334 (décision d'auteur du 2026-11-19, 11 h 24) : NASA POWER refuse aussi les robots (run du 2026-11-19, 05 h 13 UTC,
rien collecté) ; on passe à NOAA GHCN-Daily, relevés des stations au sol publiés en données ouvertes sur AWS (Registry
of Open Data, bucket public noaa-ghcn-pds, sans clé). Pour chaque point, la station la plus proche (liste publique
ghcnd-stations.txt) qui a des températures (ghcnd-inventory.txt) jusqu'à l'année en cours ; t_moy = TAVG, sinon
(TMAX + TMIN) / 2 ; valeurs marquées douteuses (qualité non vide) écartées. robots.txt toujours vérifié.

0.10.322 : le premier passage (run 44458151315) a trouvé l'archive d'Open-Meteo interdite aux robots par son robots.txt ;
on la respecte et on passe à NASA POWER (données quotidiennes publiques de la NASA, sans clé), même sortie.

Décision de l'auteur, 2026-11-19, 4 h 43. Open-Meteo : données de réanalyse publiques, gratuites pour un usage non
commercial, sans clé ; une requête par point et par passage. Rien n'entre dans le bot. L'historique long (depuis DEBUT)
sert de référence saisonnière : l'adaptateur meteo:<point> rend l'ANOMALIE du jour par rapport aux mêmes jours de
l'année des années précédentes (c'est l'intensité qui compte, pas la température brute).

Registre : registre/meteo-points.csv (point, jour, t_moy), réécrit à chaque passage.
"""
from __future__ import annotations

import csv
import os
import sys
import time
from datetime import date
from pathlib import Path

import httpx

import politesse

REG = Path(os.environ.get("ALPHABET_REGISTRE", "registre"))
SORTIE = REG / "meteo-points.csv"
BASE = "https://noaa-ghcn-pds.s3.amazonaws.com"
URL = BASE + "/csv/by_station/{station}.csv"
RAYON_KM = 150
DEBUT = "2016-01-01"
PAUSE = 2.0
# point : (latitude, longitude, écosystème et compartiment qui le lisent)
POINTS = {
    "bandar_abbas": (27.18, 56.27, "ormuz : milieu physique (chaleur sur le détroit)"),
    "teheran": (35.69, 51.39, "ormuz : intérieur iranien (chaleur, eau)"),
    "houston": (29.76, -95.37, "énergie mondiale : climat (golfe du Mexique, raffinage)"),
    "berlin": (52.52, 13.41, "énergie mondiale : climat (chauffage européen, gaz)"),
    "shanghai": (31.23, 121.47, "énergie mondiale : demande (Chine)"),
    "delhi": (28.61, 77.21, "énergie mondiale : demande (Inde, chaleur et électricité)"),
    "kyiv": (50.45, 30.52, "russie-ukraine : hiver et saisons (boue, gel, front)"),
    "moscou": (55.76, 37.62, "russie-ukraine : hiver et saisons ; demande de gaz"),
}


def distance_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    import math
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def lire_stations(texte: str) -> dict[str, tuple[float, float, str]]:
    """ghcnd-stations.txt (colonnes fixes) : identifiant 1-11, latitude 13-20, longitude 22-30, nom 42-71."""
    out = {}
    for l in texte.splitlines():
        try:
            out[l[0:11].strip()] = (float(l[12:20]), float(l[21:30]), l[41:71].strip())
        except ValueError:
            continue
    return out


def lire_inventaire(texte: str, an_min: int) -> set[str]:
    """ghcnd-inventory.txt : stations qui ont TAVG, ou TMAX et TMIN, jusqu'à an_min au moins."""
    el: dict[str, set[str]] = {}
    for l in texte.splitlines():
        p = l.split()
        if len(p) >= 6 and p[3] in ("TAVG", "TMAX", "TMIN") and p[5].isdigit() and int(p[5]) >= an_min:
            el.setdefault(p[0], set()).add(p[3])
    return {k for k, v in el.items() if "TAVG" in v or {"TMAX", "TMIN"} <= v}


def choisir(stations: dict, valides: set[str], lat: float, lon: float) -> tuple[str, float] | None:
    c = [(distance_km((lat, lon), stations[s][:2]), s) for s in valides if s in stations]
    c = [x for x in c if x[0] <= RAYON_KM]
    return (min(c)[1], round(min(c)[0], 1)) if c else None


def lire_station(texte: str, debut: str) -> list[tuple[str, float]]:
    """CSV par station : ID,DATE,ELEMENT,DATA_VALUE,M_FLAG,Q_FLAG,S_FLAG,OBS_TIME ; dixièmes de °C."""
    jours: dict[str, dict[str, float]] = {}
    for r in csv.reader(texte.splitlines()):
        if len(r) < 6 or r[2] not in ("TAVG", "TMAX", "TMIN") or r[5].strip():
            continue
        try:
            j = f"{r[1][:4]}-{r[1][4:6]}-{r[1][6:8]}"
            v = int(r[3]) / 10
        except (ValueError, IndexError):
            continue
        if j >= debut:
            jours.setdefault(j, {})[r[2]] = v
    out = []
    for j, e in sorted(jours.items()):
        if "TAVG" in e:
            out.append((j, round(e["TAVG"], 2)))
        elif "TMAX" in e and "TMIN" in e:
            out.append((j, round((e["TMAX"] + e["TMIN"]) / 2, 2)))
    return out


def principal() -> int:
    lignes = []
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=180, follow_redirects=True) as c:
        if not politesse.autorise(c, BASE + "/csv/by_station/"):
            print("::warning::GHCN-Daily : refusé par robots.txt ; rien collecté.")
            return 0
        try:
            stations = lire_stations(c.get(BASE + "/ghcnd-stations.txt").raise_for_status().text)
            valides = lire_inventaire(c.get(BASE + "/ghcnd-inventory.txt").raise_for_status().text, date.today().year)
        except Exception as e:
            print(f"::warning::GHCN-Daily : liste des stations illisible ({type(e).__name__}) ; rien collecté.")
            return 0
        print(f"GHCN-Daily : {len(stations)} stations, {len(valides)} avec températures cette année.")
        for nom, (lat, lon, _) in POINTS.items():
            ch = choisir(stations, valides, lat, lon)
            if not ch:
                print(f"::warning::{nom} : aucune station à moins de {RAYON_KM} km")
                continue
            st, km = ch
            try:
                vals = lire_station(c.get(URL.format(station=st)).raise_for_status().text, DEBUT)
            except Exception as e:
                vals = []
                print(f"::warning::GHCN-Daily {nom} ({st}) : {type(e).__name__}")
            lignes += [(nom, j, t) for j, t in vals]
            print(f"{nom} : station {st} {stations[st][2]} à {km} km, {len(vals)} jours"
                  + (f", dernier {vals[-1]}" if vals else ""), flush=True)
            time.sleep(PAUSE)
    if not lignes:
        return 0
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with SORTIE.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["point", "jour", "t_moy"])
        w.writerows(lignes)
    print(f"GHCN-Daily : {len(lignes)} valeurs.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
