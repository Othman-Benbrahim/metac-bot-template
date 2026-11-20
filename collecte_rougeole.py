"""Total des cas de rougeole de l'année publié par le CDC (page « Measles Cases and Outbreaks »), relevé à chaque passage
(0.10.403, décision d'auteur du 2026-11-20 : pari sur le modèle des comptes cumulés, version 1). La page n'offre pas de
fichier de données : on lit la phrase « As of <date>, <n> confirmed measles cases » et on garde une ligne par date de
décompte (aucun texte conservé). Fichier robots respecté. Rien d'autre n'est collecté.

    python collecte_rougeole.py     # complète registre/rougeole-cdc.csv
"""
from __future__ import annotations

import csv
import re
import sys
from datetime import datetime
from pathlib import Path

import httpx

import politesse

URL = "https://www.cdc.gov/measles/data-research/index.html"
SORTIE = Path("registre") / "rougeole-cdc.csv"
PHRASE = re.compile(r"As of ([A-Z][a-z]+ \d{1,2}, \d{4}),\s*(?:a total of\s*)?([\d,]+)\s+confirmed", re.I)


def lire(html: str) -> tuple[str, int] | None:
    texte = re.sub(r"<[^>]+>", " ", html)
    texte = re.sub(r"\s+", " ", texte)
    m = PHRASE.search(texte)
    if not m:
        return None
    jour = datetime.strptime(m.group(1), "%B %d, %Y").date().isoformat()
    return jour, int(m.group(2).replace(",", ""))


def principal() -> int:
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=60, follow_redirects=True) as c:
        if not politesse.autorise(c, URL):
            print("::warning::CDC : refusé par robots.txt ; rien collecté.")
            return 0
        r = c.get(URL)
    v = lire(r.text) if r.status_code == 200 else None
    if not v:
        print(f"::warning::CDC rougeole : total introuvable (HTTP {r.status_code})")
        return 0
    lignes = {}
    if SORTIE.exists():
        lignes = {x["jour"]: int(x["total"]) for x in csv.DictReader(SORTIE.open(encoding="utf-8"))}
    lignes[v[0]] = v[1]
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with SORTIE.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["jour", "total"])
        for j in sorted(lignes):
            w.writerow([j, lignes[j]])
    print(f"CDC rougeole : {v[1]} cas au {v[0]} ; {len(lignes)} relevés")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
