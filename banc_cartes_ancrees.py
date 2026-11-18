"""Banc des cartes ancrées (bot 0.10.274) : accord entre lecteurs, hallucinations, lien avec l'issue.

Préenregistrement : preenregistrements/cartes-ancrees.md. Questions : les questions DISTINCTES du banc
jugement_alphabet (première date de jeu), recherche gelée (cache, trace_recherche). Deux lecteurs : gpt-5-mini
(Azure) et Claude Haiku 4.5 (Bedrock, crédits jusqu'au 23). Un appel par lecteur et par question.

    python banc_cartes_ancrees.py --budget 1 --budget-bedrock 3
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
import bras_m
import cartes_ancrees as ca
import psychometrie_alphabet as ps
import trace_recherche as tr

FICHIER = Path("registre/banc-cartes-ancrees.jsonl")
RESUME = Path("registre/banc-cartes-ancrees.json")
LECTEURS = {"gpt": bv.GPT, "haiku": bv.HAIKU}
CARTES = ("declencheur", "proportion")


def lignes() -> list[dict]:
    return [json.loads(l) for l in FICHIER.read_text(encoding="utf-8").splitlines() if l.strip()] if FICHIER.exists() else []


def notes_libres() -> dict[str, dict]:
    """Notes LIBRES (1 à 4) déjà données par chaque lecteur sur ces questions (bancs du 2026-11-17 et 18)."""
    q = lambda qid: ":".join(qid.split(":")[:2])       # par question distincte, première date de jeu
    gpt, haiku = {}, {}
    for x in sorted(bja.lignes(), key=lambda x: x["question_id"].split(":")[-1]):
        if x.get("notes") and not x.get("exclue"):
            gpt.setdefault(q(x["question_id"]), {k: v["note"] for k, v in x["notes"].items()})
    for x in sorted(bv.lignes(), key=lambda x: x["question_id"].split(":")[-1]):
        h = x.get("haiku") or {}
        if h.get("notes") and not h.get("exclue"):
            haiku.setdefault(q(x["question_id"]), {k: v["note"] for k, v in h["notes"].items()})
    return {"gpt": gpt, "haiku": haiku}


def Q(x: dict) -> str:
    return ":".join(x["question_id"].split(":")[:2])


def resumer(ls: list[dict]) -> dict:
    libres = notes_libres()
    out = {"version_bot": ap.VERSION_BOT, "questions": len(ls), "note": "Spearman : accord de rang entre lecteurs"}
    # 1. accord entre lecteurs, ancrées contre libres, sur les mêmes questions
    for c in CARTES:
        paires_a = [(x["ancre"]["gpt"][c], x["ancre"]["haiku"][c]) for x in ls
                    if x.get("ancre", {}).get("gpt", {}).get(c) is not None and x.get("ancre", {}).get("haiku", {}).get(c) is not None]
        paires_l = [(libres["gpt"][Q(x)][c], libres["haiku"][Q(x)][c]) for x in ls
                    if c in libres["gpt"].get(Q(x), {}) and c in libres["haiku"].get(Q(x), {})]
        communs = [x for x in ls if x.get("ancre", {}).get("gpt", {}).get(c) is not None
                   and x.get("ancre", {}).get("haiku", {}).get(c) is not None
                   and c in libres["gpt"].get(Q(x), {}) and c in libres["haiku"].get(Q(x), {})]
        sp = lambda ps_: (None if len(ps_) < 10 else ps.spearman([a for a, _ in ps_], [b for _, b in ps_]))
        a = sp([(x["ancre"]["gpt"][c], x["ancre"]["haiku"][c]) for x in communs])
        l_ = sp([(libres["gpt"][Q(x)][c], libres["haiku"][Q(x)][c]) for x in communs])
        out[f"accord_{c}"] = {"n_communs": len(communs), "ancrees": None if a is None else round(a, 3),
                              "libres": None if l_ is None else round(l_, 3),
                              "gain": None if a is None or l_ is None else round(a - l_, 3),
                              "n_ancrees_toutes": len(paires_a), "accord_ancrees_toutes": None if sp(paires_a) is None else round(sp(paires_a), 3),
                              "n_libres_toutes": len(paires_l)}
    # 2. hallucinations : part des faits proposés rejetés par le code
    for lec in LECTEURS:
        p = sum(x["ancre"][lec]["faits_proposes"] for x in ls if lec in x.get("ancre", {}))
        r = sum(x["ancre"][lec]["faits_rejetes"] for x in ls if lec in x.get("ancre", {}))
        out[f"hallucinations_{lec}"] = {"faits_proposes": p, "faits_rejetes": r, "part": round(r / p, 3) if p else None}
    # 3. lien avec l'issue (descriptif), note ancrée de chaque lecteur
    for lec in LECTEURS:
        for c in CARTES:
            v = [(x["ancre"][lec][c], x["issue"]) for x in ls if x.get("ancre", {}).get(lec, {}).get(c) is not None]
            rho = None if len(v) < 10 else ps.spearman([a for a, _ in v], [b for _, b in v])
            out[f"issue_{lec}_{c}"] = {"n": len(v), "spearman": None if rho is None else round(rho, 3)}
    g = out.get("accord_declencheur", {}).get("gain")
    out["verdict_principal"] = ("ancrage retenu : accord nettement meilleur (≥ +0,15)" if g is not None and g >= 0.15
                                else "ancrage non retenu" if g is not None else "en attente")
    return out


async def principal(budget: float, budget_bedrock: float) -> int:
    from forecasting_tools import MonetaryCostManager
    base = bv.base_banc()
    deja = {x["question_id"] for x in lignes()}
    vus, textes = set(), {}
    cumul = {"gpt": 0.0, "haiku": 0.0}
    pire = {"gpt": 0.0, "haiku": 0.0}
    plafond = {"gpt": budget, "haiku": budget_bedrock}
    with FICHIER.open("a", encoding="utf-8") as f:
        for x in sorted(bja.candidates(), key=lambda x: x["jeu"]):
            qid = f'{x["source"]}:{x["id"]}:{x["jeu"]}'
            cle_q = f'{x["source"]}:{x["id"]}'
            if qid not in base or cle_q in vus:
                continue
            vus.add(cle_q)                       # une seule ligne par question distincte (première date de jeu)
            if qid in deja:
                continue
            if any(fb.depasse(cumul[k], pire[k], plafond[k]) for k in LECTEURS):
                print(f"Plafond atteint ({cumul}). Arrêt.")
                break
            info = datetime.fromisoformat(x["jeu"]).replace(tzinfo=timezone.utc)
            rech, _ = await tr.chercher_fige(qid, x["titre"], info, ar.chercher_avant)
            if bras_m.recherche_vide(rech):
                continue                         # rien à extraire : ces questions vont au banc de l'abstention
            if x["jeu"] not in textes:
                try:
                    qs = await fb._json(f"{fb.DEPOT}/question_sets/{x['jeu']}-llm.json")
                    textes[x["jeu"]] = {str(q["id"]): q for q in qs.get("questions", [])}
                except Exception:
                    textes[x["jeu"]] = {}
            src = textes[x["jeu"]].get(x["id"]) or {}
            q = {"titre": x["titre"], "cloture": x["cloture"],
                 "criteres": str(src.get("market_info_resolution_criteria") or src.get("resolution_criteria") or "")}
            ancre, brut = {}, {}
            for lec, modele in LECTEURS.items():
                with MonetaryCostManager() as cm:
                    try:
                        r = await bv.appeler(modele, ca.consigne(q, rech, x["jeu"]))
                        brut[lec] = {k: r.get(k) for k in ("declencheur", "distance")}
                        ancre[lec] = ca.ancrer(r, rech, x["jeu"], x["cloture"])
                    except Exception as e:
                        ancre[lec] = {"erreur": f"{type(e).__name__}: {e}"[:200], "faits_proposes": 0, "faits_rejetes": 0}
                    c = float(cm.current_usage or 0)
                cumul[lec] += c
                pire[lec] = max(pire[lec], c)
            f.write(json.dumps({"type": "banc_cartes_ancrees", "question_id": qid, "jeu": x["jeu"], "issue": x["issue"],
                                "forme": x["forme"], "ancre": ancre, "extraits": brut,
                                "recherche": {"empreinte": tr.tracer(rech, x["jeu"])["empreinte"]},
                                "version_bot": ap.VERSION_BOT,
                                "licence": "ForecastBench, Forecasting Research Institute, CC BY-SA 4.0"},
                               ensure_ascii=False) + "\n")
            f.flush()
            print(f"{qid[:44]} : gpt {ancre['gpt'].get('declencheur')}/{ancre['gpt'].get('proportion')} "
                  f"({ancre['gpt'].get('declencheur_motif')}) · haiku {ancre['haiku'].get('declencheur')}/"
                  f"{ancre['haiku'].get('proportion')} ({ancre['haiku'].get('declencheur_motif')})", flush=True)
    r = resumer(lignes())
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    print(f"Coûts : Azure {cumul['gpt']:.2f} $, Bedrock {cumul['haiku']:.2f} $")
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--budget", type=float, default=1.0)
    a.add_argument("--budget-bedrock", type=float, default=3.0)
    o = a.parse_args()
    sys.exit(asyncio.run(principal(o.budget, o.budget_bedrock)))
