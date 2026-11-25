"""Taux directeurs des banques centrales, BIS (2026-11-25, validé par l'auteur à 18 h 12, proposition 1).

Fichier en bloc « Central bank policy rates (CSV, flat) » : https://data.bis.org/static/bulk/WS_CBPOL_csv_flat.zip
(page data.bis.org/bulkdownload). Conditions (bis.org/about/legal/permitted-use-statistics) : reproduction permise,
la BIS citée comme source, aucun frais ajouté, aucune caution implicite. robots.txt vérifié.

Les noms de colonnes ne sont pas devinés : sont gardées celles dont le nom commence par FREQ, REF_AREA, TIME_PERIOD et
OBS_VALUE (format « CODE:Libellé » des fichiers plats de la BIS) ; toutes les colonnes vues sont notées dans etat.json.
Écrit registre/bis/taux-directeurs.csv.gz (freq, pays, date, taux) et etat.json.
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import sys
import zipfile
from pathlib import Path

import httpx

import politesse

URL = "https://data.bis.org/static/bulk/WS_CBPOL_csv_flat.zip"
DOSSIER = Path("registre") / "bis"


def colonne(entete: list[str], code: str) -> int | None:
    for i, h in enumerate(entete):
        if h.split(":")[0].strip().upper() == code:
            return i
    return None


def lire(contenu: bytes) -> tuple[list[str], list[tuple]]:
    z = zipfile.ZipFile(io.BytesIO(contenu))
    nom = next(n for n in z.namelist() if n.lower().endswith(".csv"))
    r = csv.reader(io.TextIOWrapper(z.open(nom), encoding="utf-8-sig"))
    entete = next(r)
    i = {k: colonne(entete, k) for k in ("FREQ", "REF_AREA", "TIME_PERIOD", "OBS_VALUE")}
    if None in i.values():
        return entete, []
    out = []
    for l in r:
        v = l[i["OBS_VALUE"]].strip()
        if not v or v.upper() == "NAN":
            continue
        try:
            out.append((l[i["FREQ"]].split(":")[0], l[i["REF_AREA"]].split(":")[0], l[i["TIME_PERIOD"]], float(v)))
        except ValueError:
            continue
    return entete, out


def principal() -> int:
    DOSSIER.mkdir(parents=True, exist_ok=True)
    etat: dict = {"source": "BIS, central bank policy rates (WS_CBPOL)", "url": URL}
    with httpx.Client(headers={"User-Agent": politesse.UA}, follow_redirects=True, timeout=300) as c:
        if not politesse.autorise(c, URL):
            etat["statut"] = "refuse_robots"
        else:
            r = c.get(URL)
            etat["http"] = r.status_code
            if r.status_code == 200:
                entete, L = lire(r.content)
                etat["colonnes"] = entete
                if L:
                    with gzip.open(DOSSIER / "taux-directeurs.csv.gz", "wt", encoding="utf-8", newline="") as f:
                        w = csv.writer(f)
                        w.writerow(["freq", "pays", "date", "taux"])
                        w.writerows(L)
                    etat.update({"statut": "ok", "lignes": len(L), "pays": sorted({x[1] for x in L}),
                                 "frequences": sorted({x[0] for x in L}), "date_max": max(x[2] for x in L)})
                else:
                    etat["statut"] = "colonnes introuvables"
    (DOSSIER / "etat.json").write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(etat, ensure_ascii=False, indent=1)[:3000])
    return 0 if etat.get("statut") == "ok" else 1


if __name__ == "__main__":
    sys.exit(principal())
