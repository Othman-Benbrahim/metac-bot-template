"""Sonde Webamon (offre gratuite, sans clé) : structure des réponses avant toute collecte (bot 0.10.340, ombre).

Demande de l'auteur du 2026-11-19, 12 h 24 (docs collées) : voir s'il y a quelque chose à prendre. Offre gratuite :
https://search.webamon.com, sans authentification, 25 résultats au plus par requête, quota quotidien. Le compartiment
visé est information-cyber:cyber (niveau technique), aujourd'hui sans série : il faudrait des COMPTES par jour
(campagnes de hameçonnage, nouveaux domaines malveillants), jamais un indicateur technique.

Cette sonde fait une poignée de requêtes (size=1) et n'écrit que la FORME des réponses : clés de premier niveau, présence
d'un total de résultats, noms des champs d'un document (sans leurs valeurs). Aucun domaine, aucune adresse, aucune
donnée de l'index « infostealers » (données personnelles volées : jamais interrogé). robots.txt vérifié.

    python sonde_webamon.py      # écrit registre/webamon-sonde.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

import politesse

BASE = "https://search.webamon.com"
SORTIE = Path("registre") / "webamon-sonde.json"
INDEX = ("detections", "new_domains", "scans")          # jamais « infostealers »
PAUSE = 5.0


def forme(obj, profondeur: int = 0):
    """Squelette d'un JSON : clés et types, sans aucune valeur textuelle (les nombres de premier niveau sont gardés :
    ce sont des totaux, pas des indicateurs)."""
    if isinstance(obj, dict):
        return {k: (v if profondeur == 0 and isinstance(v, (int, float)) else forme(v, profondeur + 1)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [forme(obj[0], profondeur + 1)] if obj else []
    return type(obj).__name__


def principal() -> int:
    out = {}
    with httpx.Client(headers={"User-Agent": politesse.UA, "Accept": "application/json"}, timeout=60) as c:
        if not politesse.autorise(c, BASE + "/search"):
            print("::warning::Webamon : refusé par robots.txt ; rien interrogé.")
            return 0
        for idx in INDEX:
            try:
                r = c.get(BASE + "/search", params={"lucene_query": "*", "index": idx, "size": 1})
                out[idx] = {"statut_http": r.status_code,
                            "forme": forme(r.json()) if r.headers.get("content-type", "").startswith("application/json") else None}
            except Exception as e:
                out[idx] = {"erreur": type(e).__name__}
            print(idx, json.dumps(out[idx], ensure_ascii=False)[:600], flush=True)
            time.sleep(PAUSE)
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
