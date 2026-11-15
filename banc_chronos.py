"""Banc du taux de base par modèle de fondation, Chronos-2 (0.10.132, décision d'auteur du 2026-11-15, d'après
Kaljevic, Arzola et Zhang, arXiv 2610.07232). AUCUN modèle de langue, aucun coût : modèle ouvert sur processeur.

Pour chaque question de série ForecastBench résolue (FRED, DBnomics), jeux postérieurs au 2026-07-01 : B (comptage
des hausses) et B Chronos (probabilité de hausse lue sur la distribution prévue par Chronos-2), sur la série strictement
avant la date d'information. Règle et critère : preenregistrements/b-chronos.md.
Registre : registre/banc-chronos.jsonl ; résumé : registre/banc-chronos.json.

    python banc_chronos.py [--max 1000]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
from datetime import date
from pathlib import Path

import alphabet_pipeline as ap
import banc_a as ba
import banc_forecastbench as fb

REGISTRE = Path("registre")
FICHIER = REGISTRE / "banc-chronos.jsonl"
RESUME = REGISTRE / "banc-chronos.json"
SOURCES = ("fred", "dbnomics")
MODELE = "amazon/chronos-2"
CONTEXTE_MAX = 1024
_PIPE = None


def repartition(x: float, niveaux: list[float], valeurs: list[float]) -> float:
    """F(x) interpolée linéairement entre les quantiles (valeurs croissantes), bornée aux niveaux extrêmes."""
    vs = sorted(valeurs)
    if x <= vs[0]:
        return niveaux[0]
    if x >= vs[-1]:
        return niveaux[-1]
    for (q0, v0), (q1, v1) in zip(zip(niveaux, vs), zip(niveaux[1:], vs[1:])):
        if v0 <= x <= v1:
            return q0 if v1 == v0 else q0 + (q1 - q0) * (x - v0) / (v1 - v0)
    return niveaux[-1]


def pas_horizon(dates: list[date], h: int) -> int:
    ecarts = [(b - a).days for a, b in zip(dates, dates[1:])]
    pas = statistics.median(ecarts) if ecarts else 1
    return max(1, round(h / (pas or 1)))


def pipeline():
    global _PIPE
    if _PIPE is None:
        from chronos import BaseChronosPipeline
        _PIPE = BaseChronosPipeline.from_pretrained(MODELE, device_map="cpu")
    return _PIPE


def b_chronos(points: list[dict], h: int, avant: date, p_egal: float, pipe=None) -> dict | None:
    import numpy as np
    pts = sorted((date.fromisoformat(p["date"][:10]), float(p["valeur"])) for p in points
                 if p.get("date") and p.get("valeur") is not None and p["date"][:10] < avant.isoformat())
    pts = pts[-CONTEXTE_MAX:]
    if len(pts) < 30 or h <= 0:
        return None
    k = pas_horizon([p[0] for p in pts], h)
    pipe = pipe or pipeline()
    niveaux = list(pipe.quantiles)
    qs, _ = pipe.predict_quantiles([np.array([p[1] for p in pts], dtype="float32")], prediction_length=k,
                                   quantile_levels=niveaux)
    valeurs = [float(v) for v in qs[0][0, k - 1, :].tolist()]
    dernier = pts[-1][1]
    p_haut = 1 - repartition(dernier, niveaux, valeurs)
    p = max(0.001, min(0.999, (1 - p_egal) * p_haut))
    return {"p": p, "k": k, "points": len(pts), "p_haut_continu": round(p_haut, 4), "part_sans_changement": round(p_egal, 4),
            "mediane": valeurs[len(valeurs) // 2], "dernier": dernier}


def lignes() -> list[dict]:
    if not FICHIER.exists():
        return []
    return [json.loads(l) for l in FICHIER.read_text(encoding="utf-8").splitlines() if l.strip()]


def resumer(ls: list[dict]) -> dict:
    import audit_b
    import score_registre as sr
    pl = sr.log_score
    ok = sorted((x for x in ls if x.get("issue") in (0, 1) and x.get("p_B") is not None
                 and isinstance(x.get("ombre_b_chronos"), dict) and x["ombre_b_chronos"].get("p") is not None),
                key=lambda x: x["ordre"])
    moy = lambda s, f: round(sum(pl(f(x), x["issue"]) for x in s) / len(s), 4) if s else None
    comb = lambda x: ba.combiner(x["ombre_b_chronos"]["p"], x["p_B"])
    return {"version_bot": ap.VERSION_BOT, "questions": len(ls), "appliquees": len(ok),
            "note": "perte log, plus bas = mieux ; aucun modèle de langue",
            "B": moy(ok, lambda x: x["p_B"]), "B_chronos": moy(ok, lambda x: x["ombre_b_chronos"]["p"]),
            "moitie_B_moitie_chronos_descriptif": moy(ok, comb),
            "par_source": {s: {"n": len(v), "B": moy(v, lambda x: x["p_B"]), "B_chronos": moy(v, lambda x: x["ombre_b_chronos"]["p"])}
                           for s in SOURCES for v in [[x for x in ok if x["source_question"] == s]] if v},
            "critere": sr.critere_ombre_b(ok, "ombre_b_chronos", "b_chronos", exclure_vus=False),
            "audit_b": audit_b.pour_resume(ls)}


async def principal(apres: str, max_q: int) -> int:
    try:                                   # vérification au démarrage : sans modèle, rien n'est lancé
        import numpy as np
        essai = b_chronos([{"date": f"2026-01-{i + 1:02d}", "valeur": float(i % 7)} for i in range(30)], 3,
                          date(2026, 2, 1), 0.0)
        print(f"Chronos-2 chargé ({MODELE}) ; essai : {essai['p']:.3f}")
    except Exception as e:
        print(f"Chronos-2 indisponible : {type(e).__name__}: {e}. Rien n'est lancé.")
        return 1
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
            except Exception:
                vue = None
            ch = None
            if vue and vue.get("frequence") is not None:
                h = (date.fromisoformat(x["resolution"]) - date.fromisoformat(j)).days
                p_egal = float((x.get("_b_ar") or {}).get("part_sans_changement") or 0.0)
                try:
                    ch = b_chronos((x.get("_releve") or {}).get("points") or [], h, date.fromisoformat(j), p_egal)
                except Exception as e:
                    ch = {"erreur": f"{type(e).__name__}: {e}"[:200]}
            ligne = {"type": "banc_chronos", "jeu": j, "ordre": [r_, j], "source_question": x["source"],
                     "question_id": x["qid"], "version_bot": ap.VERSION_BOT, "titre": x["titre"], "issue": x["issue"],
                     "p_B": (vue or {}).get("frequence"), "ombre_b_chronos": ch, "modele": MODELE,
                     "licence": "ForecastBench, Forecasting Research Institute, CC BY-SA 4.0"}
            f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
            f.flush()
            deja.add(x["qid"])
            faites += 1
            print(f"{x['qid'][:60]} : B {ligne['p_B']} · Chronos {(ch or {}).get('p')} · issue {x['issue']}")
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
