"""Banc des signaux coûteux (0.10.114, décision d'auteur du 2026-11-15). Suite du banc du langage : le coefficient appris
sur les actes de langage était NÉGATIF (les annonces surestiment l'issue). Hypothèse de l'auteur : l'INTENTION de celui
qui parle prime sur l'information ; théorie : parole gratuite (cheap talk, Crawford et Sobel, Econometrica 1982) contre
signal coûteux (Fearon, Journal of Conflict Resolution 1997 : se lier les mains, payer d'avance).

Pour chaque question de conflit (ACLED) du banc du bras A : recherche bornée avant la date, puis gpt-5-mini qualifie
chaque extrait : acte ou description ; sens (hausse, baisse, neutre) ; QUI parle (acteur concerné, adversaire, tiers,
média) ; ce que l'acte COÛTE à son auteur (gratuit : parole seule ; coûteux : engagement public devant son camp,
mobilisation, dépense, décision officielle ou juridique). Variables :
  G = (actes gratuits en hausse − en baisse) / (actes gratuits + 1)
  K = (actes coûteux en hausse − en baisse) / (actes coûteux + 1)
Modèle (deux paramètres, fixé d'avance) : logit(p) = logit(A) + βG·G + βK·K ; maximum a posteriori (a priori normal 0,
écart-type 1), validation croisée « un jeu laissé de côté ». Pré-enregistrement : preenregistrements/signaux-couteux.md.

    python banc_signaux.py --budget 3
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import alphabet_modeles as am
import alphabet_pipeline as ap
import alphabet_retro as ar
import banc_a as ba
import banc_forecastbench as fb

REGISTRE = Path("registre")
FICHIER = REGISTRE / "banc-signaux.jsonl"
RESUME = REGISTRE / "banc-signaux.json"
MODELE = "azure_ai/gpt-5-mini"


def consigne(titre: str, criteres: str, recherche: str, jeu: str) -> str:
    return f"""Nous sommes le {jeu}. Voici une question de prévision et des extraits de presse antérieurs à cette date.

QUESTION : {titre}
CRITÈRES : {criteres[:1500]}

EXTRAITS :
{recherche[:7000]}

Pour chaque extrait utile (au plus 12), dis :
- "type" : "acte" si le texte rapporte un engagement de quelqu'un (annonce, menace, promesse, ultimatum, appel,
  mobilisation, décision à venir) ; "description" s'il décrit seulement ce qui se passe ou s'est passé ;
- "sens" : l'effet de l'extrait sur la probabilité que la réponse soit OUI : "hausse", "baisse" ou "neutre" ;
- "locuteur" (pour un acte) : "acteur_concerne" (celui qui agirait), "adversaire", "tiers" ou "media" ;
- "cout" (pour un acte) : "gratuit" si c'est une parole seule qui ne coûte rien à son auteur s'il recule ;
  "couteux" s'il lui coûte quelque chose : engagement public devant son propre camp, mobilisation de personnes ou de
  moyens, dépense, décision officielle ou juridique déjà prise.
