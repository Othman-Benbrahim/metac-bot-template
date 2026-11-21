"""Carte de couverture : quelles fiches d'écosystème gouvernent les questions du banc de M (piste écosystémique,
décision de l'auteur du 2026-11-21, 11 h 14). Descriptif, rien dans le bot.

Le modèle choisit PAR LE SENS, et non par les mots, de 0 à 2 fiches parmi les fiches d'écosystème, d'après le titre de
la question. Les fiches lui sont présentées par leur nom et leur but seulement, sans aucun fait daté de 2026 ou après
(les questions du banc datent de 2026 : pas de fuite par les fiches). Sert à décider quelles fiches achever en priorité.

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

SORTIE = Path("registre") / "couverture-fiches-banc-m.json"
MODELE = bja.MODELE
_ANNEE_RECENTE = re.compile(r"[^.;()]*\b20(2[6-9]|[3-9]\d)\b[^.;()]*")


def sans_dates_recentes(texte: str) -> str:
    """Retire les propositions qui citent une année de 2026 ou après."""
    return re.sub(r"\s{2,}", " ", _ANNEE_RECENTE.sub("", texte or "")).strip(" ;,")


def fiches() -> dict[str, str]:
    out = {}
    for f in sorted(glob.glob("ecosystemes/*.yaml")):
        d = yaml.safe_load(open(f, encoding="utf-8"))
        if isinstance(d, dict) and d.get("theme") and d.get("compartiments"):
            but = sans_dates_recentes(str((d.get("declaration") or {}).get("but", "")))
            but = re.sub(r"\(questions du tournoi[^)]*\)", "", but)
            out[d["theme"]] = f"{d.get('nom')} : {but}"
    return out


def consigne(titre: str, catalogue: dict[str, str]) -> str:
    liste = "\n".join(f"- {k} : {v}" for k, v in catalogue.items())
    return f"""Voici une question de prévision et une liste d'écosystèmes. Un écosystème est un domaine avec ses propres
acteurs, règles et déclencheurs. Choisis, PAR LE SENS (ce qui décide réellement de l'issue), de 0 à 2 écosystèmes dont
les règles gouvernent l'issue de la question. Ne choisis pas un écosystème parce qu'un mot de la question y figure. Si
aucun ne gouverne l'issue, rends une liste vide.

QUESTION : {titre}

ÉCOSYSTÈMES :
{liste}

Rends UNIQUEMENT un objet JSON : {{"fiches": ["identifiant", ...], "pourquoi": "une phrase"}}"""


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
            r = ap.extraire_json(await am.llm(MODELE, temperature=0.2, timeout=120, allowed_tries=2).invoke(
                consigne(x["titre"], catalogue)))
            ch = [f for f in (r.get("fiches") or []) if f in catalogue][:2]
            out.append({"question": qid, "titre": x["titre"], "issue": x["issue"], "fiches": ch,
                        "pourquoi": str(r.get("pourquoi", ""))[:200]})
        except Exception as e:
            out.append({"question": qid, "titre": x["titre"], "erreur": f"{type(e).__name__}"})
    compte = collections.Counter(f for o in out for f in o.get("fiches", []))
    aucune = sum(1 for o in out if not o.get("fiches") and "erreur" not in o)
    res = {"version_bot": ap.VERSION_BOT, "questions": len(out), "sans_fiche": aucune,
           "par_fiche": dict(compte.most_common()), "detail": out}
    SORTIE.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"sans fiche : {aucune} ; par fiche : {dict(compte.most_common())}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(principal()))
