"""Collecte du Federal Register : les textes officiels américains AVANT leur publication (bot 0.10.299, en ombre).

Décision d'auteur du 2026-11-18, 22 h 35 (carte blanche). Le Federal Register affiche en « inspection publique » les
décrets, règles et avis la veille ou quelques jours avant leur publication officielle : l'avenir déjà présent, daté,
officiel, du domaine public (gouvernement fédéral américain). Carte : DÉCLENCHEUR. API officielle, sans clé.

Gardés (registre/federal-register.jsonl) : numéro, agences, type, titre, date de dépôt, date de publication prévue,
première date où nous l'avons vu. Rien n'entre dans le bot.

    python collecte_federal_register.py
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
SORTIE = REG / "federal-register.jsonl"
API = "https://www.federalregister.gov/api/v1/public-inspection-documents/current.json"


def lignes(donnees: dict, vus: set[str], aujourdhui: str) -> list[dict]:
    out = []
    for d in donnees.get("results") or []:
        num = str(d.get("document_number") or "")
        if not num or num in vus:
            continue
        vus.add(num)
        out.append({"numero": num, "type": d.get("type"), "titre": (d.get("title") or "")[:300],
                    "agences": [a.get("name") for a in d.get("agencies") or [] if isinstance(a, dict)],
                    "depose_le": str(d.get("filed_at") or "")[:10], "publication_prevue": d.get("publication_date"),
                    "vu_le": aujourdhui})
    return out


def principal() -> int:
    vus = {json.loads(l)["numero"] for l in SORTIE.read_text(encoding="utf-8").splitlines() if l.strip()} if SORTIE.exists() else set()
    aujourdhui = datetime.now(timezone.utc).date().isoformat()
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=60) as c:
        if not politesse.autorise(c, API):
            print("::warning::Federal Register : refusé par robots.txt ; rien collecté.")
            return 0
        r = c.get(API)
        r.raise_for_status()
        nouvelles = lignes(r.json(), vus, aujourdhui)
    with SORTIE.open("a", encoding="utf-8") as f:
        for l in nouvelles:
            f.write(json.dumps(l, ensure_ascii=False) + "\n")
    print(f"Federal Register : {len(nouvelles)} nouveau(x) document(s) en inspection publique.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
