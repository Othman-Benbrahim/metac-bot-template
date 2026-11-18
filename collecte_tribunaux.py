"""Collecte CourtListener : affaires suivies dans les tribunaux américains (bot 0.10.301, en ombre).

Décision d'auteur du 2026-11-18, 22 h 35 (carte blanche) ; jeton enregistré par l'auteur (COURTLISTENER_CLE).
Carte : DÉCLENCHEUR (une audience fixée, une décision attendue). Interface REST v4 de Free Law Project ; limite gratuite
très basse (5 par minute, 50 par heure, 125 par jour) : au plus 40 requêtes par nuit, espacées de 13 s.

Suivi : les dossiers récemment modifiés de la Cour suprême et de la cour d'appel du circuit de Washington, plus les
recherches de registre/tribunaux-requetes.txt (affaires liées aux questions du tournoi, modifiable). Gardés
(registre/tribunaux-dossiers.jsonl) : identifiant, tribunal, nom de l'affaire, numéro, dates (dépôt, plaidoirie,
dernière modification). Les affaires concernent des institutions et des personnalités publiques ; rien d'autre.

    python collecte_tribunaux.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import date
from pathlib import Path

import httpx

import politesse

REG = Path(os.environ.get("ALPHABET_REGISTRE", "registre"))
REQUETES = REG / "tribunaux-requetes.txt"
SORTIE = REG / "tribunaux-dossiers.jsonl"
API = "https://www.courtlistener.com/api/rest/v4"
MAX_REQUETES = 40
PAUSE = 13.0


def dossier(d: dict, vu_le: str) -> dict:
    return {"id": str(d.get("id") or d.get("docket_id")), "tribunal": d.get("court_id") or d.get("court"),
            "affaire": (d.get("case_name") or d.get("caseName") or "")[:250],
            "numero": d.get("docket_number") or d.get("docketNumber"), "depot": d.get("date_filed") or d.get("dateFiled"),
            "plaidoirie": d.get("date_argued") or d.get("dateArgued"), "maj": d.get("date_modified"), "vu_le": vu_le}


def principal() -> int:
    cle = os.environ.get("COURTLISTENER_CLE")
    if not cle:
        print("::warning::COURTLISTENER_CLE absente : rien collecté.")
        return 0
    vus = {}
    if SORTIE.exists():
        for l in SORTIE.read_text(encoding="utf-8").splitlines():
            if l.strip():
                x = json.loads(l)
                vus[x["id"]] = x.get("maj")
    vu_le = date.today().isoformat()
    demandes = [("dockets", {"court": "scotus", "order_by": "-date_modified"}),
                ("dockets", {"court": "cadc", "order_by": "-date_modified"})]
    if REQUETES.exists():
        demandes += [("search", {"type": "r", "q": q.strip(), "order_by": "dateFiled desc"})
                     for q in REQUETES.read_text(encoding="utf-8").splitlines() if q.strip() and not q.startswith("#")]
    n, faites = 0, 0
    with httpx.Client(headers={"User-Agent": politesse.UA, "Authorization": f"Token {cle}"}, timeout=40) as c, \
            SORTIE.open("a", encoding="utf-8") as f:
        for chemin, params in demandes[:MAX_REQUETES]:
            r = c.get(f"{API}/{chemin}/", params=params)
            faites += 1
            if r.status_code == 429:
                print("limite CourtListener atteinte : reprise au prochain passage")
                break
            if r.status_code >= 400:
                print(f"{chemin} {params} : HTTP {r.status_code}")
            else:
                for d in (r.json().get("results") or [])[:20]:
                    x = dossier(d, vu_le)
                    if x["id"] != "None" and vus.get(x["id"]) != x["maj"]:
                        f.write(json.dumps(x, ensure_ascii=False) + "\n")
                        vus[x["id"]] = x["maj"]
                        n += 1
            time.sleep(PAUSE)
    print(f"CourtListener : {faites} requête(s), {n} dossier(s) nouveaux ou mis à jour.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
