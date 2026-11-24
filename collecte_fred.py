"""Collecte de séries publiques de la FRED (Réserve fédérale de Saint-Louis) — bot 0.10.318, en ombre.

Décision de l'auteur, 2026-11-19, 4 h 43 (« let's go ; dans le code aussi, pas uniquement en fiche ») : brancher les
traces gratuites qui manquent en bas de l'échelle des écosystèmes (énergie mondiale, inflation mondiale). Téléchargement
CSV public de la FRED, sans clé ; robots.txt respecté ; une requête par série et par passage. Rien n'entre dans le bot.

Registre : registre/fred.csv (serie, jour, valeur), réécrit à chaque passage depuis DEBUT.
"""
from __future__ import annotations

import csv
import io
import os
import sys
import time
from pathlib import Path

import httpx

import politesse

REG = Path(os.environ.get("ALPHABET_REGISTRE", "registre"))
SORTIE = REG / "fred.csv"
URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
DEBUT = "2015-01-01"
PAUSE = 2.0
# identifiant FRED : ce que la série dit, et l'écosystème qui la lit
SERIES = {
    "DCOILBRENTEU": "prix du Brent, dollars le baril, quotidien (énergie mondiale : prix)",
    "DCOILWTICO": "prix du WTI, quotidien (énergie mondiale : prix)",
    "DHHNGSP": "prix du gaz Henry Hub, quotidien (énergie mondiale : prix)",
    "WCESTUS1": "stocks commerciaux de brut américains hors réserve stratégique, hebdomadaire (énergie mondiale : stocks)",
    "WCSSTUS1": "réserve stratégique américaine de brut, hebdomadaire (énergie mondiale : stocks)",
    "T10YIE": "inflation anticipée à 10 ans par les marchés, quotidien (inflation mondiale : anticipations)",
    "DFF": "taux directeur effectif de la Réserve fédérale, quotidien (inflation mondiale : banques centrales)",
    "DFEDTARU": "borne haute de la fourchette cible de la Fed, quotidien (banques centrales : brique d'inertie) ; 0.10.499",
    "DFEDTARL": "borne basse de la fourchette cible de la Fed, quotidien (banques centrales : brique d'inertie) ; 0.10.499",
    "ECBDFR": "taux de la facilité de dépôt de la BCE (inflation mondiale : banques centrales)",
    "DGS10": "taux américain à 10 ans, quotidien (inflation mondiale : marchés financiers)",
    "DTWEXBGS": "indice large du dollar, quotidien (inflation mondiale : monnaies)",
    "CPIAUCSL": "indice des prix à la consommation américain, mensuel (inflation mondiale : prix à la consommation)",
    "CPILFESL": "inflation sous-jacente américaine, mensuel (inflation mondiale : prix à la consommation)",
    "UNRATE": "taux de chômage américain, mensuel (inflation mondiale : salaires et emploi)",
    "CES0500000003": "salaire horaire moyen américain, mensuel (inflation mondiale : salaires et emploi)",
    "PFOODINDEXM": "indice mondial des prix alimentaires (FMI), mensuel (inflation mondiale : alimentation)",
    "VIXCLS": "indice de volatilité implicite du S&P 500, quotidien (crises bancaires : confiance)",
    "DPSACBW027SBOG": "dépôts des banques commerciales américaines, hebdomadaire (crises bancaires : dépôts)",
    "UMCSENT": "confiance des ménages américains (Université du Michigan), mensuel (humain : attente)",
    "CBBTCUSD": "cours du bitcoin (Coinbase), quotidien (crises bancaires : cryptomonnaies) ; 0.10.358",
    "NASDAQCOM": "indice Nasdaq Composite, quotidien (seuils de prix) ; 0.10.398",
    "SP500": "indice S&P 500, quotidien (seuils de prix) ; 0.10.398",
    "DJIA": "indice Dow Jones, quotidien (seuils de prix) ; 0.10.398",
    "CBETHUSD": "cours de l'ether (Coinbase), quotidien (crises bancaires : cryptomonnaies) ; 0.10.358",
    # 0.10.389 (décision d'auteur du 2026-11-20, 14 h 48) : prix mondiaux mensuels du FMI, matières stratégiques
    "PCOPPUSDM": "prix mondial du cuivre (FMI), mensuel (matières stratégiques) ; 0.10.389",
    "PNICKUSDM": "prix mondial du nickel (FMI), mensuel (matières stratégiques) ; 0.10.389",
    "PURANUSDM": "prix mondial de l'uranium (FMI), mensuel (matières stratégiques) ; 0.10.389",
    "PALUMUSDM": "prix mondial de l'aluminium (FMI), mensuel (matières stratégiques) ; 0.10.389",
    "PIORECRUSDM": "prix mondial du minerai de fer (FMI), mensuel (matières stratégiques) ; 0.10.389",
    "PZINCUSDM": "prix mondial du zinc (FMI), mensuel (matières stratégiques) ; 0.10.389",
    "PWHEAMTUSDM": "prix mondial du blé (FMI), mensuel (alimentation mondiale) ; 0.10.389",
    "PMAIZMTUSDM": "prix mondial du maïs (FMI), mensuel (alimentation mondiale) ; 0.10.389",
}


def lire_csv(texte: str, serie: str) -> list[tuple[str, float]]:
    out = []
    for r in csv.reader(io.StringIO(texte)):
        if len(r) < 2 or not r[0][:4].isdigit():
            continue
        try:
            out.append((r[0], float(r[1])))
        except ValueError:
            continue                      # « . » = pas de valeur ce jour-là
    return out


def principal() -> int:
    lignes, manquantes = [], []
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=60, follow_redirects=True) as c:
        if not politesse.autorise(c, URL):
            print("::warning::FRED : refusé par robots.txt ; rien collecté.")
            return 0
        for serie in SERIES:
            try:
                r = c.get(URL, params={"id": serie, "cosd": DEBUT})
                r.raise_for_status()
                vals = lire_csv(r.text, serie)
            except Exception as e:
                vals = []
                print(f"::warning::FRED {serie} : {type(e).__name__}")
            if not vals:
                manquantes.append(serie)
            lignes += [(serie, j, v) for j, v in vals]
            print(f"{serie} : {len(vals)} valeurs" + (f", dernière {vals[-1]}" if vals else ""), flush=True)
            time.sleep(PAUSE)
    if not lignes:
        return 0
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with SORTIE.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["serie", "jour", "valeur"])
        w.writerows(lignes)
    print(f"FRED : {len(lignes)} valeurs ; séries vides : {manquantes or 'aucune'}.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
