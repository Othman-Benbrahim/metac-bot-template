"""Successions des chefs d'État et de gouvernement depuis 1990, d'après Wikidata (2026-11-25, validé par l'auteur à
18 h 12, proposition 2 : « successions et durée au pouvoir, à partir de ce qu'on a déjà »).

Prolonge Archigos (qui s'arrête en 2015, ecosystemes/dirigeants-ages.csv). Une requête : pour chaque État souverain
(Q3624078), toutes les déclarations « chef d'État » (P35) et « chef de gouvernement » (P6) avec date de début (P580)
depuis 1990, et la date de fin (P582) quand elle existe. Écrit registre/successions/mandats.csv
(iso2, poste, personne, qid, debut, fin) et etat.json. Les agrégats sont faits par l'adaptateur `successions`, après
lecture de la vraie donnée (premier passage du 2026-11-25).
"""
from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

import httpx

import politesse

SPARQL = "https://query.wikidata.org/sparql"
DOSSIER = Path("registre") / "successions"
REQUETE = """SELECT ?iso ?poste ?p ?pLabel ?debut ?fin WHERE {
  ?o wdt:P31 wd:Q3624078; wdt:P297 ?iso.
  VALUES (?prop ?ps ?poste) { (p:P35 ps:P35 "etat") (p:P6 ps:P6 "gouvernement") }
  ?o ?prop ?st. ?st ?ps ?p. ?st pq:P580 ?debut. FILTER(YEAR(?debut) >= 1990)
  OPTIONAL { ?st pq:P582 ?fin }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,fr". } }"""


def lignes_de(json_rep: dict) -> list[dict]:
    out = []
    for b in json_rep["results"]["bindings"]:
        out.append({"iso2": b["iso"]["value"], "poste": b["poste"]["value"], "personne": b.get("pLabel", {}).get("value", ""),
                    "qid": b["p"]["value"].rsplit("/", 1)[-1], "debut": b["debut"]["value"][:10],
                    "fin": b.get("fin", {}).get("value", "")[:10]})
    return sorted({tuple(x.values()): x for x in out}.values(), key=lambda x: (x["iso2"], x["poste"], x["debut"]))


def principal() -> int:
    DOSSIER.mkdir(parents=True, exist_ok=True)
    etat: dict = {"source": "Wikidata (CC0)", "requete": REQUETE}
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=180) as c:
        if not politesse.autorise(c, SPARQL + "?query=x"):
            etat["statut"] = "refuse_robots"
        else:
            for essai in range(3):
                try:
                    r = c.get(SPARQL, params={"query": REQUETE, "format": "json"},
                              headers={"Accept": "application/sparql-results+json"})
                    r.raise_for_status()
                    L = lignes_de(r.json())
                    break
                except Exception as ex:
                    etat["statut"] = f"erreur {type(ex).__name__}: {str(ex)[:150]}"
                    L = None
                    time.sleep(20)
            if L is not None:
                with (DOSSIER / "mandats.csv").open("w", encoding="utf-8", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=["iso2", "poste", "personne", "qid", "debut", "fin"])
                    w.writeheader()
                    w.writerows(L)
                etat.update({"statut": "ok", "lignes": len(L), "pays": len({x["iso2"] for x in L}),
                             "sans_fin": sum(1 for x in L if not x["fin"]),
                             "par_decennie": {d: sum(1 for x in L if x["debut"][:3] == d[:3]) for d in ("1990", "2000", "2010", "2020")},
                             "debut_max": max(x["debut"] for x in L) if L else None})
    (DOSSIER / "etat.json").write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in etat.items() if k != "requete"}, ensure_ascii=False, indent=1))
    return 0 if etat.get("statut") == "ok" else 1


if __name__ == "__main__":
    sys.exit(principal())
