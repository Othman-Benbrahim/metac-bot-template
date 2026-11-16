"""Nowcasts d'inflation de la Fed de Cleveland, relevés chaque jour (bot 0.10.181, en ombre).

Décision d'auteur du 2026-11-16 (14 h 00) : brancher les deux nowcasts publics (GDPNow, inflation de Cleveland).
La Fed de Cleveland publie chaque jour ouvré ses estimations en temps réel de l'inflation (IPC, IPC sous-jacent, PCE,
PCE sous-jacent ; variation mensuelle, annuelle, trimestrielle annualisée) sur https://www.clevelandfed.org/
indicators-and-data/inflation-nowcasting, en tableaux HTML, sans fichier ni API. Elle n'archive pas ses estimations
jour par jour en téléchargement : on garde donc NOS relevés datés, qui deviennent l'historique sans fuite (ce que la
Fed disait tel jour). Pas de rattrapage possible.

Registre : registre/nowcast-inflation.csv (releve_le, periode, mesure, valeur) ; « periode » est le libellé du mois ou
du trimestre visé tel que la page l'écrit (ex. « November 2026 », « 2026:Q4 ») ; « mesure » est l'en-tête de colonne
(ex. « CPI », « Core CPI », « PCE », « Core PCE »), préfixé du tableau (« mois » ou « trimestre » ou « annee »).
"""
from __future__ import annotations

import csv
import html
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

PAGE = "https://www.clevelandfed.org/indicators-and-data/inflation-nowcasting"
SORTIE = Path("registre") / "nowcast-inflation.csv"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
      "From": "alphabet-situationnel-bot (GitHub Othman-Benbrahim)"}


def _texte(cellule: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", cellule))).strip()


def tableaux(page: str) -> list[list[list[str]]]:
    out = []
    for t in re.findall(r"<table.*?</table>", page, re.S | re.I):
        lignes = []
        for tr in re.findall(r"<tr.*?</tr>", t, re.S | re.I):
            cellules = [_texte(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", tr, re.S | re.I)]
            if cellules:
                lignes.append(cellules)
        if lignes:
            out.append(lignes)
    return out


def releves(tabs: list[list[list[str]]]) -> list[tuple[str, str, float]]:
    """(période, mesure, valeur) : première ligne = en-têtes ; première colonne = période ; cellules numériques."""
    out = []
    for t in tabs:
        entetes = t[0]
        if not any(re.search(r"CPI|PCE", h, re.I) for h in entetes):
            continue
        genre = "trimestre" if any(re.search(r"\d{4}\s*:?\s*Q[1-4]", l[0]) for l in t[1:]) else (
            "annee" if any(re.search(r"year", h, re.I) for h in entetes[:1]) else "mois")
        for l in t[1:]:
            if len(l) < 2:
                continue
            for h, v in zip(entetes[1:], l[1:]):
                m = re.search(r"-?\d+(?:\.\d+)?", v)
                if m and re.search(r"CPI|PCE", h, re.I):
                    out.append((l[0], f"{genre}:{h}", float(m.group(0))))
    return out


def principal() -> int:
    jour = datetime.now(timezone.utc).date().isoformat()
    with httpx.Client(headers=UA, timeout=60, follow_redirects=True) as c:
        r = c.get(PAGE)
    if r.status_code != 200:
        print(f"Page indisponible (HTTP {r.status_code}).")
        return 1
    tabs = tableaux(r.text)
    rel = releves(tabs)
    print(f"{len(tabs)} tableaux, {len(rel)} valeurs relevées.")
    for p, m, v in rel[:12]:
        print(f"  {p} | {m} | {v}")
    if not rel:
        print("Aucune valeur : la page a changé de forme (ou s'affiche par JavaScript) ; rien d'écrit.")
        return 1
    anciens = list(csv.DictReader(SORTIE.open(encoding="utf-8"))) if SORTIE.exists() else []
    garde = [x for x in anciens if x["releve_le"] != jour]
    SORTIE.parent.mkdir(exist_ok=True)
    with SORTIE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["releve_le", "periode", "mesure", "valeur"])
        w.writeheader()
        w.writerows(garde)
        for p, m, v in rel:
            w.writerow({"releve_le": jour, "periode": p, "mesure": m, "valeur": v})
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(f"## Nowcast d'inflation (Cleveland)\n\n{len(rel)} valeurs relevées le {jour}.\n")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
