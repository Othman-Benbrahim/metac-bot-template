"""Sonde de Telegram (aperçus publics) et des citations de l'ISW, avant tout collecteur (bot 0.10.249, rien d'écrit).

Décisions d'auteur du 2026-11-18 (4 h 31 et 4 h 36) : observatoire Telegram fondé sur les MÉTADONNÉES (rythme, horaire,
synchronie, silence ; claude/principe-metadonnees.md), liste des chaînes tenue à jour par les citations de l'Institute
for the Study of War (ISW). Avant d'écrire un collecteur, cette sonde vérifie, avec une pause de 3 secondes et au plus
une douzaine de requêtes :
1. robots.txt de t.me et de understandingwar.org (on s'arrête si l'accès est interdit) ;
2. l'aperçu public d'une chaîne (https://t.me/s/DeepStateUA) : code HTTP, nombre de messages lisibles, dates ;
3. la page des derniers bilans de l'ISW : liens vers des chaînes t.me cités dans un bilan récent.
Elle n'écrit RIEN dans le dépôt : tout va dans le journal du passage.

    python sonde_telegram.py
"""
from __future__ import annotations

import re
import sys
import time
from collections import Counter

import httpx

UA = {"User-Agent": "alphabet-situationnel-bot/1.0 (recherche non commerciale ; GitHub Othman-Benbrahim)"}


def lire(c: httpx.Client, url: str) -> httpx.Response | None:
    time.sleep(3)
    try:
        r = c.get(url)
    except Exception as e:
        print(f"  {url} : {type(e).__name__}")
        return None
    print(f"  {url} : HTTP {r.status_code}, {len(r.content)} octets")
    return r


def principal() -> int:
    with httpx.Client(headers=UA, timeout=60, follow_redirects=True) as c:
        for site in ("https://t.me/robots.txt", "https://www.understandingwar.org/robots.txt"):
            print(f"## {site}")
            r = lire(c, site)
            if r is not None and r.status_code == 200:
                print(r.text[:1500])
        print("\n## Aperçu public d'une chaîne")
        r = lire(c, "https://t.me/s/DeepStateUA")
        if r is not None and r.status_code == 200:
            h = r.text
            dates = re.findall(r'<time datetime="([^"]+)"', h)
            print(f"messages : {h.count('tgme_widget_message_wrap')} ; dates : {dates[:2]} … {dates[-2:]}")
            print("transferts (forwarded_from) :", h.count("tgme_widget_message_forwarded_from"))
            print("vues :", re.findall(r'tgme_widget_message_views">([^<]+)<', h)[:5])
        print("\n## ISW : bilans récents et chaînes citées")
        r = lire(c, "https://www.understandingwar.org/research/russia-ukraine/")
        liens = []
        if r is not None and r.status_code == 200:
            liens = [l for l in re.findall(r'href="(https://www\.understandingwar\.org/research/russia-ukraine/[^"#?]+)"', r.text)
                     if "assessment" in l or "campaign" in l]
            liens = list(dict.fromkeys(liens))
            print(f"{len(liens)} liens de bilans ; premiers : {liens[:5]}")
        for l in liens[:2]:
            rr = lire(c, l)
            if rr is not None and rr.status_code == 200:
                ch = Counter(m.lower() for m in re.findall(r'https?://t\.me/(?:s/)?([A-Za-z][A-Za-z0-9_]{3,31})', rr.text))
                print(f"  {len(ch)} chaînes citées, {sum(ch.values())} citations ; en tête : {ch.most_common(25)}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
