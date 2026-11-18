"""Sonde du filtre de contenu d'Azure (bot 0.10.286) : qu'est-ce qui fait refuser la consigne des cartes ancrées ?

Décision d'auteur du 2026-11-18, 19 h 42 (« oui, je te suis »). Le bot n'est PAS modifié (décision de 19 h 40 : rien
ne change côté Metaculus avant le tournoi). Constat : au banc des cartes ancrées (run 44363011276), Azure a refusé 22
consignes sur 114 (« filtered due to the prompt triggering Azure OpenAI's content management policy ») ; aucune
consigne du bot ni des bancs du jugement n'a été refusée (530 lignes de bancs, 30 passages du bot relus).

Les 22 consignes refusées sont rejouées, recherche gelée identique, en quatre variantes, une seule chose changée à la
fois :
- identique : la consigne d'origine (le refus se reproduit-il ?) ;
- recherche_4000 : recherche ramenée à 4 000 caractères (comme les consignes du jugement) ;
- sans_mot_pour_mot : sans l'exigence de copier des phrases mot pour mot ;
- sans_criteres : sans les critères de résolution de la question.
Aucune probabilité n'est calculée : on ne compte que les refus. Environ 90 appels gpt-5-mini.

    python banc_filtre_azure.py --budget 0.5
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import alphabet_pipeline as ap
import alphabet_retro as ar
import banc_forecastbench as fb
import banc_jugement_alphabet as bja
import banc_jugement_variantes as bv
import cartes_ancrees as ca
import trace_recherche as tr

SOURCE = Path("registre/banc-cartes-ancrees.jsonl")
FICHIER = Path("registre/banc-filtre-azure.jsonl")
RESUME = Path("registre/banc-filtre-azure.json")
VARIANTES = ("identique", "recherche_4000", "sans_mot_pour_mot", "sans_criteres")
COPIE = [
    ("Chaque fait doit être appuyé par une PHRASE COPIÉE MOT POUR MOT depuis les résultats de recherche ci-dessous\n"
     "(au moins 20 caractères).", "Chaque fait doit s'appuyer sur les résultats de recherche ci-dessous."),
    (" Une phrase qui n'est pas dans la recherche sera rejetée.", ""),
    ('"phrase exacte contenant la valeur"', '"passage qui contient la valeur"'),
    ('"phrase exacte"', '"passage qui l\'appuie"'),
]


def refusees() -> list[str]:
    ls = [json.loads(l) for l in SOURCE.read_text(encoding="utf-8").splitlines() if l.strip()] if SOURCE.exists() else []
    return [x["question_id"] for x in ls if "filtered" in str((x.get("ancre", {}).get("gpt") or {}).get("erreur", ""))]


def consigne(variante: str, q: dict, rech: str, jeu: str) -> str:
    if variante == "recherche_4000":
        return ca.consigne(q, rech[:4000], jeu)
    if variante == "sans_criteres":
        return ca.consigne(dict(q, criteres=""), rech, jeu)
    t = ca.consigne(q, rech, jeu)
    if variante == "sans_mot_pour_mot":
        for a, b in COPIE:
            t = t.replace(a, b)
    return t


def est_refus(e: Exception) -> bool:
    m = str(e).lower()
    return "content management" in m or "filtered due to" in m or "content_filter" in m


def resumer(ls: list[dict]) -> dict:
    out = {"version_bot": ap.VERSION_BOT, "questions": len(ls), "note": "nombre de consignes refusées par variante"}
    for v in VARIANTES:
        r = [x["variantes"].get(v) for x in ls if v in x.get("variantes", {})]
        out[v] = {"essais": len(r), "refus": sum(1 for a in r if a == "refus"),
                  "acceptees": sum(1 for a in r if a == "acceptee"), "autres_erreurs": sum(1 for a in r if a == "erreur")}
    return out


async def principal(budget: float) -> int:
    from forecasting_tools import MonetaryCostManager
    cibles = set(refusees())
    cand = {f'{x["source"]}:{x["id"]}:{x["jeu"]}': x for x in bja.candidates()}
    textes, cumul, pire = {}, 0.0, 0.0
    lignes = []
    for qid in sorted(cibles):
        x = cand.get(qid)
        if not x:
            continue
        if fb.depasse(cumul, pire, budget):
            print(f"Plafond atteint ({cumul:.2f} $). Arrêt.")
            break
        info = datetime.fromisoformat(x["jeu"]).replace(tzinfo=timezone.utc)
        rech, _ = await tr.chercher_fige(qid, x["titre"], info, ar.chercher_avant)
        if x["jeu"] not in textes:
            try:
                qs = await fb._json(f"{fb.DEPOT}/question_sets/{x['jeu']}-llm.json")
                textes[x["jeu"]] = {str(q["id"]): q for q in qs.get("questions", [])}
            except Exception:
                textes[x["jeu"]] = {}
        src = textes[x["jeu"]].get(x["id"]) or {}
        q = {"titre": x["titre"], "cloture": x["cloture"],
             "criteres": str(src.get("market_info_resolution_criteria") or src.get("resolution_criteria") or "")}
        res = {}
        for v in VARIANTES:
            with MonetaryCostManager() as cm:
                try:
                    await bv.appeler(bv.GPT, consigne(v, q, rech, x["jeu"]))
                    res[v] = "acceptee"
                except Exception as e:
                    res[v] = "refus" if est_refus(e) else "erreur"
                c = float(cm.current_usage or 0)
            cumul += c
            pire = max(pire, c)
        lignes.append({"type": "banc_filtre_azure", "question_id": qid, "variantes": res,
                       "longueur_recherche": len(rech or ""), "longueur_criteres": len(q["criteres"]),
                       "recherche": {"empreinte": tr.tracer(rech, x["jeu"])["empreinte"]}, "version_bot": ap.VERSION_BOT})
        print(f"{qid[:40]} : {res}", flush=True)
    FICHIER.write_text("".join(json.dumps(l, ensure_ascii=False) + "\n" for l in lignes), encoding="utf-8")
    r = resumer(lignes)
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    print(f"Coût : {cumul:.2f} $")
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--budget", type=float, default=0.5)
    sys.exit(asyncio.run(principal(a.parse_args().budget)))
