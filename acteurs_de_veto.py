"""Acteurs de veto (Tsebelis) par pays : reconnaissance du pays dans un titre et CHECKS de la DPI 2023
(préenregistrement preenregistrements/acteurs-de-veto.md, 2026-11-20).

Pays reconnus : noms de la DPI (registre/dpi/dpi-2023-veto.csv), plus une table de noms courants et d'alias fixée
le 2026-11-20 avant toute lecture des issues (NOMS : les abréviations de la DPI ramenées au nom usuel en anglais ;
ALIAS : démonymes et institutions nationales). Une question n'est retenue que si UN SEUL pays est reconnu.
"""
from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path

DPI = Path("registre") / "dpi" / "dpi-2023-veto.csv"

# nom usuel en anglais → nom de la DPI (abréviations de la DPI)
NOMS = {
    "united states": "USA", "u.s.": "USA", "usa": "USA", "united kingdom": "UK", "britain": "UK", "u.k.": "UK",
    "china": "PRC", "north korea": "PRK", "south korea": "ROK", "korea": "ROK", "germany": "FRG/Germany",
    "south africa": "S. Africa", "czech republic": "Czech Rep.", "czechia": "Czech Rep.",
    "dominican republic": "Dom. Rep.", "central african republic": "Cent. Af. Rep.", "cape verde": "C. Verde Is.",
    "equatorial guinea": "Eq. Guinea", "papua new guinea": "P. N. Guinea", "bosnia": "Bosnia-Herz",
    "united arab emirates": "UAE", "democratic republic of the congo": "Congo (DRC)", "drc": "Congo (DRC)",
    "ivory coast": "Cote d'Ivoire", "côte d'ivoire": "Cote d'Ivoire", "trinidad": "Trinidad-Tobago",
    "solomon islands": "Solomon Is.", "comoros": "Comoro Is.", "saint lucia": "St. Lucia", "burma": "Myanmar",
    "east timor": "Timor-Leste",
}
# démonymes et institutions nationales → nom de la DPI
ALIAS = {
    "american": "USA", "congress": "USA", "senate": "USA", "supreme court": "USA", "white house": "USA",
    "british": "UK", "westminster": "UK", "house of commons": "UK", "chinese": "PRC", "german": "FRG/Germany",
    "bundestag": "FRG/Germany", "french": "France", "israeli": "Israel", "knesset": "Israel", "russian": "Russia",
    "duma": "Russia", "kremlin": "Russia", "ukrainian": "Ukraine", "rada": "Ukraine", "iranian": "Iran",
    "japanese": "Japan", "indian": "India", "italian": "Italy", "spanish": "Spain", "canadian": "Canada",
    "australian": "Australia", "brazilian": "Brazil", "mexican": "Mexico", "turkish": "Turkey", "polish": "Poland",
    "hungarian": "Hungary", "taiwanese": "Taiwan", "venezuelan": "Venezuela", "argentine": "Argentina",
    "argentinian": "Argentina", "saudi": "Saudi Arabia", "egyptian": "Egypt", "pakistani": "Pakistan",
    "south korean": "ROK", "north korean": "PRK", "dutch": "Netherlands", "swedish": "Sweden", "greek": "Greece",
    "irish": "Ireland", "scottish": "UK", "philippine": "Philippines", "nigerian": "Nigeria",
}


@lru_cache(maxsize=1)
def table() -> dict[tuple[str, int], float]:
    out = {}
    if not DPI.exists():
        return out
    for r in csv.DictReader(DPI.open(encoding="utf-8")):
        try:
            v = float(r["checks"])
        except (TypeError, ValueError):
            continue
        if v >= 1:                       # -999 et vides : manquants
            out[(r["countryname"], int(r["year"][:4]))] = v
    return out


@lru_cache(maxsize=1)
def _motif() -> re.Pattern:
    noms = {n for n, _ in table()}
    cles = {n.lower(): n for n in noms if len(n) > 3 and not re.search(r"[./()]", n)}
    cles.update(NOMS)
    cles.update(ALIAS)
    alterne = "|".join(sorted((re.escape(k) for k in cles), key=len, reverse=True))
    return re.compile(r"(?<![\w.])(" + alterne + r")(?![\w])", re.I), cles


def pays(titre: str) -> set[str]:
    rx, cles = _motif()
    return {cles[m.lower()] for m in rx.findall(titre or "") if m.lower() in cles}


def checks(nom: str, annee: int) -> float | None:
    t = table()
    a = min(annee, 2023)
    while a >= 1975:
        if (nom, a) in t:
            return t[(nom, a)]
        a -= 1
    return None


def tranche(v: float | None) -> str | None:
    if v is None:
        return None
    return "1-2" if v < 3 else "3-4" if v < 5 else "5+"
