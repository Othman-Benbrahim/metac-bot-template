"""Sonde des interdictions de survol temporaires de la FAA (bot 0.10.299) : que publie-t-on, sous quelle forme ?

Décision d'auteur du 2026-11-18, 22 h 35 (carte blanche). Idée : une interdiction de survol « VIP » précède souvent le
déplacement d'un chef d'État aux États-Unis ; avec les avions d'État déjà collectés, une rencontre au sommet se
prépare de façon visible (cartes RÉSEAU, RÉCIPROCITÉ). Avant toute collecte, cette sonde regarde ce que rendent les
adresses publiques de la FAA (robots.txt respecté), sans rien enregistrer d'autre qu'un résumé.

    python sonde_tfr.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import httpx

import politesse

ADRESSES = ["https://tfr.faa.gov/tfr2/list.jsp", "https://tfr.faa.gov/tfr3/", "https://tfr.faa.gov/tfrapi/exportTfrList"]
SORTIE = Path("registre/sonde-tfr.json")


def principal() -> int:
    out = {}
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=30, follow_redirects=True) as c:
        for u in ADRESSES:
            try:
                if not politesse.autorise(c, u):
                    out[u] = {"etat": "refusé par robots.txt"}
                    continue
                r = c.get(u)
                t = r.text
                out[u] = {"etat": r.status_code, "type": r.headers.get("content-type"), "taille": len(t),
                          "mentions_vip": len(re.findall(r"\bVIP\b", t)), "extrait": t[:300]}
            except Exception as e:
                out[u] = {"etat": f"{type(e).__name__}: {str(e)[:120]}"}
            print(u, json.dumps(out[u], ensure_ascii=False)[:400], flush=True)
    SORTIE.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
