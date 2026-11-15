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


VERSION_REGIMES = (0, 10, 113)


def proprietes(points: list[dict], avant: date, b_ar: dict | None) -> dict:
    """0.10.113 (preenregistrements/regimes-causaux.md) : propriétés du régime causal, mesurées AVANT la date.
    - saisonnalité : moyennes mensuelles sur 10 ans, pas d'un mois au suivant, part de variance expliquée par le mois
      (règle du bot 0.10.32 : au moins 3 pas par mois, R² ≥ 0,2 et F ≥ 2,5) ;
    - inertie : φ de l'AR(1) sur les différences (celui de B_AR) hors de la bande de Bartlett ±2/√n ;
    - entropie de permutation normalisée (Bandt et Pompe, ordre 3)."""
    import math
    from datetime import timedelta
    import alphabet_compte as ac
    import banc_o as bo
    pts = sorted((date.fromisoformat(p["date"][:10]), float(p["valeur"])) for p in points
                 if p.get("date") and p.get("valeur") is not None and p["date"][:10] < avant.isoformat())
    mois: dict[tuple, list[float]] = {}
    for d, v in pts:
        if d >= avant - timedelta(days=3653):
            mois.setdefault((d.year, d.month), []).append(v)
    cles = sorted(mois)
    moy = [sum(mois[k]) / len(mois[k]) for k in cles]
    saison = None
    if len(cles) >= 37:
        dates = [date(y, m, 1) for y, m in cles]
        incr = [b - a for a, b in zip(moy, moy[1:])]
        saison = ac._saison(dates, incr, list(range(len(incr))), 12)
    n5 = len([p for p in pts if p[0] >= avant - timedelta(days=1826)])
    phi = (b_ar or {}).get("phi")
    inertie = phi is not None and n5 > 30 and abs(phi) > 2 / math.sqrt(n5)
    ent = bo.entropie_permutation([p for p in pts if p[0] >= avant - timedelta(days=1826)])
    return {"saison_forte": saison is not None, "r2_saison": round(saison["r2"], 3) if saison else None,
            "phi": phi, "inertie_forte": bool(inertie), "entropie": round(ent, 4) if ent is not None else None}


def aiguiller(prop: dict, p_b: float | None, b_ar: dict | None, b_saison: dict | None) -> tuple[str, float | None]:
    """Règle fixée d'avance : saisonnalité forte → B saisonnier ; sinon inertie forte → B autorégressif ; sinon B."""
    if prop.get("saison_forte") and (b_saison or {}).get("p") is not None:
        return "B_saison", b_saison["p"]
    if prop.get("inertie_forte") and (b_ar or {}).get("p") is not None:
        return "B_AR", b_ar["p"]
    return "B", p_b


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
    # 0.10.113 : aiguillage par régime causal, sur les questions NOUVELLES (version ≥ 0.10.113), ordre entrelacé
    import hashlib
    nv = [x for x in lignes if x.get("p_regime") is not None and x.get("p_B") is not None and x.get("issue") in (0, 1)
          and tuple(int(t) for t in str(x.get("version_bot", "0")).split(".")) >= VERSION_REGIMES]
    rang: dict[str, int] = {}
    for j in sorted({x["jeu"] for x in nv}):
        for r_, x in enumerate(sorted((x for x in nv if x["jeu"] == j),
                                      key=lambda x: hashlib.sha1(x["question_id"].encode()).hexdigest())):
            rang[x["question_id"]] = r_
    nv.sort(key=lambda x: (rang[x["question_id"]], x["jeu"]))
    if nv:
        n_ = len(nv)
        out["regimes"] = {"n": n_, "choix": {k: sum(x["aiguillage_regime"] == k for x in nv) for k in ("B", "B_AR", "B_saison")},
                          "B": round(sum(pl(x["p_B"], x["issue"]) for x in nv) / n_, 4),
                          "aiguillage": round(sum(pl(x["p_regime"], x["issue"]) for x in nv) / n_, 4),
                          "critere": sr.critere_ombre_b([dict(x, o={"p": x["p_regime"]}) for x in nv], "o", "regimes_causaux")}
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
                try:
                    prop = proprietes((x.get("_releve") or {}).get("points") or [], date.fromisoformat(j), x.get("_b_ar"))
                except Exception as e:
                    prop = {"erreur": f"{type(e).__name__}: {e}"[:200]}
                choix, p_aig = aiguiller(prop, (vue or {}).get("frequence"), x.get("_b_ar"), x.get("_b_saison"))
                ligne = {"type": "banc_b", "jeu": j, "source_question": x["source"], "question_id": x["qid"],
                         "proprietes": prop, "aiguillage_regime": choix, "p_regime": p_aig,
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
