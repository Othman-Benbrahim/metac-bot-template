"""Exploration (décision de l'auteur du 2026-11-22, 1 h 43 - 1 h 45 : « juste pour voir ») : le graphe des types
(ontologie.py) appliqué aux articles vus par GDELT, source orientée connue (registre des émetteurs de lecteur-local :
ancrage états-unien, perspective occidentale établie par l'ONS). AUCUNE décision ne se prend sur ce résultat : il sert à
voir si la mécanique s'allume sur un vrai flux, quels types ressortent ou restent muets, et quels termes font du bruit.

Pour un jour (par défaut, avant-hier, jour complet chez GDELT) : chaque article de la table GKG (titre, source, personnes,
organisations, lieux ; pas de texte) devient une situation au format du collecteur de lecteur-local (mêmes listes
validées, mêmes règles de lecture : compter.situation), puis passe par la même reconnaissance des types
(realiser.compatible). Essai à blanc et plafonds de quota de gdelt_bq.py.

Sortie : registre/situations-gdelt-essai.json (résumé ; aucun titre gardé).

    python mise_au_point/situations_gdelt.py --lecteur <chemin de lecteur-local> [--jour AAAA-MM-JJ]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import gdelt_bq  # noqa: E402

SORTIE = Path("registre/situations-gdelt-essai.json")
PLAFOND_GO = 30.0


def sql() -> str:
    return f"""
SELECT DocumentIdentifier AS url, SourceCommonName AS source,
       REGEXP_EXTRACT(Extras, r'<PAGE_TITLE>(.*?)</PAGE_TITLE>') AS titre,
       SUBSTR(V2Persons, 1, 1500) AS personnes, SUBSTR(V2Organizations, 1, 1500) AS organisations,
       SUBSTR(V2Locations, 1, 1500) AS lieux
FROM `{gdelt_bq.TABLE}`
WHERE _PARTITIONTIME = TIMESTAMP(@jour)
"""


def noms_gkg(champ: str | None, lieux: bool = False) -> list[str]:
    """V2Persons / V2Organizations : « nom,décalage;… » ; V2Locations : « type#nom#pays#… ;… »."""
    out = []
    for morceau in (champ or "").split(";"):
        if lieux:
            p = morceau.split("#")
            if len(p) > 1 and p[1]:
                out.append(p[1])
        else:
            n = morceau.rsplit(",", 1)[0].strip()
            if n:
                out.append(n.title())            # GKG écrit souvent les noms en minuscules
                if len(n) <= 5:
                    out.append(n.upper())        # sigles (imf → IMF)
    return list(dict.fromkeys(out))


def principal(a) -> int:
    lect = Path(a.lecteur).resolve()
    sys.path.insert(0, str(lect))
    import compter
    import realiser
    import yaml
    from ontologie import graphe
    from google.cloud import bigquery
    from google.oauth2 import service_account

    termes = compter.lire_valides(lect / "listes/valides.txt")
    for t in termes:
        t["re"] = compter.motif(t["terme"])
    acteurs = compter.lire_acteurs(lect / "listes/acteurs.txt")
    niveaux = compter.lire_niveaux(lect / "listes/inventaire-fiches.csv")
    emetteurs = compter.lire_emetteurs(lect / "listes/emetteurs.txt")
    g = graphe(yaml.safe_load(Path("ecosystemes/regles-coutumieres.yaml").read_text(encoding="utf-8"))["regles"])
    noms = {n["id"]: n["texte"] for n in g["situations"]}
    regles = [x for x in g["aretes"] if x["compartiments"]]
    continent_de = realiser.continents_des_pays()

    jour = a.jour or (date.today() - timedelta(days=2)).isoformat()
    cred = service_account.Credentials.from_service_account_info(json.loads(os.environ["GCP_SA_KEY"]))
    client = bigquery.Client(project=os.environ["GCP_PROJET"], credentials=cred)
    params = [bigquery.ScalarQueryParameter("jour", "STRING", jour)]
    essai = client.query(sql(), job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False,
                                                                  query_parameters=params))
    go = essai.total_bytes_processed / 1e9
    mois = datetime.now(timezone.utc).strftime("%Y-%m")
    cpt = gdelt_bq.compteur()
    deja = float(cpt.get(mois, 0.0))
    print(f"BigQuery (situations GDELT) : jour {jour}, essai à blanc {go:.2f} Go ; mois {mois} : {deja:.1f} Go", flush=True)
    if go > PLAFOND_GO or deja + go > gdelt_bq.PLAFOND_MOIS_GO:
        raise RuntimeError(f"requête refusée : {go:.1f} Go (plafond {PLAFOND_GO} Go ; mois {deja + go:.0f} Go)")
    lignes = client.query(sql(), job_config=bigquery.QueryJobConfig(query_parameters=params)).result()
    cpt[mois] = round(deja + go, 3)
    gdelt_bq.COMPTEUR.write_text(json.dumps(cpt, ensure_ascii=False, indent=1), encoding="utf-8")

    n_articles = n_sit = 0
    termes_vus, types, sources_type = Counter(), Counter(), {}
    comps, acts, esp, sources = Counter(), Counter(), Counter(), Counter()
    titres_vus = set()
    for r in lignes:
        titre = re.sub(r"\s+", " ", r["titre"] or "").strip()
        if not titre or titre.lower() in titres_vus:          # titres en double retirés (reprises)
            continue
        titres_vus.add(titre.lower())
        n_articles += 1
        texte = " ; ".join([titre] + noms_gkg(r["personnes"]) + noms_gkg(r["organisations"])
                           + noms_gkg(r["lieux"], lieux=True))
        src = (r["source"] or "?").lower()
        s = compter.situation(texte, emetteurs.get(src, {}).get("langue1", ""), termes, [], acteurs, niveaux, src)
        if s is None:
            continue
        n_sit += 1
        sources[src] += 1
        termes_vus.update(s["termes"])
        comps.update(c["compartiment"] for c in s["compartiments"])
        acts.update(x["acteur"] for x in s["acteurs"])
        esp.update(s["espace"])
        for x in regles:
            if realiser.realise(s, x, continent_de):
                k = f'{noms[x["de"]]} [{x["regle"]}]'
                types[k] += 1
                sources_type.setdefault(k, Counter())[src] += 1
    muets = sorted(f'{noms[x["de"]]} [{x["regle"]}]' for x in regles
                   if f'{noms[x["de"]]} [{x["regle"]}]' not in types)
    res = {"jour": jour, "go_lus": round(go, 2), "articles_distincts": n_articles, "situations": n_sit,
           "part_avec_situation": round(n_sit / n_articles, 3) if n_articles else None,
           "types_actifs": [{"type": k, "articles": v, "sources": dict(sources_type[k].most_common(5))}
                            for k, v in types.most_common()],
           "types_muets": muets,
           "termes_les_plus_frequents": termes_vus.most_common(40),
           "compartiments": comps.most_common(30), "acteurs": acts.most_common(30), "espace": esp.most_common(30),
           "sources": sources.most_common(30),
           "avertissement": "exploration sur GDELT (source orientée connue), titres et noms seulement ; aucune décision"}
    SORTIE.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("articles_distincts", "situations", "part_avec_situation")}, ensure_ascii=False))
    for t in res["types_actifs"][:25]:
        print(f'  {t["articles"]:6d}  {t["type"]}')
    print("termes les plus fréquents :", res["termes_les_plus_frequents"][:25])
    print("types muets :", len(muets))
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--lecteur", required=True)
    p.add_argument("--jour")
    sys.exit(principal(p.parse_args()))
