"""Banc de la règle d'abstention : sans recherche, le modèle juge-t-il mieux que le taux des semblables ? (0.10.263)

Décision d'auteur du 2026-11-18, 12 h 57 (« les trois, et envoie-moi le banc de test ») ; d'après Khmelinskaya
(sortie « je m'abstiens », Q10) et la trace du 2026-11-18 (21 % des questions du banc sans aucune recherche).
Préenregistrement : preenregistrements/abstention.md.

Questions : les 309 du banc jugement_alphabet dont la recherche GELÉE (cache, trace_recherche) est vide au sens de
bras_m.recherche_vide. Sur chacune, M de gpt-5-mini (notes puis jugement final, mêmes consignes que le banc) avec ce
qu'il a vraiment (rien), contre le taux des questions semblables (p_B du banc). La règle d'abstention est adoptée
SAUF si le modèle aveugle bat le taux des semblables (intervalle 90 % par blocs entièrement sous zéro) : la charge de
la preuve est sur le modèle, la règle la plus simple l'emporte par défaut.

    python banc_abstention.py --budget 1
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
import trace_recherche as tr

FICHIER = Path("registre/banc-abstention.jsonl")
RESUME = Path("registre/banc-abstention.json")
GPT = bv.GPT


def lignes() -> list[dict]:
    return [json.loads(l) for l in FICHIER.read_text(encoding="utf-8").splitlines() if l.strip()] if FICHIER.exists() else []


def resumer(ls: list[dict]) -> dict:
    import score_registre as sr
    ok = [x for x in ls if x.get("p_M_aveugle") is not None]
    pl = sr.log_score
    r = {"version_bot": ap.VERSION_BOT, "questions_sans_recherche": len(ls), "n": len(ok),
         "note": "perte log, plus bas = mieux ; écart = M aveugle − semblables"}
    if not ok:
        return r
    n = len(ok)
    r.update(semblables=round(sum(pl(x["p_B"], x["issue"]) for x in ok) / n, 4),
             M_aveugle=round(sum(pl(x["p_M_aveugle"], x["issue"]) for x in ok) / n, 4),
             M_banc_descriptif=round(sum(pl(x["p_M_banc"], x["issue"]) for x in ok) / n, 4),
             oui=sum(x["issue"] for x in ok))
    c = sr.critere_ombre_b([dict(x, p_B=x["p_B"], o={"p": x["p_M_aveugle"]}) for x in ok], "o", "abstention",
                           exclure_vus=False, bloc_par="question", tout_juger=True)
    r["critere"] = c
    import profil_erreurs as pe          # 0.10.265 : les deux côtés des erreurs, toujours affichés
    r["profils"] = pe.profils(ok, {"semblables": "p_B", "M_aveugle": "p_M_aveugle"})
    r["unites"] = pe.unites(ok)
    iv = c.get("intervalle_90_par_blocs")
    r["verdict"] = ("abstention REJETÉE : le modèle aveugle bat les semblables" if iv and iv[1] < 0
                    else "abstention ADOPTABLE : le modèle aveugle ne bat pas les semblables")
    return r


async def principal(budget: float) -> int:
    from forecasting_tools import MonetaryCostManager
    base = bv.base_banc()
    deja = {x["question_id"] for x in lignes()}
    textes: dict[str, dict] = {}
    cumul, pire = 0.0, 0.0
    with FICHIER.open("a", encoding="utf-8") as f:
        for x in bja.candidates():
            qid = f'{x["source"]}:{x["id"]}:{x["jeu"]}'
            if qid not in base or qid in deja:
                continue
            info = datetime.fromisoformat(x["jeu"]).replace(tzinfo=timezone.utc)
            rech, _ = await tr.chercher_fige(qid, x["titre"], info, ar.chercher_avant)
            if not bras_m.recherche_vide(rech):
                continue
            if fb.depasse(cumul, pire, budget):
                print(f"Plafond atteint ({cumul:.2f} $). Arrêt.")
                break
            if x["jeu"] not in textes:
                try:
                    qs = await fb._json(f"{fb.DEPOT}/question_sets/{x['jeu']}-llm.json")
                    textes[x["jeu"]] = {str(q["id"]): q for q in qs.get("questions", [])}
                except Exception:
                    textes[x["jeu"]] = {}
            src = textes[x["jeu"]].get(x["id"]) or {}
            q = {"titre": x["titre"], "cloture": x["cloture"],
                 "criteres": str(src.get("market_info_resolution_criteria") or src.get("resolution_criteria") or ""),
                 "contexte": str(src.get("background") or "")}
            b = base[qid]
            p_b = float(b["p_B"])
            res: dict = {}
            with MonetaryCostManager() as cm:
                try:
                    notes = bja.lire_notes(await bv.appeler(GPT, bja.consigne_notes(q, p_b, rech, x["jeu"])))
                    if len(notes) >= 4:
                        res["p_M_aveugle"] = bv.borne((await bv.appeler(GPT, bja.consigne_finale(q, p_b, notes, rech, x["jeu"])))["p"])
                        res["notes"] = {k: v["note"] for k, v in notes.items()}
                except Exception as e:
                    res["erreur"] = f"{type(e).__name__}: {e}"[:200]
                c = float(cm.current_usage or 0)
            f.write(json.dumps({"type": "banc_abstention", "question_id": qid, "jeu": x["jeu"], "forme": x["forme"],
                                "issue": x["issue"], "p_B": p_b, "p_M_banc": b["p_M"], **res,
                                "recherche": tr.tracer(rech, x["jeu"]), "cout_usd": round(c, 4),
                                "version_bot": ap.VERSION_BOT,
                                "licence": "ForecastBench, Forecasting Research Institute, CC BY-SA 4.0"},
                               ensure_ascii=False) + "\n")
            f.flush()
            cumul, pire = cumul + c, max(pire, c)
            print(f"{qid[:46]} : semblables {p_b:.3f} · M aveugle {res.get('p_M_aveugle')} · issue {x['issue']}")
    r = resumer(lignes())
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--budget", type=float, default=1.0)
    sys.exit(asyncio.run(principal(a.parse_args().budget)))
