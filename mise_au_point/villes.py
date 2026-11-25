"""Villes de 15 000 habitants et plus → pays (2026-11-25, source validée par l'auteur à 14 h 36 : GeoNames, CC BY 4.0,
via le paquet geonamescache 3.0.2, MIT, qui embarque le fichier cities15000 de GeoNames). Écrit ecosystemes/villes.csv,
lu par villes_pays.py (comptes RSS en ombre, pays des briefs, page des entités).

Garde-fous contre les faux positifs (une ville ne doit pas compter quand le mot veut dire autre chose) :
- la recherche se fait en respectant la casse (« Nice », jamais « nice ») ;
- un nom qui est aussi un mot courant en anglais ou en français (fréquence Zipf ≥ 4 dans wordfreq 3.1.1, MIT) n'est gardé
  que pour une ville d'au moins 500 000 habitants (« Paris » oui, « Nice » et « Mobile » non) ;
- un nom porté par des villes de plusieurs pays va au pays de la plus peuplée si elle l'est au moins dix fois plus que la
  suivante (« Paris » → France, pas Texas), sinon il est écarté (« Victoria », « San Fernando ») ;
- les noms d'au moins 4 lettres ; un nom qui est aussi un nom de pays est écarté (« Andorra », « Djibouti ») ;
- en plus du nom officiel, les variantes en alphabet latin des villes d'au moins 100 000 habitants (« Kiev », « Bombay »),
  sauf si la variante est le nom officiel d'une autre ville (« Victoria » pour Hong Kong).
    uv run --with geonamescache==3.0.2 --with wordfreq==3.1.1 python mise_au_point/villes.py
"""
from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

import geonamescache
from wordfreq import zipf_frequency

ICI = Path(__file__).resolve().parent.parent
# noms de villes qui sont surtout des noms de personnes ou des mots dans l'actualité : jamais retenus
EXCLUS = {"Kennedy", "Austin", "Houston", "Jackson", "Lincoln", "Madison", "Charlotte", "Phoenix", "Columbus", "Victoria",
          "Trump", "Biden", "Mobile", "Reading", "Split", "Bath", "Nice", "Orange", "Gary", "Florence", "Eugene", "Tyler",
          "Marion", "Laval", "Valence", "Bergen", "Hamilton", "Wellington", "Kingston", "Richmond", "Stanley", "Douglas"}
SORTIE = ICI / "ecosystemes" / "villes.csv"


def _latin(s: str) -> bool:
    return all(unicodedata.name(ch, "").startswith(("LATIN", "SPACE", "HYPHEN", "APOSTROPHE", "DIGIT")) or ch in "-'’. "
               for ch in s)


def variantes(v: dict) -> set[str]:
    out = {v["name"]}
    if v["population"] >= 100_000:
        for a in v.get("alternatenames", []):
            # un seul mot, 5 lettres au moins ; un mot fréquent seulement pour une ville d'un million d'habitants et plus
            # (« Londres », « Moscou ») : sinon « White House » (Casablanca), « Gold », « Old Town » rattachaient à tort
            if ((5 <= len(a) or v["population"] >= 1_000_000) and len(a) <= 30 and re.fullmatch(r"[A-Z][a-zà-ÿ]+", a) and _latin(a)
                    and (max(zipf_frequency(a.lower(), "en"), zipf_frequency(a.lower(), "fr")) < 3.0 or v["population"] >= 1_000_000)):
                out.add(a)
    return {x for x in out if len(x) >= 4}


def principal() -> int:
    g = geonamescache.GeonamesCache(min_city_population=15000)
    pays = g.get_countries()
    noms_pays = {p["name"].lower() for p in pays.values()} | {p["iso3"].lower() for p in pays.values()}
    iso3 = {k: p["iso3"] for k, p in pays.items()}
    porteurs = defaultdict(list)
    villes = list(g.get_cities().values())
    officiels = {v["name"] for v in villes}
    for v in villes:
        for x in variantes(v):
            if x != v["name"] and x in officiels:      # « Victoria » (ancien nom de Hong Kong) est aussi le nom d'autres villes
                continue
            porteurs[x].append(v)
    lignes, ecartes = [], defaultdict(int)
    for x, vs in porteurs.items():
        if x in EXCLUS:
            ecartes["exclu (nom de personne ou mot)"] += 1
            continue
        if x.lower() in noms_pays:
            ecartes["nom de pays"] += 1
            continue
        par_pays = {}
        for v in vs:
            par_pays[v["countrycode"]] = max(par_pays.get(v["countrycode"], 0), v["population"])
        rang = sorted(par_pays.items(), key=lambda t: -t[1])
        if len(rang) > 1 and rang[0][1] < 10 * rang[1][1]:
            ecartes["ambigu entre pays"] += 1
            continue
        code, pop = rang[0]
        if max(zipf_frequency(x.lower(), "en"), zipf_frequency(x.lower(), "fr")) >= 4.0 and pop < 500_000:
            ecartes["mot courant"] += 1
            continue
        ville = max((v for v in vs if v["countrycode"] == code), key=lambda v: v["population"])["name"]
        lignes.append((x, code, iso3.get(code, ""), ville, pop))
    with SORTIE.open("w", encoding="utf-8", newline="") as f:
        f.write("# Villes de 15 000 habitants et plus (GeoNames, CC BY 4.0, via geonamescache 3.0.2) ; mise_au_point/villes.py\n")
        w = csv.writer(f)
        w.writerow(["variante", "iso2", "iso3", "ville", "population"])
        w.writerows(sorted(lignes, key=lambda t: (t[1], -t[4], t[0])))
    print(len(lignes), "variantes ;", dict(ecartes))
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
