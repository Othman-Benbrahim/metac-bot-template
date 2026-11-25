"""Entités prioritaires des briefs, mises à jour chaque semaine (2026-11-25 : sources validées par l'auteur à 13 h 20 ;
mise à jour « au moins une fois par semaine »). Écrit registre/entites/entites.csv, lu par brief.priorites() en plus des
entités validées à la main (lecteur-local, listes/entites-prioritaires-proposees.txt).

Sources :
- OpenSanctions, « US CIA World Leaders » (CC BY-NC 4.0 ; usage non commercial) : chefs d'État, de gouvernement et
  membres des gouvernements de 199 pays, mis à jour chaque jour. Seuls des titulaires de fonctions publiques ;
  ni entourage ni famille.
- Wikidata (CC0), requête SPARQL : dirigeants actuels (sans date de fin) des entreprises cotées sur les grandes places,
  des banques centrales et des organisations internationales.

Règle contre les faux positifs : on garde le nom complet ; le nom de famille seul n'est retenu que pour les chefs d'État
et de gouvernement (« Macron », « Modi »), et s'il fait au moins 4 lettres. Une entité ne compte jamais seule, seulement
associée à un mot déclencheur validé (brief.score).
robots.txt vérifié avant chaque requête.
    uv run python collecte_entites.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

import httpx

import politesse

SORTIE = Path("registre") / "entites" / "entites.csv"
CIA = "https://data.opensanctions.org/datasets/latest/us_cia_world_leaders/targets.nested.json"
SPARQL = "https://query.wikidata.org/sparql"
CHEF = re.compile(r"^(president|prime minister|premier|chancellor|king|queen|emir|sultan|supreme leader|head of state|"
                  r"chief executive|taoiseach|grand duke|prince|chairman of the presidium)\b", re.I)
PAS_CHEF = re.compile(r"\b(vice|deputy|first deputy|acting)\b", re.I)
REQUETES = {
    # entreprises cotées (NYSE, NASDAQ, Londres, Tokyo, Euronext Paris, Francfort) : PDG actuel
    "entreprise": """SELECT DISTINCT ?p ?pLabel ?oLabel WHERE {
  VALUES ?ex { wd:Q13677 wd:Q82059 wd:Q171240 wd:Q217475 wd:Q2385849 wd:Q151139 }
  ?o wdt:P414 ?ex; p:P169 ?st. ?st ps:P169 ?p. FILTER NOT EXISTS { ?st pq:P582 ?fin }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,fr". } }""",
    # banques centrales : président ou gouverneur actuel
    "banque centrale": """SELECT DISTINCT ?p ?pLabel ?oLabel WHERE {
  ?o wdt:P31 wd:Q66344. VALUES ?prop { p:P488 p:P1037 } ?o ?prop ?st. ?st (ps:P488|ps:P1037) ?p.
  FILTER NOT EXISTS { ?st pq:P582 ?fin }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,fr". } }""",
    # organisations internationales : dirigeant actuel
    "organisation internationale": """SELECT DISTINCT ?p ?pLabel ?oLabel WHERE {
  ?o wdt:P31 wd:Q484652. VALUES ?prop { p:P488 p:P1037 } ?o ?prop ?st. ?st (ps:P488|ps:P1037) ?p.
  FILTER NOT EXISTS { ?st pq:P582 ?fin }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,fr". } }""",
}


def _postes(x, out: list[str]) -> list[str]:
    """Noms de tous les postes (schéma Position) trouvés dans une entité imbriquée."""
    if isinstance(x, dict):
        if x.get("schema") == "Position":
            out += (x.get("properties") or {}).get("name", [])
        for v in x.values():
            _postes(v, out)
    elif isinstance(x, list):
        for v in x:
            _postes(v, out)
    return out


def personnes_cia(texte: str) -> list[dict]:
    out = []
    for l in texte.splitlines():
        try:
            e = json.loads(l)
        except ValueError:
            continue
        if e.get("schema") != "Person":
            continue
        pr = e.get("properties") or {}
        nom = (pr.get("name") or [""])[0].strip()
        if len(nom) < 5:
            continue
        postes = _postes(pr, [])
        topics = pr.get("topics") or []
        chef = "gov.head" in topics or any(CHEF.search(p) and not PAS_CHEF.search(p) for p in postes)
        out.append({"nom": nom, "sorte": "dirigeant public", "pays": ";".join(pr.get("country") or []),
                    "poste": "; ".join(postes)[:120], "chef": chef, "source": "OpenSanctions/CIA World Leaders"})
    return out


def variantes(nom: str, chef: bool) -> list[str]:
    v = [nom]
    nom_famille = nom.split()[-1] if len(nom.split()) > 1 else ""
    if chef and len(nom_famille) >= 4 and nom_famille.isalpha():
        v.append(nom_famille)
    return v


def principal() -> int:
    lignes, bilan = [], {}
    with httpx.Client(headers={"User-Agent": politesse.UA}, follow_redirects=True, timeout=180) as c:
        if politesse.autorise(c, CIA):
            try:
                r = c.get(CIA)
                r.raise_for_status()
                cia = personnes_cia(r.text)
                lignes += cia
                bilan["cia"] = {"personnes": len(cia), "chefs": sum(x["chef"] for x in cia)}
            except Exception as ex:
                bilan["cia"] = f"erreur {type(ex).__name__}: {str(ex)[:120]}"
        else:
            bilan["cia"] = "refuse_robots"
        for sorte, q in REQUETES.items():
            try:
                r = c.get(SPARQL, params={"query": q, "format": "json"}, headers={"Accept": "application/sparql-results+json"})
                r.raise_for_status()
                res = r.json()["results"]["bindings"]
                n = 0
                for b in res:
                    nom = b.get("pLabel", {}).get("value", "")
                    if len(nom) < 5 or re.fullmatch(r"Q\d+", nom):
                        continue
                    lignes.append({"nom": nom, "sorte": sorte, "pays": "", "poste": b.get("oLabel", {}).get("value", "")[:120],
                                   "chef": False, "source": "Wikidata"})
                    n += 1
                bilan[sorte] = n
            except Exception as ex:
                bilan[sorte] = f"erreur {type(ex).__name__}: {str(ex)[:120]}"
    print(json.dumps(bilan, ensure_ascii=False))
    if not lignes:
        print("aucune entité : fichier précédent conservé")
        return 0
    vus = set()
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with SORTIE.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["variantes", "nom", "sorte", "pays", "poste", "chef", "source"])
        for x in lignes:
            if x["nom"].lower() in vus:
                continue
            vus.add(x["nom"].lower())
            w.writerow(["/".join(variantes(x["nom"], x["chef"])), x["nom"], x["sorte"], x["pays"], x["poste"],
                        int(x["chef"]), x["source"]])
    print(len(vus), "entités ->", SORTIE)
    return 0


if __name__ == "__main__":
    sys.exit(principal())
