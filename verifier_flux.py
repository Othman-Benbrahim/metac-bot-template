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
# 2026-11-27 : sources primaires (décision de l'auteur, 18 h). Adresses SUPPOSÉES, à vérifier : rien n'est ajouté à la
# collecte avant ce passage. ReliefWeb n'est pas repris (retiré en 0.10.167 : page vide pour GitHub). Crisis Group a
# refusé GitHub (403) le 17/11 sur ses pages ; son flux est sondé une fois, et un nouveau refus sera respecté.
# ONU Info (retiré en 0.10.170) et le Parlement européen (déjà collecté par FeedBurner) ne sont pas repris.
CANDIDATS = {
    "Security Council Report, tout": "https://www.securitycouncilreport.org/feed/",
    "Security Council Report, What's in Blue": "https://www.securitycouncilreport.org/whatsinblue/feed/",
    "Crisis Group": "https://www.crisisgroup.org/rss",
    "ElectionGuide (IFES)": "https://www.electionguide.org/feed/",
    "ONU, couverture des réunions": "https://press.un.org/en/rss.xml",
    "Conseil de l'UE, communiqués": "https://www.consilium.europa.eu/en/rss/pressreleases.ashx",
    "Commission européenne, presse": "https://ec.europa.eu/commission/presscorner/api/rss?language=en",
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
