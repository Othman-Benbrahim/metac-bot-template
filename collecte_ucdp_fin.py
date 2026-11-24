"""UCDP Conflict Termination Dataset v4-2024 (Uppsala), niveau conflit — bot 0.10.500.

Décision de l'auteur du 2026-11-24 (16 h 28) : découpage des accords par type et âge de la guerre (« matriochka »).
Données codées (identifiants, dates, type de conflit, issue de l'épisode : 1 accord de paix, 2 cessez-le-feu,
3 et 4 victoire, 5 faible activité, 6 acteur disparu) ; aucun texte. Citation : Kreutz, J. (2010), « How and when
armed conflicts end », Journal of Peace Research 47(2) ; UCDP. robots.txt respecté.
Sortie : registre/ucdp-fin-conflits.csv (fichier tel que publié). Usage : python collecte_ucdp_fin.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import httpx

import politesse

URL = "https://ucdp.uu.se/downloads/monadterm/UCDPConflictTerminationDataset_v4_2024_Conflict.csv"
SORTIE = Path("registre") / "ucdp-fin-conflits.csv"


def principal() -> int:
    with httpx.Client(follow_redirects=True, timeout=120, headers={"User-Agent": politesse.UA}) as c:
        if not politesse.autorise(c, URL):
            print("UCDP fin des conflits : refusé par robots.txt, rien collecté")
            return 0
        r = c.get(URL)
        r.raise_for_status()
    texte = r.content.decode("utf-8-sig", errors="replace")
    SORTIE.parent.mkdir(exist_ok=True)
    SORTIE.write_text(texte, encoding="utf-8", newline="\n")
    lignes = texte.splitlines()
    print(f"UCDP fin des conflits : {len(lignes) - 1} lignes ; en-têtes : {lignes[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
