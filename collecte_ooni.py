"""Censure d'internet par pays et par jour, tirée de l'API d'agrégation d'OONI (bot 0.10.175, en ombre).

Décision d'auteur du 2026-11-16 (12 h 51) : « tu peux préparer », réserve acceptée (le nombre de mesures dépend des
volontaires présents dans le pays : on prend des PARTS, et l'indicateur est absent sous un minimum de mesures).

Source : Open Observatory of Network Interference (OONI), https://api.ooni.io/api/v1/aggregation, gratuit, sans clé.
Licence des données OONI : CC BY-NC-SA 4.0 (attribution, usage non commercial, partage à l'identique). Les comptes
dérivés enregistrés ici sont publiés sous la même licence, avec la mention « Source : OONI ».

On garde, par pays (code ISO à deux lettres), jour de mesure et test :
  mesures, anomalies, confirmees (blocages confirmés)
pour les tests : web_connectivity (sites web) ; telegram, whatsapp, signal, facebook_messenger (messageries).

Registres : registre/ooni-censure.csv ; registre/ooni-jours.txt (jours couverts).
Les mesures arrivent parfois avec retard : chaque passage relit les 7 derniers jours et remplace leurs comptes.

Usage : python collecte_ooni.py [--depuis AAAA-MM-JJ]
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx

API = "https://api.ooni.io/api/v1/aggregation"
TABLE_CODES = "https://raw.githubusercontent.com/datasets/country-codes/main/data/country-codes.csv"
TESTS = ("web_connectivity", "telegram", "whatsapp", "signal", "facebook_messenger")
MESSAGERIES = ("telegram", "whatsapp", "signal", "facebook_messenger")
COMPTES = Path("registre") / "ooni-censure.csv"
JOURS = Path("registre") / "ooni-jours.txt"
UA = {"User-Agent": "alphabet-situationnel-bot/1.0 (recherche ; GitHub Othman-Benbrahim)"}


def pays_iso(c: httpx.Client) -> list[str]:
    try:
        r = c.get(TABLE_CODES, timeout=60)
        r.raise_for_status()
        codes = sorted({(x.get("ISO3166-1-Alpha-2") or "").strip() for x in csv.DictReader(io.StringIO(r.text))})
        codes = [k for k in codes if len(k) == 2 and k.isalpha()]
        if len(codes) > 150:
            return codes + (["XK"] if "XK" not in codes else [])
    except Exception as e:
        print(f"liste des pays indisponible ({type(e).__name__}).")
    return []


def lignes_api(corps: dict) -> list[tuple[str, int, int, int]]:
    """(jour, mesures, anomalies, confirmées) depuis une réponse d'agrégation par jour."""
    out = []
    for x in corps.get("result") or []:
        j = str(x.get("measurement_start_day") or "")[:10]
        if not j:
            continue
        out.append((j, int(x.get("measurement_count") or 0), int(x.get("anomaly_count") or 0),
                    int(x.get("confirmed_count") or 0)))
    return out


def lire() -> tuple[dict[tuple, list[int]], set[str]]:
    comptes = {}
    if COMPTES.exists():
        for x in csv.DictReader(COMPTES.open(encoding="utf-8")):
            comptes[(x["pays"], x["jour"], x["test"])] = [int(x["mesures"]), int(x["anomalies"]), int(x["confirmees"])]
    jours = set(JOURS.read_text(encoding="utf-8").split()) if JOURS.exists() else set()
    return comptes, jours


def ecrire(comptes: dict[tuple, list[int]], jours: set[str]) -> None:
    COMPTES.parent.mkdir(exist_ok=True)
    with COMPTES.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pays", "jour", "test", "mesures", "anomalies", "confirmees"])
        for (p, j, t), v in sorted(comptes.items(), key=lambda k: (k[0][1], k[0][0], k[0][2])):
            w.writerow([p, j, t, *v])
    JOURS.write_text("\n".join(sorted(jours)) + "\n", encoding="utf-8")


def obtenir(c: httpx.Client, params: dict) -> dict | None:
    for essai in range(5):
        try:
            r = c.get(API, params=params)
        except httpx.HTTPError:
            time.sleep(3 * 2 ** essai)
            continue
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(min(60, 3 * 2 ** essai))
            continue
        if r.status_code >= 400:
            print(f"  HTTP {r.status_code} pour {params.get('probe_cc')} / {params.get('test_name')} : {r.text[:150]}")
            return None
        return r.json()
    return None


def principal() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--depuis", default="")
    a = ap.parse_args()
    hier = datetime.now(timezone.utc).date() - timedelta(days=1)
    debut = date.fromisoformat(a.depuis) if a.depuis else hier - timedelta(days=6)
    comptes, jours = lire()
    echecs = 0
    with httpx.Client(headers=UA, follow_redirects=True, timeout=120) as c:
        pays = pays_iso(c)
        if not pays:
            print("Aucune liste de pays : arrêt.")
            return 1
        print(f"{len(pays)} pays × {len(TESTS)} tests, du {debut} au {hier}.")
        for i, p in enumerate(pays):
            for t in TESTS:
                corps = obtenir(c, {"probe_cc": p, "test_name": t, "since": debut.isoformat(),
                                    "until": (hier + timedelta(days=1)).isoformat(), "axis_x": "measurement_start_day"})
                time.sleep(0.3)
                if corps is None:
                    echecs += 1
                    continue
                for j, n, an, co in lignes_api(corps):
                    if debut.isoformat() <= j <= hier.isoformat() and n:
                        comptes[(p, j, t)] = [n, an, co]
            if (i + 1) % 25 == 0:
                print(f"  {i + 1} pays lus")
        if echecs > len(pays) * len(TESTS) // 2:
            print(f"Trop d'échecs ({echecs}) : jours non marqués comme couverts.")
        else:
            d = debut
            while d <= hier:
                jours.add(d.isoformat())
                d += timedelta(days=1)
    ecrire(comptes, jours)
    bilan = f"{echecs} requête(s) en échec ; {len(jours)} jours couverts ; {len(comptes)} cases pays × jour × test."
    print(bilan)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(f"## OONI censure\n\n{bilan}\n\nSource : OONI (CC BY-NC-SA 4.0).\n")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
