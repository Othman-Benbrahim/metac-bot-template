"""Banc du bras A (0.10.106, décision d'auteur du 2026-11-15 : jouer sur les marges réelles, A et sa combinaison avec
B). Pour chaque question de série ForecastBench déjà résolue (FRED, DBnomics, ACLED), postérieure aux connaissances
des modèles : B par le code (comme au banc), puis le jugement du modèle A, qui voit LES MÊMES DONNÉES que B (taux de base
et son calcul, derniers points de la série strictement avant la date d'information) et une recherche bornée à cette date.
Pas de lecture de l'alphabet. Registre à part : registre/banc-a.jsonl ; résumé et critère : registre/banc-a.json.

Pré-enregistrement : preenregistrements/a-plus-b.md (commité avant tout passage). Combinaison fixée d'avance :
logit(AB) = ½·logit(A) + ½·logit(B). Ordre des questions (0.10.107, amendement du 2026-11-15) : entrelacé entre les
jeux, rang de la question dans son jeu selon l'empreinte SHA-1 de son identifiant, puis jeu ; seules les lignes à partir
de la version 0.10.107 comptent pour le critère.

    python banc_a.py --n 10 --budget 3
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import alphabet_modeles as am
import alphabet_pipeline as ap
import alphabet_retro as ar
import banc_forecastbench as fb

REGISTRE = Path("registre")
FICHIER = REGISTRE / "banc-a.jsonl"
RESUME = REGISTRE / "banc-a.json"
SOURCES = ("fred", "dbnomics", "acled")
APRES = "2026-07-01"          # jeux postérieurs aux connaissances de gpt-5-mini et de Claude Haiku 4.5
POIDS_A = 0.5                 # fixé avant tout passage (pré-enregistrement)
JEUX_VUS = {"2026-09-27", "2026-10-11", "2026-10-25"}   # vus par le banc de l'alphabet


def logit(p: float) -> float:
    p = min(max(p, 1e-3), 1 - 1e-3)
    return math.log(p / (1 - p))


def sigmoide(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def combiner(p_a: float, p_b: float, poids: float = POIDS_A) -> float:
    return sigmoide(poids * logit(p_a) + (1 - poids) * logit(p_b))


def consigne_a(x: dict, vue: dict | None, releve: list[dict], recherche: str, jeu: str) -> str:
    pts = "\n".join(f"{p['date'][:10]} : {p['valeur']}" for p in releve[-30:]) or "(aucun relevé)"
    base = (f"{vue['frequence']:.3f} — {vue.get('classe_de_reference')} ; calcul : {vue.get('calcul')}"
            if vue and vue.get("frequence") is not None else "(non calculé)")
    return f"""Tu es un prévisionniste. Nous sommes le {jeu}. Donne la probabilité que la réponse soit OUI.

QUESTION : {x['titre']}
CRITÈRES DE RÉSOLUTION : {x['criteres']}
CONTEXTE : {x['contexte'][:3000]}

TAUX DE BASE CALCULÉ PAR LE CODE : {base}
DERNIERS POINTS DE LA SÉRIE (avant le {jeu}) :
{pts}

RÉSULTATS DE RECHERCHE (antérieurs au {jeu}) :
{recherche[:6000] or "(aucun)"}

