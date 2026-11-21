"""Carte de couverture v3 : quelles RÈGLES SOURCÉES gouvernent les questions du banc de M (piste écosystémique, décision
de l'auteur du 2026-11-21, 12 h 17 : « ça me semble la bonne méthode »). Descriptif, rien dans le bot.

Les deux premières cartes laissaient le modèle désigner une fiche (v1) puis rédiger une règle (v2) : il en inventait
toujours une, souvent tautologique (« la décision relève de l'exécutif »). Ici, il ne rédige rien : il CHOISIT, parmi les
règles de ecosystemes/regles-coutumieres.yaml qui ont une source, celles qui gouvernent réellement l'issue, ou aucune. Une
question n'a de position que si une règle sourcée s'applique ; la couverture monte à mesure que les fiches s'achèvent.
Toute règle dont le texte cite une année de 2026 ou après est exclue en entier (les questions du banc datent de 2026 ;
un filtre partiel laissait des faits de 2026 sans leur date).

    python couverture_regles.py
"""
from __future__ import annotations

import asyncio
import collections
import json
import sys
from pathlib import Path

import alphabet_modeles as am
import alphabet_pipeline as ap
import banc_jugement_alphabet as bja
import regles_coutumieres as rc
from couverture_fiches import sans_dates_recentes

SORTIE = Path("registre") / "couverture-regles-banc-m.json"
MODELE = bja.MODELE
LONGUEUR = 420          # caractères de règle montrés par règle


def catalogue() -> dict[str, dict]:
    """id -> {ecosysteme, texte (sans faits de 2026 ou après), compartiments}, règles sourcées seulement."""
    out = {}
    for r in rc.regles():
        if r.get("statut") != "source":
            continue
        t = str(r.get("regle", ""))
        if sans_dates_recentes(t) != t.strip(" ;,"):   # la règle cite 2026 ou après : exclue en entier (un filtre
            continue                                   # partiel laissait des faits de 2026 sans leur date)
        out[r["id"]] = {"ecosysteme": sans_dates_recentes(str(r.get("ecosysteme", ""))), "texte": t[:LONGUEUR],
                        "compartiments": r.get("compartiments") or []}
    return out


def consigne(titre: str, cat: dict[str, dict]) -> str:
    liste = "\n".join(f"- {i} [{v['ecosysteme']}] : {v['texte']}" for i, v in cat.items())
    return f"""Voici une question de prévision et une liste de règles, chacune tirée d'une source vérifiée. Choisis les
règles (au plus 3) qui gouvernent RÉELLEMENT l'issue de cette question : celles qui, appliquées, changent ce qu'on doit
attendre (une procédure, un calendrier, un taux de base, un seuil). Une règle qui ne parle que du même domaine sans peser
sur l'issue ne compte pas. Si aucune ne s'applique, rends une liste vide : c'est une réponse normale et fréquente.

QUESTION : {titre}

RÈGLES :
{liste}

Rends UNIQUEMENT un objet JSON : {{"regles": ["identifiant", ...], "pourquoi": "une phrase par règle retenue"}}"""


async def principal() -> int:
    cat = catalogue()
    qs = {}
    for x in bja.lignes():
        if x.get("p_M") is not None and not x.get("exclue"):
            qs[x["question_id"].split(":")[1]] = x          # une ligne par question distincte
    print(f"{len(cat)} règles sourcées ; {len(qs)} questions distinctes du banc de M.")
    out = []
    for qid, x in sorted(qs.items()):
        try:
            r = ap.extraire_json(await am.llm(MODELE, temperature=0.2, timeout=180, allowed_tries=2).invoke(
                consigne(x["titre"], cat)))
            choisis = [str(i) for i in (r.get("regles") or [])]
            gardes = [i for i in choisis if i in cat][:3]
            out.append({"question": qid, "titre": x["titre"], "issue": x["issue"], "regles": gardes,
                        "rejetes": [i for i in choisis if i not in cat],
                        "compartiments": sorted({c for i in gardes for c in cat[i]["compartiments"]}),
                        "pourquoi": str(r.get("pourquoi", ""))[:400]})
        except Exception as e:
            out.append({"question": qid, "titre": x["titre"], "erreur": f"{type(e).__name__}"})
    compte = collections.Counter(i for o in out for i in o.get("regles", []))
    couvertes = sum(1 for o in out if o.get("regles"))
    res = {"version_bot": ap.VERSION_BOT, "version_selection": 3, "regles_au_catalogue": len(cat),
           "questions": len(out), "couvertes": couvertes,
           "identifiants_inventes": sum(len(o.get("rejetes", [])) for o in out),
           "par_regle": dict(compte.most_common()), "detail": out}
    SORTIE.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"couvertes : {couvertes} sur {len(out)} ; par règle : {dict(compte.most_common())}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(principal()))
