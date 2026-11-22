"""Indicateurs du développement dans le monde (Banque mondiale, WDI) en bloc — bot 0.10.463, hors cadre.

Décision de l'auteur, 2026-11-22, 19 h 41 : observation de l'état avant pour H2 (signal × terrain). Le terrain est
mesuré SANS tri théorique des variables : tous les indicateurs WDI assez renseignés sont gardés, et ce sont les données
qui feront ressortir les candidats (observation 2015-2021 ; test 2022-2026 réservé, préenregistrement dans le projet).

Source : fichier CSV complet publié par la Banque mondiale (licence CC BY 4.0), téléchargé une fois par passage ;
robots.txt respecté. Rien n'entre dans le bot.

Règles fixées avant tout regard sur les données :
- économies seulement (les agrégats régionaux, sans région dans WDICountry.csv, sont écartés) ;
- années 2010 à la dernière disponible ;
- un indicateur est gardé si au moins 70 % des cellules économie × année sont renseignées sur 2014-2021.

Registres :
- registre/banque-mondiale-wdi.csv.gz : une ligne par (pays ISO3, année), une colonne par indicateur gardé ;
- registre/banque-mondiale-indicateurs.csv : code, nom, couverture 2014-2021.
"""
from __future__ import annotations

import csv
import gzip
import io
import os
import sys
import zipfile
from pathlib import Path

REG = Path(os.environ.get("ALPHABET_REGISTRE", "registre"))
SORTIE = REG / "banque-mondiale-wdi.csv.gz"
LISTE = REG / "banque-mondiale-indicateurs.csv"
URL = "https://databank.worldbank.org/data/download/WDI_CSV.zip"
AN0 = 2010
COUV_AN0, COUV_AN1, COUV_MIN = 2014, 2021, 0.70


def economies(texte_pays: str) -> set[str]:
    """Codes ISO3 des économies (une région renseignée) ; les agrégats n'ont pas de région."""
    out = set()
    for r in csv.DictReader(io.StringIO(texte_pays.lstrip("﻿"))):
        if (r.get("Region") or "").strip():
            out.add(r["Country Code"].strip())
    return out


def lire(texte_donnees: str, eco: set[str]) -> tuple[dict, dict, list[int]]:
    """→ valeurs {(iso3, annee): {code: valeur}}, noms {code: nom}, années gardées."""
    lec = csv.reader(io.StringIO(texte_donnees.lstrip("﻿")))
    entete = next(lec)
    i_pays, i_nom, i_code = entete.index("Country Code"), entete.index("Indicator Name"), entete.index("Indicator Code")
    cols = [(j, int(h)) for j, h in enumerate(entete) if h.strip().isdigit() and int(h) >= AN0]
    vals: dict[tuple[str, int], dict[str, float]] = {}
    noms: dict[str, str] = {}
    for r in lec:
        if len(r) <= i_code or r[i_pays] not in eco:
            continue
        code = r[i_code]
        noms[code] = r[i_nom]
        for j, an in cols:
            if j < len(r) and r[j].strip():
                try:
                    vals.setdefault((r[i_pays], an), {})[code] = float(r[j])
                except ValueError:
                    pass
    return vals, noms, [an for _, an in cols]


def couverture(vals: dict, noms: dict, eco: set[str]) -> dict[str, float]:
    cellules = len(eco) * (COUV_AN1 - COUV_AN0 + 1)
    n = dict.fromkeys(noms, 0)
    for (p, an), d in vals.items():
        if COUV_AN0 <= an <= COUV_AN1:
            for code in d:
                n[code] += 1
    return {code: n[code] / cellules for code in noms}


def ecrire(vals: dict, noms: dict, annees: list[int], eco: set[str], couv: dict[str, float],
           sortie: Path = SORTIE, liste: Path = LISTE) -> list[str]:
    gardes = sorted(c for c, v in couv.items() if v >= COUV_MIN)
    sortie.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(sortie, "wt", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pays", "annee"] + gardes)
        for p in sorted(eco):
            for an in annees:
                d = vals.get((p, an), {})
                w.writerow([p, an] + [("%.6g" % d[c]) if c in d else "" for c in gardes])
    with liste.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["code", "nom", "couverture_2014_2021"])
        for c in sorted(noms):
            w.writerow([c, noms[c], "%.3f" % couv[c]])
    return gardes


def principal() -> int:
    import httpx
    import politesse
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=600, follow_redirects=True) as c:
        if not politesse.autorise(c, URL):
            print("::warning::Banque mondiale : refusé par robots.txt ; rien collecté.")
            return 0
        r = c.get(URL)
        r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    noms_fichiers = z.namelist()
    f_pays = next(n for n in noms_fichiers if n.lower().endswith("country.csv"))
    f_don = next(n for n in noms_fichiers if n.lower() in ("wdicsv.csv", "wdidata.csv"))
    eco = economies(z.read(f_pays).decode("utf-8", "replace"))
    vals, noms, annees = lire(z.read(f_don).decode("utf-8", "replace"), eco)
    couv = couverture(vals, noms, eco)
    gardes = ecrire(vals, noms, annees, eco, couv)
    print(f"Banque mondiale : {len(eco)} économies, années {annees[0]}-{annees[-1]}, {len(noms)} indicateurs, "
          f"{len(gardes)} gardés (couverture ≥ {COUV_MIN:.0%} sur {COUV_AN0}-{COUV_AN1}).")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
