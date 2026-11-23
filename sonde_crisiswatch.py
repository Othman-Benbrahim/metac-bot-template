"""Sonde de la base CrisisWatch (Crisis Group) — bot 0.10.469, hors cadre, lancée à la main.

Décision de l'auteur, 2026-11-23, 7 h 46 : lire CrisisWatch dans le temps (depuis 2003) pour calibrer la lecture du bot
et mettre la carte à jour, au moyen d'un « standard de lecture » des cartes publiées. Avant d'écrire le lecteur, cette
sonde regarde COMMENT la base est construite : elle imprime dans le journal la structure HTML (balises, classes,
libellés courts de tendance, motifs de liens et paramètres de filtre), jamais le texte des résumés. Rien n'est écrit
dans le dépôt. robots.txt respecté ; une requête par page, espacées de 5 secondes.
"""
from __future__ import annotations

import collections
import re
import sys
import time
from html.parser import HTMLParser

import httpx

import politesse

PAGES = ["https://www.crisisgroup.org/crisiswatch/database",
         "https://www.crisisgroup.org/crisiswatch/database?page=1",
         "https://www.crisisgroup.org/crisiswatch"]
MOTS_TENDANCE = re.compile(r"(deteriorat|improv|unchanged|risk alert|resolution opportunit|conflict risk|"
                           r"trend|arrow|crisis_state|cw-)", re.I)


class Structure(HTMLParser):
    def __init__(self):
        super().__init__()
        self.classes = collections.Counter()
        self.balises = collections.Counter()
        self.liens = collections.Counter()
        self.params = collections.Counter()
        self.tendances = collections.Counter()
        self.attrs_tendance = collections.Counter()
        self.pile = []
        self.texte_court = collections.Counter()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.balises[tag] += 1
        for c in (a.get("class") or "").split():
            self.classes[c] += 1
        for k, v in attrs:
            v = v or ""
            if MOTS_TENDANCE.search(v) and k in ("class", "alt", "title", "aria-label", "data-trend", "src", "href"):
                self.attrs_tendance[f"{tag}[{k}]={v[:80]}"] += 1
        h = a.get("href") or ""
        if "crisiswatch" in h or "?" in h:
            base = re.sub(r"\d+", "N", h.split("#")[0])[:120]
            self.liens[base] += 1
            if "?" in h:
                for p in h.split("?", 1)[1].split("&"):
                    self.params[re.sub(r"=.*", "=", p)[:60]] += 1
        self.pile.append(tag)

    def handle_endtag(self, tag):
        if self.pile and self.pile[-1] == tag:
            self.pile.pop()

    def handle_data(self, data):
        d = " ".join(data.split())
        # seuls les libellés COURTS qui ressemblent à une tendance ou à une date sont relevés (pas de prose)
        if 0 < len(d) <= 40 and (MOTS_TENDANCE.search(d) or re.fullmatch(r"\d{1,2} \w+ \d{4}|\w+ \d{4}", d)):
            self.texte_court[d] += 1


def principal() -> int:
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=60, follow_redirects=True) as c:
        for url in PAGES:
            if not politesse.autorise(c, url):
                print(f"::warning::refusé par robots.txt : {url}")
                continue
            r = c.get(url)
            print(f"\n=== {url} → {r.status_code}, {len(r.text)} caractères, type {r.headers.get('content-type')}")
            if r.status_code != 200:
                continue
            s = Structure()
            s.feed(r.text)
            print("classes les plus fréquentes :", s.classes.most_common(60))
            print("attributs qui évoquent une tendance :", s.attrs_tendance.most_common(40))
            print("libellés courts (tendance, dates) :", s.texte_court.most_common(40))
            print("motifs de liens :", s.liens.most_common(30))
            print("paramètres de filtre :", s.params.most_common(30))
            print("formulaires et champs :", {k: v for k, v in s.balises.items() if k in ("form", "select", "option", "input")})
            time.sleep(5)
    return 0


if __name__ == "__main__":
    sys.exit(principal())
