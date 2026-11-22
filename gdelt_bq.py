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
    python gdelt_bq.py --mode comptes  # 0.10.281 : mêmes questions, mêmes filtres, NOMBRE d'articles par jour
    python gdelt_bq.py --mode comptes_jeu  # 0.10.290 : comptes pour les questions distinctes de 2026 du jeu de données
    python gdelt_bq.py --mode comptes_metaculus_2025  # 0.10.293 : questions Metaculus distinctes d'avant 2026
    python gdelt_bq.py --mode manifestations  # 0.10.463 : manifestations par pays et par semaine, 2015-2026 (H2)
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
COMPTES = Path("registre/gdelt-bq-comptes.json")
COMPTES_JEU = Path("registre/gdelt-bq-comptes-jeu.json")
COMPTES_META_2025 = Path("registre/gdelt-bq-comptes-metaculus-2025.json")
DYADES = Path("registre/gdelt-dyades.json")          # 0.10.312 : réciprocité entre États (preenregistrements/reciprocite-dyades.md)
TABLE_EVENEMENTS = "gdelt-bq.gdeltv2.events_partitioned"
DYADES_DEBUT, DYADES_FIN, DYADES_N = "2023-01-01", "2026-10-31", 40
# 0.10.463 (décision de l'auteur, 2026-11-22, 19 h 41) : observation de l'état avant pour H2 (signal × terrain).
# Manifestations (CAMEO, code racine 14) par pays du lieu de l'action (codes FIPS 10-4) et par semaine, avec le total
# des événements du même pays et de la même semaine (dénominateur : volume de couverture). Observation 2015-2021,
# test 2022-2026 réservé (claude/preenregistrement-reserve-h2-terrain dans le projet).
MANIFS = Path("registre/gdelt-manifestations-semaines.csv")
MANIFS_DEBUT, MANIFS_FIN = "2015-02-19", "2026-11-21"
# 0.10.464 : mode court pour la mécanique en temps réel (mecanique.py) : les 62 dernières semaines, même requête.
MANIFS_RECENTES = Path("registre/gdelt-manifestations-recentes.csv")
MANIFS_COURT_SEMAINES = 62
PLAFOND_REQUETE_GO = {"nuit": 25.0, "court": 5.0, "bancs": 120.0, "comptes": 120.0, "comptes_jeu": 120.0,
                     "comptes_metaculus_2025": 120.0, "dyades": 120.0, "manifestations": 150.0,
                     "manifestations_court": 10.0}
PLAFOND_MOIS_GO = 800.0
PAR_QUESTION = 15


def mots(titre: str) -> list[str]:
    import alphabet_recherche as ar_
    return [m.strip('"').lower() for m in ar_.gdelt_mots(titre).split() if len(m.strip('"')) > 2]


TITRES_COMMUNS = {"president", "prime", "minister", "chair", "fed", "ceo", "governor", "senator", "king", "queen",
                  "chancellor", "secretary", "general", "party", "election", "court", "supreme", "house", "senate",
                  "january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
                  "november", "december", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}


def requis_et_options(titre: str) -> tuple[list[str], list[str]]:
    """0.10.279 (premier passage des bancs : trop de bruit avec « 2 mots sur 4 ») : les NOMS PROPRES de la question
    sont tous exigés dans le titre de l'article ; les autres mots-clés sont des options dont une au moins est exigée."""
    tous = mots(titre)
    propres = {w.lower() for i, w in enumerate(re.findall(r"[\w-]+", titre)) if i > 0 and w[:1].isupper()}
    requis = [w for w in tous if w in propres and w not in TITRES_COMMUNS][:2]   # 2 noms au plus, les plus distinctifs
    return requis, [w for w in tous if w not in requis]


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
         (SELECT COUNTIF(STRPOS(LOWER(g.titre), w) > 0) FROM UNNEST(q.requis) w) AS r_trouves,
         ARRAY_LENGTH(q.requis) AS n_requis,
         (SELECT COUNTIF(STRPOS(LOWER(g.titre), w) > 0) FROM UNNEST(q.options) w) AS o_trouves,
         ARRAY_LENGTH(q.options) AS n_options
  FROM g JOIN q ON g.jour BETWEEN TIMESTAMP(q.debut) AND TIMESTAMP(q.fin)
  WHERE g.titre IS NOT NULL
)
SELECT qid, vu, url, titre, r_trouves + o_trouves AS trouves FROM m
WHERE r_trouves = n_requis
  AND (CASE WHEN n_requis = 0 THEN o_trouves >= LEAST(2, n_options)
            ELSE (n_options = 0 OR o_trouves >= 1) END)
