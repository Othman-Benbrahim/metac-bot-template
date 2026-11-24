"""Taux d'exécution des annonces, premier terrain : les droits de douane américains depuis janvier 2025 (bot 0.10.486).

Décision de l'auteur : mesure validée le 2026-11-23 à 18 h 05 ; terrain et sources laissés au choix de Claude le
2026-11-24 à 12 h 11 (« champ libre »). Rien n'entre dans le bot. Deux sources de producteurs indépendants (règle du
2026-11-19) :

- L'ANNONCE : TiRADE (Tariff Rates in Announcements, Declarations, and Events), Global Linkages Lab, Brown University.
  Chaque taux de droit de douane menacé, annoncé ou appliqué par le président, une ligne par document source (discours,
  Truth Social, décret, déclaration de la Maison-Blanche), codé à la main avec l'extrait et le lien. Mise à jour chaque
  lundi ; aucune licence (« les sources ont été obtenues gratuitement et n'en imposent aucune ») ; citer le jeu de
  données. https://www.globallinkages.org/datasets/tirade/
- LE FAIT : le Federal Register (gouvernement fédéral, domaine public) : proclamations et décrets présidentiels qui
  parlent de droits de douane, avis du représentant au commerce (USTR). API officielle, sans clé. On ne garde que le
  numéro, le type, le titre, les dates et le lien (jamais le texte).

Sorties : registre/annonces/tirade-<version>.csv (instantané tel quel, empreinte SHA-256 dans le journal) et
registre/annonces/federal-register-tarifs.jsonl (relu en entier à chaque passage).

    python collecte_annonces_tarifs.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

import httpx

import politesse

REG = Path(os.environ.get("ALPHABET_REGISTRE", "registre")) / "annonces"
TIRADE = "https://www.globallinkages.org/datasets/tirade/"
FR = "https://www.federalregister.gov/api/v1/documents.json"
DEBUT = "2025-01-20"
CHAMPS = ["document_number", "type", "presidential_document_type", "title", "signing_date", "publication_date",
          "effective_on", "executive_order_number", "proclamation_number", "citation", "html_url", "agencies"]


def versions(html: str) -> list[str]:
    """Les versions citées sur une page TiRADE (v1.1, v1.11…), de la plus récente à la plus ancienne."""
    vs = set(re.findall(r"datasets/tirade/(v\d+\.\d+)", html))
    return sorted(vs, key=lambda v: [int(x) for x in v[1:].split(".")], reverse=True)


def lien_csv(html: str, base: str) -> str | None:
    m = re.search(r'href="([^"]+?rate-statements\.csv)"', html) or re.search(r'href="([^"]+?\.csv)"', html)
    if not m:
        return None
    return str(httpx.URL(base).join(m.group(1)))


def tirade(c: httpx.Client) -> None:
    point = TIRADE + "v1.1"                                  # page qui liste toutes les versions
    if not politesse.autorise(c, point):
        print("::warning::TiRADE : refusé par robots.txt ; rien collecté.")
        return
    r = c.get(point)
    r.raise_for_status()
    vs = versions(r.text)
    print(f"TiRADE : versions vues {vs[:4]}…")
    for v in vs:
        if (REG / f"tirade-{v}.csv").exists():
            print(f"TiRADE : {v} déjà en registre.")
            return
        page = TIRADE + v
        p = c.get(page)
        time.sleep(1)
        if p.status_code != 200:
            print(f"TiRADE : page {v} : HTTP {p.status_code}")
            continue
        url = lien_csv(p.text, page) or f"{page}/tirade-{v}-rate-statements.csv"
        d = c.get(url)
        time.sleep(1)
        if d.status_code != 200 or not d.content.lstrip()[:200].lower().count(b","):
            print(f"TiRADE : CSV {v} illisible ({d.status_code}) : {url}")
            continue
        (REG / f"tirade-{v}.csv").write_bytes(d.content)
        print(f"TiRADE : {v} enregistré ({len(d.content)} octets, SHA-256 {hashlib.sha256(d.content).hexdigest()}) depuis {url}")
        return
    print("::warning::TiRADE : aucune version téléchargeable.")


def federal_register(c: httpx.Client) -> None:
    if not politesse.autorise(c, FR):
        print("::warning::Federal Register : refusé par robots.txt ; rien collecté.")
        return
    requetes = {
        "presidentiel": {"conditions[type][]": "PRESDOCU", "conditions[term]": "tariff OR duties OR \"Harmonized Tariff Schedule\""},
        "ustr": {"conditions[agencies][]": "trade-representative-office-of-united-states",
                 "conditions[term]": "tariff OR duties OR \"Section 301\""},
    }
    vus, out = set(), []
    for nom, cond in requetes.items():
        params = {**cond, "conditions[publication_date][gte]": DEBUT, "per_page": 1000, "order": "oldest",
                  "fields[]": CHAMPS}
        url, n = FR, 0
        while url:
            r = c.get(url, params=params if url == FR else None)
            r.raise_for_status()
            j = r.json()
            for d in j.get("results") or []:
                if d.get("document_number") in vus:
                    continue
                vus.add(d.get("document_number"))
                d["agencies"] = [a.get("name") for a in d.get("agencies") or [] if isinstance(a, dict)]
                d["requete"] = nom
                out.append(d)
                n += 1
            url = j.get("next_page_url")
            time.sleep(1)
        print(f"Federal Register ({nom}) : {n} documents depuis {DEBUT}")
    out.sort(key=lambda d: (d.get("signing_date") or d.get("publication_date") or "", d.get("document_number") or ""))
    (REG / "federal-register-tarifs.jsonl").write_text("".join(json.dumps(d, ensure_ascii=False) + "\n" for d in out),
                                                       encoding="utf-8")


def principal() -> int:
    REG.mkdir(parents=True, exist_ok=True)
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=60, follow_redirects=True) as c:
        for f in (tirade, federal_register):
            try:
                f(c)
            except Exception as e:                           # une source en panne ne bloque pas l'autre
                print(f"::warning::{f.__name__} : {type(e).__name__}: {str(e)[:200]}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
