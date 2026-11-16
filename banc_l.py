"""Banc du langage (0.10.112, décision d'auteur du 2026-11-15). Deux idées neuves, sur les questions de conflits
(ACLED), là où le jugement du modèle (A) apporte déjà de l'information :

1. LE LANGAGE COMME ACTE. Les textes ne font pas que décrire : certains engagent (annonces datées, menaces,
   promesses, ultimatums). Pour chaque passage des résultats de recherche (bornés avant la date d'information), le modèle
   dit s'il DÉCRIT ou s'il ENGAGE, et dans quel sens pour l'événement de la question. Variable : E = (actes vers la
   hausse − actes vers la baisse) / (nombre d'actes + 1).
2. LE DÉSACCORD COMME SIGNAL. Le modèle donne, pour chaque passage, la probabilité de l'événement que ce passage seul
   suggère. Variable : D = écart-type de ces probabilités (0 si moins de 2 passages). Hypothèse : quand les sources se
   contredisent, A devrait se rapprocher de B.

Modèles, un paramètre chacun, appris et jugés par validation croisée « un jeu laissé de côté » (chaque jeu prédit par
un paramètre appris sur les autres jeux seulement), a priori normal centré sur 0 (écart-type 1) :
- acte :     logit(p) = logit(A) + β·E
- désaccord : logit(p) = logit(A) + γ·D·(logit(B) − logit(A))
Critères : preenregistrements/langage.md. Registre : registre/banc-l.jsonl ; résumé : registre/banc-l.json.

    python banc_l.py --budget 3
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import statistics
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import alphabet_modeles as am
import alphabet_pipeline as ap
import alphabet_retro as ar
import banc_a as ba
import banc_forecastbench as fb
import garde_injection as gi

REGISTRE = Path("registre")
FICHIER = REGISTRE / "banc-l.jsonl"
RESUME = REGISTRE / "banc-l.json"
MODELE = "azure_ai/gpt-5-mini"


def consigne_extraction(titre: str, criteres: str, recherche: str, jeu: str) -> str:
    return f"""Nous sommes le {jeu}. Voici une question de prévision et des extraits de presse antérieurs à cette date.

QUESTION : {titre}
CRITÈRES : {criteres[:1500]}

EXTRAITS :
{gi.bloc(recherche, 7000)}

Pour chaque extrait utile (au plus 12), dis :
- "type" : "acte" si le texte ENGAGE quelqu'un (annonce datée, menace, promesse, ultimatum, appel à manifester,
  décision officielle à venir) ; "description" s'il décrit seulement ce qui se passe ou s'est passé ;
