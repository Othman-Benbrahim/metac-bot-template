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

0.10.100 : Microsoft Azure AI Foundry. Les modèles s'écrivent « azure_ai/<nom du déploiement> » (ex.
« azure_ai/mistral-medium-2505 ») ; la clé va dans le secret AZURE_AI_API_KEY, l'adresse du point d'accès dans le secret
AZURE_AI_API_BASE (litellm les lit lui-même). Plan de transition entre fournisseurs : TRANSITION-FOURNISSEURS.md.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import time

def famille_mistral(modele) -> bool:
    """0.10.100 : un modèle Mistral, quel que soit le fournisseur (API Mistral, Azure AI Foundry, Bedrock, OVH…)."""
    return "mistral" in str(modele).lower() or "magistral" in str(modele).lower()


# 0.10.100 (contrainte d'auteur du 2026-11-14 : plusieurs fournisseurs, plusieurs IA) : la version EXACTE du modèle servi
# (« mistral-medium-2508 », et non l'alias « mistral-medium-latest ») est relevée à chaque appel, par un traceur litellm.
# Le lecteur d'une série se définit par le modèle et sa version, pas par le fournisseur : même version ailleurs, même
# série ; autre version, autre lecteur.
SERVIS: dict[str, dict[str, int]] = {}
_TRACEUR = []


def installer_traceur() -> None:
    if _TRACEUR:
        return
    try:
        import litellm
        from litellm.integrations.custom_logger import CustomLogger
    except Exception:
        return

    class _Traceur(CustomLogger):
        def _noter(self, kwargs, response_obj):
            demande = f"{kwargs.get('custom_llm_provider') or '?'}/{kwargs.get('model') or '?'}"
            servi = str(getattr(response_obj, "model", None) or "?")
            SERVIS.setdefault(demande, {})
            SERVIS[demande][servi] = SERVIS[demande].get(servi, 0) + 1

        def log_success_event(self, kwargs, response_obj, start_time, end_time):
            self._noter(kwargs, response_obj)

        async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
            self._noter(kwargs, response_obj)

    t = _Traceur()
    litellm.callbacks = list(getattr(litellm, "callbacks", []) or []) + [t]
    _TRACEUR.append(t)


def servis_et_vider() -> dict:
    """Modèles servis depuis le dernier relevé : {demandé : {servi : appels}}."""
    out = {k: dict(v) for k, v in SERVIS.items()}
    SERVIS.clear()
    return out


def adapter(modele: str, kw: dict | None = None, env=os.environ) -> tuple[str, dict]:
    """0.10.101 : nom de modèle et paramètres litellm selon le fournisseur.

    « azure_ai/<déploiement> » avec un point d'accès Foundry de la forme « …/openai/v1[/responses] » (API OpenAI v1 de
    Microsoft Foundry, 2026) : appelé comme un modèle compatible OpenAI, avec l'adresse et la clé Azure passées
    explicitement (elles ne se mélangent pas avec la passerelle OPENAI_API_BASE). Les modèles de raisonnement (gpt-5,
    o1/o3/o4) n'acceptent que leur température par défaut : `drop_params` retire ce qu'ils refusent."""
    kw = dict(kw or {})
    m = str(modele)
    if m.startswith("azure_ai/") and "/openai/" in (env.get("AZURE_AI_API_BASE") or ""):
        base = re.sub(r"/(responses|chat/completions)/?$", "", env["AZURE_AI_API_BASE"].strip().rstrip("/"))
        dep = m.split("/", 1)[1]
        m = f"openai/{dep}"
        kw.update(base_url=base, api_key=env.get("AZURE_AI_API_KEY"))
    nom = m.rsplit("/", 1)[-1].lower()
    if re.match(r"(gpt-5|o1|o3|o4)", nom):
        kw["drop_params"] = True
        kw.pop("top_p", None)
    return m, kw


def llm(modele: str, **kw):
    """Un GeneralLlm adapté au fournisseur (voir `adapter`)."""
    from forecasting_tools import GeneralLlm
    m, k = adapter(modele, kw)
    return GeneralLlm(model=m, **k)


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
        # 0.10.59 : délai imposé par le bot lui-même. Le délai confié à la bibliothèque n'a pas été tenu (banc du
        # 2026-11-13 : 44 minutes bloquées sur la sonde d'un modèle NVIDIA, sans erreur).
        delai = float(os.environ.get("ALPHABET_SONDE_DELAI") or "90")
        if appel is None:
            extra = {"top_p": 1} if famille_mistral(modele) else {}   # Mistral : top_p = 1 à température nulle
            co = llm(modele, temperature=0, timeout=60, allowed_tries=1, **extra).invoke(SONDE)
        else:
            co = appel(modele, SONDE)
        try:
            texte = await asyncio.wait_for(co, delai)
        except asyncio.TimeoutError:
            raise TimeoutError(f"aucune réponse en {delai:.0f} s") from None
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
