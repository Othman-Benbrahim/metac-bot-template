"""Collecte du rythme de publication des sites officiels : « le silence des routines » (bot 0.10.299, en ombre).

Décision d'auteur du 2026-11-18, 22 h 35 (carte blanche). Idée : une rupture d'habitude (un ministère qui publie chaque
jour et se tait, un point presse annulé, un agenda présidentiel qui se vide) peut parler plus que le bruit. Cartes :
PÉRIODICITÉ, SEUIL. Prolonge preenregistrements/silence-*. Préenregistrement : preenregistrements/sources-hors-cadre.md.

Sources : flux RSS OFFICIELS (registre/routines-sources.csv, modifiable). Seuls des COMPTES par source et par jour de
publication sont gardés (registre/routines-comptes.csv), plus les empreintes des éléments déjà vus
(registre/routines-vus.txt) et un bilan de santé (registre/routines-sante.csv). Aucun texte. robots.txt respecté ;
une source qui refuse est notée, jamais forcée.

    python collecte_routines.py
"""
from __future__ import annotations

import csv
import hashlib
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import httpx

import politesse

REG = Path(os.environ.get("ALPHABET_REGISTRE", "registre"))
SOURCES = REG / "routines-sources.csv"
COMPTES = REG / "routines-comptes.csv"
VUS = REG / "routines-vus.txt"
SANTE = REG / "routines-sante.csv"


def elements(xml: bytes) -> list[tuple[str, str]]:
    """(identifiant, jour de publication AAAA-MM-JJ) de chaque élément RSS ou Atom."""
    racine = ET.fromstring(xml)
    out = []
    for it in racine.iter():
        tag = it.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        champs = {c.tag.split("}")[-1]: (c.text or "").strip() or c.attrib.get("href", "") for c in it}
        ident = champs.get("guid") or champs.get("id") or champs.get("link") or champs.get("title", "")
        brut = champs.get("pubDate") or champs.get("published") or champs.get("updated") or champs.get("date") or ""
        jour = None
        try:
            jour = parsedate_to_datetime(brut).astimezone(timezone.utc).date().isoformat()
        except Exception:
            try:
                jour = datetime.fromisoformat(brut.replace("Z", "+00:00")).date().isoformat()
            except Exception:
                pass
        if ident and jour:
            out.append((ident, jour))
    return out


def principal() -> int:
    sources = list(csv.DictReader(SOURCES.open(encoding="utf-8")))
    vus = set(VUS.read_text(encoding="utf-8").split()) if VUS.exists() else set()
    nouveaux: dict[tuple[str, str], int] = {}
    sante = []
    aujourdhui = datetime.now(timezone.utc).date().isoformat()
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=30, follow_redirects=True) as c:
        for s in sources:
            nom, url = s["source"], s["url"]
            etat, n = "ok", 0
            try:
                if not politesse.autorise(c, url):
                    etat = "refusé par robots.txt"
                else:
                    r = c.get(url)
                    if r.status_code >= 400:
                        etat = f"HTTP {r.status_code}"
                    else:
                        for ident, jour in elements(r.content):
                            h = hashlib.sha1(f"{nom}|{ident}".encode()).hexdigest()[:16]
                            if h in vus:
                                continue
                            vus.add(h)
                            nouveaux[(nom, jour)] = nouveaux.get((nom, jour), 0) + 1
                            n += 1
            except Exception as e:
                etat = f"{type(e).__name__}: {str(e)[:100]}"
            sante.append({"jour": aujourdhui, "source": nom, "etat": etat, "nouveaux": n})
            print(f"{nom} : {etat} ; {n} nouvel(s) élément(s)", flush=True)
    neuf = not COMPTES.exists()
    with COMPTES.open("a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if neuf:
            w.writerow(["source", "jour", "n"])
        for (nom, jour), n in sorted(nouveaux.items()):
            w.writerow([nom, jour, n])
    VUS.write_text("\n".join(sorted(vus)) + "\n", encoding="utf-8")
    neuf = not SANTE.exists()
    with SANTE.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["jour", "source", "etat", "nouveaux"])
        if neuf:
            w.writeheader()
        w.writerows(sante)
    return 0


if __name__ == "__main__":
    sys.exit(principal())