QUALIFY ROW_NUMBER() OVER (PARTITION BY qid, LOWER(titre) ORDER BY vu) = 1
   AND ROW_NUMBER() OVER (PARTITION BY qid ORDER BY r_trouves + o_trouves DESC, vu DESC) <= {PAR_QUESTION}
"""


def sql_comptes() -> str:
    """0.10.281 (préenregistrements tendance-attention, sursauts-attention) : même filtre que sql(), titres en double
    retirés, puis NOMBRE d'articles par question et par jour. Même coût (mêmes colonnes, mêmes jours lus)."""
    base = sql(0).split("SELECT qid, vu, url, titre, r_trouves + o_trouves AS trouves FROM m")[0]
    return base + """, f AS (
  SELECT qid, vu, titre FROM m
  WHERE r_trouves = n_requis
    AND (CASE WHEN n_requis = 0 THEN o_trouves >= LEAST(2, n_options)
              ELSE (n_options = 0 OR o_trouves >= 1) END)
  QUALIFY ROW_NUMBER() OVER (PARTITION BY qid, LOWER(titre) ORDER BY vu) = 1
)
SELECT qid, SUBSTR(CAST(vu AS STRING), 1, 8) AS jour, COUNT(*) AS n FROM f GROUP BY qid, jour
"""


def compteur() -> dict:
    return json.loads(COMPTEUR.read_text(encoding="utf-8")) if COMPTEUR.exists() else {}


def lancer(questions: list[dict], mode: str, client=None, agreger: bool = False) -> dict:
    """questions : [{qid, titre, debut (AAAA-MM-JJ), fin}] → {qid: [{vu, url, titre}]}. Essai à blanc d'abord."""
    qs = []
    for q in questions:
        r, o = requis_et_options(q["titre"])
        if r or o:
            qs.append(dict(q, requis=r, options=o))
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
        bigquery.ArrayQueryParameter("requis", "STRING", q["requis"]),
        bigquery.ArrayQueryParameter("options", "STRING", q["options"]),
        bigquery.ScalarQueryParameter("debut", "STRING", q["debut"]),
        bigquery.ScalarQueryParameter("fin", "STRING", q["fin"])) for q in qs]),
        bigquery.ScalarQueryParameter("d0", "STRING", d0), bigquery.ScalarQueryParameter("d1", "STRING", d1)]
    texte = sql_comptes() if agreger else sql(len(qs))
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
    if agreger:                                      # {qid: {AAAA-MM-JJ: n}}
        cpts: dict[str, dict[str, int]] = {}
        for r in lignes:
            j = str(r["jour"])
            cpts.setdefault(r["qid"], {})[f"{j[:4]}-{j[4:6]}-{j[6:8]}"] = int(r["n"])
        return cpts
    out: dict[str, list[dict]] = {}
    for r in lignes:
        vu = str(r["vu"])
        import html
        out.setdefault(r["qid"], []).append({"vu": f"{vu[:4]}-{vu[4:6]}-{vu[6:8]}", "url": r["url"],
                                             "titre": re.sub(r"\s+", " ", html.unescape(r["titre"] or ""))[:200]})
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


def questions_bancs() -> list[dict]:
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
    return qs


