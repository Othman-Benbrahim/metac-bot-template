"""Correlates of War, guerres entre États v4.0 (1816-2007 ; Sarkees et Wayman 2010) — bot 0.10.502.

Décision de l'auteur du 2026-11-24 (16 h 38 : les deux sous-familles ne doivent pas être éludées ; « matriochka ») :
ETH/PRIO ne couvre que les guerres civiles ; COW donne la durée des guerres entre États (dates de début et de fin par
participant, issue). Données codées (noms d'États compris) ; robots.txt respecté.
Sortie : registre/cow-guerres-etats.csv (fichier tel que publié).
"""
from __future__ import annotations

import sys
from pathlib import Path

import httpx

import politesse

URL = "https://correlatesofwar.org/wp-content/uploads/Inter-StateWarData_v4.0.csv"
SORTIE = Path("registre") / "cow-guerres-etats.csv"


def principal() -> int:
    with httpx.Client(follow_redirects=True, timeout=120, headers={"User-Agent": politesse.UA}) as c:
        if not politesse.autorise(c, URL):
            print("COW : refusé par robots.txt, rien collecté")
            return 0
        r = c.get(URL)
        r.raise_for_status()
    texte = r.content.decode("utf-8-sig", errors="replace")
    SORTIE.parent.mkdir(exist_ok=True)
    SORTIE.write_text(texte, encoding="utf-8", newline="\n")
    L = texte.splitlines()
    print(f"COW guerres entre États : {len(L) - 1} lignes ; en-têtes : {L[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
