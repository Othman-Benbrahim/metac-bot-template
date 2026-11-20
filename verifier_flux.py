"""Vérifier depuis les serveurs de GitHub qu'un flux RSS candidat est lisible, avant de l'ajouter (bot 0.10.391).

Leçon du run 44749464241 : S&P Global Energy répondait aux vérifications faites ailleurs, mais refuse (403) les serveurs
de GitHub. Décision de l'auteur du 2026-11-20, 15 h 05 : chercher d'autres sources spécialisées ouvertes et les vérifier
d'abord. Pour chaque flux : fichier robots (politesse.autorise), code HTTP, nombre d'articles, date du plus récent.
Rien n'est collecté. `python verifier_flux.py` écrit registre/verification-flux.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

import httpx

import collecte_rss as cr
import politesse

SORTIE = Path("registre") / "verification-flux.md"
CANDIDATS = {
    "Mining Weekly, dernières nouvelles": "https://www.miningweekly.com/page/latest-news/feed",
    "MINING.COM": "https://www.mining.com/feed/",
    "Mining Technology": "https://www.mining-technology.com/feed/",
    "The Northern Miner": "https://www.northernminer.com/feed/",
    "International Mining": "https://im-mining.com/feed/",
    "Global Mining Review": "https://www.globalminingreview.com/rss/globalminingreview.xml",
    "Engineering & Mining Journal": "https://www.e-mj.com/feed/",
    "Canadian Mining Journal": "https://www.canadianminingjournal.com/feed/",
    "OilPrice.com": "https://oilprice.com/rss/main",
    "Rigzone": "https://www.rigzone.com/news/rss/rigzone_latest.aspx",
}


def principal() -> int:
    L = ["# Vérification des flux candidats depuis GitHub", "", "| Flux | Robots | HTTP | Articles | Plus récent |", "|---|---|---|---|---|"]
    ok = 0
    with httpx.Client(headers=cr.UA, follow_redirects=True, timeout=30) as c:
        for nom, url in CANDIDATS.items():
            if not politesse.autorise(c, url):
                L.append(f"| {nom} | refusé | — | — | — |")
                continue
            try:
                r = c.get(url)
                arts = cr.articles(r.content) if r.status_code == 200 else []
                recent = max((a["jour"] for a in arts), default="—")
                L.append(f"| {nom} | autorisé | {r.status_code} | {len(arts)} | {recent} |")
                ok += bool(arts)
            except Exception as e:
                L.append(f"| {nom} | autorisé | erreur {type(e).__name__} | — | — |")
    L += ["", f"{ok} flux lisibles sur {len(CANDIDATS)}."]
    SORTIE.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