def mode_comptes() -> int:
    """0.10.281 : nombre d'articles par jour sur les 90 jours avant le jeu (questions distinctes des bancs)."""
    qs = questions_bancs()
    res = lancer(qs, "comptes", agreger=True)
    COMPTES.write_text(json.dumps({q["qid"]: {"debut": q["debut"], "fin": q["fin"], "jours": res.get(q["qid"], {}),
                                              "filtrable": bool(sum(requis_et_options(q["titre"]), []))}
                                   for q in qs}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(qs)} question(s) distincte(s) ; {sum(1 for q in qs if res.get(q['qid']))} avec au moins un article.")
    return 0


def mode_comptes_jeu(avant_2026: bool = False, source: str | None = None, sortie: Path = COMPTES_JEU,
                     mode: str = "comptes_jeu") -> int:
    """0.10.290 (préenregistrement tendance-attention-large.md) : comptes quotidiens, 90 jours avant la PREMIÈRE date
    de jeu, pour chaque question distincte de 2026 du jeu de données (toutes plateformes). 0.10.293 : variante
    « questions Metaculus d'avant 2026 » (préenregistrement tendance-metaculus.md)."""
    import banc_jugement as bj
    xs = bj.cohorte_complete([json.loads(l) for l in bj.REGISTRE.read_text(encoding="utf-8").splitlines() if l.strip()])
    vus, qs = set(), []
    for x in sorted(xs, key=lambda x: x["jeu"]):
        k = f'{x["source"]}:{x["id"]}'
        if k in vus:
            continue
        vus.add(k)
        if (x["jeu"] >= "2026-01-01") == avant_2026 or (source and x["source"] != source):
            continue
        jeu = date.fromisoformat(x["jeu"][:10])
        qs.append({"qid": f'{k}:{x["jeu"]}', "titre": x["titre"],
                   "debut": (jeu - timedelta(days=90)).isoformat(), "fin": (jeu - timedelta(days=1)).isoformat()})
    res = lancer(qs, mode, agreger=True)
    sortie.write_text(json.dumps({q["qid"]: {"debut": q["debut"], "fin": q["fin"], "jours": res.get(q["qid"], {}),
                                                  "filtrable": bool(sum(requis_et_options(q["titre"]), []))}
                                       for q in qs}, ensure_ascii=False), encoding="utf-8")
    print(f"{len(qs)} question(s) distincte(s) ; {sum(1 for q in qs if res.get(q['qid']))} avec au moins un article.")
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


def sql_dyades() -> str:
    """Paires de gouvernements et d'armées de deux pays différents, par semaine et par sens ; les DYADES_N paires les
    plus actives. Partition filtrée sur la période (coût borné par l'essai à blanc)."""
    return f"""
WITH e AS (
  SELECT Actor1CountryCode AS a, Actor2CountryCode AS b, GoldsteinScale AS g, QuadClass AS c,
         DATE_TRUNC(PARSE_DATE('%Y%m%d', CAST(SQLDATE AS STRING)), WEEK(MONDAY)) AS semaine
  FROM `{TABLE_EVENEMENTS}`
  WHERE _PARTITIONTIME BETWEEN TIMESTAMP(@d0) AND TIMESTAMP(@d1)
    AND SQLDATE BETWEEN CAST(REPLACE(@d0, '-', '') AS INT64) AND CAST(REPLACE(@d1, '-', '') AS INT64)
    AND Actor1Type1Code IN ('GOV', 'MIL') AND Actor2Type1Code IN ('GOV', 'MIL')
    AND Actor1CountryCode IS NOT NULL AND Actor2CountryCode IS NOT NULL
    AND Actor1CountryCode != Actor2CountryCode),
paires AS (
  SELECT LEAST(a, b) AS p1, GREATEST(a, b) AS p2, COUNT(*) AS n FROM e GROUP BY p1, p2
  ORDER BY n DESC LIMIT {DYADES_N})
SELECT e.a, e.b, CAST(e.semaine AS STRING) AS semaine, COUNT(*) AS n, SUM(e.g) AS somme_g,
       COUNTIF(e.c = 1) AS coop_verbale, COUNTIF(e.c = 2) AS coop_materielle,
       COUNTIF(e.c = 3) AS conflit_verbal, COUNTIF(e.c = 4) AS conflit_materiel
FROM e JOIN paires ON LEAST(e.a, e.b) = paires.p1 AND GREATEST(e.a, e.b) = paires.p2
GROUP BY e.a, e.b, semaine"""


def mode_dyades(client=None) -> int:
    from google.cloud import bigquery
    if client is None:
        from google.oauth2 import service_account
        cred = service_account.Credentials.from_service_account_info(json.loads(os.environ["GCP_SA_KEY"]))
        client = bigquery.Client(project=os.environ["GCP_PROJET"], credentials=cred)
    params = [bigquery.ScalarQueryParameter("d0", "STRING", DYADES_DEBUT),
              bigquery.ScalarQueryParameter("d1", "STRING", DYADES_FIN)]
    texte = sql_dyades()
    essai = client.query(texte, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False,
                                                                  query_parameters=params))
    go = essai.total_bytes_processed / 1e9
    mois = datetime.now(timezone.utc).strftime("%Y-%m")
    cpt = compteur()
    deja = float(cpt.get(mois, 0.0))
    print(f"BigQuery (dyades) : {DYADES_DEBUT} → {DYADES_FIN}, essai à blanc {go:.2f} Go ; mois {mois} : {deja:.1f} Go", flush=True)
    if go > PLAFOND_REQUETE_GO["dyades"]:
        raise RuntimeError(f"requête refusée : {go:.1f} Go > plafond {PLAFOND_REQUETE_GO['dyades']} Go (dyades)")
    if deja + go > PLAFOND_MOIS_GO:
        raise RuntimeError(f"requête refusée : le mois atteindrait {deja + go:.0f} Go (> {PLAFOND_MOIS_GO:.0f} Go)")
    lignes = list(client.query(texte, job_config=bigquery.QueryJobConfig(query_parameters=params)).result())
    cpt[mois] = round(deja + go, 3)
    COMPTEUR.write_text(json.dumps(cpt, ensure_ascii=False, indent=1), encoding="utf-8")
    out: dict[str, dict] = {}
    for r in lignes:
        out.setdefault(f'{r["a"]}>{r["b"]}', {})[r["semaine"]] = {
            "n": int(r["n"]), "somme_g": round(float(r["somme_g"] or 0), 2), "coop_verbale": int(r["coop_verbale"]),
            "coop_materielle": int(r["coop_materielle"]), "conflit_verbal": int(r["conflit_verbal"]),
            "conflit_materiel": int(r["conflit_materiel"])}
    DYADES.write_text(json.dumps({"debut": DYADES_DEBUT, "fin": DYADES_FIN, "sens": out}, ensure_ascii=False), encoding="utf-8")
    print(f"{len(out)} sens de paires ; {sum(len(v) for v in out.values())} semaines-sens.")
    return 0


