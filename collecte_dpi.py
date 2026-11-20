"""Database of Political Institutions 2023 (Banque interaméricaine de développement, CC BY 4.0) : extrait des acteurs de
veto par pays et par année (préenregistrement preenregistrements/acteurs-de-veto.md, 2026-11-20).

Garde : pays, code ISO3 (ifs), année, CHECKS, CHECKS_LAX, système (présidentiel, parlementaire…), POLARIZ. Aucun modèle
de langue. Rien n'entre dans le bot.

    python collecte_dpi.py      # écrit registre/dpi/dpi-2023-veto.csv
"""
from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

import httpx

import politesse

URL = "https://data.iadb.org/files/download/30f45628-8608-4c0c-ad55-bc4c870dd62d"
SORTIE = Path("registre") / "dpi" / "dpi-2023-veto.csv"
COLONNES = ["countryname", "ifs", "year", "checks", "checks_lax", "system", "polariz"]


def extraire(texte: str) -> list[dict]:
    lignes = list(csv.DictReader(io.StringIO(texte)))
    if not lignes:
        return []
    cles = {k.strip().lower(): k for k in lignes[0]}
    manque = [c for c in COLONNES if c not in cles]
    if manque:
        raise ValueError(f"colonnes absentes : {manque} ; présentes : {list(cles)[:30]}")
    return [{c: (r[cles[c]] or "").strip() for c in COLONNES} for r in lignes]


def principal() -> int:
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=180, follow_redirects=True) as c:
        if not politesse.autorise(c, URL):
            print("::warning::DPI : refusé par robots.txt")
            return 1
        r = c.get(URL)
        r.raise_for_status()
    texte = r.content.decode("utf-8-sig", errors="replace")
    xs = extraire(texte)
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with SORTIE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLONNES)
        w.writeheader()
        w.writerows(xs)
    (SORTIE.parent / "LISEZMOI.md").write_text(
        "# DPI 2023\n\nScartascini, Cruz, Keefer, *The Database of Political Institutions 2023 (DPI2023)*, Banque "
        "interaméricaine de développement, licence CC BY 4.0. Source : https://data.iadb.org/dataset/the-database-of-"
        "political-institutions-dpi-2023 . Extrait (colonnes " + ", ".join(COLONNES) + ") pour l'essai acteurs_de_veto.\n",
        encoding="utf-8")
    annees = sorted({x["year"] for x in xs})
    print(f"DPI : {len(xs)} lignes, {len({x['ifs'] for x in xs})} pays, années {annees[0]}-{annees[-1]}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
