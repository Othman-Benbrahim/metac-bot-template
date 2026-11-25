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
# 2026-11-25, 13 h 25 : l'auteur télécharge lui-même le fichier CIA World Leaders d'OpenSanctions une fois par mois et le
# dépose ici (le robots.txt d'OpenSanctions refuse les robots, pas un téléchargement manuel) ; il est lu s'il existe.
MANUEL = Path("donnees_manuelles") / "us_cia_world_leaders.targets.nested.json"
CIA = "https://data.opensanctions.org/datasets/latest/us_cia_world_leaders/targets.nested.json"
SPARQL = "https://query.wikidata.org/sparql"
# intitulés de chef ; « President, Bundesbank » (virgule : président d'une institution) n'en est pas un ; « Fed. President »
# (Allemagne) en est un
CHEF = re.compile(r"^((fed\.|federal) )?(president|prime minister|premier|chancellor|king|queen|emir|sultan|supreme leader|"
                  r"head of state|taoiseach|grand duke|chairman of the presidium)\b(?!,)", re.I)
# noms de famille qui sont aussi des mots courants ou des prénoms fréquents : jamais retenus seuls
COURANTS = {"pierre", "store", "muhammad", "mohammed", "mohamed", "ahmed", "ahmad", "hassan", "hussein", "abdullah",
            "abdallah", "hamdan", "james", "john", "grant", "price", "young", "brown", "white", "black", "green", "little",
            "rose", "hope", "king", "prince", "noble", "power", "rich", "wood", "stone", "rock", "field", "house", "bishop",
            "baker", "martin", "michel", "thomas", "francis", "louis", "paul", "peter", "george", "charles", "edward",
            "salman", "faisal", "khalid", "sultan", "said", "saeed", "salem", "ibrahim", "ismail", "yusuf", "joseph",
            "daniel", "david", "samuel", "moses", "simon", "victor", "felix", "marcel", "michal", "store", "costa",
            "santos", "silva", "garcia", "lopez", "martinez", "rodriguez", "gonzalez", "hernandez", "perez", "sanchez"}
