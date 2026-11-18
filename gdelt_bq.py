"""GDELT par BigQuery : une requête GROUPÉE pour toutes les questions, filtrée chez Google (bot 0.10.277).

Décisions d'auteur du 2026-11-18 : 16 h 26 (BigQuery, filtrage chez Google pour ne pas charger notre base) ; 16 h 54
(« je valide » : requête longue de nuit + mise à jour courte avant chaque passage du bot ; les résultats remplacent
l'API GDELT, qui nous refuse ; banc du complément ensuite).
Sonde du 2026-11-18 (run 44340182121, essai à blanc) : 1 jour titres + adresses = 0,11 Go lus ; 90 jours avec filtre
de titres = 15,1 Go. BigQuery facture les COLONNES × JOURS lus, pas le nombre de filtres : une requête pour toutes
les questions coûte comme une requête pour une seule, à période égale.

Pour chaque question : quelques mots-clés (alphabet_recherche.gdelt_mots) et une fenêtre de dates. BigQuery garde,
parmi les articles VUS par GDELT dans la fenêtre, ceux dont le TITRE contient au moins 2 des mots (ou le seul mot),
classés par nombre de mots trouvés puis par date ; 15 au plus par question. Rien d'autre ne revient : date de
passage chez GDELT, adresse, titre. Dates sûres par construction (date où GDELT a vu l'article).

Garde-fous du quota (offre gratuite : 1 To lu par mois) : essai à blanc avant chaque requête ; refus au-delà du
plafond par requête ; compteur mensuel (registre/bigquery-compteur.json) qui bloque à 800 Go.
Secrets : GCP_SA_KEY (compte de service, rôle Utilisateur de tâches BigQuery) ; variable GCP_PROJET.

    python gdelt_bq.py --mode nuit     # questions ouvertes du tournoi, 30 jours
    python gdelt_bq.py --mode court    # mêmes questions, 48 dernières heures, fusionnées
    python gdelt_bq.py --mode bancs    # questions distinctes des bancs de jugement, 90 jours avant la date du jeu
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

TABLE = "gdelt-bq.gdeltv2.gkg_partitioned"
COMPTEUR = Path("registre/bigquery-compteur.json")
TOURNOI = Path("registre/gdelt-bq-tournoi.json")
BANCS = Path("registre/gdelt-bq-bancs.json")
PLAFOND_REQUETE_GO = {"nuit": 25.0, "court": 5.0, "bancs": 120.0}
PLAFOND_MOIS_GO = 800.0
PAR_QUESTION = 15


def mots(titre: str) -> list[str]:
    import alphabet_recherche as ar_
    return [m.strip('"').lower() for m in ar_.gdelt_mots(titre).split() if len(m.strip('"')) > 2]


def cle(qid: str) -> str:
    return hashlib.sha1(str(qid).encode()).hexdigest()[:16]


def sql(n_questions: int) -> str:
    """Une requête paramétrée : @qs = tableau de (qid, mots, debut, fin) ; @d0, @d1 = bornes de partition (élagage)."""
    return f"""
WITH q AS (SELECT * FROM UNNEST(@qs)),
g AS (
  SELECT DATE AS vu, DocumentIdentifier AS url,
         REGEXP_EXTRACT(Extras, r'<PAGE_TITLE>(.*?)</PAGE_TITLE>') AS titre,
         _PARTITIONTIME AS jour
  FROM `{TABLE}`
  WHERE _PARTITIONTIME BETWEEN TIMESTAMP(@d0) AND TIMESTAMP(@d1)
),
m AS (
  SELECT q.qid, g.vu, g.url, g.titre,
         (SELECT COUNTIF(STRPOS(LOWER(g.titre), w) > 0) FROM UNNEST(q.mots) w) AS trouves,
         ARRAY_LENGTH(q.mots) AS n_mots
  FROM g JOIN q ON g.jour BETWEEN TIMESTAMP(q.debut) AND TIMESTAMP(q.fin)
  WHERE g.titre IS NOT NULL
)
SELECT qid, vu, url, titre, trouves FROM m
WHERE trouves >= LEAST(2, n_mots)
QUALIFY ROW_NUMBER() OVER (PARTITION BY qid, url ORDER BY vu) = 1
   AND ROW_NUMBER() OVER (PARTITION BY qid ORDER BY trouves DESC, vu DESC) <= {PAR_QUESTION}
