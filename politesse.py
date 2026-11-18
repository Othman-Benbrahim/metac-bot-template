"""Politesse des collectes (bot 0.10.299) : identité claire, robots.txt respecté, aucun contournement.

Règles de l'auteur : respecter robots.txt, ne jamais contourner un blocage, sources publiques et institutionnelles,
aucune personne privée. Une source qui refuse est notée « refusée » dans le bilan de santé, jamais forcée.
"""
from __future__ import annotations

from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

UA = "alphabet-situationnel/0.10 (recherche non commerciale ; https://github.com/Othman-Benbrahim/metac-bot-template)"
_ROBOTS: dict[str, RobotFileParser | None] = {}


def autorise(client, url: str) -> bool:
    """robots.txt du site lu une fois par passage ; absent ou illisible = autorisé (usage courant), refus explicite = non."""
    p = urlparse(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _ROBOTS:
        try:
            r = client.get(base + "/robots.txt", headers={"User-Agent": UA}, timeout=20)
            if r.status_code >= 400:
                _ROBOTS[base] = None
            else:
                rp = RobotFileParser()
                rp.parse(r.text.splitlines())
                _ROBOTS[base] = rp
        except Exception:
            _ROBOTS[base] = None
    rp = _ROBOTS[base]
    return True if rp is None else rp.can_fetch(UA, url)
