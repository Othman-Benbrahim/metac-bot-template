"""Suites de modèles et test de disponibilité (0.6.0).

Chaque rôle reçoit une SUITE de modèles, séparés par des virgules, dans une variable du dépôt :

    ALPHABET_LLM            réflexion : plan, taux de base, lecture, bras A
    ALPHABET_PETIT_LLM      tâches légères : résumés, analyse des réponses, modèle du chercheur Exa
    ALPHABET_CONTRADICTEUR  contradicteur, en ombre (facultatif)

Au début d'un passage qui a des questions à traiter, chaque suite est essayée dans l'ordre par un appel minuscule ;
le premier modèle qui rend un JSON correct est gardé pour TOUT le passage : une question n'est jamais lue par deux
codeurs. Le modèle retenu pour chaque rôle est écrit dans chaque ligne du registre.

Avec une passerelle compatible OpenAI (Fantasy AI), les modèles s'écrivent « openai/<identifiant> » et l'adresse de
la passerelle va dans OPENAI_API_BASE (variable ALPHABET_API_BASE du dépôt), la clé dans OPENAI_API_KEY (secret
FANTASY_API_KEY) : litellm les lit lui-même, pour le bot comme pour le chercheur Exa.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import time

ROLES = {"principal": "ALPHABET_LLM", "petit": "ALPHABET_PETIT_LLM", "contradicteur": "ALPHABET_CONTRADICTEUR"}
SONDE = 'Réponds uniquement par cet objet JSON, sans rien d\'autre : {"ok": true}'


def suite(valeur: str | None) -> list[str]:
    return [m.strip() for m in (valeur or "").split(",") if m.strip()]


def json_ok(texte: str) -> bool:
    m = re.search(r"\{.*\}", texte or "", re.S)
    if not m:
        return False
    try:
        return json.loads(m.group(0)).get("ok") is True
    except Exception:
        return False


async def sonder(modele: str, appel=None) -> dict:
    """Un appel minuscule ; rend {modele, disponible, json_ok, secondes, erreur}."""
    debut = time.monotonic()
    try:
        if appel is None:
            from forecasting_tools import GeneralLlm
            texte = await GeneralLlm(model=modele, temperature=0, timeout=60, allowed_tries=1).invoke(SONDE)
        else:
            texte = await appel(modele, SONDE)
        ok = json_ok(texte)
        return {"modele": modele, "disponible": True, "json_ok": ok, "secondes": round(time.monotonic() - debut, 1),
                "erreur": None if ok else f"réponse sans JSON valide : {str(texte)[:120]}"}
    except Exception as e:
        return {"modele": modele, "disponible": False, "json_ok": False,
                "secondes": round(time.monotonic() - debut, 1), "erreur": f"{type(e).__name__}: {e}"[:200]}


async def choisir(env=os.environ, appel=None) -> tuple[dict, list[dict]]:
    """Premier modèle valide de chaque suite. Le petit rôle retombe sur le principal ; le contradicteur peut manquer."""
    choix, essais = {}, []
    for role, var in ROLES.items():
        choix[role] = None
        for m in suite(env.get(var)):
            r = await sonder(m, appel)
            r["role"] = role
            essais.append(r)
            if r["json_ok"]:
                choix[role] = m
                break
    if choix["petit"] is None:
        choix["petit"] = choix["principal"]
    return choix, essais


def appliquer(choix: dict, env=os.environ) -> None:
    """Remplace chaque suite par le modèle retenu, pour la configuration du bot ; « {petit} » dans
    ALPHABET_CHERCHEUR devient le petit modèle retenu (ex. « smart-searcher/{petit} »)."""
    if choix.get("principal"):
        env["ALPHABET_LLM"] = choix["principal"]
    if choix.get("petit"):
        env["ALPHABET_PETIT_LLM"] = choix["petit"]
    env["ALPHABET_CONTRADICTEUR"] = choix.get("contradicteur") or ""
    if "{petit}" in env.get("ALPHABET_CHERCHEUR", "") and choix.get("petit"):
        env["ALPHABET_CHERCHEUR"] = env["ALPHABET_CHERCHEUR"].replace("{petit}", choix["petit"])
    env["ALPHABET_MODELES"] = json.dumps({**choix, "chercheur": env.get("ALPHABET_CHERCHEUR") or None},
                                         ensure_ascii=False)


def modeles_retenus(env=os.environ) -> dict | None:
    try:
        return json.loads(env["ALPHABET_MODELES"])
    except Exception:
        return None


if __name__ == "__main__":
    c, e = asyncio.run(choisir())
    print(json.dumps({"choix": c, "essais": e}, ensure_ascii=False, indent=2))
