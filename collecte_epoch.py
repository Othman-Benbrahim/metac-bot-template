"""Epoch AI, base des modèles d'IA (all_ai_models.csv, mise à jour quotidienne, licence CC BY) — bot 0.10.505.

Source validée par l'auteur le 2026-11-24 (14 h 35, « à brancher ») ; décision du 2026-11-24 (16 h 52 : « On commence »,
produits). Mesure de la cadence de sortie des modèles par laboratoire, pour les questions « le modèle X sortira-t-il
d'ici… ». Colonnes de texte libre (résumé, notes, citations, liens) écartées. robots.txt respecté.
Sortie : registre/epoch-modeles.csv.
"""
from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

import httpx

import politesse

URL = "https://epoch.ai/data/all_ai_models.csv"
SORTIE = Path("registre") / "epoch-modeles.csv"
TEXTE = ("abstract", "note", "citation", "link", "description", "reference", "source", "comment", "url")


def principal() -> int:
    with httpx.Client(follow_redirects=True, timeout=180, headers={"User-Agent": politesse.UA}) as c:
        if not politesse.autorise(c, URL):
            print("Epoch : refusé par robots.txt, rien collecté")
            return 0
        r = c.get(URL)
        r.raise_for_status()
    lec = csv.DictReader(io.StringIO(r.content.decode("utf-8-sig", errors="replace")))
    ent = lec.fieldnames or []
    garde = [x for x in ent if not any(t in x.lower() for t in TEXTE)]
    SORTIE.parent.mkdir(exist_ok=True)
    n = 0
    with SORTIE.open("w", encoding="utf-8", newline="\n") as f:
        w = csv.DictWriter(f, fieldnames=garde, extrasaction="ignore")
        w.writeheader()
        for x in lec:
            w.writerow(x)
            n += 1
    print(f"Epoch : {n} modèles ; colonnes gardées : {garde}")
    print(f"  écartées : {[x for x in ent if x not in garde]}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
