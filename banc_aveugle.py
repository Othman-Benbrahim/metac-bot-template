"""Banc du jugement aveugle au taux de base : l'indépendance des sources (bot 0.10.227, en ombre).

Décision d'auteur du 2026-11-17 (14 h 16), après la lecture de R. Sinclair, *Thinking and Writing* (CIA, 1984) :
« tout ce qui concerne l'indépendance des sources et de leur appréhension ». Constat de départ : lors de l'erreur du
taux de base ACLED (2026-11-15), le bras A « s'ancrait » sur le B qu'on lui montrait ; Sinclair décrit ce conservatisme
(chaque donnée nouvelle est lue à travers le cadre déjà posé). Si le modèle voit B, son jugement n'est plus une source
indépendante de B : les combiner revient à compter B deux fois.

Sur les questions ACLED « une fois » de ForecastBench (jeux postérieurs au 2026-07-01) qu'AUCUN banc à modèle de langue
n'a lues, une seule recherche bornée avant la date d'information, puis sur les mêmes entrées :
- A_voit    : la consigne du bras A, inchangée (elle montre B et dit « pars du taux de base ») ;
- A_aveugle : la même consigne SANS la ligne du taux de base ni l'instruction d'en partir (la série brute reste :
              c'est une donnée, B est notre lecture de cette donnée) ;
- C_aveugle : combinaison mécanique, logit moyen de A_aveugle et de B à poids égaux (0,5, fixé d'avance, rien
              n'est appris).
Critère principal : C_aveugle contre A_voit (règle d'adoption commune : 100 premières questions, intervalle corrigé
pour le nombre d'essais ouverts). Descriptif : chacun contre B ; distance |A − B| moyenne (l'ancrage se voit comme une
distance plus courte quand le modèle voit B).
Pré-enregistrement : preenregistrements/jugement-aveugle.md. Registre : registre/banc-aveugle.jsonl ; résumé :
registre/banc-aveugle.json. Deux appels gpt-5-mini et une recherche par question.

    python banc_aveugle.py --n 131 --budget 4
"""
from __future__ import annotations

import argparse
import asyncio
import glob
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import alphabet_modeles as am
import alphabet_pipeline as ap
import alphabet_retro as ar
import banc_a as ba
import banc_forecastbench as fb

REGISTRE = Path("registre")
FICHIER = REGISTRE / "banc-aveugle.jsonl"
RESUME = REGISTRE / "banc-aveugle.json"
MODELE = "azure_ai/gpt-5-mini"
VUS = Path("preenregistrements/silence-vus.txt")
POIDS = 0.5                      # fixé avant tout passage


def consigne_aveugle(x: dict, vue: dict | None, releve: list[dict], recherche: str, jeu: str) -> str:
    """La consigne du bras A sans le taux de base ni l'instruction d'en partir ; tout le reste est identique."""
    s = ba.consigne_a(x, vue, releve, recherche, jeu)
    debut = s.index("TAUX DE BASE CALCULÉ PAR LE CODE")
    fin = s.index("DERNIERS POINTS DE LA SÉRIE")
    s = s[:debut] + s[fin:]
    return s.replace("Pars du taux de base, puis ajuste seulement si les données ou les recherches le justifient. ",
                     "Juge d'après les données et les recherches. ")