Rends UNIQUEMENT un objet JSON :
{{"extraits": [{{"type": "acte" | "description", "sens": "hausse" | "baisse" | "neutre",
"locuteur": "acteur_concerne" | "adversaire" | "tiers" | "media" | null, "cout": "gratuit" | "couteux" | null}}]}}"""


def variables(ex: list[dict]) -> dict:
    out = {"n_extraits": len(ex)}
    for nom, c in (("G", "gratuit"), ("K", "couteux")):
        a = [e for e in ex if e.get("type") == "acte" and e.get("cout") == c]
        out[nom] = (sum(e.get("sens") == "hausse" for e in a) - sum(e.get("sens") == "baisse" for e in a)) / (len(a) + 1)
        out[f"n_{c}"] = len(a)
    return out


def lg(p: float) -> float:
    p = min(max(p, 1e-3), 1 - 1e-3)
    return math.log(p / (1 - p))


def sig(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def ajuster2(xs: list[tuple[float, float, float, int]], sd: float = 1.0) -> tuple[float, float]:
    """(βG, βK) de logit(p) = décalage + βG·G + βK·K, maximum a posteriori, Newton à deux dimensions."""
    b = [0.0, 0.0]
    for _ in range(60):
        g = [-b[0] / sd ** 2, -b[1] / sd ** 2]
        h = [[-1 / sd ** 2, 0.0], [0.0, -1 / sd ** 2]]
        for off, z1, z2, y in xs:
            p = sig(off + b[0] * z1 + b[1] * z2)
            w = p * (1 - p)
            g[0] += (y - p) * z1
            g[1] += (y - p) * z2
            h[0][0] -= w * z1 * z1
            h[0][1] -= w * z1 * z2
            h[1][1] -= w * z2 * z2
        h[1][0] = h[0][1]
        det = h[0][0] * h[1][1] - h[0][1] * h[1][0]
        if det == 0:
            break
        d0 = (h[1][1] * g[0] - h[0][1] * g[1]) / det
        d1 = (-h[1][0] * g[0] + h[0][0] * g[1]) / det
        b = [b[0] - d0, b[1] - d1]
        if abs(d0) + abs(d1) < 1e-8:
            break
    return b[0], b[1]


def validation_croisee(ls: list[dict]) -> list[dict]:
    out = []
    for j in sorted({x["jeu"] for x in ls}):
        bg, bk = ajuster2([(lg(x["p_A"]), x["G"], x["K"], x["issue"]) for x in ls if x["jeu"] != j])
        for x in ls:
            if x["jeu"] == j:
                out.append(dict(x, beta_G=bg, beta_K=bk, p_signaux=sig(lg(x["p_A"]) + bg * x["G"] + bk * x["K"])))
    return sorted(out, key=lambda x: (x.get("ordre") or [10 ** 6, x["jeu"]]))


def resumer(ls: list[dict]) -> dict:
    import score_registre as sr
    ok = [x for x in ls if x.get("G") is not None and x.get("issue") in (0, 1)]
    if len({x["jeu"] for x in ok}) < 2:
        return {"n": len(ok), "note": "moins de deux jeux"}
    cv = validation_croisee(ok)
    n = len(cv)
    tous = ajuster2([(lg(x["p_A"]), x["G"], x["K"], x["issue"]) for x in ok])
    moy = lambda c: round(sum(sr.log_score(x[c], x["issue"]) for x in cv) / n, 4)
    return {"version_bot": ap.VERSION_BOT, "n": n, "note": "perte log, plus bas = mieux ; validation croisée par jeu",
            "A": moy("p_A"), "B": moy("p_B"), "signaux": moy("p_signaux"),
            "beta_G_tout": round(tous[0], 3), "beta_K_tout": round(tous[1], 3),
            "hypothese_signes": "βG < 0 (la parole gratuite surestime), βK > 0 (le signal coûteux annonce)",
            "questions_avec_gratuits": sum(x["n_gratuit"] > 0 for x in cv),
            "questions_avec_couteux": sum(x["n_couteux"] > 0 for x in cv),
            "critere": sr.critere_ombre_b([dict(x, p_B=x["p_A"], o={"p": x["p_signaux"]}) for x in cv], "o",
                                          "signaux_couteux", exclure_vus=False)}


def lignes() -> list[dict]:
    if not FICHIER.exists():
        return []
    return [json.loads(l) for l in FICHIER.read_text(encoding="utf-8").splitlines() if l.strip()]


async def principal(budget: float) -> int:
    from forecasting_tools import MonetaryCostManager
    if not ar.recherche_bornee_disponible():
        print("Il faut une recherche bornable dans le temps. Rien n'est lancé.")
        return 1
    a = {}
    for x in ba.lignes():
        if (x.get("source_question") == "acled" and x.get("modeles_A") == MODELE and x.get("p_A") is not None
                and not x.get("exclue") and x.get("issue") in (0, 1)):
            a.setdefault(x["question_id"], x)
    deja = {x["question_id"] for x in lignes()}
    cibles = sorted((x for q, x in a.items() if q not in deja), key=lambda x: (x.get("ordre") or [10 ** 6, x["jeu"]]))
    print(f"{len(a)} questions ACLED avec A ; {len(cibles)} à traiter.")
    textes = {}
    for j in sorted({x["jeu"] for x in cibles}):
        qs = await fb._json(f"{fb.DEPOT}/question_sets/{j}-llm.json")
        rs = await fb._json(f"{fb.DEPOT}/resolution_sets/{j}_resolution_set.json")
        for i in fb.apparier(qs, rs, ("acled",)):
            y = fb.construire(i, j)
            textes[y["qid"]] = y
    REGISTRE.mkdir(exist_ok=True)
    cumul, pire = 0.0, 0.0
    with FICHIER.open("a", encoding="utf-8") as f:
        for x in cibles:
            if fb.depasse(cumul, pire, budget):
                print(f"Plafond atteint : {cumul:.2f} $. Arrêt.")
                break
            q = textes.get(x["question_id"])
            if not q:
                continue
            with MonetaryCostManager() as cm:
                try:
                    rech = await ar.chercher_avant(q["titre"], datetime.fromisoformat(x["jeu"]).replace(tzinfo=timezone.utc))
                except Exception:
                    rech = ""
                try:
                    r = ap.extraire_json(await am.llm(MODELE, temperature=0.2, timeout=300, allowed_tries=2).invoke(
                        consigne(q["titre"], q["criteres"], rech, x["jeu"])))
                    ex = [e for e in (r.get("extraits") or []) if isinstance(e, dict)][:12]
                    v = variables(ex)
                except Exception as e:
                    ex, v = [], {"G": None, "K": None, "erreur": f"{type(e).__name__}: {e}"[:200]}
                cout = float(cm.current_usage or 0)
            f.write(json.dumps({"type": "banc_signaux", "jeu": x["jeu"], "ordre": x.get("ordre"),
                                "question_id": x["question_id"], "version_bot": ap.VERSION_BOT, "issue": x["issue"],
                                "p_A": x["p_A"], "p_B": x["p_B"], "extraits": ex, **v, "cout_usd": round(cout, 4)},
                               ensure_ascii=False) + "\n")
            f.flush()
            cumul += cout
            pire = max(pire, cout)
            print(f"{x['question_id'][:55]} : G {v.get('G')} · K {v.get('K')} · {cout:.4f} $")
    r = resumer(lignes())
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Coût {cumul:.2f} $.")
    print(json.dumps(r, ensure_ascii=False, indent=1)[:3000])
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--budget", type=float, default=3.0)
    sys.exit(asyncio.run(principal(p.parse_args().budget)))
