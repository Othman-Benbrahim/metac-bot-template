"""Sonde BigQuery GDELT (bot 0.10.276) : ce que coûteraient nos recherches, mesuré par ESSAI À BLANC (gratuit).

Décision d'auteur du 2026-11-18, 16 h 26 : GDELT par BigQuery (base publique gdelt-bq.gdeltv2), le filtrage se faisant
chez Google pour ne pas charger notre base. L'offre gratuite compte les octets LUS pour filtrer (1 To par mois) ;
un essai à blanc (dry run) annonce ce volume sans rien exécuter ni consommer. Rien n'est lu ici, rien n'est dépensé.
Secrets : GCP_SA_KEY (clé JSON d'un compte de service, rôle « Utilisateur de tâches BigQuery ») ; variable GCP_PROJET.
"""
from __future__ import annotations

import json
import os
import sys

TABLE = "gdelt-bq.gdeltv2.gkg_partitioned"
COLONNES = "DATE, DocumentIdentifier, V2Persons, V2Organizations, V2Themes, V2Tone, Extras"


def requetes() -> dict[str, str]:
    j = "TIMESTAMP('{d}')"
    un_jour = f"_PARTITIONTIME = {j.format(d='2026-03-01')}"
    q90 = f"_PARTITIONTIME BETWEEN {j.format(d='2025-12-01')} AND {j.format(d='2026-03-01')}"
    filtre = "(LOWER(Extras) LIKE '%lula%' AND LOWER(Extras) LIKE '%brazil%')"
    return {
        "1 jour, colonnes utiles, sans filtre": f"SELECT {COLONNES} FROM `{TABLE}` WHERE {un_jour}",
        "1 jour, titre seul (Extras) + adresse": f"SELECT DocumentIdentifier, Extras FROM `{TABLE}` WHERE {un_jour}",
        "90 jours, titre + adresse, filtre mots-clés": f"SELECT DATE, DocumentIdentifier FROM `{TABLE}` WHERE {q90} AND {filtre}",
        "90 jours, personnes + adresse": f"SELECT DATE, DocumentIdentifier FROM `{TABLE}` WHERE {q90} AND V2Persons LIKE '%Lula%'",
    }


def principal() -> int:
    if not os.environ.get("GCP_SA_KEY") or not os.environ.get("GCP_PROJET"):
        print("::error::secret GCP_SA_KEY ou variable GCP_PROJET manquant")
        return 1
    from google.cloud import bigquery
    from google.oauth2 import service_account
    cred = service_account.Credentials.from_service_account_info(json.loads(os.environ["GCP_SA_KEY"]))
    client = bigquery.Client(project=os.environ["GCP_PROJET"], credentials=cred)
    cfg = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
    bilan = {}
    for nom, sql in requetes().items():
        try:
            go = client.query(sql, job_config=cfg).total_bytes_processed / 1e9
            bilan[nom] = round(go, 2)
            print(f"{nom} : {go:.2f} Go lus (soit {1000 / go:.0f} requêtes de ce type par mois gratuit)"
                  if go else f"{nom} : 0 Go", flush=True)
        except Exception as e:
            bilan[nom] = f"{type(e).__name__}: {str(e)[:200]}"
            print(f"{nom} : {bilan[nom]}", flush=True)
    os.makedirs("registre", exist_ok=True)
    with open("registre/sonde-bigquery.json", "w", encoding="utf-8") as f:
        json.dump({"table": TABLE, "essai_a_blanc_go": bilan}, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(principal())