Pars du taux de base, puis ajuste seulement si les données ou les recherches le justifient. Si tu connais déjà l'issue
réelle de cette question (elle est passée pour toi), dis-le honnêtement.
Rends UNIQUEMENT un objet JSON : {{"p": nombre entre 0,01 et 0,99, "raison": "une phrase", "connait_issue": true ou false}}"""


VERSION_CRITERE = (0, 10, 107)


def rang(qid: str) -> str:
    return hashlib.sha1(qid.encode()).hexdigest()


def version(x: dict) -> tuple:
    try:
        return tuple(int(t) for t in str(x.get("version_bot", "0")).split("."))
    except ValueError:
        return (0,)


def lignes() -> list[dict]:
    if not FICHIER.exists():
        return []
    return [json.loads(l) for l in FICHIER.read_text(encoding="utf-8").splitlines() if l.strip()]


def resumer(ls: list[dict]) -> dict:
    import score_registre as sr
    out = {"version_bot": ap.VERSION_BOT, "note": "perte log, plus bas = mieux ; une série par jeu de modèles"}
    par: dict[str, list[dict]] = {}
    for x in sorted(ls, key=lambda x: (x.get("ordre") or [10 ** 6, x["jeu"]])):
        if (x.get("issue") in (0, 1) and x.get("p_A") is not None and x.get("p_B") is not None and not x.get("exclue")
                and version(x) >= VERSION_CRITERE):
            par.setdefault(x["modeles_A"], []).append(x)
    for mods, xs in par.items():
        pl = sr.log_score
        n = len(xs)
        par_source: dict[str, dict] = {}
        for x in xs:
            a = par_source.setdefault(x["source_question"], {"n": 0, "A": 0.0, "B": 0.0, "AB": 0.0})
            a["n"] += 1
            for k, v in (("A", x["p_A"]), ("B", x["p_B"]), ("AB", x["p_AB"])):
                a[k] += pl(v, x["issue"])
        lignes_ab = [dict(x, ombre_ab={"p": x["p_AB"]}) for x in xs]
        out[mods] = {"n": n,
                     **{k: round(sum(pl(x[c], x["issue"]) for x in xs) / n, 4) for k, c in
                        (("A", "p_A"), ("B", "p_B"), ("AB", "p_AB"))},
                     "par_source": {s: {"n": v["n"], **{k: round(v[k] / v["n"], 4) for k in ("A", "B", "AB")}}
                                    for s, v in sorted(par_source.items())},
                     "critere_AB": sr.critere_ombre_b(lignes_ab, "ombre_ab", "a_plus_b")}
    return out


async def principal(n: int, budget: float) -> int:
    from forecasting_tools import MonetaryCostManager
    modeles = [m.strip() for m in (os.environ.get("ALPHABET_BANC_A_MODELES") or "azure_ai/gpt-5-mini").split(",") if m.strip()]
    if not ar.recherche_bornee_disponible():
        print("Il faut une recherche bornable dans le temps (EXA_API_KEY ou TINYFISH_API_KEY). Rien n'est lancé.")
        return 1
    am.installer_traceur()
    am.servis_et_vider()
    deja = {(x["question_id"], x["modeles_A"]) for x in lignes()}
    cle_mods = ",".join(modeles)
    jeux = sorted(fb.jeux_candidats(date.today(), date.fromisoformat(APRES), n_max=26))
    REGISTRE.mkdir(exist_ok=True)
    faites, cumul, pire = 0, 0.0, 0.0
    tous = []
    for j in jeux:
        try:
            qs = await fb._json(f"{fb.DEPOT}/question_sets/{j}-llm.json")
            rs = await fb._json(f"{fb.DEPOT}/resolution_sets/{j}_resolution_set.json")
        except Exception as e:
            print(f"Jeu {j} indisponible : {type(e).__name__}")
            continue
        if j in JEUX_VUS:
            continue
        items = sorted((fb.construire(i, j) for i in fb.apparier(qs, rs, SOURCES)), key=lambda x: rang(x["qid"]))
        tous += [(r, j, x) for r, x in enumerate(items)]
    tous.sort(key=lambda t: (t[0], t[1]))
    print(f"{len(tous)} questions candidates, entrelacées entre {len(jeux)} jeux.")
    with FICHIER.open("a", encoding="utf-8") as f:
        if True:
            j = None
            for r_, j, x in tous:
                if faites >= n:
                    break
                if (x["qid"], cle_mods) in deja:
                    continue
                if fb.depasse(cumul, pire, budget):
                    print(f"Plafond atteint : {cumul:.2f} $ + {pire:.2f} $ > {budget:.2f} $. Arrêt.")
                    n = faites
                    break
                with MonetaryCostManager() as cm:
                    vue = await fb.vue_calculee(x, x["_q"], j)
                    if not vue or vue.get("frequence") is None:
                        continue                     # pas de B par le code : la comparaison n'a pas de sens
                    info = datetime.fromisoformat(j).replace(tzinfo=timezone.utc)
                    try:
                        recherche = await ar.chercher_avant(x["titre"], info)
                    except Exception as e:
                        recherche = f"(recherche indisponible : {type(e).__name__})"
                    consigne = consigne_a(x, vue, (x.get("_releve") or {}).get("points") or [], recherche, j)
                    par_modele, exclue = {}, False
                    for m in modeles:
                        try:
                            r = ap.extraire_json(await am.llm(m, temperature=0.2, timeout=300, allowed_tries=2).invoke(consigne))
                            p = float(r["p"])
                            par_modele[m] = {"p": min(0.99, max(0.01, p)), "raison": str(r.get("raison", ""))[:300],
                                             "connait_issue": bool(r.get("connait_issue"))}
                            exclue = exclue or bool(r.get("connait_issue"))
                        except Exception as e:
                            par_modele[m] = {"erreur": f"{type(e).__name__}: {e}"[:200]}
                    cout = float(cm.current_usage or 0)
                ps = [v["p"] for v in par_modele.values() if "p" in v]
                p_a = sigmoide(sum(logit(p) for p in ps) / len(ps)) if ps else None
                p_b = float(vue["frequence"])
                ligne = {"type": "banc_a", "jeu": j, "ordre": [r_, j], "source_question": x["source"], "question_id": x["qid"],
                         "version_bot": ap.VERSION_BOT, "titre": x["titre"], "issue": x["issue"],
                         "modeles_A": cle_mods, "A_par_modele": par_modele, "p_A": p_a, "p_B": p_b,
                         "p_AB": combiner(p_a, p_b) if p_a is not None else None, "exclue": exclue,
                         "modeles_servis": am.servis_et_vider(), "cout_usd": round(cout, 4),
                         "licence": "ForecastBench, Forecasting Research Institute, CC BY-SA 4.0"}
                f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
                f.flush()
                cumul += cout
                pire = max(pire, cout)
                if p_a is not None:
                    faites += 1
                print(f"{x['qid'][:60]} : A {p_a} · B {p_b:.3f} · issue {x['issue']} · {cout:.4f} $"
                      + (" · EXCLUE (issue connue)" if exclue else ""))
    r = resumer(lignes())
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{faites} question(s) ; coût {cumul:.2f} $ (plafond {budget:.2f} $).")
    print(json.dumps(r.get(cle_mods, {}), ensure_ascii=False)[:1500])
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--n", type=int, default=10)
    a.add_argument("--budget", type=float, default=3.0)
    o = a.parse_args()
    sys.exit(asyncio.run(principal(o.n, o.budget)))
