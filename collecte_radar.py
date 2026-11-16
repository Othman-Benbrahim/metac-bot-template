"""Coupures d'internet par pays et par cause, tirées de Cloudflare Radar (bot 0.10.177, en ombre).

Décision d'auteur du 2026-11-16 (13 h 08) : jeton Radar en lecture seule, secret CLOUDFLARE_RADAR_TOKEN.
Source : Cloudflare Radar, annotations de coupures (« outages »), https://api.cloudflare.com/client/v4/radar/
annotations/outages ; données sous licence CC BY-NC 4.0 (attribution, usage non commercial). Source : Cloudflare Radar.

L'apport par rapport à IODA (déjà branché) : la CAUSE de chaque coupure (panne électrique, coupure ordonnée par un
gouvernement, action militaire, câble sectionné, intempéries, problème technique…).

On garde une ligne par coupure et par pays : id, pays, debut, fin, cause, type (national, régional, réseau), portee.
Registre : registre/radar-coupures.csv ; registre/radar-couverture.txt (premier jour couvert).

Usage : python collecte_radar.py [--depuis AAAA-MM-JJ]   (par défaut : les 30 derniers jours)
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx

API = "https://api.cloudflare.com/client/v4/radar/annotations/outages"
SORTIE = Path("registre") / "radar-coupures.csv"
COUVERTURE = Path("registre") / "radar-couverture.txt"
CHAMPS = ["id", "pays", "debut", "fin", "cause", "type", "portee", "motif"]
# 0.10.185 : les coupures ordonnées pendant les examens nationaux (Irak, Syrie, Algérie…) sont routinières et sans
# rapport avec une crise ; repérées dans la description de Cloudflare, elles sont écartées de l'état « coupure
# décidée par l'État » (règle fixée avant tout regard sur les issues).
EXAMENS = re.compile(r"\bexam|baccalaur|ministerial (?:exam|test)|school test", re.I)


def lignes(annotation: dict) -> list[dict]:
    """Une ligne par pays d'une annotation de coupure."""
    o = annotation.get("outage") or {}
    pays = [str(x).upper() for x in (annotation.get("locations") or []) if isinstance(x, str)]
    pays += [str(d.get("code")).upper() for d in (annotation.get("locationsDetails") or [])
             if isinstance(d, dict) and d.get("code") and str(d.get("code")).upper() not in pays]
    commun = {"id": str(annotation.get("id") or ""), "debut": str(annotation.get("startDate") or "")[:10],
              "fin": str(annotation.get("endDate") or "")[:10],
              "cause": str(o.get("outageCause") or annotation.get("outageCause") or "").upper(),
              "type": str(o.get("outageType") or annotation.get("outageType") or "").upper(),
              "portee": str(annotation.get("scope") or "")[:80],
              "motif": "examens" if EXAMENS.search(" ".join(str(annotation.get(k) or "") for k in ("description", "scope")))
              else ""}
    return [{**commun, "pays": p} for p in pays if len(p) == 2]


def lire() -> dict[tuple, dict]:
    if not SORTIE.exists():
        return {}
    return {(x["id"], x["pays"]): x for x in csv.DictReader(SORTIE.open(encoding="utf-8"))}


def principal() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--depuis", default="")
    a = ap.parse_args()
    jeton = os.environ.get("CLOUDFLARE_RADAR_TOKEN", "")
    if not jeton:
        print("CLOUDFLARE_RADAR_TOKEN absent : rien à faire.")
        return 1
    aujourd_hui = datetime.now(timezone.utc).date()
    debut = date.fromisoformat(a.depuis) if a.depuis else aujourd_hui - timedelta(days=30)
    connues = lire()
    avant = len(connues)
    lues = 0
    maintenant = datetime.now(timezone.utc).replace(microsecond=0)
    with httpx.Client(headers={"Authorization": f"Bearer {jeton}"}, timeout=60) as c:
        # 0.10.184 : une fin dans le futur est refusée (400) ; fenêtres de 30 jours au plus, fin = maintenant
        d = datetime(debut.year, debut.month, debut.day, tzinfo=timezone.utc)
        while d < maintenant:
            f = min(maintenant, d + timedelta(days=30))
            offset = 0
            while True:
                r = c.get(API, params={"dateStart": d.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                       "dateEnd": f.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                       "limit": 100, "offset": offset, "format": "json"})
                if r.status_code in (401, 403):
                    print(f"Jeton refusé (HTTP {r.status_code}) : vérifier la permission « Radar : Read » et le compte choisi.")
                    return 1
                if r.status_code >= 400:
                    print(f"HTTP {r.status_code} ({d.date()} → {f.date()}) : {r.text[:400]}")
                    return 1
                corps = r.json()
                ann = ((corps.get("result") or {}).get("annotations")) or []
                for x in ann:
                    for l in lignes(x):
                        connues[(l["id"], l["pays"])] = l
                lues += len(ann)
                if len(ann) < 100:
                    break
                offset += 100
                time.sleep(1)
            print(f"  {d.date()} → {f.date()} : {lues} annotations lues au total")
            d = f
            time.sleep(1)
    SORTIE.parent.mkdir(exist_ok=True)
    with SORTIE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CHAMPS)
        w.writeheader()
        for k in sorted(connues, key=lambda k: (connues[k]["debut"], k)):
            w.writerow({c: connues[k].get(c, "") for c in CHAMPS})
    ancien = COUVERTURE.read_text(encoding="utf-8").strip() if COUVERTURE.exists() else ""
    if not ancien or debut.isoformat() < ancien:
        COUVERTURE.write_text(debut.isoformat() + "\n", encoding="utf-8")
    causes: dict[str, int] = {}
    for v in connues.values():
        causes[v["cause"] or "?"] = causes.get(v["cause"] or "?", 0) + 1
    bilan = (f"{lues} annotations lues depuis le {debut} ; {len(connues) - avant} lignes nouvelles ; "
             f"{len(connues)} au total. Causes : " + ", ".join(f"{k} {n}" for k, n in sorted(causes.items(), key=lambda t: -t[1])))
    print(bilan)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(f"## Cloudflare Radar\n\n{bilan}\n\nSource : Cloudflare Radar (CC BY-NC 4.0).\n")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
