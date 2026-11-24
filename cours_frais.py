"""Dernier cours frais d'une matière première (API Ninjas, offre gratuite, clé API_NINJAS_KEY ; source validée par
l'auteur le 2026-11-24, 22 h 50). FRED reprend le Brent de l'EIA, publié une fois par semaine : la brique des prix se
taisait sur les échéances courtes. On garde l'historique FRED pour la volatilité ; seul le dernier règlement journalier
vient d'ici. Offre gratuite : dernier règlement terminé, pas d'historique, usage non commercial.
Rien n'est écrit dans le dépôt : le cours est lu à la demande, gardé en mémoire le temps d'un passage ; seul le chiffre
utilisé est scellé dans le journal de la brique.
"""
from __future__ import annotations

import datetime as dt
import os
from functools import lru_cache

import httpx

URL = "https://api.api-ninjas.com/v1/commodityprice"
NOMS = {"DCOILBRENTEU": "brent_crude_oil"}            # série FRED → nom API Ninjas


@lru_cache(maxsize=16)
def dernier(serie: str) -> dict | None:
    """{"jour", "prix", "contrat", "bourse"} ou None (pas de clé, série non couverte, erreur)."""
    cle, nom = os.environ.get("API_NINJAS_KEY"), NOMS.get(serie)
    if not cle or not nom:
        return None
    try:
        r = httpx.get(URL, params={"name": nom}, headers={"X-Api-Key": cle}, timeout=20)
        r.raise_for_status()
        x = r.json()
        x = x[0] if isinstance(x, list) else x
        p, t = float(x["price"]), int(x["updated"])
    except Exception:
        return None
    if p <= 0:
        return None
    return {"jour": dt.datetime.fromtimestamp(t, dt.timezone.utc).date().isoformat(), "prix": p,
            "contrat": x.get("futures_contract") or x.get("futures_contract_month"), "bourse": x.get("exchange")}
