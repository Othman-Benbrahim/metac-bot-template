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

0.10.16 : Amazon Bedrock, provisoire (crédits jusqu'au 23 novembre 2026). Les modèles s'écrivent
« bedrock/<identifiant ou profil d'inférence> » (ex. « bedrock/global.anthropic.claude-opus-5-5 ») ; la clé d'API Bedrock
va dans le secret AWS_BEARER_TOKEN_BEDROCK, la région dans la variable AWS_REGION_NAME (us-east-1 par défaut). Placés en
tête de suite, devant les modèles Fantasy : quand la clé est absente, refusée ou les crédits épuisés (échec durable),
le passage retombe sur Fantasy. Changer de modèle, c'est changer de codeur : le score sépare les lignes par modèle.
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


PASSAGERE = re.compile(r"at capacity|ServiceUnavailable|\b50[234]\b|RateLimit|Throttling|TooManyRequests|\b429\b|Timeout|timed out|overloaded",
                      re.I)


def passagere(r: dict) -> bool:
    """Une indisponibilité qui passe (saturation, quota par minute, délai) : on peut réessayer plus tard."""
    return bool(r.get("erreur")) and not r.get("disponible") and bool(PASSAGERE.search(r["erreur"]))


async def choisir(env=os.environ, appel=None, attendre=asyncio.sleep) -> tuple[dict, list[dict]]:
    """Premier modèle valide de chaque suite. Le petit rôle retombe sur le principal ; le contradicteur peut manquer.

    0.7.3 : si AUCUN modèle principal ne répond et que tous les échecs sont passagers (modèle saturé, quota par
    minute), la suite principale est ressayée après une attente (ALPHABET_SONDE_TOURS tours, 3 par défaut ; 60 s
    puis 120 s). Un échec durable (modèle inconnu, clé refusée) ne fait pas attendre."""
    choix, essais = {}, []
    tours = max(1, int(env.get("ALPHABET_SONDE_TOURS") or "3"))
    for role, var in ROLES.items():
        choix[role] = None
        for tour in range(tours if role == "principal" else 1):
            if tour:
                await attendre(60 * tour)
            ce_tour = []
            for m in suite(env.get(var)):
                r = await sonder(m, appel)
                r["role"] = role
                if tour:
                    r["tour"] = tour + 1
                essais.append(r)
                ce_tour.append(r)
                if r["json_ok"]:
                    choix[role] = m
                    break
            if choix[role] or not ce_tour or not all(passagere(r) for r in ce_tour):
                break
    if choix["petit"] is None:
        choix["petit"] = choix["principal"]
    return choix, essais


def appliquer(choix: dict, env=os.environ) -> None:
    """Remplace chaque suite par le modèle retenu, pour la configuration du bot ; « {petit} » dans
    ALPHABET_CHERCHEUR devient le petit modèle retenu (ex. « smart-searcher/{petit} »)."""
    # 0.7.4 : secours des rôles légers en cours de passage : le reste de la suite légère, puis le principal retenu.
    reste = [m for m in suite(env.get("ALPHABET_PETIT_LLM")) if m != choix.get("petit")]
    env["ALPHABET_PETIT_SECOURS"] = ",".join(dict.fromkeys(reste + [choix.get("principal") or ""]).keys()).strip(",")
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
