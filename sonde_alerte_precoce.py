"""Sondes des sources d'alerte précoce : CrisisWatch (International Crisis Group) et ACAPS (bot 0.10.195).

Décision d'auteur du 2026-11-16 (17 h 18) : « on a qu'à le faire », après le pilote des revues (mécanismes trop locaux)
: chercher des calendriers saisonniers et des déclencheurs datés par pays chez les organismes d'alerte précoce.

Rien n'est écrit : les sondes affichent la forme des pages et des réponses, pour écrire ensuite les vrais collecteurs
sans deviner (leçon de la récolte Metaculus).
- CrisisWatch : base mensuelle depuis 2003, par pays (« deteriorated », « improved », « conflict risk alert »,
  « resolution opportunity »). Page publique https://www.crisisgroup.org/crisiswatch/database ; on cherche où se
  trouvent le pays, le mois et l'étiquette de tendance dans le HTML.
- ACAPS : API gratuite après inscription (https://api.acaps.org/register) ; jeton par identifiant et mot de passe
  (secrets ACAPS_USER, ACAPS_PASSWORD) ; on liste les points d'accès (calendrier saisonnier, INFORM Severity).
FEWS NET écarté pour l'instant : service américain suspendu en 2025, partiellement rouvert, pays retirés en 2026.
"""
from __future__ import annotations

import os
import re
import sys

import httpx

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
      "From": "alphabet-situationnel-bot (GitHub Othman-Benbrahim)"}


def sonde_crisiswatch(c: httpx.Client) -> None:
    print("=== CrisisWatch")
    for url in ("https://www.crisisgroup.org/crisiswatch/database", "https://www.crisisgroup.org/crisiswatch/database?page=1",
                "https://www.crisisgroup.org/crisiswatch"):
        try:
            r = c.get(url)
        except httpx.HTTPError as e:
            print(f"{url} : {type(e).__name__}")
            continue
        h = r.text
        print(f"{url} : HTTP {r.status_code}, {len(h)} caractères")
        for mot in ("deteriorat", "improv", "risk-alert", "risk alert", "resolution", "unchanged", "views-row", "c-crisiswatch",
                    "data-country", "<time", "datetime=", "?date=", "location", "crisiswatch-entry"):
            print(f"  « {mot} » : {len(re.findall(re.escape(mot), h, re.I))}")
        cls = re.findall(r'class="([^"]*(?:crisis|cw-|trend|alert|deterior|improv)[^"]*)"', h, re.I)
        print("  classes utiles :", sorted(set(cls))[:40])
        liens = sorted(set(re.findall(r'href="(/crisiswatch/database\?[^"]+)"', h)))[:25]
        print("  liens de filtre :", liens)
        i = h.lower().find("deteriorat")
        if i > 0:
            print("  extrait autour de « deteriorat » :", re.sub(r"\s+", " ", h[max(0, i - 900):i + 300]))


def sonde_acaps(c: httpx.Client) -> None:
    print("=== ACAPS")
    u, p = os.environ.get("ACAPS_USER", ""), os.environ.get("ACAPS_PASSWORD", "")
    jeton = os.environ.get("ACAPS_TOKEN", "").strip()
    if not jeton:
        if not u or not p:
            print("ACAPS_TOKEN, ou ACAPS_USER et ACAPS_PASSWORD, absents : inscription sur https://api.acaps.org/register")
            return
        r = c.post("https://api.acaps.org/api/v1/token-auth/", data={"username": u, "password": p})
        print(f"jeton : HTTP {r.status_code}")
        if r.status_code != 200:
            print("  ", r.text[:300])
            return
        jeton = (r.json() or {}).get("token", "")
    h = {"Authorization": f"Token {jeton}"}
    racine = c.get("https://api.acaps.org/api/v1/", headers=h)
    print(f"racine : HTTP {racine.status_code}")
    try:
        d = racine.json()
        for k, v in (d.items() if isinstance(d, dict) else []):
            print(f"  {k} : {v}")
    except ValueError:
        liens = sorted(set(re.findall(r'/api/v1/[a-z0-9\-/]+', racine.text)))
        print("  points d'accès trouvés :", liens[:60])
    for chemin in ("seasonal-events-calendar/", "seasonal-calendar/", "inform-severity-index/", "risk-list/"):
        rr = c.get(f"https://api.acaps.org/api/v1/{chemin}", headers=h)
        print(f"  {chemin} : HTTP {rr.status_code} {rr.text[:400]!r}")


def principal() -> int:
    with httpx.Client(headers=UA, timeout=60, follow_redirects=True) as c:
        sonde_crisiswatch(c)
        sonde_acaps(c)
    return 0


if __name__ == "__main__":
    sys.exit(principal())
