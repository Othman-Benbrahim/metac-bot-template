"""Indicateurs placés là où ils ont un sens, sur questions de conflits FRAÎCHES (0.10.129, décision d'auteur du
2026-11-15 : « la bonne source, au bon endroit »). AUCUN modèle de langue, aucun coût.

Questions : ACLED de ForecastBench, forme « une fois » (pas « dix fois », réglée par B corrigé), jeux postérieurs au
2026-07-01, absentes de preenregistrements/silence-vus.txt. Ordre entrelacé fixé d'avance (rang SHA-1 dans le jeu, puis
jeu). Pour chacune : B corrigé (code), indicateurs mesurés avant la date (banc_indicateurs), puis le modèle FIGÉ du
pré-enregistrement preenregistrements/indicateurs-pertinents.md :

    logit(p) = logit(B) − 0,4151·z_fcdo·[violence] − 0,4837·z_pluie·[manifestations, émeutes] + 0,4695·z_pluie·[violence]

z = (valeur − moyenne) / écart-type des 76 questions d'apprentissage ; indicateur non mesuré : z = 0.
Registre : registre/banc-indicateurs-frais.jsonl ; résumé et critère : registre/banc-indicateurs-frais.json.

    python banc_indicateurs_frais.py [--max 250]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import date
from pathlib import Path

import httpx

import alphabet_pipeline as ap
import banc_a as ba
import banc_forecastbench as fb
import banc_indicateurs as bi

REGISTRE = Path("registre")
FICHIER = REGISTRE / "banc-indicateurs-frais.jsonl"
RESUME = REGISTRE / "banc-indicateurs-frais.json"
VUS = Path("preenregistrements/silence-vus.txt")

# figés le 2026-11-15 sur les 76 questions « une fois » du banc des indicateurs (preenregistrements/indicateurs-pertinents.md)
NORMALISATION = {"fcdo": (0.13432835820895522, 0.34100476593420487), "pluie": (0.27020096169782704, 1.3246231102772206)}
COEFFICIENTS = {("fcdo", "violence"): -0.4151, ("pluie", "mobilisation"): -0.4837,
                ("pluie", "violence"): 0.4695}   # amendement du 2026-11-15 (13 h 40), avant tout passage
FAMILLES = {"Battles": "violence", "Explosions/Remote violence": "violence", "Violence against civilians": "violence",
            "fatalities": "violence", "Protests": "mobilisation", "Riots": "mobilisation",
            "Strategic developments": "strategique"}


def famille(titre: str) -> str:
    m = re.search(r"'([^']+)'", titre)
    return FAMILLES.get(m.group(1) if m else "fatalities", "autre")


def z(ind: dict, k: str) -> float:
    if not (ind.get("presents") or {}).get(k):
        return 0.0
    moy, et = NORMALISATION[k]
    return (float(ind[k]) - moy) / et


def p_pertinent(p_b: float, fam: str, ind: dict) -> float:
    return ba.sigmoide(ba.logit(p_b) + sum(c * z(ind, k) for (k, g), c in COEFFICIENTS.items() if g == fam))


def vus() -> set[str]:
    if not VUS.exists():
        return set()
    return {l.strip() for l in VUS.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")}


def lignes() -> list[dict]:
    if not FICHIER.exists():
        return []
    return [json.loads(l) for l in FICHIER.read_text(encoding="utf-8").splitlines() if l.strip()]


def resumer(ls: list[dict]) -> dict:
    import score_registre as sr
    pl = sr.log_score
    ok = sorted((x for x in ls if x.get("issue") in (0, 1) and x.get("p_B") is not None), key=lambda x: x["ordre"])
    out = {"version_bot": ap.VERSION_BOT, "n": len(ok), "note": "perte log, plus bas = mieux ; aucun modèle de langue"}
    if not ok:
        return out
    n = len(ok)
    out.update({"B": round(sum(pl(x["p_B"], x["issue"]) for x in ok) / n, 4),
                "pertinent": round(sum(pl(x["p_pertinent"], x["issue"]) for x in ok) / n, 4),
                "touchees": sum(1 for x in ok if abs(x["p_pertinent"] - x["p_B"]) > 1e-9),
                "par_famille": {g: {"n": len(s), "oui": sum(x["issue"] for x in s),
                                    "B": round(sum(pl(x["p_B"], x["issue"]) for x in s) / len(s), 4),
                                    "pertinent": round(sum(pl(x["p_pertinent"], x["issue"]) for x in s) / len(s), 4)}
                                for g in sorted({x["famille"] for x in ok}) for s in [[x for x in ok if x["famille"] == g]]},
                "critere": sr.critere_ombre_b([dict(x, o={"p": x["p_pertinent"]}) for x in ok], "o",
                                              "indicateurs_pertinents", exclure_vus=False)})
    import audit_b                       # 0.10.130 : garde-fou sur B, par forme de question
    out["audit_b"] = audit_b.pour_resume(ls)
    return out


async def principal(max_q: int) -> int:
    exclus = vus()
    deja = {x["question_id"] for x in lignes()}
    jeux = sorted(fb.jeux_candidats(date.today(), date.fromisoformat(ba.APRES), n_max=26))
    tous = []
    for j in jeux:
        try:
            qs = await fb._json(f"{fb.DEPOT}/question_sets/{j}-llm.json")
            rs = await fb._json(f"{fb.DEPOT}/resolution_sets/{j}_resolution_set.json")
        except Exception as e:
            print(f"Jeu {j} indisponible : {type(e).__name__}")
            continue
        items = sorted((fb.construire(i, j) for i in fb.apparier(qs, rs, ("acled",))), key=lambda x: ba.rang(x["qid"]))
        items = [x for x in items if fb.facteur_acled(x["titre"]) == 1.0]
        tous += [(r, j, x) for r, x in enumerate(items) if x["qid"] not in exclus]
    tous.sort(key=lambda t: (t[0], t[1]))
    print(f"{len(tous)} questions ACLED « une fois » jamais lues, entrelacées.")
    REGISTRE.mkdir(exist_ok=True)
    faites = 0
    cache_pays, cache_ind = {}, {}
    async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers=bi.UA) as c:
        with FICHIER.open("a", encoding="utf-8") as fo:
            for r_, j, x in tous:
                if faites >= max_q:
                    break
                if x["qid"] in deja:
                    continue
                vue = await fb.vue_calculee(x, x["_q"], j)
                nom = bi.pays_de(x["titre"])
                if not vue or vue.get("frequence") is None or not nom:
                    continue
                f = await bi.fiche_pays(c, nom, cache_pays)
                if (nom, j) not in cache_ind:
                    cache_ind[(nom, j)] = await bi.indicateurs(c, f, date.fromisoformat(j))
                ind = cache_ind[(nom, j)]
                fam = famille(x["titre"])
                p_b = float(vue["frequence"])
                fo.write(json.dumps({"type": "banc_indicateurs_frais", "jeu": j, "ordre": [r_, j], "question_id": x["qid"],
                                     "titre": x["titre"], "source_question": "acled", "pays": nom, "famille": fam, "version_bot": ap.VERSION_BOT, "issue": x["issue"],
                                     "p_B": p_b, "p_pertinent": p_pertinent(p_b, fam, ind), **ind,
                                     "licence": "ForecastBench, Forecasting Research Institute, CC BY-SA 4.0"},
                                    ensure_ascii=False) + "\n")
                fo.flush()
                faites += 1
                print(f"{nom[:22]:22s} {j} {fam:12s} B {p_b:.3f} → {p_pertinent(p_b, fam, ind):.3f} · issue {x['issue']}")
    for h, ds in sorted(bi.LENTEURS.items()):
        print(f"{h} : {len(ds)} appels, moyenne {sum(ds) / len(ds):.1f} s, {sum(d >= 19.5 for d in ds)} délais dépassés")
    r = resumer(lignes())
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1)[:2500])
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--max", type=int, default=250)
    o = a.parse_args()
    sys.exit(asyncio.run(principal(o.max)))
