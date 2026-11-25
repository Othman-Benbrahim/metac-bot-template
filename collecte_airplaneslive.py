"""Relevé airplanes.live : aéronefs militaires visibles et codes d'urgence, par pays (bot 0.10.354, ombre).

Décision d'auteur du 2026-11-19 (15 h 38) : une petite collecte pour deux usages.
1. Contrôle de couverture : le même compte que collecte_militaires.py (adsb.fi), par un autre réseau de récepteurs au
   sol (point /v2/mil). L'écart entre les deux dit la part des variations qui vient des récepteurs, pas du ciel ; et
   l'un sert de secours si l'autre tombe.
2. Codes transpondeur d'urgence visibles (point /v2/squawk/…) : 7700 urgence générale, 7600 panne radio, 7500
   intervention illicite (détournement). Comptes seulement.

Conditions : usage non commercial, sans clé, sans garantie de service, une requête par seconde au plus
(https://airplanes.live/api-guide). Données : airplanes.live. Les points /ladd et /pia (appareils dont les propriétaires
demandent la discrétion) ne sont jamais interrogés. robots.txt vérifié. Aucun appareil nommé : des comptes par pays.

Registres (ajout à chaque relevé) :
- registre/militaires-airplaneslive.csv (releve, pays, appareils) ;
- registre/urgences-airplaneslive.csv (releve, code, pays, appareils) ;
- registre/airplaneslive-releves.txt : relevés réussis ;
- registre/airplaneslive-refus.txt : refus du site (401, 403, 429), notés sans échec (2026-11-25).
"""
from __future__ import annotations

import csv
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

import collecte_militaires as cm
import politesse

BASE = "https://api.airplanes.live/v2"
MIL = Path("registre") / "militaires-airplaneslive.csv"
URG = Path("registre") / "urgences-airplaneslive.csv"
RELEVES = Path("registre") / "airplaneslive-releves.txt"
REFUS = Path("registre") / "airplaneslive-refus.txt"   # 2026-11-25 : refus du site (401, 403, 429), datés
CODES = {"7700": "urgence", "7600": "panne_radio", "7500": "detournement"}
PAUSE = 1.5


def ajouter(chemin: Path, entete: list[str], lignes: list[list]) -> None:
    chemin.parent.mkdir(exist_ok=True)
    neuf = not chemin.exists()
    with chemin.open("a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if neuf:
            w.writerow(entete)
        w.writerows(lignes)


def principal() -> int:
    releve = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=60, follow_redirects=True) as c:
        if not politesse.autorise(c, BASE + "/mil"):
            print("::warning::airplanes.live : refusé par robots.txt ; rien relevé.")
            return 0
        try:
            g = c.get(cm.FRONTIERES)
            g.raise_for_status()
            polys = cm.polygones(g.json())
            r = c.get(BASE + "/mil")
            r.raise_for_status()
            mil = cm.compter(r.json(), polys)
            urg = {}
            for code in CODES:
                time.sleep(PAUSE)
                r = c.get(f"{BASE}/squawk/{code}")
                r.raise_for_status()
                urg[code] = cm.compter(r.json(), polys)
        except httpx.HTTPStatusError as e:
            # 2026-11-25 (décision de l'auteur, 22 h 54) : depuis le 22 novembre le site répond 403 à chaque passage.
            # Un refus du site n'est pas une panne de notre côté : on ne le force pas, on le note (refus.txt) et on
            # sort sans échec, pour ne plus envoyer de courriel d'échec deux fois par jour. Le relevé réessaie seul.
            if e.response.status_code in (401, 403, 429):
                with REFUS.open("a", encoding="utf-8") as f:
                    f.write(f"{releve} {e.response.status_code} {e.request.url}\n")
                print(f"::warning::airplanes.live refuse l'accès ({e.response.status_code}) ; noté, non forcé.")
                return 0
            print(f"Relevé impossible : {type(e).__name__}: {str(e)[:150]}")
            return 1
        except Exception as e:
            print(f"Relevé impossible : {type(e).__name__}: {str(e)[:150]}")
            return 1
    ajouter(MIL, ["releve", "pays", "appareils"], [[releve, k, v] for k, v in sorted(mil.items())])
    ajouter(URG, ["releve", "code", "pays", "appareils"],
            [[releve, code, k, v] for code, d in urg.items() for k, v in sorted(d.items())])
    with RELEVES.open("a", encoding="utf-8") as f:
        f.write(releve + "\n")
    bilan = (f"{releve} : {sum(mil.values())} aéronefs militaires visibles ; urgences "
             + ", ".join(f"{CODES[c]} {sum(d.values())}" for c, d in urg.items()) + ". Données : airplanes.live.")
    print(bilan)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fo:
            fo.write(f"## airplanes.live\n\n{bilan}\n")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