def sql_manifestations() -> str:
    """Par pays (lieu de l'action) et par semaine : tous les événements, manifestations (racine 14), manifestations
    « racines » (IsRootEvent = 1, l'événement principal de l'article) et articles qui citent une manifestation.
    Aucun texte, aucun acteur : des comptes."""
    return f"""
SELECT ActionGeo_CountryCode AS pays,
       CAST(DATE_TRUNC(PARSE_DATE('%Y%m%d', CAST(SQLDATE AS STRING)), WEEK(MONDAY)) AS STRING) AS semaine,
       COUNT(*) AS evenements,
       COUNTIF(EventRootCode = '14') AS manifs,
       COUNTIF(EventRootCode = '14' AND IsRootEvent = 1) AS manifs_racine,
       SUM(IF(EventRootCode = '14', NumArticles, 0)) AS articles_manifs
FROM `{TABLE_EVENEMENTS}`
WHERE _PARTITIONTIME BETWEEN TIMESTAMP(@d0) AND TIMESTAMP(@d1)
  AND SQLDATE BETWEEN CAST(REPLACE(@d0, '-', '') AS INT64) AND CAST(REPLACE(@d1, '-', '') AS INT64)
  AND ActionGeo_CountryCode IS NOT NULL AND ActionGeo_CountryCode != ''
GROUP BY pays, semaine"""


