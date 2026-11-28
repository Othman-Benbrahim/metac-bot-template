"""Veille des trêves pour la table des guerres suivies (décision de l'auteur, 2026-11-28, 01 h 50).

La brique des accords pendant une guerre lit l'état de chaque guerre dans ecosystemes/guerres-suivies.csv, tenue à la
main : son cycle est celui des événements (cessez-le-feu, ruptures), pas du calendrier. Ce module NE MODIFIE PAS la
table : il signale quand elle est peut-être à vérifier.

1. GDELT (BigQuery, quotidien, structuré) : par guerre suivie, le nombre d'événements CAMEO 0871 (« déclarer une
   trêve, un cessez-le-feu ») entre les belligérants, chaque jour des 29 derniers jours (coût borné par un essai à
   blanc et le compteur mensuel de gdelt_bq.py).
2. Le puits (complément) : les titres des 3 derniers jours qui nomment un belligérant et un mot de trêve.
3. Garde-fou du modèle de langue (demande de l'auteur) : le codage automatique de GDELT confond « déclarer » et
   « refuser » une trêve. Pour une guerre en alerte, un modèle lit les titres du puits (titres seulement) et classe
   chacun : trêve déclarée, trêve proposée ou négociée, trêve refusée ou rompue, sans rapport. L'alerte n'est gardée
   « à vérifier » que si au moins un titre rapporte une trêve déclarée ; sinon elle est notée « écartée par le
   garde-fou » (jamais supprimée). Sans modèle disponible : « non filtrée ».

Seuils fixés avant toute donnée (2026-11-28, 02 h) : alerte GDELT si la veille compte au moins 5 événements 0871 entre
les belligérants ET au moins 4 fois la moyenne quotidienne des 28 jours précédents (plancher 0,5) ; alerte du puits si
au moins 3 titres distincts sur les 3 derniers jours. Sorties : registre/treves-alertes.json (dernier passage) et
registre/treves-journal.jsonl (toutes les alertes). Les alertes apparaissent aussi sur la page des briefs (couches.py).

    uv run --with "google-cloud-bigquery==3.27.0" python treves.py
"""
from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ICI = Path(__file__).resolve().parent
SORTIE = ICI / "registre" / "treves-alertes.json"
JOURNAL = ICI / "registre" / "treves-journal.jsonl"

# guerre → (paires de codes pays CAMEO des belligérants, mots des titres qui nomment un belligérant)
GUERRES = {
    "russie_ukraine": ([("RUS", "UKR")], r"russia|russian|ukraine|ukrainian|kyiv|kiev|moscow|kremlin|zelensky|putin"),
    "israel_hamas": ([("ISR", "PSE")], r"israel|israeli|hamas|gaza|palestinian"),
    "yemen_houthis": ([("YEM", "YEM"), ("SAU", "YEM")], r"houthi|houthis|yemen|yemeni|sanaa|ansar allah"),
    "etats_unis_houthis": ([("USA", "YEM")], r"houthi|houthis|yemen"),
    "israel_iran": ([("ISR", "IRN")], r"israel|israeli|iran|iranian|tehran"),
    "etats_unis_iran": ([("USA", "IRN")], r"iran|iranian|tehran"),
}
TREVE = re.compile(r"\b(ceasefire|cease-fire|truce|armistice|cessez-le-feu|tr[eê]ve|halt (to|of) (the )?fighting)\b", re.I)
GDELT_MIN, GDELT_RAPPORT, GDELT_PLANCHER, GDELT_REF = 5, 4.0, 0.5, 28
PUITS_MIN, PUITS_JOURS = 3, 3
PLAFOND_GO = 5.0


