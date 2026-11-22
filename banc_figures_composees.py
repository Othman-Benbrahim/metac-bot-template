"""Figures composées (compétition, intention, convention) dans le lecteur : M10 (sept notes + trois figures) contre M7.

Décision d'auteur du 2026-11-22, 5 h 07 et 5 h 16. Préenregistrement : preenregistrements/figures-composees.md. Essai
figures_composees. Aucune nouvelle carte : trois compositions de cartes existantes. M7 et M10 partagent les mêmes sept
notes. Recherche gelée seulement. Rien dans le bot.

    python banc_figures_composees.py --n 150 --budget 5 --budget-bedrock 1
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

FICHIER = Path("registre/banc-figures-composees.jsonl")
RESUME = Path("registre/banc-figures-composees.json")
MODELE = "azure_ai/gpt-5-mini"
HAIKU = "bedrock/global.anthropic.claude-haiku-4-5-20251001-v1:0"
N_ACCORD = 60
FIGURES = (
    ("competition", "COMPÉTITION",
     "CONTRAINTE (la ressource ou la position ne peut revenir à toutes les parties) + HIÉRARCHIE (une règle "
     "d'attribution — vote, score, classement, combat, enchère — produit un ordre entre les parties), avec POLARITÉ "
     "quand elles sont deux"),
    ("intention", "INTENTION",
     "HIÉRARCHIE (un acteur identifiable occupe la position qui décide l'issue) + INCERTITUDE (pour les autres, son "
     "choix reste indéterminé) + aucune CONTRAINTE qui dicterait ce choix"),
    ("convention", "CONVENTION",
     "ÉMERGENCE (une régularité collective acceptée) ou HIÉRARCHIE (une autorité qui déclare) + une règle (CONTRAINTE "
     "formelle) : le fait existe parce qu'il est accepté ou déclaré, et peut changer par décision sans que rien de "
     "matériel ne bouge"),
)
CLES_FIG = tuple(f[0] for f in FIGURES)


def consigne_notes10(bja, q: dict, p_b: float, recherche: str, jeu: str) -> str:
    base = bja.consigne_notes(q, p_b, recherche, jeu)
    figs = "\n".join(f"- \"{k}\" (figure {nom} = {compo})" for k, nom, compo in FIGURES)
    ajout = f"""

