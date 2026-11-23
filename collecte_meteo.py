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

0.10.476 (décision de l'auteur, 2026-11-23, 18 h 16 : fiche Inde, « le climat est un facteur structurel ») : la PLUIE
(élément PRCP de GHCN-Daily, dixièmes de mm) pour les points de POINTS_PLUIE, avec sa propre station (la plus proche
qui relève la pluie cette année, souvent pas la même que pour la température). Registre : registre/meteo-pluie.csv
(point, jour, pluie_mm). Adaptateur pluie:<point> : pluie des 30 derniers jours rapportée à la normale des mêmes
fenêtres des années précédentes, en pour cent (la mousson se lit en écart à la normale, comme l'IMD).
"""
from __future__ import annotations

import csv
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import httpx

import politesse

REG = Path(os.environ.get("ALPHABET_REGISTRE", "registre"))
SORTIE = REG / "meteo-points.csv"
BASE = "https://noaa-ghcn-pds.s3.amazonaws.com"
URL = BASE + "/csv/by_station/{station}.csv"
RAYON_KM = 150
RAYON_MAX_KM = 300          # 0.10.339 : si rien à 150 km (Delhi, Iran au premier passage), on élargit
ESSAIS_STATIONS = 6         # stations essayées par point, de la plus proche à la plus lointaine
FRAICHEUR_JOURS = 45        # une station dont le dernier relevé a plus de 45 jours cède la place à la suivante
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
    "nagpur": (21.15, 79.09, "inde : chaleur et mousson (centre du pays)"),
    "mumbai": (19.08, 72.88, "inde : mousson (côte ouest)"),
    "kolkata": (22.57, 88.36, "inde : mousson (est)"),
    "chennai": (13.08, 80.27, "inde : mousson et pluies du nord-est (sud-est)"),
}
# 0.10.476 : points où l'on relève aussi la pluie (fiche Inde, mousson)
POINTS_PLUIE = ("delhi", "nagpur", "mumbai", "kolkata", "chennai")


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


def lire_inventaire(texte: str, an_min: int, element: str = "temperature") -> set[str]:
    """ghcnd-inventory.txt : stations qui ont TAVG, ou TMAX et TMIN (element « temperature »), ou PRCP (« pluie »),
    jusqu'à an_min au moins."""
    el: dict[str, set[str]] = {}
    for l in texte.splitlines():
        p = l.split()
        if len(p) >= 6 and p[3] in ("TAVG", "TMAX", "TMIN", "PRCP") and p[5].isdigit() and int(p[5]) >= an_min:
            el.setdefault(p[0], set()).add(p[3])
    if element == "pluie":
        return {k for k, v in el.items() if "PRCP" in v}
    return {k for k, v in el.items() if "TAVG" in v or {"TMAX", "TMIN"} <= v}


# 0.10.341 : pays admis par point (préfixe FIPS des identifiants GHCN). Le premier passage élargi avait pris pour
# Téhéran une station du Turkménistan (281 km, autre climat) : mieux vaut rien qu'un faux témoin. Bandar Abbas admet
# Oman et les Émirats, sur le même détroit.
PAYS = {"bandar_abbas": ("IR", "MU", "TC"), "teheran": ("IR",), "houston": ("US",), "berlin": ("GM",),
        "shanghai": ("CH",), "delhi": ("IN",), "kyiv": ("UP",), "moscou": ("RS",), "nagpur": ("IN",),
        "mumbai": ("IN",), "kolkata": ("IN",), "chennai": ("IN",)}


def candidates(stations: dict, valides: set[str], lat: float, lon: float,
               pays: tuple[str, ...] | None = None) -> list[tuple[str, float]]:
    """Stations admises (pays admis) par distance croissante : d'abord dans RAYON_KM, sinon dans RAYON_MAX_KM."""
    c = sorted((distance_km((lat, lon), stations[s][:2]), s) for s in valides
               if s in stations and (not pays or s[:2] in pays))
    for r in (RAYON_KM, RAYON_MAX_KM):
        dedans = [(s, round(d, 1)) for d, s in c if d <= r]
        if dedans:
            return dedans[:ESSAIS_STATIONS]
    return []


def choisir(stations: dict, valides: set[str], lat: float, lon: float) -> tuple[str, float] | None:
    c = candidates(stations, valides, lat, lon)
    return c[0] if c else None


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


def lire_pluie(texte: str, debut: str) -> list[tuple[str, float]]:
    """PRCP en dixièmes de mm ; valeurs douteuses (qualité non vide) écartées."""
    out = []
    for r in csv.reader(texte.splitlines()):
        if len(r) < 6 or r[2] != "PRCP" or r[5].strip():
            continue
        try:
            j = f"{r[1][:4]}-{r[1][4:6]}-{r[1][6:8]}"
            v = int(r[3]) / 10
        except (ValueError, IndexError):
            continue
        if j >= debut and v >= 0:
            out.append((j, round(v, 1)))
    return sorted(out)


def meilleure_station(c, cands: list, lecteur, nom: str) -> tuple:
    """La plus proche qui soit fraîche ; sinon la plus fraîche."""
    limite = (date.today() - timedelta(days=FRAICHEUR_JOURS)).isoformat()
    meilleur = (None, 0.0, [])
    for st, km in cands:
        try:
            v = lecteur(c.get(URL.format(station=st)).raise_for_status().text, DEBUT)
        except Exception as e:
            v = []
            print(f"::warning::GHCN-Daily {nom} ({st}) : {type(e).__name__}")
        if v and (not meilleur[2] or v[-1][0] > meilleur[2][-1][0]):
            meilleur = (st, km, v)
        if v and v[-1][0] >= limite:
            meilleur = (st, km, v)
            break
        time.sleep(PAUSE)
    return meilleur


def principal() -> int:
    lignes = []
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=180, follow_redirects=True) as c:
        if not politesse.autorise(c, BASE + "/csv/by_station/"):
            print("::warning::GHCN-Daily : refusé par robots.txt ; rien collecté.")
            return 0
        try:
            stations = lire_stations(c.get(BASE + "/ghcnd-stations.txt").raise_for_status().text)
            inventaire = c.get(BASE + "/ghcnd-inventory.txt").raise_for_status().text
            valides = lire_inventaire(inventaire, date.today().year)
            valides_pluie = lire_inventaire(inventaire, date.today().year, "pluie")
        except Exception as e:
            print(f"::warning::GHCN-Daily : liste des stations illisible ({type(e).__name__}) ; rien collecté.")
            return 0
        print(f"GHCN-Daily : {len(stations)} stations, {len(valides)} avec températures cette année.")
        for nom, (lat, lon, _) in POINTS.items():
            cands = candidates(stations, valides, lat, lon, PAYS.get(nom))
            if not cands:
                print(f"::warning::{nom} : aucune station à moins de {RAYON_MAX_KM} km")
                continue
            limite = (date.today() - timedelta(days=FRAICHEUR_JOURS)).isoformat()
            meilleur = (None, 0.0, [])
            for st, km in cands:                       # la plus proche qui soit fraîche ; sinon la plus fraîche
                try:
                    v = lire_station(c.get(URL.format(station=st)).raise_for_status().text, DEBUT)
                except Exception as e:
                    v = []
                    print(f"::warning::GHCN-Daily {nom} ({st}) : {type(e).__name__}")
                if v and (not meilleur[2] or v[-1][0] > meilleur[2][-1][0]):
                    meilleur = (st, km, v)
                if v and v[-1][0] >= limite:
                    meilleur = (st, km, v)
                    break
                time.sleep(PAUSE)
            st, km, vals = meilleur
            if not st:
                continue
            lignes += [(nom, j, t) for j, t in vals]
            print(f"{nom} : station {st} {stations[st][2]} à {km} km, {len(vals)} jours"
                  + (f", dernier {vals[-1]}" if vals else ""), flush=True)
            time.sleep(PAUSE)
        pluies = []
        for nom in POINTS_PLUIE:
            lat, lon, _ = POINTS[nom]
            cands = candidates(stations, valides_pluie, lat, lon, PAYS.get(nom))
            if not cands:
                print(f"::warning::{nom} (pluie) : aucune station à moins de {RAYON_MAX_KM} km")
                continue
            st, km, vals = meilleure_station(c, cands, lire_pluie, nom)
            if not st:
                continue
            pluies += [(nom, j, x) for j, x in vals]
            print(f"{nom} (pluie) : station {st} {stations[st][2]} à {km} km, {len(vals)} jours"
                  + (f", dernier {vals[-1]}" if vals else ""), flush=True)
            time.sleep(PAUSE)
    if pluies:
        REG.mkdir(parents=True, exist_ok=True)
        with (REG / "meteo-pluie.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["point", "jour", "pluie_mm"])
            w.writerows(pluies)
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
