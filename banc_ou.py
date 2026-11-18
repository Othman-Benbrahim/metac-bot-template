"""Banc du retour vers la moyenne (Ornstein-Uhlenbeck) sur les séries (0.10.283, décision d'auteur du 2026-11-18, 19 h 08,
« on teste, c'est gratuit »). Calqué sur banc_bn.py (classe de référence pondérée, 0.10.233).
AUCUN modèle de langue, aucun coût. Autre domaine que GDELT, questions RÉELLES : pour chaque question de série
ForecastBench résolue (FRED, DBnomics), jeux postérieurs au 2026-07-01 : B (comptage des hausses sur 5 ans) et B_OU
B_OU (retour vers la moyenne autour d'une tendance linéaire ; règle dans banc_forecastbench.b_ou), calculés sur la série strictement avant la date d'information.

Critère : celui des ombres de B (score_registre.critere_ombre_b, essai b_ou) ; préenregistrement
preenregistrements/b-ou.md. Registre : registre/banc-ou.jsonl ; résumé : registre/banc-ou.json.

    python banc_ou.py [--max 1000]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

import alphabet_pipeline as ap
import banc_a as ba
import banc_forecastbench as fb

REGISTRE = Path("registre")
FICHIER = REGISTRE / "banc-ou.jsonl"
RESUME = REGISTRE / "banc-ou.json"
SOURCES = ("fred", "dbnomics")
MOTIF = "option-adjusted spread"


def lignes() -> list[dict]:
    if not FICHIER.exists():
        return []
    return [json.loads(l) for l in FICHIER.read_text(encoding="utf-8").splitlines() if l.strip()]


def _bic(x: dict) -> bool:
    return float((x.get("ombre_b_ou") or {}).get("bic_ecart") or 0.0) >= 2.0


def resumer(ls: list[dict]) -> dict:
    import audit_b
    import score_registre as sr
    pl = sr.log_score
    ok = sorted((x for x in ls if x.get("issue") in (0, 1) and x.get("p_B") is not None
                 and isinstance(x.get("ombre_b_ou"), dict) and x["ombre_b_ou"].get("p") is not None),
                key=lambda x: x["ordre"])
    jug = ok                                  # aucune forme exclue
    mot = [x for x in ok if MOTIF in x.get("titre", "")]
    moy = lambda s, f: round(sum(pl(f(x), x["issue"]) for x in s) / len(s), 4) if s else None
    out = {"version_bot": ap.VERSION_BOT, "questions": len(ls), "appliquees": len(ok),
           "note": "perte log, plus bas = mieux ; aucun modèle de langue ; B_OU : retour vers la moyenne autour d'une tendance linéaire",
           "toutes": {"n": len(jug), "B": moy(jug, lambda x: x["p_B"]), "B_OU": moy(jug, lambda x: x["ombre_b_ou"]["p"])},
           "ecarts_de_credit_descriptif": {"n": len(mot), "oui": sum(x["issue"] for x in mot),
                                           "B": moy(mot, lambda x: x["p_B"]), "B_OU": moy(mot, lambda x: x["ombre_b_ou"]["p"])},
           "par_source": {s: {"n": len(v), "B": moy(v, lambda x: x["p_B"]), "B_OU": moy(v, lambda x: x["ombre_b_ou"]["p"])}
                          for s in SOURCES for v in [[x for x in jug if x["source_question"] == s]] if v},
           "critere": sr.critere_ombre_b(jug, "ombre_b_ou", "b_ou", exclure_vus=False),
           # 0.10.285 : variante AFFICHÉE, non jugée (amendement de b-ou.md) : le rappel seulement si le BIC le préfère
           # d'au moins 2 points sur l'historique de la série ; sinon B
           "variante_bic": {"n": len(jug), "rappel_choisi": sum(1 for x in jug if _bic(x)),
                            "B": moy(jug, lambda x: x["p_B"]), "B_OU": moy(jug, lambda x: x["ombre_b_ou"]["p"]),
                            "B_OU_si_BIC": moy(jug, lambda x: x["ombre_b_ou"]["p"] if _bic(x) else x["p_B"]),
                            "par_source": {s: {"n": len(v), "rappel_choisi": sum(1 for x in v if _bic(x)),
                                               "B": moy(v, lambda x: x["p_B"]),
                                               "B_OU_si_BIC": moy(v, lambda x: x["ombre_b_ou"]["p"] if _bic(x) else x["p_B"])}
                                           for s in SOURCES for v in [[x for x in jug if x["source_question"] == s]] if v}},
           "audit_b": audit_b.pour_resume(ls)}
    return out


async def principal(apres: str, max_q: int) -> int:
    deja = {x["question_id"] for x in lignes()}
    jeux = sorted(fb.jeux_candidats(date.today(), date.fromisoformat(apres), n_max=26))
    tous = []
    for j in jeux:
        try:
            qs = await fb._json(f"{fb.DEPOT}/question_sets/{j}-llm.json")
            rs = await fb._json(f"{fb.DEPOT}/resolution_sets/{j}_resolution_set.json")
        except Exception as e:
            print(f"Jeu {j} indisponible : {type(e).__name__}")
            continue
        items = sorted((fb.construire(i, j) for i in fb.apparier(qs, rs, SOURCES)), key=lambda x: ba.rang(x["qid"]))
        tous += [(r, j, x) for r, x in enumerate(items)]
    tous.sort(key=lambda t: (t[0], t[1]))
    print(f"{len(tous)} questions de séries, entrelacées entre {len(jeux)} jeux.")
    REGISTRE.mkdir(exist_ok=True)
    faites = 0
    with FICHIER.open("a", encoding="utf-8") as f:
        for r_, j, x in tous:
            if faites >= max_q:
                break
            if x["qid"] in deja:
                continue
            try:
                vue = await fb.vue_calculee(x, x["_q"], j)
            except Exception as e:
                vue, x["_b_ou"] = None, {"erreur": f"{type(e).__name__}: {e}"[:200]}
            ligne = {"type": "banc_ou", "jeu": j, "ordre": [r_, j], "source_question": x["source"], "question_id": x["qid"],
                     "version_bot": ap.VERSION_BOT, "titre": x["titre"], "issue": x["issue"],
                     "p_B": (vue or {}).get("frequence"), "calcul_B": (vue or {}).get("calcul"),
                     "ombre_b_ou": x.get("_b_ou"),
                     "licence": "ForecastBench, Forecasting Research Institute, CC BY-SA 4.0"}
            f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
            f.flush()
            deja.add(x["qid"])
            faites += 1
            t = (x.get("_b_ou") or {}).get("p")
            print(f"{x['qid'][:60]} : B {ligne['p_B']} · B_OU {t} · issue {x['issue']}")
    r = resumer(lignes())
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{faites} question(s) ajoutée(s).")
    print(json.dumps(r, ensure_ascii=False, indent=1)[:3000])
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--apres", default="2026-07-01")
    a.add_argument("--max", type=int, default=1000)
    o = a.parse_args()
    sys.exit(asyncio.run(principal(o.apres, o.max)))