Note AUSSI ces trois FIGURES, chacune composée de cartes déjà connues (1 = absente de la situation, 4 = présente et
décisive pour l'issue), et dis vers quel côté elle pousse (\"sens\" : \"oui\", \"non\" ou \"neutre\") :
{figs}
Ajoute-les dans le même objet \"notes\", avec la même forme : {{"note": 1-4, "pourquoi": "une phrase", "sens": "oui|non|neutre"}}."""
    i = base.rfind("Rends UNIQUEMENT")
    return base[:i].rstrip() + ajout + "\n" + base[i:]


def lire_figures(r: dict) -> dict:
    out = {}
    for k in CLES_FIG:
        v = (r.get("notes") or {}).get(k)
        try:
            n = int(round(float(v["note"] if isinstance(v, dict) else v)))
        except (TypeError, ValueError, KeyError):
            continue
        if 1 <= n <= 4:
            s = str(v.get("sens", "neutre")).lower() if isinstance(v, dict) else "neutre"
            out[k] = {"note": n, "sens": s if s in ("oui", "non", "neutre") else "neutre",
                      "pourquoi": str(v.get("pourquoi", ""))[:300] if isinstance(v, dict) else ""}
    return out


def consigne_finale10(bja, q: dict, p_b: float, notes: dict, figures: dict, recherche: str, jeu: str) -> str:
    base = bja.consigne_finale(q, p_b, notes, recherche, jeu)
    lignes = "\n".join(f"- figure {nom} ({compo.split(' (')[0]}…) : {figures[k]['note']}/4, pousse vers "
                       f"{figures[k]['sens'].upper()} — {figures[k]['pourquoi']}"
                       for k, nom, compo in FIGURES if k in figures)
    i = base.find("RÉSULTATS DE RECHERCHE")
    return base[:i] + "LE COMITÉ A AUSSI NOTÉ TROIS FIGURES COMPOSÉES (1 = absente, 4 = présente et décisive) :\n" + \
        lignes + "\n\n" + base[i:]


def resumer(ls: list[dict]) -> dict:
    import score_registre as sr
    import banc_accord_lecteur as bal
    pl = sr.log_score
    ok = [x for x in ls if x.get("issue") in (0, 1) and x.get("p_M7") is not None and x.get("p_M10") is not None]
    out = {"n": len(ok), "note": "perte log, plus bas = mieux ; M7 et M10 partagent les mêmes sept notes"}
    if ok:
        n = len(ok)
        moy = lambda k: round(sum(pl(x[k], x["issue"]) for x in ok) / n, 4)

        def disc(k):
            o = [x[k] for x in ok if x["issue"] == 1]
            z = [x[k] for x in ok if x["issue"] == 0]
            return round(sum(o) / len(o) - sum(z) / len(z), 3) if o and z else None
        out.update({"B_semblables": moy("p_B"), "M7": moy("p_M7"), "M10": moy("p_M10"),
                    "discrimination": {"B": disc("p_B"), "M7": disc("p_M7"), "M10": disc("p_M10")},
                    "part_des_1": {k: round(sum((x.get("figures") or {}).get(k, {}).get("note") == 1 for x in ok) / n, 3)
                                   for k in CLES_FIG},
                    "critere": sr.critere_ombre_b([dict(x, p_B=x["p_M7"], o={"p": x["p_M10"]}) for x in ok], "o",
                                                  "figures_composees", exclure_vus=False, bloc_par="question")})
    acc = [{"r1": {"notes": {k: v["note"] for k, v in (x.get("figures") or {}).items()}},
            "r2": {"notes": {k: v["note"] for k, v in (x.get("figures_r2") or {}).items()}},
            "x": {"notes": {k: v["note"] for k, v in (x.get("figures_x") or {}).items()}}}
           for x in ls if x.get("figures_r2") is not None]
    if acc:
        out["accord_figures"] = {"n": len(acc), "stabilite_r1_r2": bal.comparer(acc, "r1", "r2", CLES_FIG),
                                 "accord_r1_x": bal.comparer([a for a in acc if a["x"]["notes"]], "r1", "x", CLES_FIG),
                                 "seuils": bal.SEUILS}
    return out


def lignes() -> list[dict]:
    return [json.loads(l) for l in FICHIER.read_text(encoding="utf-8").splitlines() if l.strip()] if FICHIER.exists() else []


async def principal(n: int, budget: float, budget_bedrock: float) -> int:
    from datetime import datetime, timezone
    from forecasting_tools import MonetaryCostManager
    import alphabet_modeles as am
    import alphabet_pipeline as ap
    import banc_accord_lecteur as bal
    import banc_forecastbench as fb
    import banc_jugement_alphabet as bja
    import trace_recherche as tr

    admis = {x["question_id"] for x in bja.lignes() if not x.get("exclue") and x.get("p_M") is not None}
    deja = {x["question_id"] for x in lignes()}
    cumul = {"azure": 0.0, "bedrock": 0.0}
    pire = {"azure": 0.0, "bedrock": 0.0}
    plafond = {"azure": budget, "bedrock": budget_bedrock}
    textes: dict[str, dict] = {}
    faites, sautees = len(deja), 0
    llm = lambda m: am.llm(m, temperature=0.2, timeout=300, allowed_tries=2)
    FICHIER.parent.mkdir(exist_ok=True)
    with FICHIER.open("a", encoding="utf-8") as f:
        for x in bja.candidates():
            qid = f'{x["source"]}:{x["id"]}:{x["jeu"]}'
            if faites >= n:
                break
            if qid not in admis or qid in deja:
                continue
            if fb.depasse(cumul["azure"], pire["azure"], plafond["azure"]):
                print(f"Plafond atteint ({cumul}). Arrêt.")
                break
            info = datetime.fromisoformat(x["jeu"]).replace(tzinfo=timezone.utc)
            rech, du_cache = await tr.chercher_fige(qid, x["titre"], info, bal._pas_de_recherche_neuve)
            if not du_cache:
                sautees += 1
                continue
            if x["jeu"] not in textes:
                try:
                    qs = await fb._json(f"{fb.DEPOT}/question_sets/{x['jeu']}-llm.json")
                    textes[x["jeu"]] = {str(q["id"]): q for q in qs.get("questions", [])}
                except Exception:
                    textes[x["jeu"]] = {}
            src = textes[x["jeu"]].get(x["id"])
            if not src:
                sautees += 1
                continue
            q = {"titre": x["titre"], "cloture": x["cloture"],
                 "criteres": str(src.get("market_info_resolution_criteria") or src.get("resolution_criteria") or ""),
                 "contexte": str(src.get("background") or "")}
            p_b = float(x["p_S"])
            ligne = {"type": "banc_figures_composees", "question_id": qid, "jeu": x["jeu"], "titre": x["titre"],
                     "issue": x["issue"], "p_B": p_b, "version_bot": ap.VERSION_BOT, "modele": MODELE}
            with MonetaryCostManager() as cm:
                try:
                    r = ap.extraire_json(await llm(MODELE).invoke(consigne_notes10(bja, q, p_b, rech, x["jeu"])))
                    notes, figs = bja.lire_notes(r), lire_figures(r)
                    ligne["notes"] = {k: v["note"] for k, v in notes.items()}
                    ligne["figures"] = figs
                    if len(notes) == len(bja.CLES) and len(figs) == len(CLES_FIG):
                        r7 = ap.extraire_json(await llm(MODELE).invoke(bja.consigne_finale(q, p_b, notes, rech, x["jeu"])))
                        r10 = ap.extraire_json(await llm(MODELE).invoke(
                            consigne_finale10(bja, q, p_b, notes, figs, rech, x["jeu"])))
                        ligne["p_M7"] = min(0.99, max(0.01, float(r7["p"])))
                        ligne["p_M10"] = min(0.99, max(0.01, float(r10["p"])))
                    if faites < N_ACCORD:
                        r2 = ap.extraire_json(await llm(MODELE).invoke(consigne_notes10(bja, q, p_b, rech, x["jeu"])))
                        ligne["figures_r2"] = lire_figures(r2)
                except Exception as e:
                    ligne["erreur"] = f"{type(e).__name__}: {e}"[:200]
                cout = float(cm.current_usage or 0)
            cumul["azure"] += cout
            pire["azure"] = max(pire["azure"], cout)
            if faites < N_ACCORD and not fb.depasse(cumul["bedrock"], pire["bedrock"], plafond["bedrock"]):
                with MonetaryCostManager() as cm:
                    try:
                        rx = ap.extraire_json(await llm(HAIKU).invoke(consigne_notes10(bja, q, p_b, rech, x["jeu"])))
                        ligne["figures_x"] = lire_figures(rx)
                    except Exception as e:
                        ligne["erreur_x"] = f"{type(e).__name__}: {e}"[:200]
                    cb = float(cm.current_usage or 0)
                cumul["bedrock"] += cb
                pire["bedrock"] = max(pire["bedrock"], cb)
            f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
            f.flush()
            faites += 1
            print(f"{qid[:48]} : M7 {ligne.get('p_M7')} · M10 {ligne.get('p_M10')} · issue {x['issue']} · "
                  f"figures {[(k, v['note'], v['sens']) for k, v in ligne.get('figures', {}).items()]}")
    r = resumer(lignes())
    r["sautees_sans_recherche_gelee"] = sautees
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"coût : {cumul}")
    print(json.dumps(r, ensure_ascii=False, indent=1)[:2500])
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--n", type=int, default=150)
    a.add_argument("--budget", type=float, default=5.0)
    a.add_argument("--budget-bedrock", type=float, default=1.0)
    o = a.parse_args()
    sys.exit(asyncio.run(principal(o.n, o.budget, o.budget_bedrock)))
