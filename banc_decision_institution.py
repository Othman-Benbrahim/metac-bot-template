"""Banc rétrospectif de l'outil « décision d'institution » (preenregistrements/decision-institution.md, 2026-11-21).

Même mécanique que le banc de M (banc_jugement_alphabet.py) : questions de jugement résolues de ForecastBench, recherche
bornée avant la date du jeu et GELÉE (cache partagé avec M), taux de départ des semblables. Un appel gpt-5-mini par
question, qui relève des faits ; le code combine. Coupe-circuit après 20 questions.

    python banc_decision_institution.py --budget 3
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import alphabet_modeles as am
import alphabet_pipeline as ap
import alphabet_retro as ar
import banc_forecastbench as fb
import banc_jugement as bj
import banc_jugement_alphabet as bja
import decision_institution as di
import garde_injection as gi
import trace_recherche as tr

REGISTRE = Path("registre")
FICHIER = REGISTRE / "banc-decision-institution.jsonl"
RESUME = REGISTRE / "banc-decision-institution.json"
MODELE = bja.MODELE
COUPE_APRES, COUPE_PART = 20, 0.5


def candidates() -> list[dict]:
    """Une ligne par question : le jeu déjà cherché pour M s'il existe (recherche gelée réutilisée), sinon le premier
    par empreinte."""
    xs = bj.cohorte_complete([json.loads(l) for l in bj.REGISTRE.read_text(encoding="utf-8").splitlines() if l.strip()])
    bj.calculer(xs)
    deja_m = {x["question_id"] for x in bja.lignes()}
    par: dict[tuple, list] = {}
    for x in xs:
        if di.est_decision(x["titre"], x["forme"]):
            par.setdefault((x["source"], x["id"]), []).append(x)
    out = []
    for v in par.values():
        v = sorted(v, key=lambda x: (f'{x["source"]}:{x["id"]}:{x["jeu"]}' not in deja_m, bja.rang(x)))
        out.append(v[0])
    return sorted(out, key=bja.rang)


def lignes() -> list[dict]:
    if not FICHIER.exists():
        return []
    return [json.loads(l) for l in FICHIER.read_text(encoding="utf-8").splitlines() if l.strip()]


def resumer(ls: list[dict]) -> dict:
    import score_registre as sr
    ok = [x for x in ls if x.get("issue") in (0, 1) and x.get("x") is not None and not x.get("exclue")]
    out = {"version_bot": ap.VERSION_BOT, "n": len(ok), "note": "perte log, plus bas = mieux ; outil en validation croisée"}
    if len(ok) < 20:
        return out
    p_cv = di.validation_croisee(ok)
    pl = sr.log_score
    for x, p in zip(ok, p_cv):
        x["p_outil"] = p
    moy = lambda xs, k: round(sum(pl(x[k], x["issue"]) for x in xs) / len(xs), 4) if xs else None
    fed = [x for x in ok if "fed" in x["titre"].lower() or "federal reserve" in x["titre"].lower()]
    hors = [x for x in ok if x not in fed]
    out.update({
        "oui": round(sum(x["issue"] for x in ok) / len(ok), 3),
        "faits_utilisables": round(sum(di.utilisable(x["x"]) for x in ok) / len(ok), 3),
        "semblables": moy(ok, "p_S"), "outil": moy(ok, "p_outil"),
        "fed": {"n": len(fed), "semblables": moy(fed, "p_S"), "outil": moy(fed, "p_outil")},
        "hors_fed": {"n": len(hors), "semblables": moy(hors, "p_S"), "outil": moy(hors, "p_outil")},
        "coefficients_sur_tout": di.coefficients(ok),
        "critere": sr.critere_ombre_b([dict(x, p_B=x["p_S"], o={"p": x["p_outil"]}) for x in ok], "o",
                                      "decision_institution", exclure_vus=False, bloc_par="question", tout_juger=True)})
    m = {x["question_id"]: x for x in bja.lignes() if x.get("p_M") is not None and not x.get("exclue")}
    com = [dict(x, p_M=m[x["question_id"]]["p_M"]) for x in ok if x["question_id"] in m]
    out["avec_M"] = {"n": len(com), "semblables": moy(com, "p_S"), "outil": moy(com, "p_outil"), "M": moy(com, "p_M")}
    return out


async def principal(budget: float) -> int:
    from forecasting_tools import MonetaryCostManager
    if not ar.recherche_bornee_disponible():
        print("Il faut une recherche bornable dans le temps (EXA_API_KEY ou TINYFISH_API_KEY). Rien n'est lancé.")
        return 1
    deja = {x["question_id"] for x in lignes()}
    cand = candidates()
    print(f"{len(cand)} questions de décision d'institution (une par question).")
    textes: dict[str, dict] = {}
    REGISTRE.mkdir(exist_ok=True)
    faites, vides, cumul, pire = 0, 0, 0.0, 0.0
    with FICHIER.open("a", encoding="utf-8") as f:
        for x in cand:
            qid = f'{x["source"]}:{x["id"]}:{x["jeu"]}'
            if qid in deja:
                continue
            if fb.depasse(cumul, pire, budget):
                print(f"Plafond atteint : {cumul:.2f} $. Arrêt.")
                break
            if faites == COUPE_APRES and vides > COUPE_PART * faites:
                print(f"COUPE-CIRCUIT : {vides} questions sur {faites} sans fait utilisable. Arrêt (préenregistré).")
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
            with MonetaryCostManager() as cm:
                info = datetime.fromisoformat(x["jeu"]).replace(tzinfo=timezone.utc)
                rech, du_cache = await tr.chercher_fige(qid, x["titre"], info, ar.chercher_avant)
                res, exclue = {"recherche": {**tr.tracer(rech, x["jeu"]), "cache": du_cache}}, False
                try:
                    r = ap.extraire_json(await am.llm(MODELE, temperature=0.2, timeout=300, allowed_tries=2).invoke(
                        di.consigne(q, x["jeu"], rech, gi.bloc)))
                    res["faits"] = {k: r.get(k) for k in ("etape_avant_echeance", "date_etape", "regle", "soutien",
                                                         "confirmation", "deja_decide", "faits")}
                    res["x"] = di.indicateurs(r)
                    exclue = bool(r.get("connait_issue"))
                except Exception as e:
                    res["erreur"] = f"{type(e).__name__}: {e}"[:200]
                cout = float(cm.current_usage or 0)
            ligne = {"type": "banc_decision_institution", "jeu": x["jeu"], "question_id": qid, "source_question": x["source"],
                     "version_bot": ap.VERSION_BOT, "titre": x["titre"], "forme": x["forme"], "issue": x["issue"],
                     "p_S": float(x["p_S"]), **res, "exclue": exclue, "modele": MODELE, "cout_usd": round(cout, 4),
                     "licence": "ForecastBench, Forecasting Research Institute, CC BY-SA 4.0"}
            f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
            f.flush()
            deja.add(qid)
            cumul += cout
            pire = max(pire, cout)
            faites += 1
            vides += 0 if (res.get("x") and di.utilisable(res["x"])) else 1
            print(f"{qid[:50]} : {res.get('x')} · S {x['p_S']:.3f} · issue {x['issue']} · {cout:.4f} $", flush=True)
    r = resumer(lignes())
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{faites} question(s) ; coût {cumul:.2f} $ (plafond {budget:.2f} $).")
    print(json.dumps(r, ensure_ascii=False, indent=1)[:3000])
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--budget", type=float, default=3.0)
    o = a.parse_args()
    sys.exit(asyncio.run(principal(o.budget)))
