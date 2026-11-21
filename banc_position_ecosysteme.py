"""Banc « M avec position écosystémique contre M sans » (preenregistrements/position-ecosysteme.md, option (b) de
l'auteur du 2026-11-21, 14 h 26). Préparé, lancé une seule fois après validation de l'auteur.

Questions : celles de la carte robot (carte_robot.py, motifs Python figés, aucun appel de modèle) sur l'ensemble
jugement2026 qui ont au moins une règle sourcée (registre/carte-robot-jugement2026.json), une ligne par question.
Recherche bornée avant la date du jeu et GELÉE (cache partagé avec les autres bancs), taux de départ des semblables.

Par question, sur les mêmes entrées :
- les notes du comité (un appel, partagé par les trois bras) ;
- M0 : la synthèse finale de M telle qu'aujourd'hui ;
- M1 : la même synthèse, avec en plus les règles sourcées retenues par la carte (situation de départ → événement,
  texte de la règle) ;
- M2 (placebo) : la même synthèse avec autant de règles tirées au hasard (graine fixe) parmi celles dont l'objet
  est DIFFÉRENT : mesure ce qu'apporte du texte de règle quelconque.
Les cotes et prévisions de foule ne sont jamais lues ni transmises.

    python banc_position_ecosysteme.py --n 150 --budget 15     # Claude Haiku 4.5, crédits Bedrock
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import alphabet_modeles as am
import alphabet_pipeline as ap
import alphabet_retro as ar
import banc_forecastbench as fb
import banc_jugement as bj
import banc_jugement_alphabet as bja
import couverture_regles as cr
import garde_injection as gi
import trace_recherche as tr

REGISTRE = Path("registre")
CARTE = REGISTRE / "carte-robot-jugement2026.json"      # robot Python, décision de l'auteur du 2026-11-21, 14 h 45
FICHIER = REGISTRE / "banc-position-ecosysteme.jsonl"
RESUME = REGISTRE / "banc-position-ecosysteme.json"
HAIKU = "bedrock/global.anthropic.claude-haiku-4-5-20251001-v1:0"   # crédits Bedrock (décision de l'auteur, 14 h 36)
MODELE = HAIKU
GRAINE = sum(map(ord, "position-ecosysteme"))


def bloc_regles(ids: list[str], cat: dict) -> str:
    return "\n".join(f"- Situation de départ : {cat[i]['situation']}\n  Événement : {cat[i]['objet']}\n"
                     f"  Règle (source vérifiée) : {cat[i]['texte']}" for i in ids)


def consigne_avec_regles(q: dict, p_b: float, notes: dict, recherche: str, jeu: str, regles: str) -> str:
    base = bja.consigne_finale(q, p_b, notes, recherche, jeu)
    ajout = f"""