PAS_CHEF = re.compile(r"\b(vice|deputy|first deputy|acting)\b", re.I)
# 2026-11-25, 14 h : Wikidata garde « en fonction » des personnes sans date de fin (Joseph Bech, Premier ministre du
# Luxembourg dans les années 1950) ; on écarte les personnes décédées (P570) et les mandats commencés avant 2012.
# 2026-11-25, premier passage : data.opensanctions.org refuse notre agent par robots.txt (« refuse_robots », non forcé).
# Les dirigeants publics viennent donc aussi de Wikidata (source validée) : chefs d'État et de gouvernement actuels des
# États souverains, et ministres en fonction (poste rattaché à un État souverain, sans date de fin).
REQUETES_CHEFS = {
    "chef d'État ou de gouvernement": """SELECT DISTINCT ?p ?pLabel ?oLabel ?iso ?paysLabel WHERE {
  ?o wdt:P31 wd:Q3624078. BIND(?o AS ?pays) OPTIONAL { ?o wdt:P297 ?iso } VALUES ?prop { p:P35 p:P6 } ?o ?prop ?st. ?st (ps:P35|ps:P6) ?p.
  FILTER NOT EXISTS { ?st pq:P582 ?fin } FILTER NOT EXISTS { ?p wdt:P570 ?mort }
  OPTIONAL { ?st pq:P580 ?debut } FILTER(!BOUND(?debut) || YEAR(?debut) >= 2012)
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,fr". } }""",
}
REQUETES = {
    # 2026-11-25, 13 h 56 : la requête unique a dépassé le délai de Wikidata (504) ; une requête par classe de poste,
    # sans les libellés de pays (le code ISO suffit, la carte connaît les noms)
    "ministre": [f"""SELECT DISTINCT ?p ?pLabel ?iso ?posLabel WHERE {{
  ?pos wdt:P279 wd:{classe}. ?p p:P39 ?st. ?st ps:P39 ?pos. FILTER NOT EXISTS {{ ?st pq:P582 ?fin }} FILTER NOT EXISTS {{ ?p wdt:P570 ?mort }}
  ?st pq:P580 ?debut. FILTER(YEAR(?debut) >= 2012)
  ?pos wdt:P1001 ?o. ?o wdt:P31 wd:Q3624078. OPTIONAL {{ ?o wdt:P297 ?iso }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,fr". }} }}""" for classe in ("Q83307", "Q7330070", "Q15966511")],
    # 2026-11-25, 14 h 18 : le gouvernement américain (absent de la CIA, mal rangé dans Wikidata). Premier essai par les
    # « parties » du cabinet (Q639738) : 0 résultat. Second : postes dont la juridiction est les États-Unis (P1001 = Q30)
    # et qui sont, à n'importe quelle profondeur, une sorte de ministre (Q83307) ; mandat depuis 2021, en cours ; on garde le
    # titulaire le plus récent de chaque poste.
    "cabinet américain": """SELECT DISTINCT ?p ?pLabel ?pos ?posLabel ?debut WHERE {
  ?pos wdt:P1001 wd:Q30. { ?pos wdt:P279+ wd:Q83307 } UNION { ?pos wdt:P31/wdt:P279* wd:Q83307 }
  ?p p:P39 ?st. ?st ps:P39 ?pos. FILTER NOT EXISTS { ?st pq:P582 ?fin } FILTER NOT EXISTS { ?p wdt:P570 ?mort }
  ?st pq:P580 ?debut. FILTER(YEAR(?debut) >= 2021)
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,fr". } }""",
    # entreprises cotées (NYSE, NASDAQ, Londres, Tokyo, Euronext Paris, Francfort) : PDG actuel
    "entreprise": """SELECT DISTINCT ?p ?pLabel ?oLabel ?iso ?paysLabel ?secteurLabel ?debut WHERE {
  VALUES ?ex { wd:Q13677 wd:Q82059 wd:Q171240 wd:Q217475 wd:Q2385849 wd:Q151139 }
  ?o wdt:P414 ?ex; p:P169 ?st. OPTIONAL { ?o wdt:P452 ?secteur } OPTIONAL { ?o wdt:P17 ?pays. ?pays wdt:P297 ?iso } ?st ps:P169 ?p. FILTER NOT EXISTS { ?st pq:P582 ?fin } FILTER NOT EXISTS { ?p wdt:P570 ?mort }
  OPTIONAL { ?st pq:P580 ?debut } FILTER(!BOUND(?debut) || YEAR(?debut) >= 2012)
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,fr". } }""",
    # banques centrales : président ou gouverneur actuel
    "banque centrale": """SELECT DISTINCT ?p ?pLabel ?oLabel ?iso ?paysLabel WHERE {
  ?o wdt:P31 wd:Q66344. OPTIONAL { ?o wdt:P17 ?pays. ?pays wdt:P297 ?iso } VALUES ?prop { p:P488 p:P1037 } ?o ?prop ?st. ?st (ps:P488|ps:P1037) ?p.
  FILTER NOT EXISTS { ?st pq:P582 ?fin } FILTER NOT EXISTS { ?p wdt:P570 ?mort }
  OPTIONAL { ?st pq:P580 ?debut } FILTER(!BOUND(?debut) || YEAR(?debut) >= 2012)
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,fr". } }""",
    # organisations internationales : dirigeant actuel
    "organisation internationale": """SELECT DISTINCT ?p ?pLabel ?oLabel ?iso ?paysLabel WHERE {
  ?o wdt:P31 wd:Q484652. OPTIONAL { ?o wdt:P17 ?pays. ?pays wdt:P297 ?iso } VALUES ?prop { p:P488 p:P1037 } ?o ?prop ?st. ?st (ps:P488|ps:P1037) ?p.
  FILTER NOT EXISTS { ?st pq:P582 ?fin } FILTER NOT EXISTS { ?p wdt:P570 ?mort }
  OPTIONAL { ?st pq:P580 ?debut } FILTER(!BOUND(?debut) || YEAR(?debut) >= 2012)
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,fr". } }""",
}


