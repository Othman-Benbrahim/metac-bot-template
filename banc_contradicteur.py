"""Banc du contradicteur, partie hors domaine (amendement du 2026-11-26, E bis.1). Une passe, texte seul, sans recherche.
Jeu étiqueté avant tout appel : mise_au_point/banc_contradicteur_jeu.json. Rapport : banc_contradicteur.json.
Critère écrit avant : rappel ≥ 3/4 et fausses alertes ≤ 1/4.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os

import alphabet_modeles as am
import contradicteur_brique as cb
import dossier_interne as di


async def un(m, x):
    c = cb.consigne(x["titre"], "", x["famille"], di.DOMAINES[x["famille"]], float(x["mesure"]))
    try:
        rep = await m.invoke(c)
    except Exception as e:
        return {**x, "verdict": "erreur", "detail": type(e).__name__}
    return {**x, **cb.analyser(rep, x["titre"]), "reponse": (rep or "")[:600]}


async def principal(modele: str) -> dict:
    jeu = json.load(open("mise_au_point/banc_contradicteur_jeu.json", encoding="utf-8"))["jeu"]
    m = am.llm(modele, temperature=0.1, timeout=180, allowed_tries=2, max_tokens=4000)
    R = []
    for x in jeu:
        R.append(await un(m, x))
        print(f"{R[-1]['verdict']:>14}  attendu {'HORS' if x['hors_domaine'] else 'dans'}  {x['famille']}: {x['titre'][:90]}",
              flush=True)
    hors = [r for r in R if r["hors_domaine"]]
    dans = [r for r in R if not r["hors_domaine"]]
    rappel = sum(r["verdict"] == "hors_domaine" for r in hors) / max(1, len(hors))
    fausses = sum(r["verdict"] in ("hors_domaine", "contre_terrain") for r in dans) / max(1, len(dans))
    res = {"modele": modele, "n": len(R), "n_hors": len(hors), "rappel": rappel, "fausses_alertes": fausses,
           "illisibles": sum(r["verdict"] in ("illisible", "erreur", "rejete") for r in R),
           "critere_tenu": rappel >= 0.75 and fausses <= 0.25, "lignes": R}
    json.dump(res, open("banc_contradicteur.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nrappel {rappel:.2f} ({len(hors)} hors domaine) ; fausses alertes {fausses:.2f} ({len(dans)} dans le domaine) ; "
          f"illisibles ou rejetés {res['illisibles']} ; critère {'TENU' if res['critere_tenu'] else 'NON TENU'}")
    return res


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--modele", default=os.environ.get("ALPHABET_CONTRADICTEUR", "").split(",")[0])
    a = p.parse_args()
    asyncio.run(principal(a.modele))