def mode_manifestations(client=None, court: bool = False) -> int:
    from google.cloud import bigquery
    if client is None:
        from google.oauth2 import service_account
        cred = service_account.Credentials.from_service_account_info(json.loads(os.environ["GCP_SA_KEY"]))
        client = bigquery.Client(project=os.environ["GCP_PROJET"], credentials=cred)
    mode = "manifestations_court" if court else "manifestations"
    if court:
        hier = datetime.now(timezone.utc).date() - timedelta(days=1)
        d0, d1 = (hier - timedelta(weeks=MANIFS_COURT_SEMAINES)).isoformat(), hier.isoformat()
    else:
        d0, d1 = MANIFS_DEBUT, MANIFS_FIN
    params = [bigquery.ScalarQueryParameter("d0", "STRING", d0),
              bigquery.ScalarQueryParameter("d1", "STRING", d1)]
    texte = sql_manifestations()
    essai = client.query(texte, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False,
                                                                  query_parameters=params))
    go = essai.total_bytes_processed / 1e9
    mois = datetime.now(timezone.utc).strftime("%Y-%m")
    cpt = compteur()
    deja = float(cpt.get(mois, 0.0))
    print(f"BigQuery ({mode}) : {d0} → {d1}, essai à blanc {go:.2f} Go ; mois {mois} : {deja:.1f} Go", flush=True)
    if go > PLAFOND_REQUETE_GO[mode]:
        raise RuntimeError(f"requête refusée : {go:.1f} Go > plafond {PLAFOND_REQUETE_GO[mode]} Go ({mode})")
    if deja + go > PLAFOND_MOIS_GO:
        raise RuntimeError(f"requête refusée : le mois atteindrait {deja + go:.0f} Go (> {PLAFOND_MOIS_GO:.0f} Go)")
    lignes = list(client.query(texte, job_config=bigquery.QueryJobConfig(query_parameters=params)).result())
    cpt[mois] = round(deja + go, 3)
    COMPTEUR.write_text(json.dumps(cpt, ensure_ascii=False, indent=1), encoding="utf-8")
    ecrire_manifestations([dict(r) for r in lignes], MANIFS_RECENTES if court else MANIFS)
    return 0


def ecrire_manifestations(lignes: list[dict], sortie: Path = MANIFS) -> int:
    import csv
    cols = ["pays", "semaine", "evenements", "manifs", "manifs_racine", "articles_manifs"]
    lignes = sorted(lignes, key=lambda r: (r["pays"], r["semaine"]))
    sortie.parent.mkdir(exist_ok=True)
    with sortie.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in lignes:
            w.writerow([r[c] if r[c] is not None else 0 for c in cols])
    print(f"{len(lignes)} lignes pays-semaine ; {len({r['pays'] for r in lignes})} pays → {sortie}")
    return len(lignes)


def principal(mode: str) -> int:
    if not os.environ.get("GCP_SA_KEY") or not os.environ.get("GCP_PROJET"):
        print("::warning::GCP_SA_KEY ou GCP_PROJET absent : GDELT par BigQuery sauté.")
        return 0
    try:
        return (mode_manifestations() if mode == "manifestations" else mode_manifestations(court=True) if mode == "manifestations_court" else mode_dyades() if mode == "dyades" else mode_bancs() if mode == "bancs" else mode_comptes() if mode == "comptes"
                else mode_comptes_jeu() if mode == "comptes_jeu"
                else mode_comptes_jeu(True, "metaculus", COMPTES_META_2025, mode) if mode == "comptes_metaculus_2025"
                else mode_tournoi(mode))
    except RuntimeError as e:
        print(f"::warning::{e}")
        return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--mode", choices=["nuit", "court", "bancs", "comptes", "comptes_jeu",
                                           "comptes_metaculus_2025", "dyades", "manifestations", "manifestations_court"], default="nuit")
    sys.exit(principal(a.parse_args().mode))
