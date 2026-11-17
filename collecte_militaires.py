"""Aéronefs militaires visibles au-dessus de chaque pays, relevés plusieurs fois par jour (bot 0.10.229, en ombre).

Décision d'auteur du 2026-11-17 (15 h 25), après le tri de l'annuaire OSINT (claude/tri-osint-start-me-2026-11-17.md) :
adsb.fi n'est pas un secours d'OpenSky pour les avions d'État (aucun historique), mais son point « militaires »
permet un indicateur À PART : combien d'aéronefs marqués militaires sont visibles au-dessus d'un pays.

Source : API ouverte d'adsb.fi (https://adsb.fi), point /v2/mil (aéronefs marqués militaires, position actuelle).
Conditions : usage personnel et non commercial, citation d'adsb.fi avec un lien vers son site ; 1 requête par seconde au
plus. Un relevé = UNE requête. Données fournies par adsb.fi (https://adsb.fi), réseau de récepteurs bénévoles.
Pays : frontières terrestres de Natural Earth (domaine public, 1:50 m) ; un aéronef au-dessus de la mer n'est rattaché à
aucun pays (compté dans « mer »).

Registre (comptes seulement, aucun appareil nommé) : registre/militaires-adsbfi.csv
  (releve, pays, appareils) ; releve = date et heure UTC du relevé ; appareils = nombre d'aéronefs distincts.
registre/militaires-adsbfi-releves.txt : relevés réussis (même ceux où un pays compte zéro).

Réserves : couverture inégale (récepteurs bénévoles, rares en Afrique et en Asie centrale) ; beaucoup d'appareils
militaires coupent leur transpondeur ; l'indicateur mesure ce qui est VISIBLE, et une hausse peut venir d'un nouveau
récepteur. À lire en relatif (un pays contre lui-même), jamais en absolu.

    python collecte_militaires.py
"""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

API = "https://opendata.adsb.fi/api/v2/mil"
FRONTIERES = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
              "ne_50m_admin_0_countries.geojson")
SORTIE = Path("registre") / "militaires-adsbfi.csv"
RELEVES = Path("registre") / "militaires-adsbfi-releves.txt"
UA = {"User-Agent": "alphabet-situationnel-bot/1.0 (recherche non commerciale ; GitHub Othman-Benbrahim ; donnees adsb.fi)"}


def polygones(geojson: dict) -> list[tuple[str, tuple[float, float, float, float], list[list[list[float]]]]]:
    """[(code ISO à deux lettres, boîte, anneaux)] ; un polygone par entrée (MultiPolygon déplié)."""
    out = []
    for f in geojson.get("features", []):
        p = f.get("properties") or {}
        code = p.get("ISO_A2_EH") or p.get("ISO_A2")
        if not code or code == "-99":
            continue
        g = f.get("geometry") or {}
        polys = [g["coordinates"]] if g.get("type") == "Polygon" else g.get("coordinates", []) if g.get("type") == "MultiPolygon" else []
        for anneaux in polys:
            xs = [pt[0] for pt in anneaux[0]]
            ys = [pt[1] for pt in anneaux[0]]
            out.append((code, (min(xs), min(ys), max(xs), max(ys)), anneaux))
    return out


def dans_anneau(x: float, y: float, anneau: list[list[float]]) -> bool:
    dedans, j = False, len(anneau) - 1
    for i in range(len(anneau)):
        xi, yi = anneau[i][0], anneau[i][1]
        xj, yj = anneau[j][0], anneau[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi:
            dedans = not dedans
        j = i
    return dedans


def pays_de(lon: float, lat: float, polys: list) -> str | None:
    for code, (x0, y0, x1, y1), anneaux in polys:
        if x0 <= lon <= x1 and y0 <= lat <= y1 and dans_anneau(lon, lat, anneaux[0]) \
                and not any(dans_anneau(lon, lat, trou) for trou in anneaux[1:]):
            return code
    return None


def compter(donnees: dict, polys: list) -> dict[str, int]:
    vus: dict[str, set] = {}
    for a in donnees.get("ac") or donnees.get("aircraft") or []:
        lat, lon, ident = a.get("lat"), a.get("lon"), a.get("hex")
        if lat is None or lon is None or not ident:
            continue
        code = pays_de(float(lon), float(lat), polys) or "mer"
        vus.setdefault(code, set()).add(ident)
    return {k: len(v) for k, v in vus.items()}


def principal() -> int:
    releve = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    with httpx.Client(headers=UA, timeout=60, follow_redirects=True) as c:
        try:
            g = c.get(FRONTIERES)
            g.raise_for_status()
            polys = polygones(g.json())
            r = c.get(API)
            r.raise_for_status()
            donnees = r.json()
        except Exception as e:
            print(f"Relevé impossible : {type(e).__name__}: {str(e)[:150]}")
            return 1
    comptes = compter(donnees, polys)
    SORTIE.parent.mkdir(exist_ok=True)
    neuf = not SORTIE.exists()
    with SORTIE.open("a", encoding="utf-8", newline="") as fo:
        w = csv.writer(fo)
        if neuf:
            w.writerow(["releve", "pays", "appareils"])
        for code in sorted(comptes):
            w.writerow([releve, code, comptes[code]])
    with RELEVES.open("a", encoding="utf-8") as fo:
        fo.write(releve + "\n")
    total = sum(comptes.values())
    haut = sorted(((v, k) for k, v in comptes.items() if k != "mer"), reverse=True)[:10]
    bilan = (f"{releve} : {total} aéronefs militaires visibles, {len(comptes) - ('mer' in comptes)} pays, "
             f"{comptes.get('mer', 0)} au-dessus de la mer ; en tête : " + ", ".join(f"{k} {v}" for v, k in haut)
             + ". Données : adsb.fi (https://adsb.fi).")
    print(bilan)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fo:
            fo.write(f"## Aéronefs militaires visibles (adsb.fi)\n\n{bilan}\n")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
