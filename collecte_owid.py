"""Collecte Our World in Data (graphiques choisis) → registre/owid/<slug>.csv.gz et registre/owid/etat.json.

2026-11-25 : source validée par l'auteur à 10 h 57 (CC BY 4.0 ; une donnée non redistribuable répond 403 et n'est pas
forcée). Chaque graphique se télécharge par son adresse + « .csv » (API des graphiques d'OWID). robots.txt vérifié avant
toute requête. Les noms de graphiques viennent de pages ourworldindata.org/grapher/<slug> vues le 2026-11-25 ; un
graphique introuvable est noté dans etat.json, et sa trace sur la carte reste vide (aucune donnée inventée).
"""
from __future__ import annotations

import gzip
import json
import sys
import time
from pathlib import Path

import httpx

import politesse

GRAPHIQUES = (
    "military-expenditure-share-gdp",              # militaire:depenses (SIPRI)
    "nuclear-warhead-stockpiles",                  # militaire:arsenaux_nucleaires (FAS)
    "arctic-sea-ice",                              # arctique:glace_arctique (NSIDC)
    "antarctica-sea-ice-extent",                   # antarctique:glace_mer (NSIDC)
    "ti-corruption-perception-index",              # corruption:perception (Transparency International)
    "share-of-the-population-with-access-to-electricity",   # afrique-subsaharienne:acces_electricite (Banque mondiale)
    "global-plastics-production",                  # oceans-et-fleuves:plastiques (Geyer et al. ; OCDE)
    "capture-and-aquaculture-production",          # oceans-et-fleuves:peche (FAO)
    "proportion-using-safely-managed-drinking-water",       # eau-douce-potable:acces (OMS/UNICEF JMP)
    "share-using-safely-managed-sanitation",       # eau-douce-potable:assainissement (OMS/UNICEF JMP)
    "ozone-depleting-substance-consumption",       # environnement-dechets:ozone (PNUE)
)
URL = "https://ourworldindata.org/grapher/{slug}.csv?useColumnShortNames=true"
DOSSIER = Path("registre") / "owid"


def principal() -> int:
    DOSSIER.mkdir(parents=True, exist_ok=True)
    etat = {}
    with httpx.Client(headers={"User-Agent": politesse.UA}, follow_redirects=True, timeout=120) as c:
        for slug in GRAPHIQUES:
            url = URL.format(slug=slug)
            if not politesse.autorise(c, url):
                etat[slug] = {"statut": "refuse_robots"}
                continue
            try:
                r = c.get(url)
            except httpx.HTTPError as e:
                etat[slug] = {"statut": f"erreur {type(e).__name__}"}
                continue
            texte = r.text.lstrip("\ufeff")
            if r.status_code != 200 or not texte.lower().lstrip('"').startswith("entity"):
                etat[slug] = {"statut": f"http {r.status_code}", "debut": texte[:120]}   # 403 : donnée non redistribuable
                continue
            lignes = texte.splitlines()
            with gzip.open(DOSSIER / f"{slug}.csv.gz", "wt", encoding="utf-8") as f:
                f.write(texte)
            entites = sorted({l.split(",")[0] for l in lignes[1:]})
            etat[slug] = {"statut": "ok", "colonnes": lignes[0].split(","), "lignes": len(lignes) - 1,
                          "entites_hors_pays": [e for e in entites if not any(l.startswith(e + ",") and len(l.split(",")[1]) == 3
                                                                             for l in lignes[1:200])][:80]}
            time.sleep(1)
    (DOSSIER / "etat.json").write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(etat, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