"""


def compteur() -> dict:
    return json.loads(COMPTEUR.read_text(encoding="utf-8")) if COMPTEUR.exists() else {}


def lancer(questions: list[dict], mode: str, client=None) -> dict[str, list[dict]]:
    """questions : [{qid, titre, debut (AAAA-MM-JJ), fin}] → {qid: [{vu, url, titre}]}. Essai à blanc d'abord."""
    qs = [dict(q, mots=mots(q["titre"])) for q in questions]
    qs = [q for q in qs if q["mots"]]
    if not qs:
        return {}
    from google.cloud import bigquery
    if client is None:
        from google.oauth2 import service_account
        cred = service_account.Credentials.from_service_account_info(json.loads(os.environ["GCP_SA_KEY"]))
        client = bigquery.Client(project=os.environ["GCP_PROJET"], credentials=cred)
    d0, d1 = min(q["debut"] for q in qs), max(q["fin"] for q in qs)
    params = [bigquery.ArrayQueryParameter("qs", "STRUCT", [bigquery.StructQueryParameter(
        None, bigquery.ScalarQueryParameter("qid", "STRING", str(q["qid"])),
        bigquery.ArrayQueryParameter("mots", "STRING", q["mots"]),
        bigquery.ScalarQueryParameter("debut", "STRING", q["debut"]),
        bigquery.ScalarQueryParameter("fin", "STRING", q["fin"])) for q in qs]),
        bigquery.ScalarQueryParameter("d0", "STRING", d0), bigquery.ScalarQueryParameter("d1", "STRING", d1)]
    texte = sql(len(qs))
    essai = client.query(texte, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False,
                                                                  query_parameters=params))
    go = essai.total_bytes_processed / 1e9
    mois = datetime.now(timezone.utc).strftime("%Y-%m")
    cpt = compteur()
    deja = float(cpt.get(mois, 0.0))
    print(f"BigQuery ({mode}) : {len(qs)} question(s), {d0} → {d1}, essai à blanc {go:.2f} Go ; mois {mois} : {deja:.1f} Go",
          flush=True)
    if go > PLAFOND_REQUETE_GO[mode]:
        raise RuntimeError(f"requête refusée : {go:.1f} Go > plafond {PLAFOND_REQUETE_GO[mode]} Go ({mode})")
    if deja + go > PLAFOND_MOIS_GO:
        raise RuntimeError(f"requête refusée : le mois atteindrait {deja + go:.0f} Go (> {PLAFOND_MOIS_GO:.0f} Go)")
    lignes = list(client.query(texte, job_config=bigquery.QueryJobConfig(query_parameters=params)).result())
    cpt[mois] = round(deja + go, 3)
    COMPTEUR.parent.mkdir(exist_ok=True)
    COMPTEUR.write_text(json.dumps(cpt, ensure_ascii=False, indent=1), encoding="utf-8")
    out: dict[str, list[dict]] = {}
    for r in lignes:
        vu = str(r["vu"])
        out.setdefault(r["qid"], []).append({"vu": f"{vu[:4]}-{vu[4:6]}-{vu[6:8]}", "url": r["url"],
                                             "titre": re.sub(r"\s+", " ", r["titre"] or "")[:200]})
    for v in out.values():
        v.sort(key=lambda a: a["vu"], reverse=True)
    return out


def texte_recherche(articles: list[dict]) -> str:
    """Au format des autres moteurs (« [date] titre — adresse »), pour la chaîne de recherche et la trace."""
    if not articles:
        return ""
    return "[moteur : gdelt-bq]\n" + "\n\n".join(f"[{a['vu']}] {a['titre']} — {a['url']}" for a in articles)


