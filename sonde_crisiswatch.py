"""Sonde de CrisisWatch (International Crisis Group), avant tout collecteur (bot 0.10.230, rien d'enregistré).

Décision d'auteur du 2026-11-17 (15 h 21, 15 h 37). L'API de ReliefWeb est réservée aux organisations ; le site de Crisis
Group n'affiche aucune condition d'utilisation ; son robots.txt autorise les pages CrisisWatch mais INTERDIT la
pagination de la base (« Disallow: /crisiswatch/database?page=* ») : on ne la feuillette pas.

Cette sonde lit, avec une pause de 3 secondes entre deux requêtes et au plus une quinzaine de requêtes :
1. robots.txt (vérification au moment du passage) ;
2. la page /crisiswatch (bilan du mois) : codes HTTP, classes CSS et extraits autour des mentions de tendance,
   pour écrire ensuite un lecteur exact ;
3. le plan du site (sitemap.xml et ses sous-plans), pour trouver les adresses des bilans mensuels passés sans passer par
   la pagination interdite.
Elle n'écrit RIEN dans le dépôt (le texte appartient à Crisis Group) : tout va dans le journal du passage.

    python sonde_crisiswatch.py
"""
from __future__ import annotations

import re
import sys
import time
from collections import Counter

import httpx

BASE = "https://www.crisisgroup.org"
UA = {"User-Agent": "alphabet-situationnel-bot/1.0 (recherche non commerciale ; GitHub Othman-Benbrahim)"}
MOTS = ("deteriorat", "improv", "risk", "resolution", "unchanged", "trend", "arrow")
INTERDITS = ("/crisiswatch/database?page=",)


def lire(c: httpx.Client, url: str) -> httpx.Response | None:
    if any(i in url for i in INTERDITS):
        print(f"  (interdit par robots.txt, non lu) {url}")
        return None
    time.sleep(3)
    try:
        r = c.get(url)
    except Exception as e:
        print(f"  {url} : {type(e).__name__}")
        return None
    print(f"  {url} : HTTP {r.status_code}, {len(r.content)} octets")
    return r


def principal() -> int:
    n = 0
    with httpx.Client(headers=UA, timeout=60, follow_redirects=True) as c:
        print("## robots.txt")
        r = lire(c, f"{BASE}/robots.txt")
        n += 1
        if r is not None and r.status_code == 200:
            print("\n".join(l for l in r.text.splitlines() if "crisiswatch" in l.lower() or l.startswith("User-agent")))
        print("\n## Page /crisiswatch")
        r = lire(c, f"{BASE}/crisiswatch")
        n += 1
        if r is not None and r.status_code == 200:
            h = r.text
            classes = Counter(cl for att in re.findall(r'class="([^"]+)"', h) for cl in att.split()
                              if any(m in cl.lower() for m in MOTS))
            print("Classes CSS liées aux tendances :", classes.most_common(40))
            liens = sorted(set(re.findall(r'href="(/crisiswatch[^"#]*)"', h)))
            print(f"Liens /crisiswatch… ({len(liens)}) :", liens[:60])
            for mot in ("Deteriorated", "Improved", "Conflict Risk Alert", "Resolution Opportunit"):
                i = h.find(mot)
                print(f"\n--- extrait autour de « {mot} » (position {i}) ---")
                if i >= 0:
                    print(re.sub(r"\s+", " ", h[max(0, i - 1200): i + 1500]))
            titres = re.findall(r"<h[23][^>]*>(.*?)</h[23]>", h, flags=re.S)
            print("\nTitres h2/h3 :", [re.sub(r"<[^>]+>|\s+", " ", t).strip() for t in titres][:80])
        print("\n## Plan du site")
        r = lire(c, f"{BASE}/sitemap.xml")
        n += 1
        if r is not None and r.status_code == 200:
            locs = re.findall(r"<loc>([^<]+)</loc>", r.text)
            print(f"{len(locs)} entrées ; premières :", locs[:20])
            sous = [l for l in locs if "sitemap" in l][:10]
            cw = [l for l in locs if "crisiswatch" in l]
            for s in sous:
                if n >= 15:
                    break
                rs = lire(c, s)
                n += 1
                if rs is not None and rs.status_code == 200:
                    cw += [l for l in re.findall(r"<loc>([^<]+)</loc>", rs.text) if "crisiswatch" in l]
            cw = sorted(set(cw))
            print(f"\nAdresses contenant « crisiswatch » : {len(cw)}")
            print("Premières :", cw[:40])
            print("Dernières :", cw[-40:])
    print(f"\n{n} requêtes au total.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
