"""Banc de la fuite des recherches rétrospectives (bot 0.10.296).

Décision d'auteur du 2026-11-18, 22 h 04 (« j'accepte les deux, à appliquer »). Origine : ForecastGym (Tao, Li, Fan,
arXiv 2611.23045) : relancer une recherche après la résolution, même filtrée par date, laisse deviner l'issue pour
jusqu'à 92 % des questions. Nos bancs de jugement reposent tous sur une recherche rétrospective bornée par date.
Préenregistrement : preenregistrements/fuite-recherche.md.

Pour chaque ligne du banc jugement_alphabet (recherche gelée, la même que celle des bras A et M), Claude Haiku 4.5
(Bedrock, crédits jusqu'au 23) lit la recherche en connaissant l'issue réelle et dit si le texte contient une
information POSTÉRIEURE à la date de la question qui révèle ou laisse fortement deviner cette issue. Il doit recopier
la phrase ; le code vérifie qu'elle figure mot pour mot dans la recherche (cartes_ancrees.citation_verifiee). Une
fuite n'est comptée que citée et vérifiée.

    python banc_fuite_recherche.py --budget-bedrock 3
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import alphabet_pipeline as ap
import alphabet_retro as ar
import banc_forecastbench as fb
import banc_jugement_alphabet as bja
import banc_jugement_variantes as bv
import bras_m
import cartes_ancrees as ca
import garde_injection as gi
import trace_recherche as tr

FICHIER = Path("registre/banc-fuite-recherche.jsonl")
RESUME = Path("registre/banc-fuite-recherche.json")


def lignes() -> list[dict]:
    return [json.loads(l) for l in FICHIER.read_text(encoding="utf-8").splitlines() if l.strip()] if FICHIER.exists() else []


def consigne(titre: str, jeu: str, issue: int, recherche: str) -> str:
    return f"""Vérification de la date des informations, pour un banc d'évaluation.

Question posée le {jeu} : {titre}
Issue réelle, connue aujourd'hui : {"OUI" if issue else "NON"}.

Les résultats de recherche ci-dessous devraient tous dater d'avant le {jeu}. Indique si ce texte contient une
information PUBLIÉE APRÈS le {jeu} (ou décrivant des faits postérieurs à cette date) qui révèle l'issue réelle ou la
laisse fortement deviner. Une information antérieure qui rend seulement l'issue probable ne compte pas.
Si c'est le cas, recopie exactement la phrase en cause depuis le texte.

{gi.bloc(recherche, 6000)}

Réponds seulement par un objet JSON :
{{"revele": "oui" ou "non", "citation": "phrase recopiée du texte, ou null", "pourquoi": "une phrase"}}"""


def resumer(ls: list[dict]) -> dict:
    import profil_erreurs as pe
    import score_registre as sr
    ok = [x for x in ls if x.get("verdict") in ("fuite", "propre", "fuite_non_citee")]
    fuite = [x for x in ok if x["verdict"] == "fuite"]
    propre = [x for x in ok if x["verdict"] != "fuite"]
    q = lambda xs: len({":".join(x["question_id"].split(":")[:2]) for x in xs})
    out = {"version_bot": ap.VERSION_BOT, "lignes_lues": len(ok), "questions_lues": q(ok),
           "lignes_fuite": len(fuite), "questions_fuite": q(fuite),
           "lignes_fuite_non_citee": sum(1 for x in ok if x["verdict"] == "fuite_non_citee"),
           "part_lignes_fuite": round(len(fuite) / len(ok), 3) if ok else None,
           "note": "fuite = information postérieure à la date de la question, révélant l'issue, citée et vérifiée"}
    pl = sr.log_score
    for nom, g in (("fuite", fuite), ("propre", propre)):
        if g:
            out[f"perte_{nom}"] = {k: round(sum(pl(x[f"p_{k}"], x["issue"]) for x in g) / len(g), 4) for k in ("A", "M")}
    if len(propre) >= 20:
        out["M_contre_A_sur_lignes_propres"] = sr.critere_ombre_b(
            [dict(x, p_B=x["p_A"], o={"p": x["p_M"]}) for x in propre], "o", "jugement_alphabet", exclure_vus=False,
            bloc_par="question", tout_juger=True)
        out["unites_propres"] = pe.unites(propre)
    out["unites"] = pe.unites(ok)
    return out


async def principal(budget_bedrock: float) -> int:
    from forecasting_tools import MonetaryCostManager
    base = bv.base_banc()
    deja = {x["question_id"] for x in lignes()}
    cand = {f'{x["source"]}:{x["id"]}:{x["jeu"]}': x for x in bja.candidates()}
    cumul, pire = 0.0, 0.0
    with FICHIER.open("a", encoding="utf-8") as f:
        for qid, b in base.items():
            if qid in deja or qid not in cand:
                continue
            if fb.depasse(cumul, pire, budget_bedrock):
                print(f"Plafond atteint ({cumul:.2f} $). Arrêt.")
                break
            x = cand[qid]
            info = datetime.fromisoformat(x["jeu"]).replace(tzinfo=timezone.utc)
            rech, du_cache = await tr.chercher_fige(qid, x["titre"], info, ar.chercher_avant)
            ligne = {"type": "banc_fuite_recherche", "question_id": qid, "issue": b["issue"], "p_A": b["p_A"],
                     "p_M": b["p_M"], "recherche": {"empreinte": tr.tracer(rech, x["jeu"])["empreinte"], "cache": du_cache},
                     "version_bot": ap.VERSION_BOT}
            if bras_m.recherche_vide(rech):
                ligne["verdict"] = "sans_recherche"
            else:
                with MonetaryCostManager() as cm:
                    try:
                        r = await bv.appeler(bv.HAIKU, consigne(x["titre"], x["jeu"], b["issue"], rech))
                        cit = r.get("citation") or ""
                        verifiee = bool(cit) and ca.citation_verifiee(str(cit), rech)
                        ligne["verdict"] = ("fuite" if r.get("revele") == "oui" and verifiee else
                                            "fuite_non_citee" if r.get("revele") == "oui" else "propre")
                        ligne["citation"] = str(cit)[:400] if verifiee else None
                        ligne["pourquoi"] = str(r.get("pourquoi") or "")[:300]
                    except Exception as e:
                        ligne["verdict"] = "erreur"
                        ligne["erreur"] = f"{type(e).__name__}: {e}"[:200]
                    c = float(cm.current_usage or 0)
                cumul += c
                pire = max(pire, c)
            f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
            f.flush()
            print(f"{qid[:44]} : {ligne['verdict']}", flush=True)
    r = resumer(lignes())
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    print(f"Coût Bedrock : {cumul:.2f} $")
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--budget-bedrock", type=float, default=3.0)
    sys.exit(asyncio.run(principal(a.parse_args().budget_bedrock)))
