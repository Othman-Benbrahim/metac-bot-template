"""Cours quotidiens d'actions (Twelve Data, offre gratuite « Basic », clé TWELVEDATA_API_KEY) pour les questions de seuil
de prix (0.10.399, décision d'auteur du 2026-11-20). Aucune cote de marché de prédiction ; seulement des cours de clôture.

Limites de l'offre gratuite : 8 requêtes par minute, 800 par jour ; on fait une requête par action, avec une pause de
8 s. Rien n'entre dans le bot tant que le calibrage sur les questions d'actions n'est pas fait.

    python collecte_actions.py     # écrit registre/actions.csv
"""
from __future__ import annotations

import csv
import os
import sys
import time
from pathlib import Path

import httpx

import politesse

URL = "https://api.twelvedata.com/time_series"
SORTIE = Path("registre") / "actions.csv"
# actions vues dans les questions du bot et du registre (journal du 2026-11-20 ; questions de seuil du registre)
ACTIONS = ["NVDA", "AMD", "AVGO", "MU", "MSTR", "TSLA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NFLX", "COIN", "PLTR",
           "SNOW", "CRM", "INTC", "ORCL"]
DEBUT = "2018-01-01"
PAUSE = 8.0


def principal() -> int:
    cle = os.environ.get("TWELVEDATA_API_KEY")
    if not cle:
        print("::warning::TWELVEDATA_API_KEY absente : rien collecté.")
        return 0
    lignes, manquantes = [], []
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=60) as c:
        if not politesse.autorise(c, URL):
            print("::warning::Twelve Data : refusé par robots.txt ; rien collecté.")
            return 0
        for s in ACTIONS:
            try:
                r = c.get(URL, params={"symbol": s, "interval": "1day", "start_date": DEBUT, "outputsize": 5000,
                                       "order": "ASC", "apikey": cle})
                d = r.json()
                if d.get("status") != "ok":
                    raise ValueError(str(d.get("message") or d.get("code"))[:120])
                vals = [(v["datetime"][:10], float(v["close"])) for v in d.get("values") or []]
            except Exception as e:
                vals = []
                print(f"::warning::{s} : {type(e).__name__} {str(e)[:120]}")
            if not vals:
                manquantes.append(s)
            lignes += [(s, j, v) for j, v in vals]
            print(f"{s} : {len(vals)} cours" + (f", dernier {vals[-1]}" if vals else ""), flush=True)
            time.sleep(PAUSE)
    if not lignes:
        return 0
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with SORTIE.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["serie", "jour", "valeur"])
        w.writerows(lignes)
    print(f"Actions : {len(lignes)} cours ; manquantes : {manquantes or 'aucune'}.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
