"""Collecte des températures quotidiennes en quelques points clés des écosystèmes (Open-Meteo, archive) — 0.10.318.

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
from datetime import date, timedelta
from pathlib import Path

import httpx

import politesse

REG = Path(os.environ.get("ALPHABET_REGISTRE", "registre"))
SORTIE = REG / "meteo-points.csv"
URL = "https://archive-api.open-meteo.com/v1/archive"
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


def principal() -> int:
    fin = (date.today() - timedelta(days=6)).isoformat()      # l'archive a quelques jours de retard
    lignes = []
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=90) as c:
        if not politesse.autorise(c, URL):
            print("::warning::Open-Meteo : refusé par robots.txt ; rien collecté.")
            return 0
        for nom, (lat, lon, _) in POINTS.items():
            try:
                r = c.get(URL, params={"latitude": lat, "longitude": lon, "start_date": DEBUT, "end_date": fin,
                                       "daily": "temperature_2m_mean", "timezone": "UTC"})
                r.raise_for_status()
                d = r.json().get("daily") or {}
                vals = [(j, t) for j, t in zip(d.get("time", []), d.get("temperature_2m_mean", [])) if t is not None]
            except Exception as e:
                vals = []
                print(f"::warning::Open-Meteo {nom} : {type(e).__name__}")
            lignes += [(nom, j, t) for j, t in vals]
            print(f"{nom} : {len(vals)} jours" + (f", dernier {vals[-1]}" if vals else ""), flush=True)
            time.sleep(PAUSE)
    if not lignes:
        return 0
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with SORTIE.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["point", "jour", "t_moy"])
        w.writerows(lignes)
    print(f"Open-Meteo : {len(lignes)} valeurs.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
