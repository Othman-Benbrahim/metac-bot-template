"""Capture en direct de ce que lit le bot (bot 0.10.296).

Décision d'auteur du 2026-11-18, 22 h 04 (« j'accepte les deux, à appliquer »). Origine : ForecastGym (arXiv
2611.23045) : une recherche refaite après la résolution fuit, même filtrée par date ; seule une capture faite PENDANT
que la question est ouverte permet de rejouer plus tard sans fuite. Préenregistrement : preenregistrements/capture-recherche.md.

Rien ne change dans ce que le bot poste : la capture lit le texte de recherche déjà obtenu, l'écrit, et ne lève
jamais d'erreur. Le TEXTE va dans le cache de GitHub Actions (cache/recherche-tournoi, jamais publié dans le dépôt :
les articles ne sont pas à nous) ; le dépôt ne reçoit que les métadonnées (registre/capture-tournoi.jsonl : question,
date, moteur, adresses et dates des sources, empreinte, longueur, nom du fichier gelé).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)
DOSSIER = Path(os.environ.get("ALPHABET_CAPTURE_DOSSIER", "cache/recherche-tournoi"))


def capturer(question, texte: str) -> str | None:
    """Gèle le texte lu pour cette question et ce passage ; rend le nom du fichier, ou None. Jamais d'exception."""
    try:
        import alphabet_pipeline as ap
        import trace_recherche as tr
        qid = str(getattr(question, "id_of_question", None) or getattr(question, "id_of_post", None)
                  or getattr(question, "page_url", ""))
        maintenant = datetime.now(timezone.utc)
        fichier = hashlib.sha1(f"{qid}:{maintenant.isoformat()}".encode()).hexdigest()[:20] + ".txt"
        DOSSIER.mkdir(parents=True, exist_ok=True)
        (DOSSIER / fichier).write_text(texte or "", encoding="utf-8")
        t = tr.tracer(texte or "", maintenant.date().isoformat())
        fin = getattr(question, "scheduled_resolution_time", None) or getattr(question, "close_time", None)
        ligne = {"question_id": qid, "url": getattr(question, "page_url", "") or "",
                 "horodatage": maintenant.isoformat(timespec="seconds"),
                 "resolution_prevue": fin.astimezone(timezone.utc).date().isoformat() if fin else None,
                 "fichier": fichier, "version_bot": ap.VERSION_BOT,
                 "trace": {k: t[k] for k in ("moteur", "n_sources", "sources", "empreinte", "longueur") if k in t}}
        reg = ap.registre_ecrivable()
        with open(reg / "capture-tournoi.jsonl", "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(ligne, ensure_ascii=False, sort_keys=True) + "\n")
        return fichier
    except Exception as e:                                   # la capture ne bloque jamais une prévision
        logger.warning("capture de la recherche impossible : %s", e)
        return None
