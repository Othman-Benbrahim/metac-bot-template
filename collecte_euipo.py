"""Collecte des dépôts de marques des laboratoires d'IA à l'office européen (EUIPO) — bot 0.10.301, en ombre.

Décision d'auteur du 2026-11-18, 22 h 35 (carte blanche) ; clés enregistrées par l'auteur le 2026-11-19 (EUIPO_CLIENT_ID,
EUIPO_CLIENT_SECRET). Idée : une entreprise dépose le nom d'un produit avant de le lancer. Carte : DÉCLENCHEUR.
Interface officielle « Trademark search » 1.1.0 (spécification jointe par l'auteur) : OAuth2 « client credentials »
(l'utilisateur final reste anonyme) + en-tête X-IBM-Client-Id ; requêtes RSQL.

Seuls des DÉPOSANTS ENTREPRISES listés dans registre/euipo-deposants.txt sont interrogés (aucune personne privée).
Gardés (registre/euipo-marques.jsonl) : numéro, date de dépôt, élément verbal, déposant, statut, date de statut.

    python collecte_euipo.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import httpx

import politesse

REG = Path(os.environ.get("ALPHABET_REGISTRE", "registre"))
DEPOSANTS = REG / "euipo-deposants.txt"
SORTIE = REG / "euipo-marques.jsonl"
JETON = "https://euipo.europa.eu/cas-server-webapp/oidc/accessToken"
API = "https://api.euipo.europa.eu/trademark-search/trademarks"
JOURS = 120                     # fenêtre de dépôt relue à chaque passage (les dépôts sont publiés avec retard)


def deposants() -> list[str]:
    return [l.strip() for l in DEPOSANTS.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("#")] if DEPOSANTS.exists() else []


def requete(nom: str, depuis: date) -> str:
    return f'applicants.name=="{nom}";applicationDate>={depuis.isoformat()}'


def ligne(t: dict, deposant: str, vu_le: str) -> dict:
    return {"numero": t.get("applicationNumber"), "depot": str(t.get("applicationDate") or "")[:10],
            "verbal": ((t.get("wordMarkSpecification") or {}).get("verbalElement") or "")[:200],
            "deposant": deposant, "statut": t.get("status"), "statut_le": str(t.get("statusDate") or "")[:10],
            "vu_le": vu_le}


def principal() -> int:
    cid, secret = os.environ.get("EUIPO_CLIENT_ID"), os.environ.get("EUIPO_CLIENT_SECRET")
    if not cid or not secret:
        print("::warning::EUIPO_CLIENT_ID ou EUIPO_CLIENT_SECRET absent : rien collecté.")
        return 0
    vus = {json.loads(l)["numero"] for l in SORTIE.read_text(encoding="utf-8").splitlines() if l.strip()} if SORTIE.exists() else set()
    aujourdhui = date.today()
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=40) as c:
        r = c.post(JETON, data={"grant_type": "client_credentials", "client_id": cid, "client_secret": secret,
                                "scope": "uid"})
        if r.status_code >= 400:
            print(f"::warning::jeton EUIPO refusé (HTTP {r.status_code}) : {r.text[:200]}")
            return 0
        jeton = r.json()["access_token"]
        entetes = {"X-IBM-Client-Id": cid, "Authorization": f"Bearer {jeton}", "Accept-Language": "en"}
        n = 0
        with SORTIE.open("a", encoding="utf-8") as f:
            for nom in deposants():
                try:
                    r = c.get(API, headers=entetes, params={"query": requete(nom, aujourdhui - timedelta(days=JOURS)),
                                                            "size": 100, "sort": "applicationDate:desc"})
                    if r.status_code >= 400:
                        print(f"{nom} : HTTP {r.status_code} {r.text[:150]}")
                        continue
                    for t in r.json().get("trademarks") or []:
                        if t.get("applicationNumber") and t["applicationNumber"] not in vus:
                            vus.add(t["applicationNumber"])
                            f.write(json.dumps(ligne(t, nom, aujourdhui.isoformat()), ensure_ascii=False) + "\n")
                            n += 1
                    print(f"{nom} : {r.json().get('totalElements')} dépôt(s) dans la fenêtre", flush=True)
                except Exception as e:
                    print(f"{nom} : {type(e).__name__}: {str(e)[:150]}")
    print(f"EUIPO : {n} nouveau(x) dépôt(s).")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
