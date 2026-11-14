"""Banc du taux de base seul (0.10.104, décision d'auteur du 2026-11-15 : améliorer B plutôt que C). AUCUN modèle de
langue, aucun coût : pour chaque question de série ForecastBench déjà résolue (FRED, DBnomics), B (compte de hausses,
Jeffreys) B_AR (AR(1) sur les différences) et B_saison (même période du calendrier) sont calculés par le code avec les règles de `banc_forecastbench`, sur
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


def avec(lignes: list[dict], cle: str) -> list[dict]:
    return [x for x in ordonner(lignes) if x.get("p_B") is not None and isinstance(x.get(cle), dict)
            and x[cle].get("p") is not None and x.get("issue") in (0, 1)]


def resumer(lignes: list[dict]) -> dict:
    import score_registre as sr
    pl = sr.log_score
    out = {"version_bot": ap.VERSION_BOT, "questions": len(lignes),
           "note": "perte log (plus bas = mieux) ; aucun modèle de langue ; blocs = jeu × source"}
    for cle, nom, essai in (("ombre_b_ar", "B_AR", "b_autoregressif"), ("ombre_b_saison", "B_saison", "b_saisonnier")):
        ok = avec(lignes, cle)
        par: dict[str, dict] = {}
        for x in ok:
            a = par.setdefault(f"{x['jeu']}:{x['source_question']}", {"n": 0, "B": 0.0, nom: 0.0})
            a["n"] += 1
            a["B"] += pl(x["p_B"], x["issue"])
            a[nom] += pl(x[cle]["p"], x["issue"])
        out[nom] = {"n": len(ok), "par_bloc": {k: {"n": v["n"], "B": round(v["B"] / v["n"], 4),
                                                  nom: round(v[nom] / v["n"], 4)} for k, v in sorted(par.items())},
                    "critere": sr.critere_ombre_b(ok, cle, essai)}
    return out


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
                         "ombre_b_ar": x.get("_b_ar"), "ombre_b_saison": x.get("_b_saison"),
                         "licence": "ForecastBench, Forecasting Research Institute, CC BY-SA 4.0"}
                f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
                f.flush()
                deja.add(x["qid"])
                nouvelles += 1
    r = resumer(lignes_existantes())
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{nouvelles} question(s) ajoutée(s).")
    for nom in ("B_AR", "B_saison"):
        print(f"Critère {nom} :", json.dumps(r[nom]["critere"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--apres", default="2026-07-01")
    a.add_argument("--max", type=int, default=400)
    o = a.parse_args()
    sys.exit(asyncio.run(principal(o.apres, o.max)))
