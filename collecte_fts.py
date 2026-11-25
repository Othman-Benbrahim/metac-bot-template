"""Financement des appels humanitaires (OCHA Financial Tracking Service, publié sur le Humanitarian Data Exchange ;
source validée par l'auteur le 2026-11-25, 5 h 57). Chiffres seulement : appel, pays, année, besoins, fonds reçus.
robots.txt vérifié avant toute requête ; jeu de données trouvé par l'API publique de catalogue (CKAN) du HDX.
Écrit registre/fts/appels.csv.gz.

    python collecte_fts.py
"""
from __future__ import annotations

import csv
import gzip
import io
import sys
from pathlib import Path

import httpx

import politesse

HDX = "https://data.humdata.org/api/3/action/package_show?id={id}"
JEU = "global-requirements-and-funding-data"
SORTIE = Path("registre") / "fts" / "appels.csv.gz"
CHAMPS = ("countryCode", "code", "name", "typeName", "year", "requirements", "funding", "percentFunded")


def principal() -> int:
    with httpx.Client(headers={"User-Agent": politesse.UA}, follow_redirects=True, timeout=120) as c:
        url = HDX.format(id=JEU)
        if not politesse.autorise(c, url):
            print("refusé par robots.txt :", url)
            return 0
        r = c.get(url)
        r.raise_for_status()
        res = [x for x in r.json()["result"]["resources"]
               if x.get("format", "").lower() == "csv" and "requirements_funding" in (x.get("name") or "")
               and "cluster" not in (x.get("name") or "") and "covid" not in (x.get("name") or "")]
        if not res:
            print("ressource introuvable ; noms :", [x.get("name") for x in r.json()["result"]["resources"]])
            return 0
        u = res[0]["url"]
        if not politesse.autorise(c, u):
            print("refusé par robots.txt :", u)
            return 0
        t = c.get(u)
        t.raise_for_status()
    lignes = [l for l in t.text.splitlines() if not l.startswith("#")]   # le HDX ajoute parfois une ligne de balises
    rows = list(csv.DictReader(io.StringIO("\n".join(lignes))))
    print("colonnes :", list(rows[0])[:15] if rows else None, "lignes :", len(rows))
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(SORTIE, "wt", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(CHAMPS)
        for x in rows:
            if str(x.get("countryCode", "")).startswith("#"):
                continue
            w.writerow([x.get(k, "") for k in CHAMPS])
    print("écrit :", SORTIE)
    return 0


if __name__ == "__main__":
    sys.exit(principal())
