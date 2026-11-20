"""Chiffre d'affaires du prochain trimestre publié (0.10.406), modèle saisonnier de Foster (1977) avec φ = 1
(preenregistrements/resultats-entreprises.md, v2 : 0,766 / 0,595 sur 25 entreprises jamais vues).

Décision de l'auteur (2026-11-20, 21 h 43, option 2) : le modèle ne remplace la réponse du bot QUE si la recherche du
bot ne contient ni prévision publiée par l'entreprise (« guidance ») ni consensus des analystes ; sinon le bot garde sa
réponse et le modèle est scellé à côté (ombre), pour comparaison à la résolution.

Données : registre/edgar-trimestres.csv (EDGAR, données publiques de la SEC).
"""
from __future__ import annotations

import csv
import math
import re
from datetime import date, timedelta
from pathlib import Path

EDGAR = Path("registre") / "edgar-trimestres.csv"
FENETRE, MINIMUM = 20, 12

NOMS = {"snowflake": "SNOW", "salesforce": "CRM", "nvidia": "NVDA", "advanced micro devices": "AMD", "amd": "AMD",
        "broadcom": "AVGO", "micron": "MU", "microsoft": "MSFT", "apple": "AAPL", "alphabet": "GOOGL", "google": "GOOGL",
        "amazon": "AMZN", "meta platforms": "META", "netflix": "NFLX", "tesla": "TSLA", "oracle": "ORCL", "intel": "INTC",
        "palantir": "PLTR", "coinbase": "COIN", "adobe": "ADBE", "cisco": "CSCO", "ibm": "IBM", "qualcomm": "QCOM",
        "texas instruments": "TXN", "intuit": "INTU", "servicenow": "NOW", "palo alto networks": "PANW",
        "crowdstrike": "CRWD", "walmart": "WMT", "costco": "COST", "home depot": "HD", "nike": "NKE", "disney": "DIS",
        "jpmorgan": "JPM", "bank of america": "BAC", "goldman sachs": "GS", "visa": "V", "mastercard": "MA",
        "unitedhealth": "UNH", "johnson & johnson": "JNJ", "pfizer": "PFE", "eli lilly": "LLY", "coca-cola": "KO",
        "pepsico": "PEP", "mcdonald's": "MCD", "starbucks": "SBUX", "boeing": "BA", "caterpillar": "CAT",
        "exxon": "XOM", "chevron": "CVX", "uber": "UBER", "airbnb": "ABNB", "lowe's": "LOW", "target": "TGT",
        "honeywell": "HON", "deere": "DE", "fedex": "FDX", "lockheed martin": "LMT", "merck": "MRK", "abbvie": "ABBV",
        "amgen": "AMGN", "gilead": "GILD", "thermo fisher": "TMO", "abbott": "ABT", "procter & gamble": "PG",
        "colgate": "CL", "verizon": "VZ", "comcast": "CMCSA", "booking holdings": "BKNG", "ebay": "EBAY",
        "applied materials": "AMAT", "analog devices": "ADI", "synopsys": "SNPS", "autodesk": "ADSK"}
_REVENU = re.compile(r"\b(revenue|revenues|net sales|total sales)\b", re.I)
_INFO_PUBLIEE = re.compile(
    r"\bguidance\b|\bguided\b|\bconsensus\b|\banalysts?\b[^.]{0,40}\b(expect|estimate|forecast|project)|"
    r"\b(street|wall street)\b[^.]{0,20}\b(estimate|expect)|\boutlook\b[^.]{0,40}\brevenue|"
    r"\bcompany (expects|projects|forecasts)\b", re.I)


def entreprise(titre: str) -> str | None:
    if not _REVENU.search(titre or ""):
        return None
    m = re.search(r"\(([A-Z]{1,5})\)", titre or "")
    tickers = set(NOMS.values())
    if m and m.group(1) in tickers:
        return m.group(1)
    bas = (titre or "").lower()
    for nom, t in sorted(NOMS.items(), key=lambda x: -len(x[0])):
        if re.search(r"(?<![a-z])" + re.escape(nom) + r"(?![a-z])", bas):
            return t
    return None


def info_publiee(recherche: str) -> bool:
    """La recherche du bot contient-elle une prévision de l'entreprise ou un consensus d'analystes ?"""
    return bool(_INFO_PUBLIEE.search(recherche or ""))


def _serie(ticker: str) -> list[tuple[str, float]]:
    if not EDGAR.exists():
        return []
    pts = sorted((r["fin"], float(r["valeur"])) for r in csv.DictReader(EDGAR.open(encoding="utf-8"))
                 if r["entreprise"] == ticker and r["mesure"] == "chiffre_affaires" and float(r["valeur"]) > 0)
    bloc = pts[-1:]
    for a, b in zip(reversed(pts[:-1]), reversed(pts[1:])):     # dernier bloc de trimestres consécutifs
        if 80 <= (date.fromisoformat(b[0]) - date.fromisoformat(a[0])).days <= 100:
            bloc.insert(0, a)
        else:
            break
    return bloc


def _q(pas: list[float], p: float) -> float:
    pas = sorted(pas)
    i = p * (len(pas) - 1)
    lo, hi = int(i), min(len(pas) - 1, int(i) + 1)
    return pas[lo] + (pas[hi] - pas[lo]) * (i - lo)


