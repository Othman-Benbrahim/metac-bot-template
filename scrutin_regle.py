"""Brique « scrutin » restreinte aux scrutins à UN tour (S2) et aux PRIMAIRES (S3), branchée directement (décision de
l'auteur du 2026-11-27, 13 h 12 : « On ne peut pas le brancher directement, et voir les résultats après »).

Méthode : celle du banc (banc_scrutin.py, preenregistrements/etalon-scrutin.md), à l'identique. Moyenne des sondages des
30 jours avant la date, sur la page Wikipédia « Opinion polling for … » (API Wikimedia, robots.txt respecté), erreur
σ = 2,5 points × √(1 + jours restants / 30), 20 000 tirages, probabilité bornée à [0,02 ; 0,98].
Relance du 2026-11-27 (run 45995971880) : S2 0,093 contre 0,974 (9 questions), S3 0,213 contre 0,739 (14) ; S1
(deux tours) 1,083 contre 0,617 (7) : EXCLU. Ensemble non tranché de justesse ([−0,829 ; +0,007]) : le branchement
est une décision d'auteur prise avec ce risque connu ; suivi dans journal-scrutin.jsonl.
Abstention : hors forme, classe S1, page ou sondage du sujet introuvable, réseau indisponible.
"""
from __future__ import annotations

import re
import time
from datetime import date
from functools import lru_cache
from urllib.parse import quote

import banc_scrutin as bs

CORE = bs.CORE


@lru_cache(64)
def _page(election: str) -> tuple[str | None, str]:
    """(titre, wikitexte de la version actuelle) de la page de sondages ; (None, "") si introuvable."""
    import httpx
    import politesse
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=30, follow_redirects=True) as c:
        if not politesse.autorise(c, CORE + "/search/page"):
            return None, ""

        def get(url, **kw):
            for e in range(4):
                try:
                    r = c.get(url, **kw)
                except httpx.HTTPError:
                    time.sleep(3 * (e + 1))
                    continue
                if r.status_code in (429, 500, 502, 503, 504):
                    time.sleep(8 * (e + 1))
                    continue
                try:
                    return r.json() if r.status_code == 200 else {}
                except ValueError:
                    return {}
            return {}
        nu = re.sub(r"^(the|next)\s+", "", election.strip(), flags=re.I)
        for q in (f"Opinion polling for the {nu}", f"Opinion polling for the {election}", nu):
            pages = (get(CORE + "/search/page", params={"q": q, "limit": 5}) or {}).get("pages") or []
            bons = [p["title"] for p in pages if bs._titre_plausible(p["title"], election)]
            bons.sort(key=lambda t: "polling" not in t.lower())
            if bons:
                titre = bons[0]
                src = (get(CORE + f"/page/{quote(titre.replace(' ', '_'), safe='')}") or {}).get("source") or ""
                return (titre, src) if src else (None, "")
    return None, ""


def estimer(titre: str, jour: date, fin_question: str | None = None) -> dict | None:
    f = bs.forme(titre or "")
    if not f or f["classe"] == "S1":
        return None
    page, texte = _page(f["election"])
    if not texte:
        return None
    tabs = bs.tableaux(texte, jour.year)
    parts = bs.moyenne_sondages(tabs, jour, f["sujet"])
    if not parts:
        return None
    fin = bs._date_scrutin(texte) or (fin_question or "")[:10] or jour.isoformat()
    try:
        jr = (date.fromisoformat(fin[:10]) - jour).days
    except ValueError:
        return None
    if jr < 0:
        return None
    p = bs.probabilite(parts, f, jr)
    return {"classe": f["classe"], "sujet": f["sujet"], "election": f["election"], "page": page,
            "part_sujet": round(parts.get(parts["__sujet__"], 0), 1), "candidats": len(parts) - 1,
            "jours_restants": jr, "p_regle": p, "p": p}
