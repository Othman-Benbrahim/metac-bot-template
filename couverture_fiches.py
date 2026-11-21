"""Carte de couverture : quelles fiches d'écosystème gouvernent les questions du banc de M (piste écosystémique,
décision de l'auteur du 2026-11-21, 11 h 14). Descriptif, rien dans le bot.

Le modèle choisit PAR LE SENS, et non par les mots, de 0 à 2 fiches parmi les fiches d'écosystème, d'après le titre de
la question. Version 2 (2026-11-21, après la première carte, qui forçait des rattachements : 1 seule question sans fiche
sur 119) : chaque choix doit nommer le compartiment et la règle propre qui décide de l'issue ; le code rejette un choix
dont le compartiment n'appartient pas à la fiche ou sans règle écrite ; « aucune » est une réponse attendue.
Les fiches lui sont présentées par leur nom, leur but et les noms de leurs compartiments, sans aucune phrase citant une
année de 2026 ou après (les questions du banc datent de 2026 : pas de fuite par les fiches). Sert à décider quelles fiches achever en priorité.

    python couverture_fiches.py
"""
from __future__ import annotations

import asyncio
import collections
import glob
import json
import re
import sys
from pathlib import Path

import yaml

import alphabet_modeles as am
import alphabet_pipeline as ap
import banc_jugement_alphabet as bja

SORTIE = Path("registre") / "couverture-fiches-banc-m-v2.json"   # la v1 reste à côté, pour comparer
MODELE = bja.MODELE
_ANNEE_RECENTE = re.compile(r"[^.;()]*\b20(2[6-9]|[3-9]\d)\b[^.;()]*")


def sans_dates_recentes(texte: str) -> str:
    """Retire les propositions qui citent une année de 2026 ou après."""
    return re.sub(r"\s{2,}", " ", _ANNEE_RECENTE.sub("", texte or "")).strip(" ;,")


def fiches() -> dict[str, dict]:
    """theme -> {texte: nom et but sans faits récents, compartiments: {id: nom}}."""
    out = {}
    for f in sorted(glob.glob("ecosystemes/*.yaml")):
        d = yaml.safe_load(open(f, encoding="utf-8"))
        if isinstance(d, dict) and d.get("theme") and d.get("compartiments"):
            but = sans_dates_recentes(str((d.get("declaration") or {}).get("but", "")))
            but = re.sub(r"\(questions du tournoi[^)]*\)|les questions du tournoi[^;.]*", "", but).strip(" ;,")
            comps = {c["id"]: sans_dates_recentes(str(c.get("nom", c["id"]))) for c in d["compartiments"] if c.get("id")}
            out[d["theme"]] = {"texte": f"{d.get('nom')} : {but}", "compartiments": comps}
    return out


def consigne(titre: str, catalogue: dict[str, dict]) -> str:
    blocs = []
    for k, v in catalogue.items():
        comps = " ; ".join(f"{i} ({n})" for i, n in v["compartiments"].items())
        blocs.append(f"- {k} : {v['texte']}\n  compartiments : {comps}")
    liste = "\n".join(blocs)
    return f"""Voici une question de prévision et une liste d'écosystèmes. Chaque écosystème a ses compartiments, chacun
avec ses propres acteurs et ses propres règles. Tu dois dire quel écosystème GOUVERNE l'issue, c'est-à-dire lequel
contient la règle ou le mécanisme qui décidera de la réponse.

Règles strictes :
- Pour chaque écosystème retenu (au plus 2), nomme le compartiment précis (son identifiant) et écris en une phrase la
  règle ou le mécanisme de ce compartiment qui décide de l'issue.
- Un mot commun entre la question et l'écosystème ne suffit pas. Une règle vraie partout (« les gens réagissent aux
  nouvelles ») ne suffit pas non plus : la règle doit être propre à cet écosystème.
- Si aucun écosystème ne contient une telle règle, réponds par une liste vide. C'est une réponse normale et attendue.

QUESTION : {titre}

ÉCOSYSTÈMES :
{liste}

Rends UNIQUEMENT un objet JSON :
{{"choix": [{{"fiche": "identifiant", "compartiment": "identifiant", "regle": "une phrase"}}], "si_aucun": "une phrase"}}"""


def valider(r: dict, catalogue: dict[str, dict]) -> tuple[list[dict], list[dict]]:
    """Garde un choix seulement si la fiche existe, si le compartiment lui appartient et si la règle est écrite."""
    gardes, rejetes = [], []
    for c in (r.get("choix") or [])[:2]:
        f, comp, regle = str(c.get("fiche", "")), str(c.get("compartiment", "")), str(c.get("regle", "")).strip()
        ok = f in catalogue and comp in catalogue[f]["compartiments"] and len(regle) >= 20
        (gardes if ok else rejetes).append({"fiche": f, "compartiment": comp, "regle": regle[:300]})
    return gardes, rejetes


async def principal() -> int:
    catalogue = fiches()
    qs = {}
    for x in bja.lignes():
        if x.get("p_M") is not None and not x.get("exclue"):
            qs[x["question_id"].split(":")[1]] = x          # une ligne par question distincte
    print(f"{len(catalogue)} fiches ; {len(qs)} questions distinctes du banc de M.")
    out = []
    for qid, x in sorted(qs.items()):
        try:
            r = ap.extraire_json(await am.llm(MODELE, temperature=0.2, timeout=180, allowed_tries=2).invoke(
                consigne(x["titre"], catalogue)))
            gardes, rejetes = valider(r, catalogue)
            out.append({"question": qid, "titre": x["titre"], "issue": x["issue"], "choix": gardes,
                        "fiches": [g["fiche"] for g in gardes], "rejetes": rejetes,
                        "si_aucun": str(r.get("si_aucun", ""))[:200]})
        except Exception as e:
            out.append({"question": qid, "titre": x["titre"], "erreur": f"{type(e).__name__}"})
    compte = collections.Counter(f for o in out for f in o.get("fiches", []))
    aucune = sum(1 for o in out if not o.get("fiches") and "erreur" not in o)
    res = {"version_bot": ap.VERSION_BOT, "version_selection": 2, "questions": len(out), "sans_fiche": aucune,
           "choix_rejetes_par_le_code": sum(len(o.get("rejetes", [])) for o in out),
           "par_fiche": dict(compte.most_common()), "detail": out}
    SORTIE.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"sans fiche : {aucune} ; par fiche : {dict(compte.most_common())}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(principal()))