def _postes(x, out: list[tuple[str, list[str]]]) -> list[tuple[str, list[str]]]:
    """(nom du poste, sujets) de tous les postes (schéma Position) trouvés dans une entité imbriquée."""
    if isinstance(x, dict):
        if x.get("schema") == "Position":
            pr = x.get("properties") or {}
            out += [(n, pr.get("topics") or []) for n in pr.get("name", [])]
        for v in x.values():
            _postes(v, out)
    elif isinstance(x, list):
        for v in x:
            _postes(v, out)
    return out


def _forme(nom: str) -> tuple[str, str]:
    """La CIA écrit le nom de famille en capitales (« Narendra MODI », « ANUTHIN Chanwirakun ») : nom lisible et nom de
    famille."""
    mots = nom.split()
    fam = " ".join(m for m in mots if m.isupper() and len(m) > 1)
    lisible = " ".join(m.capitalize() if m.isupper() and len(m) > 1 else m for m in mots)
    return lisible, " ".join(m.capitalize() for m in fam.split())


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
        brut = (pr.get("name") or [""])[0].strip()
        nom, famille = _forme(brut)
        if len(nom) < 5 or len(nom.split()) < 2:          # un nom d'un seul mot (« PHILIPPE ») déclencherait à tort
            continue
        postes = _postes(pr, [])
        # chef d'État ou de gouvernement : intitulé de chef (sans « vice », « deputy »…), et sujet gov.head d'OpenSanctions
        # quand il existe (le sujet seul couvre aussi des vice-premiers ministres : 541 « chefs » au premier essai)
        chef = any(CHEF.search(n) and not PAS_CHEF.search(n) and (not t or "gov.head" in t) for n, t in postes)
        url = (pr.get("sourceUrl") or [""])[0]
        pays_nom = url.rstrip("/").split("/")[-1].replace("-", " ").title() if "foreign-governments" in url else ""
        out.append({"nom": nom, "famille": famille, "sorte": "dirigeant public", "pays_nom": pays_nom, "organisation": "gouvernement",
                    "pays": ";".join(pr.get("citizenship") or pr.get("country") or []).upper(),
                    "poste": "; ".join(n for n, _ in postes)[:120], "chef": chef, "source": "OpenSanctions/CIA World Leaders"})
    return out


def variantes(nom: str, chef: bool, famille: str = "") -> list[str]:
    v = [nom]
    fam = famille or (nom.split()[-1] if len(nom.split()) > 1 else "")
    if chef and len(fam) >= 5 and fam.lower() not in COURANTS and fam.replace(" ", "").replace("-", "").isalpha() and fam != nom:
        v.append(fam)
    return v


def _precedent() -> list[dict]:
    """Lignes du fichier précédent (une source en échec ne vide pas la liste)."""
    if not SORTIE.exists():
        return []
    with SORTIE.open(encoding="utf-8") as h:
        return [{**r, "chef": r.get("chef") == "1", "famille": ""} for r in csv.DictReader(h)]


