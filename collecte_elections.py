"""Calendrier des élections nationales par pays, tiré de Wikidata (bot 0.10.179, en ombre).

Décision d'auteur du 2026-11-16 (13 h 34) : « Oui ». Source : Wikidata (licence CC0), point d'accès SPARQL public
https://query.wikidata.org/sparql, sans clé. Fiche du catalogue des mécanismes : M10 (une élection nationale proche
s'accompagne de plus de manifestations, de coupures et de tensions).

On garde : qid, pays (ISO à deux lettres), date, type (élection ou référendum), nom anglais.
« Nationale » : l'élection s'applique (P1001, « applies to jurisdiction ») à un État souverain lui-même (P297, code
ISO), ou bien est rattachée (P17) à un pays sans autre juridiction déclarée.

Limite de complétude : celle des contributeurs de Wikidata ; les élections locales sont exclues.
Limite pour les tests rétrospectifs : Wikidata d'aujourd'hui contient aussi des élections anticipées annoncées APRÈS
la date d'une question ; l'indicateur sépare donc « élection dans les 30 jours AVANT » (sans fuite) et « élection
prévue dans les 30 jours APRÈS » (fuite possible pour les élections anticipées, déclarée).

Registre : registre/elections.csv.
Usage : python collecte_elections.py [--depuis AAAA-MM-JJ, défaut 2024-06-01] [--jusqua AAAA-MM-JJ]
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx

SPARQL = "https://query.wikidata.org/sparql"
SORTIE = Path("registre") / "elections.csv"
UA = {"User-Agent": "alphabet-situationnel-bot/1.0 (recherche ; https://github.com/Othman-Benbrahim/metac-bot-template)",
      "Accept": "application/sparql-results+json"}

REQUETE = """
SELECT DISTINCT ?e ?eLabel ?date ?iso ?type WHERE {{
  VALUES (?classe ?type) {{ (wd:Q40231 "election") (wd:Q43109 "referendum") }}
  ?e wdt:P31/wdt:P279* ?classe ;
     wdt:P585 ?date .
  FILTER(?date >= "{debut}T00:00:00Z"^^xsd:dateTime && ?date < "{fin}T00:00:00Z"^^xsd:dateTime)
  {{ ?e wdt:P1001 ?pays . ?pays wdt:P297 ?iso . }}
  UNION
  {{ ?e wdt:P17 ?pays . ?pays wdt:P297 ?iso . FILTER NOT EXISTS {{ ?e wdt:P1001 ?j . }} }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
"""


def lignes(corps: dict) -> list[dict]:
    out = []
    for b in (corps.get("results") or {}).get("bindings") or []:
        v = lambda k: (b.get(k) or {}).get("value", "")
        iso, d = v("iso").upper(), v("date")[:10]
        if len(iso) != 2 or len(d) != 10:
            continue
        out.append({"qid": v("e").rsplit("/", 1)[-1], "pays": iso, "date": d, "type": v("type"), "nom": v("eLabel")[:120]})
    return out


def interroger(c: httpx.Client, debut: date, fin: date) -> list[dict] | None:
    for essai in range(4):
        try:
            r = c.post(SPARQL, data={"query": REQUETE.format(debut=debut.isoformat(), fin=fin.isoformat())})
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(20 * 2 ** essai)
                continue
            r.raise_for_status()
            return lignes(r.json())
        except (httpx.HTTPError, ValueError) as e:
            print(f"  {debut} → {fin} : {type(e).__name__}: {str(e)[:100]}")
            time.sleep(20 * 2 ** essai)
    return None


def principal() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--depuis", default="2024-06-01")   # 0.10.225 : historique pour les combinaisons de mécanismes
    ap.add_argument("--jusqua", default="")
    a = ap.parse_args()
    aujourd_hui = datetime.now(timezone.utc).date()
    debut = date.fromisoformat(a.depuis)
    fin = date.fromisoformat(a.jusqua) if a.jusqua else aujourd_hui + timedelta(days=400)
    toutes: dict[tuple, dict] = {}
    with httpx.Client(headers=UA, timeout=120) as c:
        d = debut
        while d < fin:                                 # par trimestre, pour rester sous la limite de temps du service
            f = min(fin, d + timedelta(days=92))
            res = interroger(c, d, f)
            if res is None:
                print("Wikidata indisponible : registre inchangé.")
                return 1
            for x in res:
                toutes[(x["qid"], x["pays"])] = x
            print(f"  {d} → {f} : {len(res)} élections nationales")
            d = f
            time.sleep(5)
    SORTIE.parent.mkdir(exist_ok=True)
    with SORTIE.open("w", encoding="utf-8", newline="") as fo:
        w = csv.DictWriter(fo, fieldnames=["qid", "pays", "date", "type", "nom"])
        w.writeheader()
        for k in sorted(toutes, key=lambda k: (toutes[k]["date"], k)):
            w.writerow(toutes[k])
    bilan = f"{len(toutes)} élections nationales ({debut} → {fin}), {len({x['pays'] for x in toutes.values()})} pays."
    print(bilan)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fo:
            fo.write(f"## Élections (Wikidata)\n\n{bilan}\n")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
