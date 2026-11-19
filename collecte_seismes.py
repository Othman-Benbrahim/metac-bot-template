"""Collecte des séismes : catalogue public de l'USGS, comptes par jour (bot 0.10.355, ombre).

Décision de l'auteur du 2026-11-19 (15 h 57), après le tri des sources citées par Agentic Earth : on prend la série
complète à la source (service FDSN de l'USGS, gratuit, sans clé), pas seulement le flux d'alertes déjà lu par
collecte_rss.py. Rien n'entre dans le bot.

Premier passage : historique depuis DEBUT, une requête par an (magnitude ≥ 4,5 ; moins de 20 000 lignes par an).
Passages suivants : on reprend les RECHARGE derniers jours (l'USGS révise magnitudes et lieux).

Registre : registre/seismes-usgs.csv, une ligne par jour, jours sans séisme compris (zéro) :
jour, m45, m6, m7 (nombre de séismes au-dessus de la magnitude), mmax, iran_m45 (plateau iranien, boîte IRAN).
"""
from __future__ import annotations

import csv
import io
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import httpx

import politesse

REG = Path(os.environ.get("ALPHABET_REGISTRE", "registre"))
SORTIE = REG / "seismes-usgs.csv"
URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
DEBUT = date(2000, 1, 1)
RECHARGE = 30
PAUSE = 3.0
IRAN = (25.0, 40.0, 44.0, 63.5)        # lat min, lat max, lon min, lon max
COLONNES = ["jour", "m45", "m6", "m7", "mmax", "iran_m45"]


def dans_iran(lat: float, lon: float) -> bool:
    return IRAN[0] <= lat <= IRAN[1] and IRAN[2] <= lon <= IRAN[3]


def agreger(texte: str) -> dict[str, dict]:
    """CSV de l'USGS (time, latitude, longitude, depth, mag, …) → comptes par jour UTC."""
    out: dict[str, dict] = {}
    for r in csv.DictReader(io.StringIO(texte)):
        try:
            j, m = r["time"][:10], float(r["mag"])
            lat, lon = float(r["latitude"]), float(r["longitude"])
        except (KeyError, ValueError, TypeError):
            continue
        if m < 4.5:
            continue
        d = out.setdefault(j, {"m45": 0, "m6": 0, "m7": 0, "mmax": 0.0, "iran_m45": 0})
        d["m45"] += 1
        d["m6"] += m >= 6
        d["m7"] += m >= 7
        d["mmax"] = max(d["mmax"], m)
        d["iran_m45"] += dans_iran(lat, lon)
    return out


def lire() -> dict[str, dict]:
    if not SORTIE.exists():
        return {}
    return {r["jour"]: {k: (float(r[k]) if k == "mmax" else int(r[k])) for k in COLONNES[1:]}
            for r in csv.DictReader(SORTIE.open(encoding="utf-8"))}


def ecrire(par_jour: dict[str, dict], jusqu_a: date) -> None:
    """Tous les jours de DEBUT à jusqu_a, zéros compris."""
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    vide = {"m45": 0, "m6": 0, "m7": 0, "mmax": 0.0, "iran_m45": 0}
    with SORTIE.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLONNES)
        d = DEBUT
        while d <= jusqu_a:
            x = par_jour.get(d.isoformat(), vide)
            w.writerow([d.isoformat(), x["m45"], x["m6"], x["m7"], x["mmax"], x["iran_m45"]])
            d += timedelta(days=1)


def tranches(deja: dict[str, dict], hier: date) -> list[tuple[date, date]]:
    if not deja:
        return [(date(a, 1, 1), min(date(a + 1, 1, 1), hier + timedelta(days=1))) for a in range(DEBUT.year, hier.year + 1)]
    return [(hier - timedelta(days=RECHARGE), hier + timedelta(days=1))]


def principal() -> int:
    deja = lire()
    hier = date.today() - timedelta(days=1)
    n = 0
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=120) as c:
        if not politesse.autorise(c, URL):
            print("::warning::USGS : refusé par robots.txt ; rien collecté.")
            return 0
        for a, b in tranches(deja, hier):
            try:
                r = c.get(URL, params={"format": "csv", "starttime": a.isoformat(), "endtime": b.isoformat(),
                                       "minmagnitude": 4.5, "orderby": "time-asc", "limit": 20000})
                r.raise_for_status()
            except Exception as e:
                print(f"::warning::USGS {a} → {b} : {type(e).__name__} ; on garde l'existant.", flush=True)
                time.sleep(PAUSE)
                continue
            neuf = agreger(r.text)
            j = a
            while j < b:                     # la tranche relue remplace l'ancienne (révisions, zéros compris)
                deja.pop(j.isoformat(), None)
                j += timedelta(days=1)
            deja.update(neuf)
            n += 1
            time.sleep(PAUSE)
    if not n:
        print("::warning::USGS : aucune tranche lue ; rien écrit.")
        return 0
    ecrire(deja, hier)
    print(f"USGS : {n} requêtes ; {sum(x['m45'] for x in deja.values())} séismes ≥ 4,5 depuis {DEBUT}.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
