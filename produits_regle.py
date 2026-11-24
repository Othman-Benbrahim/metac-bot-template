"""Brique « produits » (décision de l'auteur, 2026-11-24, 16 h 52 : « On commence » ; matriochka).
Procédure : preenregistrements/produits.md, versée avant le calcul.

Sous-familles (titre seul, dans cet ordre) : comparatif (« X avant Y », course entre deux événements) = exclu ;
modele_ia ; culture (jeux, films, livres, musique) ; espace ; finance (introduction en bourse, jeton) ; grand_public
(appareils, véhicules, logiciels) ; sinon hors famille.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ICI = Path(__file__).resolve().parent
TAUX = ICI / "ecosystemes" / "produits-taux.json"
SORTIE = re.compile(r"\b(release[sd]?|releases|launch\w*|announce\w*|file|be released)\b", re.I)
COMPARATIF = re.compile(r"\bbefore (gta|grand theft|hollow knight|twitter|gpt|drake)\b|\bmarried before\b", re.I)
SOUS = (("modele_ia", r"\b(gpt[- ]?\d|gpt\d|claude|gemini|grok|llama|mythos|language model)\b"),
        ("culture", r"\b(gta|grand theft|movie|film|book|album|taylor's version|spider-man|video game|iceman)\b"),
        ("espace", r"\bstarship\b"),
        ("finance", r"\b(ipo|s-1|token|stablecoin)\b"),
        ("grand_public", r"\b(iphone|vision pro|playstation|robotaxi|self driving|fsd|smart home device|browser|switch 2)\b"))


def classe(titre: str) -> str | None:
    t = titre or ""
    if not SORTIE.search(t) or COMPARATIF.search(t):
        return None
    for c, r in SOUS:
        if re.search(r, t, re.I):
            return c
    return None


def estimer(titre: str) -> dict | None:
    c = classe(titre)
    if c is None or re.search(r"\b(doesn't|does not|not|no)\b", titre, re.I):
        return None
    try:
        T = json.loads(TAUX.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    p = T["taux"].get(c) if T.get("niveau") == 2 else T["taux"].get("produit") if T.get("niveau") == 1 else None
    return None if p is None else {"classe": c, "p": min(max(p, .01), .99), "niveau": T["niveau"]}
