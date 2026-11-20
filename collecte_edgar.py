"""Résultats trimestriels publiés à la SEC (EDGAR, API « companyfacts », données publiques) pour les questions de
résultats d'entreprise (0.10.405, décision d'auteur du 2026-11-20, 21 h 07).

La SEC exige une adresse de contact dans l'en-tête User-Agent : elle est lue dans le secret SEC_CONTACT_EMAIL et n'est
JAMAIS écrite dans le dépôt ni dans les journaux. Débit : bien sous la limite de la SEC (10 requêtes par seconde) ; une
requête par seconde. Fichier robots respecté.

Garde, par entreprise : chiffre d'affaires trimestriel et bénéfice par action dilué trimestriel (valeurs en USD,
formulaires 10-Q et 10-K, trimestres de trois mois).

    python collecte_edgar.py     # écrit registre/edgar-trimestres.csv
"""
from __future__ import annotations

import csv
import os
import sys
import time
from datetime import date
from pathlib import Path

import httpx

import politesse

SORTIE = Path("registre") / "edgar-trimestres.csv"
TICKERS = "https://www.sec.gov/files/company_tickers.json"
FAITS = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
CONCEPTS = {"chiffre_affaires": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"],
            "bpa_dilue": ["EarningsPerShareDiluted"]}
# entreprises des questions du bot et grandes capitalisations (résultats trimestriels fréquemment demandés)
ENTREPRISES = ["SNOW", "CRM", "NVDA", "AMD", "AVGO", "MU", "MSFT", "AAPL", "GOOGL", "AMZN", "META", "NFLX", "TSLA",
               "ORCL", "INTC", "PLTR", "COIN", "ADBE", "CSCO", "IBM", "QCOM", "TXN", "INTU", "NOW", "PANW", "CRWD",
               "WMT", "COST", "HD", "NKE", "DIS", "JPM", "BAC", "GS", "V", "MA", "UNH", "JNJ", "PFE", "LLY",
               "KO", "PEP", "MCD", "SBUX", "BA", "CAT", "XOM", "CVX", "UBER", "ABNB"]
# version 2 (préenregistrée le 2026-11-20, 21 h 35) : entreprises jamais vues, seules jugées
NOUVELLES_V2 = ["LOW", "TGT", "ADP", "HON", "DE", "UPS", "FDX", "LMT", "MRK", "ABBV", "AMGN", "GILD", "TMO", "ABT",
                "PG", "CL", "T", "VZ", "CMCSA", "BKNG", "EBAY", "AMAT", "ADI", "SNPS", "ADSK"]
ENTREPRISES = ENTREPRISES + NOUVELLES_V2


def trimestres(faits: dict, concept: str, unite: str) -> list[tuple[str, str, float]]:
    """(début, fin, valeur) des périodes d'environ trois mois, une valeur par fin de période (le dépôt le plus récent)."""
    out = {}
    for c in CONCEPTS[concept]:
        u = (faits.get("facts", {}).get("us-gaap", {}).get(c, {}).get("units", {}) or {}).get(unite) or []
        for x in u:
            if x.get("form") not in ("10-Q", "10-K") or not x.get("start") or not x.get("end"):
                continue
            jours = (date.fromisoformat(x["end"]) - date.fromisoformat(x["start"])).days
            if 80 <= jours <= 100:
                if x["end"] not in out or x.get("filed", "") > out[x["end"]][2]:
                    out[x["end"]] = (x["start"], float(x["val"]), x.get("filed", ""))
        if out:
            break
    return sorted((d, f, v) for f, (d, v, _) in out.items())


def annuels(faits: dict, concept: str, unite: str) -> list[tuple[str, str, float]]:
    out = {}
    for c in CONCEPTS[concept]:
        u = (faits.get("facts", {}).get("us-gaap", {}).get(c, {}).get("units", {}) or {}).get(unite) or []
        for x in u:
            if x.get("form") != "10-K" or not x.get("start") or not x.get("end"):
                continue
            if 350 <= (date.fromisoformat(x["end"]) - date.fromisoformat(x["start"])).days <= 380:
                if x["end"] not in out or x.get("filed", "") > out[x["end"]][2]:
                    out[x["end"]] = (x["start"], float(x["val"]), x.get("filed", ""))
        if out:
            break
    return sorted((d, f, v) for f, (d, v, _) in out.items())


def avec_t4(trim: list[tuple[str, str, float]], ann: list[tuple[str, str, float]]) -> list[tuple[str, str, float]]:
    """Le 10-K ne donne souvent que l'année : quatrième trimestre = année − les trois trimestres de l'exercice."""
    par_fin = {f: (d, v) for d, f, v in trim}
    for d, f, v in ann:
        if f in par_fin:
            continue
        dedans = [(dd, ff, vv) for dd, ff, vv in trim if d <= dd and ff < f]
        if len(dedans) == 3:
            par_fin[f] = (max(ff for _, ff, _ in dedans), v - sum(vv for *_, vv in dedans))
    return sorted((d, f, v) for f, (d, v) in par_fin.items())


def principal() -> int:
    contact = os.environ.get("SEC_CONTACT_EMAIL")
    if not contact:
        print("::warning::SEC_CONTACT_EMAIL absente : rien collecté.")
        return 0
    ua = f"alphabet-situationnel {contact}"   # forme exigée par la SEC : « Nom adresse@domaine »
    lignes = []
    with httpx.Client(headers={"User-Agent": ua}, timeout=60) as c:
        if not politesse.autorise(c, TICKERS):
            print("::warning::SEC : refusé par robots.txt ; rien collecté.")
            return 0
        r = c.get(TICKERS)
        if r.status_code != 200 or "json" not in r.headers.get("content-type", ""):
            print(f"::error::SEC : réponse {r.status_code} ({r.headers.get('content-type')}) : {r.text[:200]!r}")
            return 1
        carte = {v["ticker"]: int(v["cik_str"]) for v in r.json().values()}
        for t in ENTREPRISES:
            time.sleep(1.0)
            if t not in carte:
                print(f"::warning::{t} : CIK introuvable")
                continue
            try:
                r = c.get(FAITS.format(cik=carte[t]))
                if r.status_code != 200:
                    print(f"::warning::{t} : réponse {r.status_code}")
                    continue
                f = r.json()
            except Exception as e:
                print(f"::warning::{t} : {type(e).__name__}")
                continue
            ca = avec_t4(trimestres(f, "chiffre_affaires", "USD"), annuels(f, "chiffre_affaires", "USD"))
            bpa = trimestres(f, "bpa_dilue", "USD/shares")
            lignes += [(t, "chiffre_affaires", d, fin, v) for d, fin, v in ca]
            lignes += [(t, "bpa_dilue", d, fin, v) for d, fin, v in bpa]
            print(f"{t} : {len(ca)} trimestres de chiffre d'affaires, {len(bpa)} de BPA", flush=True)
    if not lignes:
        return 0
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with SORTIE.open("w", encoding="utf-8", newline="") as fo:
        w = csv.writer(fo)
        w.writerow(["entreprise", "mesure", "debut", "fin", "valeur"])
        w.writerows(lignes)
    print(f"EDGAR : {len(lignes)} valeurs trimestrielles.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
