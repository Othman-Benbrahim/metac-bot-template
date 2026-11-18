"""Banc du complément GDELT (bot 0.10.280) : les titres GDELT par BigQuery, AJOUTÉS à la recherche, aident-ils M ?

Décision d'auteur du 2026-11-18, 17 h 32 (« oui »). Préenregistrement : preenregistrements/gdelt-complement.md.
Questions : les questions distinctes des bancs de jugement qui ont au moins un titre GDELT (registre/gdelt-bq-bancs.json,
articles vus par GDELT dans les 90 jours avant la date du jeu). Deux jugements finaux de M (gpt-5-mini) par question,
mêmes notes de cartes (banc jugement_alphabet), même taux de départ, même part de la recherche gelée :
- SANS : la recherche gelée ;
- AVEC : la même recherche, plus le bloc des titres GDELT.
La place laissée à la recherche gelée est la même dans les deux bras (les titres ne la font pas déborder).

    python banc_gdelt_complement.py --budget 1.5
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
import gdelt_bq
import trace_recherche as tr

FICHIER = Path("registre/banc-gdelt-complement.jsonl")
RESUME = Path("registre/banc-gdelt-complement.json")
FENETRE = 4000          # caractères de recherche que la consigne finale montre au modèle (gi.bloc dans bja)


def lignes() -> list[dict]:
    return [json.loads(l) for l in FICHIER.read_text(encoding="utf-8").splitlines() if l.strip()] if FICHIER.exists() else []


def recherches(rech: str, articles: list[dict]) -> tuple[str, str]:
    """(sans, avec) : la même part de recherche gelée dans les deux bras ; le bloc GDELT en plus dans le second."""
    bloc = "TITRES D'ARTICLES VUS PAR GDELT AVANT CETTE DATE (titres seuls) :\n" + gdelt_bq.texte_recherche(articles)
    bloc = bloc[:1500]
    part = rech[: max(0, FENETRE - len(bloc) - 2)]
    return part, part + "\n\n" + bloc


def resumer(ls: list[dict]) -> dict:
    import profil_erreurs as pe
    import score_registre as sr
    ok = [x for x in ls if x.get("p_sans") is not None and x.get("p_avec") is not None]
    out = {"version_bot": ap.VERSION_BOT, "n": len(ok), "unites": pe.unites(ok),
           "note": "perte log, plus bas = mieux ; écart = avec − sans"}
    if not ok:
        return out
    out["profils"] = pe.profils(ok, {"sans": "p_sans", "avec": "p_avec"})
    out["critere"] = sr.critere_ombre_b([dict(x, p_B=x["p_sans"], o={"p": x["p_avec"]}) for x in ok], "o",
                                        "gdelt_complement", exclure_vus=False, bloc_par="question", tout_juger=True)
    return out


async def principal(budget: float) -> int:
    from forecasting_tools import MonetaryCostManager
    gd = json.loads(gdelt_bq.BANCS.read_text(encoding="utf-8")) if gdelt_bq.BANCS.exists() else {}
    base = bv.base_banc()
    deja = {x["question_id"] for x in lignes()}
    cand = {f'{x["source"]}:{x["id"]}:{x["jeu"]}': x for x in bja.candidates()}
    textes, cumul, pire = {}, 0.0, 0.0
    with FICHIER.open("a", encoding="utf-8") as f:
        for qid, articles in gd.items():
            if not articles or qid in deja or qid not in base or qid not in cand:
                continue
            if fb.depasse(cumul, pire, budget):
                print(f"Plafond atteint ({cumul:.2f} $). Arrêt.")
                break
            x, b = cand[qid], base[qid]
            notes = b.get("notes") or {}
            if len(notes) < 4:
                continue
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
                 "criteres": str(src.get("market_info_resolution_criteria") or src.get("resolution_criteria") or ""),
                 "contexte": str(src.get("background") or "")}
            sans, avec = recherches(rech, articles)
            res = {}
            with MonetaryCostManager() as cm:
                for bras, r in (("p_sans", sans), ("p_avec", avec)):
                    try:
                        res[bras] = bv.borne((await bv.appeler(bv.GPT, bja.consigne_finale(q, float(b["p_B"]), notes, r,
                                                                                         x["jeu"])))["p"])
                    except Exception as e:
                        res[f"erreur_{bras}"] = f"{type(e).__name__}: {e}"[:200]
                c = float(cm.current_usage or 0)
            f.write(json.dumps({"type": "banc_gdelt_complement", "question_id": qid, "jeu": x["jeu"], "issue": x["issue"],
                                "forme": x["forme"], **res, "n_titres": len(articles), "cout_usd": round(c, 4),
                                "version_bot": ap.VERSION_BOT,
                                "licence": "ForecastBench, Forecasting Research Institute, CC BY-SA 4.0 ; GDELT"},
                               ensure_ascii=False) + "\n")
            f.flush()
            cumul, pire = cumul + c, max(pire, c)
            print(f"{qid[:44]} : sans {res.get('p_sans')} · avec {res.get('p_avec')} · issue {x['issue']}", flush=True)
    r = resumer(lignes())
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    print(f"Coût : {cumul:.2f} $")
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--budget", type=float, default=1.5)
    sys.exit(asyncio.run(principal(a.parse_args().budget)))
