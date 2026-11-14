"""Banc du taux de base seul (0.10.104, décision d'auteur du 2026-11-15 : améliorer B plutôt que C). AUCUN modèle de
langue, aucun coût : pour chaque question de série ForecastBench déjà résolue (FRED, DBnomics), B (compte de hausses,
Jeffreys) et B_AR (AR(1) sur les différences) sont calculés par le code avec les règles de `banc_forecastbench`, sur
la série bornée strictement avant la date d'information. Registre à part : registre/banc-b.jsonl (le registre du banc
de l'alphabet, retro.jsonl, n'est pas touché). Résumé et critère d'adoption du B autorégressif : registre/banc-b.json.

Ordre des questions pour le critère (« les 100 premières questions de jeux non vus », pré-enregistrement
b-autoregressif.md) : jeux du plus ancien au plus récent, puis identifiant de question ; fixé avant tout calcul.

    python banc_b.py [--apres 2026-07-01] [--max 400]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

import alphabet_pipeline as ap
import banc_forecastbench as fb

REGISTRE = Path("registre")
FICHIER = REGISTRE / "banc-b.jsonl"
RESUME = REGISTRE / "banc-b.json"
SOURCES = ("fred", "dbnomics")


def lignes_existantes() -> list[dict]:
    if not FICHIER.exists():
        return []
    return [json.loads(l) for l in FICHIER.read_text(encoding="utf-8").splitlines() if l.strip()]


def ordonner(lignes: list[dict]) -> list[dict]:
    return sorted(lignes, key=lambda x: (x["jeu"], x["question_id"]))


def resumer(lignes: list[dict]) -> dict:
    import score_registre as sr
    ok = [x for x in ordonner(lignes) if x.get("p_B") is not None and isinstance(x.get("ombre_b_ar"), dict)
          and x["ombre_b_ar"].get("p") is not None and x.get("issue") in (0, 1)]
    pl = sr.log_score
    par_jeu: dict[str, dict] = {}
    for x in ok:
        a = par_jeu.setdefault(f"{x['jeu']}:{x['source_question']}", {"n": 0, "B": 0.0, "B_AR": 0.0})
        a["n"] += 1
        a["B"] += pl(x["p_B"], x["issue"])
        a["B_AR"] += pl(x["ombre_b_ar"]["p"], x["issue"])
    return {"version_bot": ap.VERSION_BOT, "questions": len(lignes), "avec_B_et_B_AR": len(ok),
            "note": "perte log (plus bas = mieux) ; aucun modèle de langue",
            "par_bloc": {k: {"n": v["n"], "B": round(v["B"] / v["n"], 4), "B_AR": round(v["B_AR"] / v["n"], 4)}
                         for k, v in sorted(par_jeu.items())},
            "critere_b_ar": sr.critere_b_ar(ok)}


async def principal(apres: str, max_q: int) -> int:
    deja = {x["question_id"] for x in lignes_existantes()}
    jeux = sorted(fb.jeux_candidats(date.today(), date.fromisoformat(apres), n_max=26))
    REGISTRE.mkdir(exist_ok=True)
    nouvelles = 0
    with FICHIER.open("a", encoding="utf-8") as f:
        for j in jeux:
            if nouvelles >= max_q:
                break
            try:
                qs = await fb._json(f"{fb.DEPOT}/question_sets/{j}-llm.json")
                rs = await fb._json(f"{fb.DEPOT}/resolution_sets/{j}_resolution_set.json")
            except Exception as e:
                print(f"Jeu {j} indisponible : {type(e).__name__}")
                continue
            items = sorted((fb.construire(i, j) for i in fb.apparier(qs, rs, SOURCES)), key=lambda x: x["qid"])
            print(f"Jeu {j} : {len(items)} questions de séries résolues.")
            for x in items:
                if nouvelles >= max_q:
                    break
                if x["qid"] in deja:
                    continue
                try:
                    vue = await fb.vue_calculee(x, x["_q"], j)
                except Exception as e:
                    vue, x["_b_ar"] = None, {"erreur": f"{type(e).__name__}: {e}"[:200]}
                ligne = {"type": "banc_b", "jeu": j, "source_question": x["source"], "question_id": x["qid"],
                         "version_bot": ap.VERSION_BOT, "titre": x["titre"], "resolution": x["resolution"],
                         "issue": x["issue"], "p_B": (vue or {}).get("frequence"), "calcul_B": (vue or {}).get("calcul"),
                         "ombre_b_ar": x.get("_b_ar"),
                         "licence": "ForecastBench, Forecasting Research Institute, CC BY-SA 4.0"}
                f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
                f.flush()
                deja.add(x["qid"])
                nouvelles += 1
    r = resumer(lignes_existantes())
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{nouvelles} question(s) ajoutée(s) ; {r['avec_B_et_B_AR']} avec B et B_AR.")
    print("Critère B_AR :", json.dumps(r["critere_b_ar"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--apres", default="2026-07-01")
    a.add_argument("--max", type=int, default=400)
    o = a.parse_args()
    sys.exit(asyncio.run(principal(o.apres, o.max)))
