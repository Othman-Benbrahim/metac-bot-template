"""Mouvements des avions d'État de régimes autoritaires, comptés par pays (bot 0.10.180, en ombre).

Décision d'auteur du 2026-11-16 (13 h 47) : les déplacements officiels des dirigeants relèvent de la vie publique
(règle éthique des sources, README-alphabet.md) ; on les compte de façon agrégée par pays, sans dossier sur personne.

Sources :
- liste des avions : plane-alert-db (sdr-enthusiasts, GitHub), catégorie « Dictator Alert » (avions immatriculés au nom
  d'États ou de régimes, d'après le projet de journalistes Dictator Alert) ; licence ODbL 1.0 / DbCL 1.0 ;
- vols : API d'OpenSky Network (/flights/aircraft, jeton OAuth déjà configuré : OPENSKY_CLIENT_ID, OPENSKY_CLIENT_SECRET),
  vols de la veille seulement (l'API n'est mise à jour que la nuit) ; une requête de moins de 24 h coûte 4 crédits,
  soit environ 1 300 crédits par jour sur les 4 000 du compte. Pas d'historique : l'API facture chaque jour passé, le
  rattrapage coûterait des centaines de milliers de crédits ;
- pays des aéroports : OurAirports (domaine public).

Registre (comptes seulement) : registre/avions-etat.csv (jour, pays, arrivees_etrangeres, departs_vers_etranger) :
  arrivees_etrangeres : vols d'avions de la liste arrivés dans le pays depuis un autre pays (visites) ;
  departs_vers_etranger : vols partis du pays vers un autre pays.
registre/avions-etat-jours.txt : jours lus entièrement.
"""
from __future__ import annotations

import csv
import io
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

LISTE = "https://raw.githubusercontent.com/sdr-enthusiasts/plane-alert-db/main/plane-alert-db.csv"
AEROPORTS = "https://davidmegginson.github.io/ourairports-data/airports.csv"
JETON_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
VOLS = "https://opensky-network.org/api/flights/aircraft"
CATEGORIES = {"Dictator Alert"}
SORTIE = Path("registre") / "avions-etat.csv"
JOURS = Path("registre") / "avions-etat-jours.txt"
UA = {"User-Agent": "alphabet-situationnel-bot/1.0 (recherche ; GitHub Othman-Benbrahim)"}


def avions(texte_csv: str) -> list[str]:
    out = []
    for x in csv.DictReader(io.StringIO(texte_csv.lstrip("﻿"))):
        cat = (x.get("Category") or x.get("#Category") or "").strip()
        hexa = (x.get("$ICAO") or x.get("ICAO") or x.get("icao") or "").strip().lower()
        if cat in CATEGORIES and len(hexa) == 6:
            out.append(hexa)
    return sorted(set(out))


def pays_aeroports(texte_csv: str) -> dict[str, str]:
    return {x["ident"]: x["iso_country"] for x in csv.DictReader(io.StringIO(texte_csv)) if x.get("ident")}


def compter(vols: list[dict], aeroports: dict[str, str]) -> dict[str, list[int]]:
    """Par pays : [arrivées depuis l'étranger, départs vers l'étranger]."""
    out: dict[str, list[int]] = {}
    for v in vols:
        dep = aeroports.get(v.get("estDepartureAirport") or "")
        arr = aeroports.get(v.get("estArrivalAirport") or "")
        if not dep or not arr or dep == arr:
            continue
        out.setdefault(arr, [0, 0])[0] += 1
        out.setdefault(dep, [0, 0])[1] += 1
    return out


def principal() -> int:
    cid, secret = os.environ.get("OPENSKY_CLIENT_ID", "").strip(), os.environ.get("OPENSKY_CLIENT_SECRET", "").strip()
    if not cid or not secret:
        print("OPENSKY_CLIENT_ID / OPENSKY_CLIENT_SECRET absents.")
        return 1
    hier = datetime.now(timezone.utc).date() - timedelta(days=1)
    jours = set(JOURS.read_text(encoding="utf-8").split()) if JOURS.exists() else set()
    if hier.isoformat() in jours:
        print(f"{hier} déjà lu.")
        return 0
    with httpx.Client(headers=UA, timeout=60, follow_redirects=True) as c:
        liste = avions(c.get(LISTE).text)
        aeroports = pays_aeroports(c.get(AEROPORTS).text)
        print(f"{len(liste)} avions « Dictator Alert » ; {len(aeroports)} aéroports.")
        r = c.post(JETON_URL, data={"grant_type": "client_credentials", "client_id": cid, "client_secret": secret})
        r.raise_for_status()
        entete = {"Authorization": f"Bearer {r.json()['access_token']}"}
        debut = int(datetime(hier.year, hier.month, hier.day, tzinfo=timezone.utc).timestamp())
        vols, lus, coupe = [], 0, False
        for h in liste:
            rr = c.get(VOLS, params={"icao24": h, "begin": debut, "end": debut + 86399}, headers=entete)
            if rr.status_code == 429:
                print(f"Crédits OpenSky épuisés après {lus} avions (attente demandée : "
                      f"{rr.headers.get('X-Rate-Limit-Retry-After-Seconds')} s) : jour non marqué comme lu.")
                coupe = True
                break
            if rr.status_code == 200 and rr.text.strip():
                try:
                    vols += rr.json() or []
                except ValueError:
                    pass
            lus += 1
            time.sleep(0.4)
    par_pays = compter(vols, aeroports)
    print(f"{hier} : {lus} avions lus, {len(vols)} vols, {sum(v[0] for v in par_pays.values())} arrivées à l'étranger.")
    if coupe:                                          # 0.10.245 : quota du jour épuisé = situation normale, pas une panne
        print("::warning::crédits OpenSky épuisés : jour non marqué comme lu, le prochain passage le reprendra.")
        return 0
    comptes = {}
    if SORTIE.exists():
        comptes = {(x["jour"], x["pays"]): [int(x["arrivees_etrangeres"]), int(x["departs_vers_etranger"])]
                   for x in csv.DictReader(SORTIE.open(encoding="utf-8"))}
    for p, v in par_pays.items():
        comptes[(hier.isoformat(), p)] = v
    SORTIE.parent.mkdir(exist_ok=True)
    with SORTIE.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["jour", "pays", "arrivees_etrangeres", "departs_vers_etranger"])
        for (j, p), v in sorted(comptes.items()):
            w.writerow([j, p, *v])
    jours.add(hier.isoformat())
    JOURS.write_text("\n".join(sorted(jours)) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