def modele(ticker: str, jour: str) -> dict | None:
    """Distribution du prochain trimestre, seulement si c'est bien le prochain à publier : le dernier trimestre
    collecté a moins de 170 jours (sinon le suivant est sans doute déjà publié et pas encore collecté)."""
    s = _serie(ticker)
    if len(s) < 4 + MINIMUM + 1:
        return None
    fin = date.fromisoformat(s[-1][0])
    if (date.fromisoformat(jour) - fin).days > 170:
        return None
    x = [math.log(v) for _, v in s]
    g = [x[i] - x[i - 4] for i in range(4, len(x))]
    eps = [b - a for a, b in zip(g[:-1], g[1:])][-FENETRE:]
    centre = x[len(x) - 4] + g[-1]
    return {"ticker": ticker, "dernier_trimestre": s[-1][0], "dernier_chiffre": s[-1][1],
            "trimestre_vise": (fin + timedelta(days=91)).isoformat(), "centre": centre, "eps": sorted(eps)}


def percentiles(m: dict, echelle: float, ps=(0.1, 0.2, 0.4, 0.6, 0.8, 0.9)) -> list[tuple[float, float]]:
    return [(p, math.exp(m["centre"] + _q(m["eps"], p)) / echelle) for p in ps]


def cdf(m: dict, y: float) -> float:
    """Fonction de répartition du chiffre (en dollars). Intérieur = la fonction quantile testée (interpolée), comprimée
    pour laisser une masse 1/(n+1) de chaque côté ; au-delà des extrêmes observés, cette masse décroît
    exponentiellement, à l'échelle de l'écart-type des variations (queues non testées : choix fixé, pas réglé)."""
    e = m["eps"]
    n = len(e)
    queue = 1 / (n + 1)
    if y <= 0:
        return 0.0
    z = math.log(y) - m["centre"]
    moy = sum(e) / n
    s = max(1e-6, math.sqrt(sum((v - moy) ** 2 for v in e) / (n - 1)))
    if z < e[0]:
        return queue * math.exp(-(e[0] - z) / s)
    if z >= e[-1]:
        return 1 - queue * math.exp(-(z - e[-1]) / s)
    for i in range(n - 1):
        if e[i] <= z < e[i + 1]:
            frac = (z - e[i]) / (e[i + 1] - e[i]) if e[i + 1] > e[i] else 0.0
            return queue + (1 - 2 * queue) * (i + frac) / (n - 1)
    return 1 - queue


_NB = r"(\d[\d,]*(?:\.\d+)?)"
_UNITE = {"bil": 1e9, "bn": 1e9, "b": 1e9, "billion": 1e9, "mil": 1e6, "m": 1e6, "million": 1e6, "mn": 1e6}


def _valeurs(option: str) -> list[float]:
    out = []
    for nb, u in re.findall(_NB + r"\s*(billion|million|bil|mil|bn|mn|b|m)?\b", option, re.I):
        out.append((float(nb.replace(",", "")), (u or "").lower()))
    unite = next((_UNITE[u] for _, u in out if u), None)
    return [v * (_UNITE[u] if u else (unite or 1.0)) for v, u in out]


def bornes(option: str) -> tuple[float, float] | None:
    """(bas, haut) en dollars pour une tranche du type « 1,615 million or less », « >1,615 mil. & <1,670 mil. »,
    « ≥1,670 mil. & ≤1,725 mil. », « >1,785 mil. »."""
    v = _valeurs(option)
    o = option.lower()
    if len(v) == 2:
        return (min(v), max(v))
    if len(v) == 1:
        if re.search(r"or less|or fewer|below|under|less than|^\s*[<≤]", o):
            return (0.0, v[0])
        if re.search(r"or more|or greater|above|over|more than|^\s*[>≥]", o):
            return (v[0], math.inf)
    return None


def repartition(m: dict, options: list[str]) -> dict[str, float] | None:
    """Probabilité de chaque tranche ; None si une tranche n'est pas lisible ou si les tranches ne couvrent pas tout."""
    b = {o: bornes(o) for o in options}
    if any(x is None for x in b.values()):
        return None
    p = {o: max(0.0, cdf(m, hi) - cdf(m, lo)) if hi != math.inf else 1 - cdf(m, lo) for o, (lo, hi) in b.items()}
    if abs(sum(p.values()) - 1) > 0.02:
        return None
    p = {o: max(0.005, x) for o, x in p.items()}
    s = sum(p.values())
    return {o: x / s for o, x in p.items()}


def echelle_numerique(m: dict, borne_basse: float | None, borne_haute: float | None) -> float | None:
    """Échelle de la question numérique (1, 1e6 ou 1e9) : celle où la médiane du modèle tombe dans les bornes."""
    med = math.exp(m["centre"] + _q(m["eps"], 0.5))
    for e in (1e6, 1e9, 1.0, 1e3):
        if borne_basse is not None and borne_haute is not None and borne_basse <= med / e <= borne_haute:
            return e
    return None


def ligne_commentaire(m: dict) -> str:
    return (f"\n\nQuarterly-revenue rule (coded, seasonal random walk, Foster 1977): last SEC-reported quarter "
            f"{m['dernier_trimestre']} at ${m['dernier_chiffre'] / 1e6:,.0f}M; next quarter = same quarter last year x "
            f"latest year-on-year growth, spread from the past {len(m['eps'])} changes in that growth. Used only because "
            f"no company guidance or analyst consensus was found in the research.")