RÈGLES SOURCÉES QUI GOUVERNENT CE TYPE DE SITUATION ET D'ÉVÉNEMENT (taux, procédures, calendriers mesurés ailleurs, sur
des cas homologues ; à combiner avec le taux de base et la recherche, pas à appliquer aveuglément) :
{regles}
"""
    coupe = base.index("Pars du taux de base.")
    return base[:coupe] + ajout + "\n" + base[coupe:]


def placebo(ids: list[str], cat: dict, rng: random.Random) -> list[str]:
    objets = {cat[i]["objet"] for i in ids}
    autres = sorted(i for i in cat if cat[i]["objet"] not in objets)
    return rng.sample(autres, len(ids))


def candidates() -> list[tuple[dict, list[str]]]:
    carte = {o["question"]: o for o in json.loads(CARTE.read_text(encoding="utf-8"))["detail"] if o.get("regles")}
    xs = bj.cohorte_complete([json.loads(l) for l in bj.REGISTRE.read_text(encoding="utf-8").splitlines() if l.strip()])
    bj.calculer(xs)
    out = {}
    for x in sorted(xs, key=lambda x: x["jeu"]):
        k = f'{x["source"]}:{x["id"]}'
        if k in carte and x["jeu"] == carte[k].get("jeu") and k not in out:
            out[k] = (x, carte[k]["regles"])
    return sorted(out.values(), key=lambda v: bja.rang(v[0]))


def lignes() -> list[dict]:
    if not FICHIER.exists():
        return []
    return [json.loads(l) for l in FICHIER.read_text(encoding="utf-8").splitlines() if l.strip()]


def resumer(ls: list[dict]) -> dict:
    import numpy as np
    import score_registre as sr
    import verification_a_priori as va
    ok = [x for x in ls if x.get("issue") in (0, 1) and all(x.get(k) is not None for k in ("p_M0", "p_M1", "p_M2"))
          and not x.get("exclue")]
    out = {"version_bot": ap.VERSION_BOT, "n": len(ok), "note": "perte log, plus bas = mieux ; une ligne par question"}
    if len(ok) < 20:
        return out
    pl = sr.log_score
    perte = {k: np.array([pl(x[k], x["issue"]) for x in ok]) for k in ("p_B", "p_M0", "p_M1", "p_M2")}
    rng = np.random.default_rng(GRAINE)

    def ic(d):
        b = np.array([d[rng.integers(0, len(d), len(d))].mean() for _ in range(5000)])
        return [round(float(v), 4) for v in np.percentile(b, [5, 95])]
    d10, d12, d20 = perte["p_M1"] - perte["p_M0"], perte["p_M1"] - perte["p_M2"], perte["p_M2"] - perte["p_M0"]
    out.update({k.replace("p_", ""): round(float(v.mean()), 4) for k, v in perte.items()})
    out.update({"M1_moins_M0": round(float(d10.mean()), 4), "intervalle_90_M1_M0": ic(d10),
                "M1_moins_M2": round(float(d12.mean()), 4), "intervalle_90_M1_M2": ic(d12),
                "M2_moins_M0": round(float(d20.mean()), 4), "intervalle_90_M2_M0": ic(d20),
                "puissance": va.puissance(d10.tolist())})
    out["adopte"] = bool(out["intervalle_90_M1_M0"][1] < 0 and out["M1_moins_M2"] < 0)
    return out


async def principal(budget: float, n: int = 150, modele: str = HAIKU) -> int:
    from forecasting_tools import MonetaryCostManager
    if not ar.recherche_bornee_disponible():
        print("Il faut une recherche bornable dans le temps (EXA_API_KEY ou TINYFISH_API_KEY). Rien n'est lancé.")
        return 1
    cat = cr.catalogue()
    rng = random.Random(GRAINE)
    deja = {x["question_id"] for x in lignes()}
    cand = candidates()
    print(f"{len(cand)} questions couvertes par la carte v5 (une par question).")
    textes: dict[str, dict] = {}
    faites, cumul, pire = 0, 0.0, 0.0
    with FICHIER.open("a", encoding="utf-8") as f:
        for x, ids in cand:
            ids = [i for i in ids if i in cat]
            plac = placebo(ids, cat, rng)               # tiré pour chaque question dans l'ordre fixé, même si déjà faite
            qid = f'{x["source"]}:{x["id"]}:{x["jeu"]}'
            if faites >= n:
                break
            if qid in deja or not ids:
                continue
            if fb.depasse(cumul, pire, budget):
                print(f"Plafond atteint : {cumul:.2f} $. Arrêt.")
                break
            if x["jeu"] not in textes:
                try:
                    qs = await fb._json(f"{fb.DEPOT}/question_sets/{x['jeu']}-llm.json")
                    textes[x["jeu"]] = {str(q["id"]): q for q in qs.get("questions", [])}
                except Exception:
                    textes[x["jeu"]] = {}
            src = textes[x["jeu"]].get(x["id"])
            if not src:
                continue
            q = {"titre": x["titre"], "cloture": x["cloture"],
                 "criteres": str(src.get("market_info_resolution_criteria") or src.get("resolution_criteria") or ""),
                 "contexte": str(src.get("background") or "")}       # jamais freeze_datetime_value ni source_intro
            p_b = float(x["p_S"])
            res, exclue = {}, False
            with MonetaryCostManager() as cm:
                info = datetime.fromisoformat(x["jeu"]).replace(tzinfo=timezone.utc)
                rech, du_cache = await tr.chercher_fige(qid, x["titre"], info, ar.chercher_avant)
                res["recherche"] = {**tr.tracer(rech, x["jeu"]), "cache": du_cache}
                llm = lambda: am.llm(modele, temperature=0.2, timeout=300, allowed_tries=2)
                try:
                    r = ap.extraire_json(await llm().invoke(bja.consigne_notes(q, p_b, rech, x["jeu"])))
                    notes = bja.lire_notes(r)
                    exclue = bool(r.get("connait_issue"))
                    for bras, consigne in (("p_M0", bja.consigne_finale(q, p_b, notes, rech, x["jeu"])),
                                           ("p_M1", consigne_avec_regles(q, p_b, notes, rech, x["jeu"], bloc_regles(ids, cat))),
                                           ("p_M2", consigne_avec_regles(q, p_b, notes, rech, x["jeu"], bloc_regles(plac, cat)))):
                        r = ap.extraire_json(await llm().invoke(consigne))
                        res[bras] = min(0.99, max(0.01, float(r["p"])))
                except Exception as e:
                    res["erreur"] = f"{type(e).__name__}: {e}"[:200]
                cout = float(cm.current_usage or 0)
            ligne = {"type": "banc_position_ecosysteme", "jeu": x["jeu"], "question_id": qid, "source_question": x["source"],
                     "version_bot": ap.VERSION_BOT, "titre": x["titre"], "forme": x["forme"], "issue": x["issue"],
                     "p_B": p_b, "regles": ids, "placebo": plac, **res, "exclue": exclue, "modele": modele,
                     "cout_usd": round(cout, 4), "licence": "ForecastBench, Forecasting Research Institute, CC BY-SA 4.0"}
            f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
            f.flush()
            deja.add(qid)
            cumul += cout
            pire = max(pire, cout)
            faites += 1
            print(f"{qid[:50]} : M0 {res.get('p_M0')} · M1 {res.get('p_M1')} · M2 {res.get('p_M2')} · B {p_b:.3f} · "
                  f"issue {x['issue']} · {cout:.4f} $", flush=True)
    r = resumer(lignes())
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{faites} question(s) ; coût {cumul:.2f} $ (plafond {budget:.2f} $).")
    print(json.dumps(r, ensure_ascii=False, indent=1)[:3000])
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--budget", type=float, default=15.0)
    a.add_argument("--n", type=int, default=150)
    a.add_argument("--modele", default=HAIKU)
    o = a.parse_args()
    sys.exit(asyncio.run(principal(o.budget, o.n, o.modele)))
