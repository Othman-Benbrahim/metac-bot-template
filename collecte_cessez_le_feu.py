"""ETH/PRIO Civil Conflict Ceasefire Dataset (Clayton et al., 2023, Journal of Conflict Resolution 67(7-8)) — 0.10.501.

Décision de l'auteur du 2026-11-24 (16 h 38) : « Cherche ETH/PRIO » (cessez-le-feu et leur tenue). Fichiers publiés par
le projet (ceasefireproject.org) : déclarations de cessez-le-feu (CFD, octobre 2022) et mois de conflit actif (seuil de
25 morts, niveau conflit UCDP). Données codées seulement : les colonnes de texte (« evidence… », « …comment… »,
« actor… » en clair) ne sont pas gardées. robots.txt respecté.
Sorties : registre/cessez-le-feu-declarations.csv, registre/cessez-le-feu-conflits-mois.csv.
"""
from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

import httpx
import openpyxl

import politesse

FICHIERS = {
    "registre/cessez-le-feu-declarations.csv": "https://ceasefireproject.org/wp-content/uploads/2022/11/CFD_oct_2022_id-1.xlsx",
    "registre/cessez-le-feu-conflits-mois.csv":
        "https://ceasefireproject.org/wp-content/uploads/2022/11/CF_incidence_25_conflict_month_2022.xlsx",
}
TEXTE = ("evidence", "comment", "source", "name", "text", "note")


def _garder(col: str) -> bool:
    c = (col or "").lower()
    return bool(c) and not any(t in c for t in TEXTE)


def principal() -> int:
    code = 0
    with httpx.Client(follow_redirects=True, timeout=180, headers={"User-Agent": politesse.UA}) as c:
        for sortie, url in FICHIERS.items():
            if not politesse.autorise(c, url):
                print(f"{url} : refusé par robots.txt")
                continue
            r = c.get(url)
            if r.status_code != 200:
                print(f"{url} : HTTP {r.status_code}")
                code = 1
                continue
            ws = openpyxl.load_workbook(io.BytesIO(r.content), read_only=True, data_only=True).worksheets[0]
            lignes = ws.iter_rows(values_only=True)
            ent = [str(x) if x is not None else "" for x in next(lignes)]
            garde = [i for i, x in enumerate(ent) if _garder(x)]
            Path(sortie).parent.mkdir(exist_ok=True)
            n = 0
            with open(sortie, "w", encoding="utf-8", newline="\n") as f:
                w = csv.writer(f)
                w.writerow([ent[i] for i in garde])
                for L in lignes:
                    w.writerow(["" if L[i] is None else L[i] for i in garde])
                    n += 1
            print(f"{sortie} : {n} lignes ; colonnes gardées : {[ent[i] for i in garde]}")
            print(f"  colonnes écartées (texte) : {[x for x in ent if not _garder(x)]}")
    return code


if __name__ == "__main__":
    sys.exit(principal())