def lus_par_un_modele() -> set[str]:
    """Questions déjà lues par un banc à modèle de langue (les bancs d'indicateurs et de combinaisons n'en ont pas)."""
    out = set()
    for f in glob.glob(str(REGISTRE / "banc-*.jsonl")):
        if "indicateurs" in f or "aveugle" in f:
            continue
        for l in open(f, encoding="utf-8"):
            try:
                out.add(json.loads(l)["question_id"])
            except (ValueError, KeyError):
                pass
    if VUS.exists():
        out |= {l.strip() for l in VUS.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")}
    return out


def lignes() -> list[dict]:
    if not FICHIER.exists():
        return []
    return [json.loads(l) for l in FICHIER.read_text(encoding="utf-8").splitlines() if l.strip()]


def resumer(ls: list[dict]) -> dict:
    import score_registre as sr
    pl = sr.log_score
    ok = sorted((x for x in ls if x.get("issue") in (0, 1) and x.get("p_voit") is not None
                 and x.get("p_aveugle") is not None and not x.get("exclue")), key=lambda x: x["ordre"])
    out = {"version_bot": ap.VERSION_BOT, "n": len(ok),
           "note": "perte log, plus bas = mieux ; A_voit, A_aveugle et C_aveugle sur les mêmes entrées"}
    if not ok:
        return out
    n = len(ok)
    moy = lambda f: round(sum(pl(f(x), x["issue"]) for x in ok) / n, 4)
    c = lambda x: ba.combiner(x["p_aveugle"], x["p_B"], POIDS)
    out.update({"A_voit": moy(lambda x: x["p_voit"]), "A_aveugle": moy(lambda x: x["p_aveugle"]),
                "C_aveugle": moy(c), "B": moy(lambda x: x["p_B"]),
                "distance_a_B": {"A_voit": round(sum(abs(x["p_voit"] - x["p_B"]) for x in ok) / n, 3),
                                 "A_aveugle": round(sum(abs(x["p_aveugle"] - x["p_B"]) for x in ok) / n, 3)},
                "p_moyenne": {"A_voit": round(sum(x["p_voit"] for x in ok) / n, 3),
                              "A_aveugle": round(sum(x["p_aveugle"] for x in ok) / n, 3),
                              "B": round(sum(x["p_B"] for x in ok) / n, 3),
                              "observe": round(sum(x["issue"] for x in ok) / n, 3)},
                "critere": sr.critere_ombre_b([dict(x, p_B=x["p_voit"], o={"p": c(x)}) for x in ok], "o",
                                              "jugement_aveugle", exclure_vus=False)})
    import audit_b
    out["audit_b"] = audit_b.pour_resume(ls)
    return out


async def principal(n: int, budget: float) -> int:
    from forecasting_tools import MonetaryCostManager
    if not ar.recherche_bornee_disponible():
        print("Il faut une recherche bornable dans le temps (EXA_API_KEY ou TINYFISH_API_KEY). Rien n'est lancé.")
        return 1
    exclus = lus_par_un_modele()
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
        tous += [(r, j, x) for r, x in enumerate(items)
                 if fb.facteur_acled(x["titre"]) == 1.0 and (x["qid"] not in exclus or x["qid"] in deja)]
    tous.sort(key=lambda t: (t[0], t[1]))
    print(f"{len(tous)} questions ACLED « une fois » jamais lues par un modèle, entrelacées.")
    REGISTRE.mkdir(exist_ok=True)
    faites, cumul, pire = 0, 0.0, 0.0
    with FICHIER.open("a", encoding="utf-8") as f:
        for r_, j, x in tous:
            if faites >= n:
                break
            if x["qid"] in deja:
                continue
            if fb.depasse(cumul, pire, budget):
                print(f"Plafond atteint : {cumul:.2f} $. Arrêt.")
                break
            with MonetaryCostManager() as cm:
                vue = await fb.vue_calculee(x, x["_q"], j)
                if not vue or vue.get("frequence") is None:
                    continue
                releve = (x.get("_releve") or {}).get("points") or []
                info = datetime.fromisoformat(j).replace(tzinfo=timezone.utc)
                try:
                    rech = await ar.chercher_avant(x["titre"], info)
                except Exception as e:
                    rech = f"(recherche indisponible : {type(e).__name__})"
                res, exclue = {}, False
                for cle, consigne in (("voit", ba.consigne_a), ("aveugle", consigne_aveugle)):
                    try:
                        r = ap.extraire_json(await am.llm(MODELE, temperature=0.2, timeout=300, allowed_tries=2).invoke(
                            consigne(x, vue, releve, rech, j)))
                        res[f"p_{cle}"] = min(0.99, max(0.01, float(r["p"])))
                        res[f"raison_{cle}"] = str(r.get("raison", ""))[:300]
                        exclue = exclue or bool(r.get("connait_issue"))
                    except Exception as e:
                        res[f"erreur_{cle}"] = f"{type(e).__name__}: {e}"[:200]
                cout = float(cm.current_usage or 0)
            ligne = {"type": "banc_aveugle", "jeu": j, "ordre": [r_, j], "question_id": x["qid"], "source_question": "acled",
                     "version_bot": ap.VERSION_BOT, "titre": x["titre"], "issue": x["issue"], "p_B": float(vue["frequence"]),
                     **res, "exclue": exclue, "modele": MODELE, "cout_usd": round(cout, 4),
                     "licence": "ForecastBench, Forecasting Research Institute, CC BY-SA 4.0"}
            f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
            f.flush()
            deja.add(x["qid"])
            cumul += cout
            pire = max(pire, cout)
            if res.get("p_voit") is not None and res.get("p_aveugle") is not None:
                faites += 1
            print(f"{x['qid'][:55]} : voit {res.get('p_voit')} · aveugle {res.get('p_aveugle')} · "
                  f"B {vue['frequence']:.3f} · issue {x['issue']} · {cout:.4f} $")
    r = resumer(lignes())
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{faites} question(s) ; coût {cumul:.2f} $ (plafond {budget:.2f} $).")
    print(json.dumps(r, ensure_ascii=False, indent=1)[:2500])
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--n", type=int, default=131)
    a.add_argument("--budget", type=float, default=4.0)
    o = a.parse_args()
    sys.exit(asyncio.run(principal(o.n, o.budget)))
