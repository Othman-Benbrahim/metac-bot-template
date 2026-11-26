"""Contradicteur des briques (amendement du 2026-11-26, preenregistrements/dossier-interne.md, sections B, C et E bis).

Il confronte une brique à la question : la question est-elle dans le domaine de la brique, et la mesure tient-elle
devant le terrain ? Réponse fermée ; il ne donne pas de probabilité. Le code vérifie la citation (hors domaine) et la
présence de sources datées (contre le terrain). Pour l'instant : banc hors ligne (hors domaine) et ombre dans le bot.
"""
from __future__ import annotations

import json
import re

VERDICTS = ("conforme", "hors_domaine", "contre_terrain")


def consigne(titre: str, criteres: str, famille: str, domaine: str, p_mesure: float, recherche: str = "") -> str:
    rech = recherche.strip() or "(none: judge the scope from the text only; do not use \"contre_terrain\")"
    return f"""You are the CONTRADICTOR of a forecasting bot. A coded rule (a "brick") produced a MEASURE for the
question below. Your only job is to check that the brick applies, and that its measure is not contradicted by facts.

QUESTION: {titre}
RESOLUTION CRITERIA: {criteres or "(not given)"}
BRICK FAMILY: {famille}
BRICK SCOPE (what it counts, and what it does not): {domaine}
MEASURE: {p_mesure:.3f}
RESEARCH: {rech}

Verdicts:
- "conforme": the question is what the brick counts, and nothing in the research contradicts the measure.
- "hors_domaine": the question asks something the brick does not count (an extra option joined by "or", a condition,
  a whole period instead of one event, a collective body instead of a person, a count of targets...). Quote the exact
  words of the question or criteria that put it outside the scope.
- "contre_terrain": the question is in scope, but dated facts in the research show the measure is far from reality.
  List the sources (url and date).

Answer with ONE JSON object and nothing else:
{{"verdict": "conforme"}}
or {{"verdict": "hors_domaine", "citation": "exact words"}}
or {{"verdict": "contre_terrain", "sources": [{{"url": "...", "date": "YYYY-MM-DD"}}]}}"""


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def analyser(rep: str, titre: str, criteres: str = "") -> dict:
    """Verdict admis par le code ; « illisible » ou « rejete » sinon."""
    m = re.search(r"\{.*\}", rep or "", re.S)
    try:
        x = json.loads(m.group(0)) if m else None
    except ValueError:
        x = None
    if not isinstance(x, dict) or x.get("verdict") not in VERDICTS:
        return {"verdict": "illisible"}
    v = x["verdict"]
    if v == "hors_domaine":
        c = _norm(x.get("citation") if isinstance(x.get("citation"), str) else "")
        if len(c) < 3 or c not in _norm(titre + " " + (criteres or "")):
            return {"verdict": "rejete", "motif": "citation_introuvable", "brut": x}
        return {"verdict": v, "citation": x["citation"]}
    if v == "contre_terrain":
        S = [s for s in (x.get("sources") or []) if isinstance(s, dict) and s.get("url") and s.get("date")]
        if not S:
            return {"verdict": "rejete", "motif": "sources_absentes", "brut": x}
        return {"verdict": v, "sources": S}
    return {"verdict": v}
