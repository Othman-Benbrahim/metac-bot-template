"""Cours quotidiens d'actions (Twelve Data, offre gratuite « Basic », clé TWELVEDATA_API_KEY) pour les questions de seuil
de prix (0.10.400).

Décision d'auteur du 2026-11-20 (19 h 49, option 1) : un appel à une API DOCUMENTÉE, avec une clé personnelle, dans les
limites de son offre, relève des conditions d'utilisation du service et non du fichier robots (le fichier robots de
api.twelvedata.com refuse les robots d'indexation). Partout ailleurs (pages, flux, sites sans clé), le fichier robots
reste respecté.
Conditions de l'offre gratuite (usage personnel et interne) : AUCUN cours brut n'est écrit dans le dépôt public ; les
cours sont lus à la demande, gardés en mémoire le temps d'un passage, et seuls des chiffres dérivés (dernier prix,
volatilité) sont scellés. Débit : une requête toutes les 8 s au plus (8 par minute, 800 par jour).
"""
from __future__ import annotations

import os
import time
from functools import lru_cache

import httpx

import politesse

URL = "https://api.twelvedata.com/time_series"
PAUSE = 8.0
_DERNIER_APPEL = [0.0]


@lru_cache(maxsize=64)
def cours(symbole: str, debut: str = "2018-01-01") -> tuple[tuple[str, float], ...]:
    """Clôtures quotidiennes (date, prix), du plus ancien au plus récent ; vide sans clé ou en cas d'erreur."""
    cle = os.environ.get("TWELVEDATA_API_KEY")
    if not cle:
        return ()
    attente = PAUSE - (time.monotonic() - _DERNIER_APPEL[0])
    if attente > 0:
        time.sleep(attente)
    try:
        with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=60) as c:
            r = c.get(URL, params={"symbol": symbole, "interval": "1day", "start_date": debut, "outputsize": 5000,
                                   "order": "ASC", "apikey": cle})
        _DERNIER_APPEL[0] = time.monotonic()
        d = r.json()
        if d.get("status") != "ok":
            return ()
        return tuple((v["datetime"][:10], float(v["close"])) for v in d.get("values") or [])
    except Exception:
        _DERNIER_APPEL[0] = time.monotonic()
        return ()