def sql() -> str:
    paires = sorted({p for ps, _ in GUERRES.values() for p in ps})
    cond = " OR ".join(f"(LEAST(Actor1CountryCode, Actor2CountryCode) = '{min(a, b)}' AND "
                       f"GREATEST(Actor1CountryCode, Actor2CountryCode) = '{max(a, b)}')" for a, b in paires)
    return f"""
SELECT LEAST(Actor1CountryCode, Actor2CountryCode) AS p1, GREATEST(Actor1CountryCode, Actor2CountryCode) AS p2,
       CAST(PARSE_DATE('%Y%m%d', CAST(SQLDATE AS STRING)) AS STRING) AS jour, COUNT(*) AS n
FROM `gdelt-bq.gdeltv2.events_partitioned`
WHERE _PARTITIONTIME BETWEEN TIMESTAMP(@d0) AND TIMESTAMP(@d1)
  AND SQLDATE BETWEEN CAST(REPLACE(@d0, '-', '') AS INT64) AND CAST(REPLACE(@d1, '-', '') AS INT64)
  AND EventCode = '0871' AND ({cond})
GROUP BY p1, p2, jour"""


def comptes_gdelt(hier: date, client=None) -> dict[tuple[str, str], dict[str, int]]:
    """{(p1, p2): {jour: n}} ; {} sans identifiants GCP. Plafond par requête et compteur mensuel partagés."""
    if client is None:
        if not os.environ.get("GCP_SA_KEY") or not os.environ.get("GCP_PROJET"):
            print("treves : GCP_SA_KEY ou GCP_PROJET absent, GDELT sauté")
            return {}
        from google.cloud import bigquery
        from google.oauth2 import service_account
        cred = service_account.Credentials.from_service_account_info(json.loads(os.environ["GCP_SA_KEY"]))
        client = bigquery.Client(project=os.environ["GCP_PROJET"], credentials=cred)
    from google.cloud import bigquery
    import gdelt_bq as g
    d0, d1 = (hier - timedelta(days=GDELT_REF)).isoformat(), hier.isoformat()
    params = [bigquery.ScalarQueryParameter("d0", "STRING", d0), bigquery.ScalarQueryParameter("d1", "STRING", d1)]
    essai = client.query(sql(), job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False,
                                                                   query_parameters=params))
    go = essai.total_bytes_processed / 1e9
    mois = datetime.now(timezone.utc).strftime("%Y-%m")
    cpt = g.compteur()
    deja = float(cpt.get(mois, 0.0))
    print(f"treves : essai à blanc {go:.2f} Go ; mois {mois} : {deja:.1f} Go")
    if go > PLAFOND_GO or deja + go > g.PLAFOND_MOIS_GO:
        print("treves : requête refusée (plafond)")
        return {}
    out: dict = {}
    for r in client.query(sql(), job_config=bigquery.QueryJobConfig(query_parameters=params)).result():
        out.setdefault((r["p1"], r["p2"]), {})[r["jour"]] = int(r["n"])
    cpt[mois] = round(deja + go, 3)
    g.COMPTEUR.write_text(json.dumps(cpt, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def alertes_gdelt(comptes: dict, hier: date) -> list[dict]:
    out = []
    for guerre, (paires, _) in GUERRES.items():
        par_jour: dict[str, int] = {}
        for a, b in paires:
            for j, n in comptes.get((min(a, b), max(a, b)), {}).items():
                par_jour[j] = par_jour.get(j, 0) + n
        n = par_jour.get(hier.isoformat(), 0)
        ref = [par_jour.get((hier - timedelta(days=k)).isoformat(), 0) for k in range(1, GDELT_REF + 1)]
        moy = max(sum(ref) / len(ref), GDELT_PLANCHER)
        if n >= GDELT_MIN and n >= GDELT_RAPPORT * moy:
            out.append({"guerre": guerre, "source": "gdelt", "jour": hier.isoformat(), "n": n,
                        "moyenne_ref": round(moy, 2)})
    return out


def titres_puits(guerre: str, hier: date) -> list[dict]:
    import puits
    rx = re.compile(r"\b(" + GUERRES[guerre][1] + r")\b", re.I)
    vus, out = set(), []
    for r in puits.charger(hier - timedelta(days=PUITS_JOURS - 1), hier):
        t = r.get("t", "")
        if TREVE.search(t) and rx.search(t) and t.lower() not in vus:
            vus.add(t.lower())
            out.append({"titre": t, "lien": r["u"], "source": r.get("d", ""), "jour": r["j"]})
    return out


def alertes_puits(hier: date) -> list[dict]:
    out = []
    for guerre in GUERRES:
        ts = titres_puits(guerre, hier)
        if len(ts) >= PUITS_MIN:
            out.append({"guerre": guerre, "source": "puits", "jour": hier.isoformat(), "n": len(ts)})
    return out


CLASSES = ("treve_declaree", "treve_proposee_ou_negociee", "treve_refusee_ou_rompue", "sans_rapport")


def consigne(guerre: str, titres: list[dict]) -> str:
    lignes = "\n".join(f"{i}. {t['titre']}" for i, t in enumerate(titres[:20]))
    return (f"Guerre suivie : {guerre}. Voici des titres d'articles (titres seulement). Classe CHAQUE titre dans une "
            f"seule de ces classes : {', '.join(CLASSES)}. « treve_declaree » seulement si le titre rapporte qu'une "
            f"trêve ou un cessez-le-feu a été déclaré, signé ou est entré en vigueur entre les belligérants de cette "
            f"guerre ; une trêve refusée, violée, rompue, seulement demandée ou en discussion n'est PAS déclarée.\n\n"
            f"{lignes}\n\nRéponds par un objet JSON seul : {{\"classes\": [\"...\", ...]}} (une classe par titre, dans "
            f"l'ordre).")


def garde_fou(alerte: dict, titres: list[dict], appel=None) -> dict:
    """Ajoute « statut » : a_verifier, ecartee_par_le_garde_fou ou non_filtree."""
    if not titres:
        return {**alerte, "statut": "non_filtree", "motif": "aucun titre du puits à lire"}
    try:
        import brief
        t, modele = brief.appeler([{"role": "user", "content": consigne(alerte["guerre"], titres)}],
                                  relais=[("essai", None)] if appel else None, appel=appel)
        cl = (brief.extraire_json(t) or {}).get("classes") or []
    except Exception as e:
        return {**alerte, "statut": "non_filtree", "motif": f"modèle indisponible ({type(e).__name__})"}
    cl = [c if c in CLASSES else "sans_rapport" for c in cl][:len(titres[:20])]
    lus = [{**x, "classe": c} for x, c in zip(titres[:20], cl)]
    declaree = [x for x in lus if x["classe"] == "treve_declaree"]
    return {**alerte, "statut": "a_verifier" if declaree else "ecartee_par_le_garde_fou", "modele": modele,
            "titres": lus}


def principal(hier: date | None = None, client=None, appel=None) -> int:
    hier = hier or (datetime.now(timezone.utc).date() - timedelta(days=1))
    try:
        comptes = comptes_gdelt(hier, client)
    except Exception as e:
        print(f"treves : GDELT en échec ({type(e).__name__}: {str(e)[:150]})")
        comptes = {}
    brutes = alertes_gdelt(comptes, hier) + alertes_puits(hier)
    par_guerre: dict[str, dict] = {}
    for a in brutes:                                    # une alerte par guerre, sources réunies
        g = par_guerre.setdefault(a["guerre"], {"guerre": a["guerre"], "jour": a["jour"], "sources": {}})
        g["sources"][a["source"]] = {k: a[k] for k in ("n", "moyenne_ref") if k in a}
    finales = [garde_fou(g, titres_puits(g["guerre"], hier), appel) for g in par_guerre.values()]
    res = {"jour": hier.isoformat(), "gdelt_lu": bool(comptes), "alertes": finales,
           "seuils": {"gdelt": f">= {GDELT_MIN} événements 0871 et >= {GDELT_RAPPORT} x la moyenne des {GDELT_REF} jours",
                      "puits": f">= {PUITS_MIN} titres distincts sur {PUITS_JOURS} jours"}}
    SORTIE.parent.mkdir(exist_ok=True)
    SORTIE.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    with JOURNAL.open("a", encoding="utf-8") as f:
        for a in finales:
            f.write(json.dumps(a, ensure_ascii=False) + "\n")
    print(f"treves {hier} : {len(finales)} alerte(s) ; "
          + ", ".join(f"{a['guerre']} → {a['statut']}" for a in finales))
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
