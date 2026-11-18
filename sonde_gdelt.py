"""Sonde GDELT (0.10.264) : la vraie réponse de GDELT sur les questions restées sans recherche.

Décision d'auteur du 2026-11-18, 13 h 14 (« pourquoi GDELT est en erreur ? il faut contrôler cela, sinon cette
situation va se reproduire »). La trace du 2026-11-18 laissait 40 questions où Exa et TinyFish ne trouvaient rien
et où GDELT, dernier relais, était en erreur, sans le motif (message tronqué). Aucun modèle de langue, aucun coût.
"""
from __future__ import annotations

import asyncio
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import alphabet_recherche as ar_
import banc_jugement_alphabet as bja


async def principal() -> int:
    traces = [json.loads(l) for l in Path("registre/trace-recherche-jugement.jsonl").read_text(encoding="utf-8").splitlines()]
    derniere = {x["question_id"]: x for x in traces}
    pannes = {q for q, x in derniere.items() if x["trace"]["moteur"] in ("panne", "aucun", "aucun résultat")}
    titres = {f'{x["source"]}:{x["id"]}:{x["jeu"]}': x for x in bja.candidates()}
    bilan, lignes = Counter(), []
    for qid in sorted(pannes):
        x = titres.get(qid)
        if not x:
            continue
        avant = datetime.fromisoformat(x["jeu"]).replace(tzinfo=timezone.utc)
        try:
            t = await ar_.gdelt(x["titre"], avant)
            n = t.count(" — http")
            etat = f"{n} article(s)" if n else "réponse vide (aucun article)"
            bilan["articles" if n else "vide"] += 1
        except Exception as e:
            etat = f"{type(e).__name__}: {str(e)[:200]}"
            bilan[type(e).__name__ + (" (texte GDELT)" if "GDELT :" in str(e) else "")] += 1
        lignes.append({"question_id": qid, "jeu": x["jeu"], "requete": ar_.gdelt_mots(x["titre"]), "gdelt": etat})
        print(f"{x['jeu']} | {ar_.gdelt_mots(x['titre'])[:70]} | {etat}")
    Path("registre/sonde-gdelt.json").write_text(json.dumps({"bilan": dict(bilan), "questions": lignes},
                                                           ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(dict(bilan), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(principal()))
