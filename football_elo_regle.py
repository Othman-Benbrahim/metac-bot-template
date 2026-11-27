"""Brique « football : vainqueur de championnat » (décision de l'auteur, 2026-11-27, 12 h 34 ; méthode retenue par
preenregistrements/football-championnats.md : critère atteint, 0,066 contre 0,219 pour « un parmi N » sur 5 940
questions construites ; 0,152 contre 0,772 sur 26 questions réelles).

Lit registre/football/etat.json (collecte_football.py : classement et résultats Wikipédia, Elo calculé sur
openfootball) et simule 10 000 fins de saison. C'est une mesure : base, pas mélange (comme l'Elo du tennis).
Abstention : autre forme que « gagner le championnat » ; championnat, saison ou club non reconnu ; classement mis à jour
il y a plus de FRAICHEUR jours ; classement et matchs restants incohérents ; état calculé il y a plus de 3 jours.
"""
from __future__ import annotations

import json
import re
from datetime import date
from functools import lru_cache
from pathlib import Path

ICI = Path(__file__).resolve().parent
ETAT = ICI / "registre" / "football" / "etat.json"
FRAICHEUR = 10
TIRAGES = 10_000
GAGNER = re.compile(r"\bwins?\b|\bwin the\b|\bbe the (winner|champion)\b|\bchampions?\b", re.I)
AUTRES = re.compile(r"\b(top \d|top four|top-four|finish|relegat\w*|reach|qualif\w*|place|second|runner-up|points|goals?|"
                    r"scorer|unbeaten|invincible|cup|champions league|europa|conference league|vs\.?|beat|iff|if )\b", re.I)
LIGUES = [("en.1", r"(?<!indian )\b(english )?premier league\b"), ("es.1", r"\bla ?liga\b"), ("it.1", r"\bserie a\b"),
          ("de.1", r"\bbundesliga\b"), ("fr.1", r"\bligue 1\b")]


@lru_cache(1)
def _etat() -> dict:
    try:
        return json.loads(ETAT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _saison_titre(titre: str) -> int | None:
    m = re.search(r"\b(20\d\d)\s*[–/-]\s*(\d\d|20\d\d)\b", titre)
    return int(m.group(1)) if m else None


def reconnaitre(titre: str) -> tuple[str, str] | None:
    """(championnat, club) ou None."""
    t = titre or ""
    if not GAGNER.search(t) or AUTRES.search(t):
        return None
    div = next((d for d, rx in LIGUES if re.search(rx, t, re.I)), None)
    m = re.match(r"\s*(?:will|can)\s+(?:the\s+)?(.+?)\s+(?:wins?|be the)\b", t, re.I)
    return (div, m.group(1).strip()) if div and m else None


def simuler(equipes: dict, restants: list, H: float, pn: float, graine: int = 20261127) -> dict:
    import numpy as np
    import banc_football as bf
    codes = sorted(equipes)
    ix = {c: i for i, c in enumerate(codes)}
    rng = np.random.default_rng(graine)
    pts = np.tile(np.array([equipes[c]["points"] for c in codes], dtype=float), (TIRAGES, 1))
    if restants:
        pr = np.array([bf.probas_match(equipes[h]["elo"], equipes[g]["elo"], H, pn) for h, g in restants])
        u = rng.random((TIRAGES, len(restants)))
        v = u < pr[:, 0]
        n = (~v) & (u < pr[:, 0] + pr[:, 1])
        l = ~(v | n)
        for col, (h, g) in enumerate(restants):
            pts[:, ix[h]] += 3 * v[:, col] + n[:, col]
            pts[:, ix[g]] += 3 * l[:, col] + n[:, col]
    gagnant = np.argmax(pts + rng.random(pts.shape) * 0.5, axis=1)
    cpt = np.bincount(gagnant, minlength=len(codes))
    return {c: float(cpt[ix[c]]) / TIRAGES for c in codes}


def estimer(titre: str, jour: date) -> dict | None:
    import banc_football as bf
    r = reconnaitre(titre)
    E = _etat()
    if r is None or not E:
        return None
    div, club = r
    L = (E.get("ligues") or {}).get(div) or {}
    s = _saison_titre(titre)
    if not L.get("equipes") or (s is not None and s != E.get("saison")):
        return None
    try:
        if (jour - date.fromisoformat(E["calcule_le"])).days > 3:
            return None
        maj = L.get("mise_a_jour")
        if not L.get("complete") and (not maj or (jour - date.fromisoformat(maj)).days > FRAICHEUR):
            return None
    except (KeyError, ValueError):
        return None
    ctl = L.get("controle") or {}
    if ctl.get("restants") != ctl.get("attendu_total", -1) - ctl.get("matchs_classement", 0):
        return None        # classement et grille de résultats pas à jour en même temps : abstention
    code = bf.trouver(club, {bf.cle(v["nom"]): k for k, v in L["equipes"].items()})
    if code is None:
        return None
    p = simuler(L["equipes"], L["restants"], L["H"], L["p_nul"])[code]
    eq = L["equipes"][code]
    return {"championnat": L["titre"], "club": eq["nom"], "points": eq["points"], "elo": eq["elo"],
            "restants": len(L["restants"]), "mise_a_jour": L.get("mise_a_jour"),
            "p_regle": min(max(p, 0.01), 0.99), "p": min(max(p, 0.01), 0.99)}