- "sens" : l'effet de cet extrait sur la probabilité que la réponse soit OUI : "hausse", "baisse" ou "neutre" ;
- "p" : la probabilité de OUI que cet extrait suggérerait s'il était seul (entre 0,01 et 0,99).
Ne juge pas la question dans son ensemble. Rends UNIQUEMENT un objet JSON :
{{"extraits": [{{"type": "acte" | "description", "sens": "hausse" | "baisse" | "neutre", "p": nombre}}]}}"""


def variables(extraits: list[dict]) -> dict:
    actes = [e for e in extraits if e.get("type") == "acte"]
    haut = sum(e.get("sens") == "hausse" for e in actes)
    bas = sum(e.get("sens") == "baisse" for e in actes)
    ps = [float(e["p"]) for e in extraits if isinstance(e.get("p"), (int, float))]
    return {"n_extraits": len(extraits), "n_actes": len(actes), "E": (haut - bas) / (len(actes) + 1),
            "D": statistics.pstdev(ps) if len(ps) >= 2 else 0.0}


def lg(p: float) -> float:
    p = min(max(p, 1e-3), 1 - 1e-3)
    return math.log(p / (1 - p))


def sig(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def ajuster(xs: list[tuple[float, float, int]], sd: float = 1.0) -> float:
    """Un coefficient c de logit(p) = décalage + c·z, maximum a posteriori (a priori normal 0, écart-type sd), Newton."""
    c = 0.0
    for _ in range(50):
        g, h = -c / sd ** 2, -1 / sd ** 2
        for off, z, y in xs:
            p = sig(off + c * z)
            g += (y - p) * z
            h -= p * (1 - p) * z * z
        if h == 0:
            break
        pas = g / h
        c -= pas
        if abs(pas) < 1e-8:
            break
    return c


def validation_croisee(ls: list[dict]) -> list[dict]:
    """Un jeu laissé de côté : les paramètres qui prédisent un jeu sont appris sur les autres jeux seulement."""
    out = []
    for j in sorted({x["jeu"] for x in ls}):
        app = [x for x in ls if x["jeu"] != j]
        b = ajuster([(lg(x["p_A"]), x["E"], x["issue"]) for x in app])
        g = ajuster([(lg(x["p_A"]), x["D"] * (lg(x["p_B"]) - lg(x["p_A"])), x["issue"]) for x in app])
        for x in ls:
            if x["jeu"] == j:
                out.append(dict(x, beta=b, gamma=g, p_acte=sig(lg(x["p_A"]) + b * x["E"]),
                                p_desaccord=sig(lg(x["p_A"]) + g * x["D"] * (lg(x["p_B"]) - lg(x["p_A"])))))
    return sorted(out, key=lambda x: (x.get("ordre") or [10 ** 6, x["jeu"]]))


def resumer(ls: list[dict]) -> dict:
    import score_registre as sr
    ok = [x for x in ls if x.get("E") is not None and x.get("issue") in (0, 1)]
    if len({x["jeu"] for x in ok}) < 2:
        return {"n": len(ok), "note": "moins de deux jeux : pas de validation croisée"}
    cv = validation_croisee(ok)
    n = len(cv)
    pl = sr.log_score
    moy = lambda c: round(sum(pl(x[c], x["issue"]) for x in cv) / n, 4)
    return {"version_bot": ap.VERSION_BOT, "n": n, "note": "perte log, plus bas = mieux ; validation croisée par jeu",
            "A": moy("p_A"), "B": moy("p_B"), "acte": moy("p_acte"), "desaccord": moy("p_desaccord"),
            "beta_moyen": round(sum(x["beta"] for x in cv) / n, 3), "gamma_moyen": round(sum(x["gamma"] for x in cv) / n, 3),
            "part_avec_actes": round(sum(x["n_actes"] > 0 for x in cv) / n, 3),
            "critere_acte": sr.critere_ombre_b([dict(x, p_B=x["p_A"], o={"p": x["p_acte"]}) for x in cv], "o",
                                               "langage_acte", exclure_vus=False),
            "critere_desaccord": sr.critere_ombre_b([dict(x, p_B=x["p_A"], o={"p": x["p_desaccord"]}) for x in cv], "o",
                                                    "desaccord", exclure_vus=False)}


def lignes() -> list[dict]:
    if not FICHIER.exists():
        return []
    return [json.loads(l) for l in FICHIER.read_text(encoding="utf-8").splitlines() if l.strip()]


async def principal(budget: float, n_max: int) -> int:
    from forecasting_tools import MonetaryCostManager
    if not ar.recherche_bornee_disponible():
        print("Il faut une recherche bornable dans le temps (EXA_API_KEY ou TINYFISH_API_KEY). Rien n'est lancé.")
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
    cumul, pire, faites = 0.0, 0.0, 0
    with FICHIER.open("a", encoding="utf-8") as f:
        for x in cibles:
            if faites >= n_max:
                break
            if fb.depasse(cumul, pire, budget):
                print(f"Plafond atteint : {cumul:.2f} $. Arrêt.")
                break
            q = textes.get(x["question_id"])
            if not q:
                continue
            with MonetaryCostManager() as cm:
                info = datetime.fromisoformat(x["jeu"]).replace(tzinfo=timezone.utc)
                try:
                    rech = await ar.chercher_avant(q["titre"], info)
                except Exception as e:
                    rech = ""
                try:
                    r = ap.extraire_json(await am.llm(MODELE, temperature=0.2, timeout=300, allowed_tries=2).invoke(
                        consigne_extraction(q["titre"], q["criteres"], rech, x["jeu"])))
                    ex = [e for e in (r.get("extraits") or []) if isinstance(e, dict)][:12]
                    v = variables(ex)
                except Exception as e:
                    ex, v = [], {"erreur": f"{type(e).__name__}: {e}"[:200]}
                cout = float(cm.current_usage or 0)
            ligne = {"type": "banc_l", "jeu": x["jeu"], "ordre": x.get("ordre"), "question_id": x["question_id"],
                     "source_question": "acled", "version_bot": ap.VERSION_BOT, "issue": x["issue"], "p_A": x["p_A"],
                     "p_B": x["p_B"], "extraits": ex, **({"E": None, "D": None} if "erreur" in v else {}), **v,
                     "cout_usd": round(cout, 4)}
            f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
            f.flush()
            cumul += cout
            pire = max(pire, cout)
            faites += 1
            print(f"{x['question_id'][:55]} : E {v.get('E')} · D {v.get('D')} · actes {v.get('n_actes')} · {cout:.4f} $")
    r = resumer(lignes())
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{faites} question(s) ; coût {cumul:.2f} $.")
    print(json.dumps(r, ensure_ascii=False, indent=1)[:3000])
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--budget", type=float, default=3.0)
    p.add_argument("--n", type=int, default=400)
    o = p.parse_args()
    sys.exit(asyncio.run(principal(o.budget, o.n)))