def principal() -> int:
    lignes, bilan = [], {}
    with httpx.Client(headers={"User-Agent": politesse.UA}, follow_redirects=True, timeout=180) as c:
        if MANUEL.exists():
            import datetime as _dt
            age = (_dt.date.today() - _dt.date.fromtimestamp(MANUEL.stat().st_mtime)).days
            cia = personnes_cia(MANUEL.read_text(encoding="utf-8"))
            lignes += cia
            bilan["cia"] = {"fichier_manuel": str(MANUEL), "personnes": len(cia), "chefs": sum(x["chef"] for x in cia)}
        elif politesse.autorise(c, CIA):
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
        for sorte, q in list(REQUETES_CHEFS.items()) + list(REQUETES.items()):
            chef = sorte in REQUETES_CHEFS
            try:
                res = []
                for qq in (q if isinstance(q, list) else [q]):
                    # Wikidata répond parfois 502/504, ou coupe la réponse (JSON tronqué) : deux nouvelles tentatives
                    for essai in range(3):
                        try:
                            r = c.get(SPARQL, params={"query": qq, "format": "json"}, headers={"Accept": "application/sparql-results+json"})
                            r.raise_for_status()
                            res += r.json()["results"]["bindings"]
                            break
                        except (httpx.HTTPError, ValueError):
                            if essai == 2:
                                raise
                            import time
                            time.sleep(30)
                n = 0
                # 2026-11-25, 13 h 52 : un dirigeant public de Wikidata (chef ou ministre) est un « dirigeant public » comme
                # ceux de la CIA, avec l'intitulé de son poste ; une entreprise garde ses secteurs (P452), plusieurs lignes
                # par entreprise réunies ici
                par = {}
                for b in res:
                    nom = b.get("pLabel", {}).get("value", "")
                    if len(nom) < 5 or re.fullmatch(r"Q\d+", nom):
                        continue
                    org = b.get("oLabel", {}).get("value", "")[:120]
                    k = (nom, org)
                    if k not in par:
                        public = sorte in ("ministre", "chef d'État ou de gouvernement", "cabinet américain")
                        poste = b.get("posLabel", {}).get("value", "") or ("chef d'État ou de gouvernement" if chef else org)
                        par[k] = {"nom": nom, "sorte": "dirigeant public" if public else sorte,
                                  "pays": "US" if sorte == "cabinet américain" else b.get("iso", {}).get("value", ""),
                                  "pays_nom": b.get("paysLabel", {}).get("value", ""), "organisation": "gouvernement" if public else org,
                                  "poste": poste[:120], "chef": chef, "source": "Wikidata", "secteurs": [],
                                  "debut": b.get("debut", {}).get("value", "")[:10], "pos": b.get("pos", {}).get("value", "")}
                    sec = b.get("secteurLabel", {}).get("value", "")
                    if sec and not re.fullmatch(r"Q\d+", sec) and sec not in par[k]["secteurs"]:
                        par[k]["secteurs"].append(sec)
                vals = list(par.values())
                if sorte == "entreprise":                     # plusieurs PDG « en fonction » : le plus récent seulement
                    parorg = {}
                    for x in vals:
                        parorg.setdefault(x["organisation"], []).append(x)
                    vals = []
                    for xs in parorg.values():
                        dat = [x for x in xs if x["debut"]]
                        vals += [max(dat, key=lambda x: x["debut"])] if dat else xs[:1]
                if sorte == "cabinet américain":              # titulaire le plus récent de chaque poste
                    parpos = {}
                    for x in vals:
                        if x["debut"] >= parpos.get(x["pos"], {"debut": ""})["debut"]:
                            parpos[x["pos"]] = x
                    vals = list(parpos.values())
                lignes += vals
                n = len(vals)
                bilan[sorte] = n
            except Exception as ex:
                bilan[sorte] = f"erreur {type(ex).__name__}: {str(ex)[:120]} ; lignes précédentes gardées"
                cible = "dirigeant public" if sorte in ("ministre", "chef d'État ou de gouvernement", "cabinet américain") else sorte
                gardees = [r for r in _precedent() if r["sorte"] in (sorte, cible) and r["source"] == "Wikidata"]
                lignes += gardees
    print(json.dumps(bilan, ensure_ascii=False))
    if not lignes:
        print("aucune entité : fichier précédent conservé")
        return 0
    vus = set()
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with SORTIE.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["variantes", "nom", "sorte", "pays", "pays_nom", "organisation", "poste", "chef", "source", "secteurs"])
        import unicodedata
        cle = lambda n: re.sub(r"[^a-z]", "", unicodedata.normalize("NFKD", n.lower()).encode("ascii", "ignore").decode())
        for x in lignes:
            if cle(x["nom"]) in vus:                          # « Lula » avec ou sans accent, une seule fois
                continue
            vus.add(cle(x["nom"]))
            w.writerow(["/".join(variantes(x["nom"], x["chef"], x.get("famille", ""))), x["nom"], x["sorte"], x.get("pays", ""),
                        x.get("pays_nom", ""), x.get("organisation", ""), x["poste"], int(x["chef"]), x["source"],
                        "; ".join(x.get("secteurs") or []) if isinstance(x.get("secteurs"), list) else x.get("secteurs", "")])
    print(len(vus), "entités ->", SORTIE)
    return 0


if __name__ == "__main__":
    sys.exit(principal())
