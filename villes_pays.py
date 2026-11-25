"""Pays d'un texte par les villes qu'il cite (2026-11-25, GeoNames validé par l'auteur à 14 h 36). Table :
ecosystemes/villes.csv (mise_au_point/villes.py : garde-fous contre les faux positifs). Recherche sensible à la casse,
par groupes de 1 à 4 mots consécutifs ; un texte qui cite « Kharkiv » ou « Goma » sans nommer le pays est rattaché à
l'Ukraine ou à la RD Congo.
"""
from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path

ICI = Path(__file__).resolve().parent
MOT = re.compile(r"[\wÀ-ÿ'’.-]+")


@lru_cache(1)
def table() -> dict[str, tuple[str, str, str]]:
    f = ICI / "ecosystemes" / "villes.csv"
    if not f.exists():
        return {}
    with f.open(encoding="utf-8") as h:
        return {r["variante"]: (r["iso2"], r["iso3"], r["ville"]) for r in csv.DictReader(l for l in h if not l.startswith("#"))}


def villes(texte: str) -> list[tuple[str, str, str]]:
    """(iso2, iso3, ville) de chaque ville reconnue, sans doublon, dans l'ordre du texte."""
    t = table()
    mots = [m.strip(".") for m in MOT.findall(texte or "")]
    out, i = [], 0
    while i < len(mots):
        for n in (4, 3, 2, 1):
            g = " ".join(mots[i:i + n])
            if len(mots[i:i + n]) == n and g in t:
                if t[g] not in out:
                    out.append(t[g])
                i += n
                break
        else:
            i += 1
    return out


def pays(texte: str, code: str = "iso2") -> set[str]:
    k = 0 if code == "iso2" else 1
    return {v[k] for v in villes(texte)}