def resultats_tournoi() -> dict:
    return json.loads(TOURNOI.read_text(encoding="utf-8")) if TOURNOI.exists() else {}


def pour_question(qid) -> str:
    """Ce que le bot lit pour une question ouverte (vide si rien)."""
    return texte_recherche(resultats_tournoi().get(cle(str(qid)), {}).get("articles", []))


def questions_tournoi() -> list[tuple[str, str]]:
    from forecasting_tools import MetaculusClient
    client = MetaculusClient()
    vus, out = set(), []
    for cible in (client.CURRENT_AI_COMPETITION_ID, client.CURRENT_MINIBENCH_ID):
        try:
            ouvertes = client.get_all_open_questions_from_tournament(cible)
            print(f"Tournoi {cible} : {len(ouvertes)} question(s) ouverte(s).", flush=True)
            for q in ouvertes:
                qid = str(getattr(q, "id_of_question", None) or getattr(q, "id_of_post", None) or q.page_url)
                if qid not in vus:
                    vus.add(qid)
                    out.append((qid, q.question_text or ""))
        except Exception as e:
            print(f"::warning::liste du tournoi {cible} indisponible ({type(e).__name__})")
    return out


def mode_tournoi(mode: str) -> int:
    auj = datetime.now(timezone.utc).date()
    debut = auj - timedelta(days=30 if mode == "nuit" else 2)
    qs = [{"qid": cle(qid), "titre": t, "debut": debut.isoformat(), "fin": auj.isoformat()} for qid, t in questions_tournoi()]
    res = lancer(qs, mode)
    base = resultats_tournoi() if mode == "court" else {}
    actives = {q["qid"] for q in qs}
    base = {k: v for k, v in base.items() if k in actives}            # questions fermées : retirées
    for q in qs:
        anciens = base.get(q["qid"], {}).get("articles", []) if mode == "court" else []
        urls, fusion = set(), []
        for a in res.get(q["qid"], []) + anciens:
            if a["url"] not in urls:
                urls.add(a["url"])
                fusion.append(a)
        base[q["qid"]] = {"titre": q["titre"][:200], "maj": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
                          "articles": sorted(fusion, key=lambda a: a["vu"], reverse=True)[:PAR_QUESTION]}
    TOURNOI.parent.mkdir(exist_ok=True)
    TOURNOI.write_text(json.dumps(base, ensure_ascii=False, indent=1), encoding="utf-8")
    n = sum(1 for v in base.values() if v["articles"])
    print(f"{len(qs)} question(s) ouverte(s) ; {n} avec au moins un article GDELT.")
    return 0


def mode_bancs() -> int:
    import banc_jugement_alphabet as bja
    vus, qs = set(), []
    for x in sorted(bja.candidates(), key=lambda x: x["jeu"]):
        k = f'{x["source"]}:{x["id"]}'
        if k in vus:
            continue
        vus.add(k)
        jeu = date.fromisoformat(x["jeu"][:10])
        qs.append({"qid": f'{x["source"]}:{x["id"]}:{x["jeu"]}', "titre": x["titre"],
                   "debut": (jeu - timedelta(days=90)).isoformat(), "fin": (jeu - timedelta(days=1)).isoformat()})
    res = lancer(qs, "bancs")
    BANCS.write_text(json.dumps({q["qid"]: res.get(q["qid"], []) for q in qs}, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    print(f"{len(qs)} question(s) distincte(s) ; {sum(1 for q in qs if res.get(q['qid']))} avec au moins un article.")
    return 0


def principal(mode: str) -> int:
    if not os.environ.get("GCP_SA_KEY") or not os.environ.get("GCP_PROJET"):
        print("::warning::GCP_SA_KEY ou GCP_PROJET absent : GDELT par BigQuery sauté.")
        return 0
    try:
        return mode_bancs() if mode == "bancs" else mode_tournoi(mode)
    except RuntimeError as e:
        print(f"::warning::{e}")
        return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--mode", choices=["nuit", "court", "bancs"], default="nuit")
    sys.exit(principal(a.parse_args().mode))
