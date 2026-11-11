"""Banc ForecastBench (bot 0.10.43 ; décision d'auteur du 2026-11-11) : jouer B et C sur des questions ForecastBench
DÉJÀ résolues, à leur date d'information, pour avoir vite assez d'issues (biais de C, λ appris, C contre B).

Source : forecastingresearch/forecastbench-datasets (Forecasting Research Institute ; CC BY-SA 4.0). Toutes les deux
semaines, un jeu de 500 questions (date D) ; le jeu de résolutions du même D les résout à plusieurs horizons, le premier
à D + 7 jours.

Garde-fous contre la fuite (§26), les mêmes que les tests rétrospectifs, plus deux :
  - seules les questions tirées de SÉRIES (fred, dbnomics, yfinance, acled, wikipedia) sont jouées : les questions de
    marchés (Metaculus, Manifold, Polymarket, Kalshi) portent la cote de la foule au gel, interdite avant scellement ;
  - jeux postérieurs à la date de connaissance du modèle (--apres) ; recherche Exa bornée à D (pages datées seulement) ;
  - sonde : si le modèle dit connaître l'issue et a raison, la question est exclue ;
  - la dernière valeur de la série au gel (`freeze_datetime_value`) est donnée : c'est un fait daté, pas une prévision.
Les lignes vont dans registre/retro.jsonl (type « retro », banc « forecastbench ») : le score des tests rétrospectifs
(biais de C, correction, C contre B) les compte avec les autres. Rien n'est posté.

    uv run python banc_forecastbench.py --n 20 [--jeu 2026-10-25] [--sources fred,dbnomics,yfinance,acled,wikipedia]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import sys
from datetime import date, datetime, timedelta, timezone

import httpx

import alphabet_pipeline as ap
import alphabet_retro as ar

DEPOT = "https://raw.githubusercontent.com/forecastingresearch/forecastbench-datasets/main/datasets"
SOURCES_SERIES = ("fred", "dbnomics", "yfinance", "acled", "wikipedia")
MARCHES = ("metaculus", "manifold", "polymarket", "kalshi", "infer")


async def _json(url: str) -> dict:
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as c:
        r = await c.get(url)
        r.raise_for_status()
        return r.json()


def jeux_candidats(aujourdhui: date, apres: date, n_max: int = 12) -> list[str]:
    """Les dates D (tous les 14 jours, ancrées sur 2026-10-25) dont la première résolution (D + 7) est passée."""
    d, out = date(2026, 10, 25), []
    while d + timedelta(days=14) + timedelta(days=7) <= aujourdhui:
        d += timedelta(days=14)
    while d > apres and len(out) < n_max:
        if d + timedelta(days=7) <= aujourdhui:
            out.append(d.isoformat())
        d -= timedelta(days=14)
    return out


def apparier(questions: dict, resolutions: dict, sources=SOURCES_SERIES) -> list[dict]:
    """Une entrée par question de série résolue (0 ou 1), à son PREMIER horizon résolu. Les questions combinées
    (identifiant en liste) et toutes les questions de marché sont écartées."""
    qs = {(q["source"], q["id"]): q for q in questions.get("questions", [])
          if q.get("source") in sources and isinstance(q.get("id"), str)}
    garde: dict = {}
    for r in resolutions.get("resolutions", []):
        if not isinstance(r.get("id"), str):
            continue
        cle = (r.get("source"), r.get("id"))
        if cle not in qs or not r.get("resolved") or r.get("resolved_to") not in (0, 1, 0.0, 1.0):
            continue
        if cle not in garde or r["resolution_date"] < garde[cle]["resolution_date"]:
            garde[cle] = r
    out = []
    for cle, r in garde.items():
        q = qs[cle]
        out.append({"question": q, "resolution_date": r["resolution_date"], "issue": int(r["resolved_to"])})
    return sorted(out, key=lambda x: (x["question"]["source"], x["question"]["id"]))


def construire(item: dict, jeu: str) -> dict:
    q, rd = item["question"], item["resolution_date"]
    sub = lambda s: str(s or "").replace("{forecast_due_date}", jeu).replace("{resolution_date}", rd)
    contexte = sub(q.get("background"))
    if q.get("freeze_datetime_value") not in (None, "", "N/A") and q.get("source") in SOURCES_SERIES:
        contexte += (f"\n\nDernière valeur connue au {str(q.get('freeze_datetime', ''))[:10]} : "
                     f"{q['freeze_datetime_value']} ({q.get('freeze_datetime_value_explanation', '')}).")
    return {"qid": f"fb:{jeu}:{q['source']}:{q['id']}:{rd}", "titre": sub(q["question"]), "contexte": contexte,
            "criteres": sub(q.get("resolution_criteria")), "url": q.get("url") or "", "resolution": rd,
            "source": q["source"], "issue": item["issue"]}


async def un_test(x: dict, jeu: str, llm, deja: set[str]) -> dict | None:
    if x["qid"] in deja:
        return None
    info = datetime.fromisoformat(jeu).replace(tzinfo=timezone.utc)
    issue = "yes" if x["issue"] == 1 else "no"
    ligne = {"type": "retro", "banc": "forecastbench", "jeu": jeu, "source_question": x["source"],
             "version_bot": ap.VERSION_BOT, "version_skill": ap.version_skill(), "question_id": x["qid"],
             "modeles": ap.modeles_actifs(), "url": x["url"], "titre": x["titre"], "date_information": jeu,
             "resolution": x["resolution"], "issue": x["issue"],
             "licence": "ForecastBench, Forecasting Research Institute, CC BY-SA 4.0"}
    try:
        sonde = ap.extraire_json(await llm(ar.consigne_sonde(x["titre"], x["criteres"])))
    except Exception as e:
        sonde = {"erreur": str(e)[:200]}
    ligne["sonde"] = sonde
    if sonde.get("connait") is True and str(sonde.get("issue") or "").lower() == issue:
        ligne["statut"] = "exclue_connue"
        return ligne
    q = ap.Question(id=x["qid"], url=x["url"], titre=x["titre"], contexte=x["contexte"], criteres=x["criteres"],
                    precisions="", resolution=date.fromisoformat(x["resolution"]))
    jours = max(1, (date.fromisoformat(x["resolution"]) - info.date()).days)

    async def chercher(req: str) -> str:
        return await ar.chercher_avant(req, info)
    c = await ap.alphabet(q, "", llm, chercher, True, jeu, jours, ar.historique_avant)
    ligne.update(statut=c.get("statut"), p_B=c.get("p_B"), p_C=c.get("p_C"), motif=c.get("motif"),
                 evenement=c.get("evenement"), etat=c.get("etat"), vues=c.get("vues"), classe_statut=c.get("classe_statut"),
                 nature_etat_nul=c.get("nature_etat_nul"), puits=c.get("puits"),
                 compte_calcule=bool((c.get("vue") or {}).get("compte_calcule")),
                 exploratoire=c.get("exploratoire"), symetrique=c.get("symetrique"),
                 ombre_causale=c.get("ombre_causale"),
                 attribution=ap.controle_attribution(c.get("dossier"), c.get("_textes")))
    return ligne


async def principal(n: int, apres: str, jeu: str | None, sources: tuple[str, ...], graine: int) -> int:
    import alphabet_bot as ab
    import alphabet_modeles as am
    if not os.environ.get("ALPHABET_CHERCHEUR", "").startswith("smart-searcher") or not os.environ.get("EXA_API_KEY"):
        print("Banc ForecastBench : la recherche doit être Exa (smart-searcher + EXA_API_KEY), seule bornable dans le "
              "temps ici. Rien n'est lancé.")
        return 1
    choix, essais = await am.choisir()
    if not choix["principal"]:
        print("Aucun modèle principal disponible. Rien n'est lancé.")
        return 1
    am.appliquer(choix)
    modele = ab.configuration().get("default")

    async def llm(consigne: str) -> str:
        return await modele.invoke(consigne)
    jeux = [jeu] if jeu else jeux_candidats(date.today(), date.fromisoformat(apres))
    deja, faites = ar.deja_faites(), 0
    rnd = random.Random(graine)
    from forecasting_tools import MonetaryCostManager
    for j in jeux:
        if faites >= n:
            break
        try:
            qs = await _json(f"{DEPOT}/question_sets/{j}-llm.json")
            rs = await _json(f"{DEPOT}/resolution_sets/{j}_resolution_set.json")
        except Exception as e:
            print(f"Jeu {j} indisponible : {type(e).__name__}")
            continue
        items = [construire(i, j) for i in apparier(qs, rs, sources)]
        rnd.shuffle(items)
        print(f"Jeu {j} : {len(items)} questions de séries résolues.")
        for x in items:
            if faites >= n:
                break
            with MonetaryCostManager() as cm:
                try:
                    ligne = await un_test(x, j, llm, deja)
                except Exception as e:
                    ligne = {"type": "retro", "banc": "forecastbench", "version_bot": ap.VERSION_BOT,
                             "question_id": x["qid"], "statut": "erreur", "motif": f"{type(e).__name__}: {e}"[:300]}
                cout = cm.current_usage
            if ligne is None:
                continue
            ligne["cout_usd"] = round(float(cout or 0), 4)
            ar.ecrire(ligne)
            deja.add(ligne["question_id"])
            faites += 1
            print(f"{ligne['question_id'][:60]} : {ligne.get('statut')} · B {ligne.get('p_B')} · C {ligne.get('p_C')} · "
                  f"issue {ligne.get('issue')} · {ligne['cout_usd']} $")
    print(f"{faites} question(s) ForecastBench écrite(s) dans registre/{ar.RETRO}.")
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--n", type=int, default=int(os.environ.get("ALPHABET_FB_N") or 20))
    a.add_argument("--apres", default=os.environ.get("ALPHABET_RETRO_APRES") or "2026-07-01",
                   help="jeux postérieurs à cette date (après la date de connaissance du modèle)")
    a.add_argument("--jeu", default=None, help="date d'un jeu (AAAA-MM-JJ) ; sinon les plus récents résolus")
    a.add_argument("--sources", default=",".join(SOURCES_SERIES))
    a.add_argument("--graine", type=int, default=0)
    args = a.parse_args()
    srcs = tuple(s for s in args.sources.split(",") if s in SOURCES_SERIES)
    sys.exit(asyncio.run(principal(args.n, args.apres, args.jeu, srcs, args.graine)))
