"""Collecte du Congrès américain : réunions de commissions programmées, nominations (bot 0.10.301, en ombre).

Décision d'auteur du 2026-11-18, 22 h 35 (carte blanche) ; clé api.data.gov enregistrée par l'auteur (CONGRESS_CLE).
Carte : DÉCLENCHEUR (une commission qui programme l'examen d'un texte ou d'une nomination). Interface officielle
api.congress.gov v3 (documentation : dépôt LibraryOfCongress/api.congress.gov), 5 000 requêtes par heure.

Gardés : registre/congres-reunions.jsonl (identifiant, chambre, type, titre, état, date, commissions ; jamais les
témoins) et registre/congres-nominations.jsonl (numéro, description, date de réception, dernière action).

    python collecte_congres.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

import httpx

import politesse

REG = Path(os.environ.get("ALPHABET_REGISTRE", "registre"))
REUNIONS = REG / "congres-reunions.jsonl"
NOMINATIONS = REG / "congres-nominations.jsonl"
API = "https://api.congress.gov/v3"
CONGRES = int(os.environ.get("CONGRES", "119"))
DETAILS_MAX = 80


def _vus(f: Path, cle: str) -> dict:
    out = {}
    if f.exists():
        for l in f.read_text(encoding="utf-8").splitlines():
            if l.strip():
                x = json.loads(l)
                out[x[cle]] = x.get("maj")
    return out


def reunion(d: dict, vu_le: str) -> dict:
    m = d.get("committeeMeeting") or d
    return {"id": str(m.get("eventId")), "chambre": m.get("chamber"), "type": m.get("type"),
            "titre": (m.get("title") or "")[:300], "etat": m.get("meetingStatus"), "date": str(m.get("date") or "")[:10],
            "commissions": [c.get("name") for c in (m.get("committees") or []) if isinstance(c, dict)],
            "maj": m.get("updateDate"), "vu_le": vu_le}


def nomination(n: dict, vu_le: str) -> dict:
    a = n.get("latestAction") or {}
    return {"id": f'{n.get("congress")}-{n.get("number")}{("-" + str(n.get("partNumber"))) if n.get("partNumber") else ""}',
            "description": (n.get("description") or "")[:300], "recue_le": n.get("receivedDate"),
            "derniere_action": (a.get("text") or "")[:300], "action_le": a.get("actionDate"),
            "maj": n.get("updateDate"), "vu_le": vu_le}


def principal() -> int:
    cle = os.environ.get("CONGRESS_CLE")
    if not cle:
        print("::warning::CONGRESS_CLE absente : rien collecté.")
        return 0
    vu_le = date.today().isoformat()
    vus_r, vus_n = _vus(REUNIONS, "id"), _vus(NOMINATIONS, "id")
    nr = nn = 0
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=40, params={"api_key": cle, "format": "json"}) as c:
        details = 0
        with REUNIONS.open("a", encoding="utf-8") as f:
            for chambre in ("house", "senate"):
                r = c.get(f"{API}/committee-meeting/{CONGRES}/{chambre}", params={"limit": 250})
                if r.status_code >= 400:
                    print(f"réunions {chambre} : HTTP {r.status_code}")
                    continue
                for it in r.json().get("committeeMeetings") or []:
                    i = str(it.get("eventId"))
                    if (i in vus_r and vus_r[i] == it.get("updateDate")) or details >= DETAILS_MAX:
                        continue
                    d = c.get(f"{API}/committee-meeting/{CONGRES}/{chambre}/{i}")
                    details += 1
                    if d.status_code < 400:
                        f.write(json.dumps(reunion(d.json(), vu_le), ensure_ascii=False) + "\n")
                        vus_r[i] = it.get("updateDate")
                        nr += 1
        with NOMINATIONS.open("a", encoding="utf-8") as f:
            r = c.get(f"{API}/nomination/{CONGRES}", params={"limit": 250, "sort": "updateDate+desc"})
            if r.status_code < 400:
                for n in r.json().get("nominations") or []:
                    x = nomination(n, vu_le)
                    if vus_n.get(x["id"]) != x["maj"]:
                        f.write(json.dumps(x, ensure_ascii=False) + "\n")
                        vus_n[x["id"]] = x["maj"]
                        nn += 1
            else:
                print(f"nominations : HTTP {r.status_code}")
    print(f"Congrès : {nr} réunion(s) nouvelles ou mises à jour, {nn} nomination(s) nouvelles ou mises à jour.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
