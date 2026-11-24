"""Brique « annonces » (décision de l'auteur, 2026-11-24, 16 h 52 : « On commence » ; découpage matriochka).
Procédure : preenregistrements/annonces.md, versée avant le calcul.

Mécanisme (carte : calendriers promis qui glissent ; questionneur Metaculus) : une annonce attendue dans un délai arrive
moins souvent que le questionneur ne l'envisage. Niveau 1 : questions « announce » ; niveau 2 : par annonceur
(nomination, entreprise, gouvernement).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ICI = Path(__file__).resolve().parent
TAUX = ICI / "ecosystemes" / "annonces-taux.json"
ANNONCE = re.compile(r"\bannounc\w*", re.I)
NOMINATION = re.compile(r"\b(announced as next|next james bond|fed chair|attorney general|nominee|as next)\b", re.I)
ENTREPRISE = re.compile(r"\b(openai|apple|microsoft|tiktok|harvey|gpt-?\d|google|meta|nvidia|tesla|amazon|ai company|"
                        r"arr|iphone|agi)\b", re.I)


def classe(titre: str) -> str | None:
    t = titre or ""
    if not ANNONCE.search(t):
        return None
    if NOMINATION.search(t):
        return "nomination"
    if ENTREPRISE.search(t):
        return "entreprise"
    return "gouvernement"


def estimer(titre: str) -> dict | None:
    c = classe(titre)
    if c is None or re.search(r"\b(not|refrain)\b", titre, re.I):    # polarité inversée : abstention
        return None
    try:
        T = json.loads(TAUX.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if T.get("niveau") == 2:
        p = T["taux"].get(c)
    elif T.get("niveau") == 1:
        p = T["taux"].get("annonce")
    else:
        return None
    return None if p is None else {"classe": c, "p": min(max(p, .01), .99), "niveau": T["niveau"]}
