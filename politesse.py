"""Politesse des collectes (bot 0.10.299) : identité claire, robots.txt respecté, aucun contournement.

Règles de l'auteur : respecter robots.txt, ne jamais contourner un blocage, sources publiques et institutionnelles,
aucune personne privée. Une source qui refuse est notée « refusée » dans le bilan de santé, jamais forcée.
"""
from __future__ import annotations

from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

UA = "alphabet-situationnel/0.10 (recherche non commerciale ; https://github.com/Othman-Benbrahim/metac-bot-template)"
_ROBOTS: dict[str, RobotFileParser | None] = {}
# 2026-11-25, 18 h 36 (décision de l'auteur, option « a ») : EXCEPTION DOCUMENTÉE. Le service de requêtes de Wikidata
# refuse les robots d'exploration dans son robots.txt, mais sa politique d'accès (wikidata.org/wiki/Wikidata:Data_access)
# le présente comme une interface pour les programmes : identité claire (UA ci-dessus), requêtes étroites, pas de rafale,
# respect des réponses 429 (Retry-After). Condition de l'auteur : « dans la mesure, petit à petit » → `pause_api`.
API_OFFICIELLES = {"https://query.wikidata.org": "Wikidata:Data_access (interface prévue pour les programmes)"}
PAUSE_API = 10   # secondes entre deux requêtes à une interface officielle


def pause_api(reponse=None) -> None:
    """Attente entre deux requêtes ; sur une réponse 429, attend ce que demande Retry-After (au moins 60 s)."""
    import time
    if reponse is not None and getattr(reponse, "status_code", 0) == 429:
        try:
            time.sleep(max(60, int(reponse.headers.get("Retry-After", "60"))))
        except ValueError:
            time.sleep(60)
        return
    time.sleep(PAUSE_API)


def autorise(client, url: str) -> bool:
    """robots.txt du site lu une fois par passage ; absent ou illisible = autorisé (usage courant), refus explicite = non."""
    p = urlparse(url)
    base = f"{p.scheme}://{p.netloc}"
    if base in API_OFFICIELLES:
        return True
    if base not in _ROBOTS:
        try:
            r = client.get(base + "/robots.txt", headers={"User-Agent": UA}, timeout=20)
            if r.status_code >= 400:
                _ROBOTS[base] = None
            else:
                rp = RobotFileParser()
                # 2026-11-25 (cas d'intellinews.com : /feed lu à tort) : des lignes vides À L'INTÉRIEUR d'un groupe
                # font oublier à l'analyseur de Python le « User-agent » et donc les refus qui suivent ; une ligne
                # « Disallow: » vide ne doit rien changer (norme) mais peut devenir « tout autorisé ». On retire les
                # commentaires, les lignes vides et les « Disallow: » vides : les groupes restent séparés par « User-agent ».
                lignes = []
                for l in r.text.splitlines():
                    l = l.split("#", 1)[0].strip()
                    if l and l.lower().replace(" ", "") != "disallow:":
                        lignes.append(l)
                rp.parse(lignes)
                _ROBOTS[base] = rp
        except Exception:
            _ROBOTS[base] = None
    rp = _ROBOTS[base]
    return True if rp is None else rp.can_fetch(UA, url)
