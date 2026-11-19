"""Collecte des interdictions temporaires de survol de la FAA (TFR) — bot 0.10.304, en ombre.

Décision d'auteur du 2026-11-18, 22 h 35 (carte blanche). La sonde du 2026-11-19 (run 44426923949,
registre/sonde-tfr.json) a trouvé la liste officielle en JSON : https://tfr.faa.gov/tfrapi/exportTfrList.
Une TFR « VIP » ou « SPECIAL » annonce, jours à l'avance, un déplacement présidentiel ou un grand événement :
l'avenir déjà présent, daté, officiel (gouvernement fédéral américain, domaine public). Cartes : RÉSEAU, RÉCIPROCITÉ.

Gardés (registre/faa-tfr.jsonl) : numéro NOTAM, type, centre de contrôle, État, description (≤ 300 caractères),
date de création, première date où nous l'avons vue. Aucune personne privée ; rien n'entre dans le bot.

    python collecte_tfr.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

import politesse

REG = Path(os.environ.get("ALPHABET_REGISTRE", "registre"))
SORTIE = REG / "faa-tfr.jsonl"
API = "https://tfr.faa.gov/tfrapi/exportTfrList"


def lignes(donnees: list, vus: set[str], aujourdhui: str) -> list[dict]:
    out = []
    for d in donnees if isinstance(donnees, list) else []:
        num = str((d or {}).get("notam_id") or "").strip()
        if not num or num in vus:
            continue
        vus.add(num)
        out.append({"notam": num, "type": (d.get("type") or "").strip(), "centre": d.get("facility"),
                    "etat": d.get("state"), "description": (d.get("description") or "").strip()[:300],
                    "cree_le": d.get("creation_date"), "vu_le": aujourdhui})
    return out


def principal() -> int:
    vus = {json.loads(l)["notam"] for l in SORTIE.read_text(encoding="utf-8").splitlines() if l.strip()} if SORTIE.exists() else set()
    aujourdhui = datetime.now(timezone.utc).date().isoformat()
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=60) as c:
        if not politesse.autorise(c, API):
            print("::warning::FAA TFR : refusé par robots.txt ; rien collecté.")
            return 0
        r = c.get(API)
        r.raise_for_status()
        nouvelles = lignes(r.json(), vus, aujourdhui)
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with SORTIE.open("a", encoding="utf-8") as f:
        for l in nouvelles:
            f.write(json.dumps(l, ensure_ascii=False) + "\n")
    types = {}
    for l in nouvelles:
        types[l["type"]] = types.get(l["type"], 0) + 1
    print(f"FAA TFR : {len(nouvelles)} nouvelle(s) interdiction(s) ; par type {types}.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
