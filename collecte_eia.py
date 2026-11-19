"""Collecte EIA : stocks, production et consommation hebdomadaires de pétrole américains (bot 0.10.333).

Décision d'auteur du 2026-11-19, 11 h 06 (point 7 validé) : brancher les stocks de brut. La FRED ne les publie pas
(WCESTUS1 et WCSSTUS1 n'y existent pas) ; ils viennent de l'Energy Information Administration, qui publie l'historique
de chaque série sur une page publique sans clé (LeafHandler). Hors cadre : rien n'entre dans le bot ; sert la fiche
energie-mondiale et son identité « variation des stocks = production − demande » (Schelling, ch. 2).
robots.txt respecté (politesse.autorise) ; une requête par série, pause entre deux.

Séries (codes EIA) :
- WCESTUS1 : stocks de brut hors réserve stratégique (milliers de barils) ;
- WCSSTUS1 : réserve stratégique (SPR) ;
- WCRFPUS2 : production de brut (milliers de barils par jour) ;
- WRPUPUS2 : produits livrés, toutes catégories (la demande apparente, milliers de barils par jour).
Registre : registre/eia.csv (serie, jour, valeur), réécrit à chaque passage.

Format de la page (vérifié au premier passage ; le script s'arrête sans rien écrire s'il ne reconnaît rien) : une ligne
par mois, une cellule « AAAA-Mmm » puis des paires (date de fin de semaine « MM/JJ », valeur avec séparateurs de
milliers).
"""
from __future__ import annotations

import csv
import html
import re
import sys
import time
from pathlib import Path

import httpx

import politesse

REG = Path("registre")
SORTIE = REG / "eia.csv"
URL = "https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx"
SERIES = {
    "WCESTUS1": "stocks de brut hors réserve stratégique (milliers de barils)",
    "WCSSTUS1": "réserve stratégique de pétrole (milliers de barils)",
    "WCRFPUS2": "production de brut (milliers de barils par jour)",
    "WRPUPUS2": "produits pétroliers livrés, demande apparente (milliers de barils par jour)",
}
DEBUT = "2015-01-01"
PAUSE = 2.0
MOIS = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def lire_page(texte: str) -> list[tuple[str, float]]:
    """Paires (jour ISO, valeur) d'une page d'historique hebdomadaire de l'EIA."""
    out = []
    for ligne in re.findall(r"<tr[^>]*>(.*?)</tr>", texte, re.S | re.I):
        cellules = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", c))).strip()
                    for c in re.findall(r"<td[^>]*>(.*?)</td>", ligne, re.S | re.I)]
        if not cellules:
            continue
        m = re.fullmatch(r"(\d{4})-([A-Z][a-z]{2})", cellules[0])
        if not m or m.group(2) not in MOIS:
            continue
        an, mois_ligne = int(m.group(1)), MOIS[m.group(2)]
        reste = cellules[1:]
        for d, v in zip(reste[0::2], reste[1::2]):
            md = re.fullmatch(r"(\d{2})/(\d{2})", d)
            v = v.replace(",", "")
            if not md or not re.fullmatch(r"-?\d+(\.\d+)?", v):
                continue
            mm, jj = int(md.group(1)), int(md.group(2))
            a = an + 1 if mm < mois_ligne else an          # semaine finissant en janvier, ligne de décembre
            out.append((f"{a:04d}-{mm:02d}-{jj:02d}", float(v)))
    return sorted(set(out))


def principal() -> int:
    lignes, manquantes = [], []
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=60, follow_redirects=True) as c:
        if not politesse.autorise(c, URL):
            print("::warning::EIA : refusé par robots.txt ; rien collecté.")
            return 0
        for serie in SERIES:
            try:
                r = c.get(URL, params={"n": "PET", "s": serie, "f": "W"})
                r.raise_for_status()
                vals = [x for x in lire_page(r.text) if x[0] >= DEBUT]
            except Exception as e:
                vals = []
                print(f"::warning::EIA {serie} : {type(e).__name__}")
            if not vals:
                manquantes.append(serie)
            lignes += [(serie, j, v) for j, v in vals]
            print(f"{serie} : {len(vals)} valeurs" + (f", dernière {vals[-1]}" if vals else ""), flush=True)
            time.sleep(PAUSE)
    if not lignes:
        print("::warning::EIA : aucune valeur reconnue (format de page changé ?) ; rien écrit.")
        return 0
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with SORTIE.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["serie", "jour", "valeur"])
        w.writerows(lignes)
    print(f"EIA : {len(lignes)} valeurs ; séries vides : {manquantes or 'aucune'}.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
