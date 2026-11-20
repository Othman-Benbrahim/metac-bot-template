"""Seuils de prix : probabilités log-normales sans dérive (référence preenregistrements/seuils-de-prix-reference.md).

Aucune cote de marché ni volatilité implicite : seulement l'historique des prix. Rien n'entre dans le bot à ce stade.
"""
from __future__ import annotations

import csv
import math
import re
from datetime import date
from functools import lru_cache
from pathlib import Path

FRED = Path("registre") / "fred.csv"
ACTIFS = {  # motif du titre → (série FRED, jours de cotation par an)
    "CBBTCUSD": (re.compile(r"\b(bitcoin|btc)\b", re.I), 365),
    "CBETHUSD": (re.compile(r"\b(ethereum|ether|eth)\b", re.I), 365),
    "DCOILBRENTEU": (re.compile(r"\bbrent\b", re.I), 252),
    "NASDAQCOM": (re.compile(r"\bnasdaq\b(?!\s*(ticker|:|-?listed))(?!.{0,40}\bper share\b)", re.I), 252),
    "SP500": (re.compile(r"\b(s&p ?500|spx)\b", re.I), 252),
    "DJIA": (re.compile(r"\bdow jones\b|\bdjia\b", re.I), 252),
}
# 0.10.400 : actions, cours lus à la demande chez Twelve Data (collecte_actions.cours), jamais écrits dans le dépôt.
# Branchées dans le bot seulement après le calibrage sur les questions d'actions (ACTIONS_DANS_LE_BOT).
ACTIONS = {
    "NVDA": r"\b(nvidia|nvda)\b", "AMD": r"\b(amd|advanced micro devices)\b", "AVGO": r"\b(broadcom|avgo)\b",
    "MU": r"\b(micron|\$?mu)\b(?= (stock|share|close|technology))", "MSTR": r"\b(microstrategy|mstr|strategy \(mstr\))\b",
    "TSLA": r"\b(tesla|tsla)\b", "AAPL": r"\b(apple|aapl)\b(?! (watch|vision|tv|music|intelligence))",
    "MSFT": r"\b(microsoft|msft)\b", "GOOGL": r"\b(alphabet|googl?)\b(?= (stock|share|close|class))",
    "AMZN": r"\b(amazon|amzn)\b(?= (stock|share|close))", "META": r"\b(meta platforms|\$meta)\b",
    "NFLX": r"\b(netflix|nflx)\b(?= (stock|share|close))", "COIN": r"\b(coinbase|\$coin)\b(?= (stock|share|close))",
    "PLTR": r"\b(palantir|pltr)\b", "SNOW": r"\b(snowflake|snow)\b(?= (stock|share|close))",
    "CRM": r"\b(salesforce|crm)\b(?= (stock|share|close))", "INTC": r"\b(intel|intc)\b(?= (stock|share|close))",
    "ORCL": r"\b(oracle|orcl)\b(?= (stock|share|close))",
}
for _s, _rx in ACTIONS.items():
    ACTIFS[_s] = (re.compile(_rx, re.I), 252)
ACTIONS_DANS_LE_BOT = False


def phi(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def p_a_la_date(s0: float, k: float, sigma: float, t_ans: float, au_dessus: bool = True) -> float:
    """Probabilité d'être au-dessus (ou au-dessous) de k à la date, marche log-normale sans dérive."""
    if t_ans <= 0 or sigma <= 0:
        return 1.0 if (s0 > k) == au_dessus else 0.0
    p = phi(math.log(s0 / k) / (sigma * math.sqrt(t_ans)))
    return p if au_dessus else 1 - p


def p_atteint_avant(s0: float, k: float, sigma: float, t_ans: float) -> float:
    """Probabilité de toucher k avant la date (principe de réflexion) ; 1 si k est déjà franchi."""
    if s0 == k:
        return 1.0
    if t_ans <= 0 or sigma <= 0:
        return 0.0
    return min(1.0, 2 * phi(-abs(math.log(k / s0)) / (sigma * math.sqrt(t_ans))))


@lru_cache(maxsize=1)
def series() -> dict[str, list[tuple[str, float]]]:
    out: dict[str, list[tuple[str, float]]] = {}
    if FRED.exists():
        for r in csv.DictReader(FRED.open(encoding="utf-8")):
            out.setdefault(r["serie"], []).append((r["jour"], float(r["valeur"])))
    for v in out.values():
        v.sort()
    return out


def points(serie: str) -> list[tuple[str, float]]:
    if serie in ACTIONS:
        import collecte_actions as ca
        return list(ca.cours(serie))
    return series().get(serie, [])


def etat(serie: str, avant: str, fenetre: int = 30) -> tuple[float, float] | None:
    """(dernier prix connu strictement avant la date, volatilité annualisée sur `fenetre` rendements)."""
    pts = [v for j, v in points(serie) if j < avant and v > 0]
    if len(pts) < fenetre + 1:
        return None
    r = [math.log(b / a) for a, b in zip(pts[-fenetre - 1:-1], pts[-fenetre:])]
    m = sum(r) / len(r)
    sd = math.sqrt(sum((x - m) ** 2 for x in r) / (len(r) - 1))
    return pts[-1], sd * math.sqrt(ACTIFS[serie][1])


def actif(titre: str) -> str | None:
    trouves = [s for s, (rx, _) in ACTIFS.items() if rx.search(titre or "")]
    return trouves[0] if len(trouves) == 1 else None


def annees(debut: str, fin: str) -> float:
    return (date.fromisoformat(fin[:10]) - date.fromisoformat(debut[:10])).days / 365.0


# ---- 0.10.399 : lecture d'une question de seuil de prix, mêmes règles que le calibrage (mise_au_point/seuils_prix_essai.py)
NUM = re.compile(r"\$\s?([\d,]+(?:\.\d+)?)\s*([kKmM]?)\b|\b([\d,]+(?:\.\d+)?)\s*([kKmM])\b")
TOUCHE = re.compile(r"\b(reach|hit|touch|dip|drop|fall|trade (above|below|over|under)|at any (point|time)|again)\b", re.I)
A_DATE = re.compile(r"\b(close|closing|settle|be (above|below|over|under)|end (of )?\w+ (above|below))\b", re.I)
HAUT = re.compile(r"\b(above|over|higher|reach|hit)\b", re.I)
BAS = re.compile(r"\b(below|under|lower|dip|drop|fall)\b", re.I)
FRAICHEUR_JOURS = 5          # dernier prix connu au plus 5 jours avant la date d'information, sinon pas de calcul


def montant(t: str) -> float | None:
    m = NUM.search(t or "")
    if not m:
        return None
    v, s = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
    try:
        x = float(v.replace(",", ""))
    except ValueError:
        return None
    return x * (1e3 if s.lower() == "k" else 1e6 if s.lower() == "m" else 1)


def lire(titre: str) -> dict | None:
    """Actif, seuil, type (« date » ou « touche ») et sens ; None si la question n'est pas reconnue sans ambiguïté."""
    a, k = actif(titre), montant(titre)
    if not a or not k:
        return None
    typ = "touche" if TOUCHE.search(titre) else "date" if A_DATE.search(titre) else None
    if not typ:
        return None
    bas, haut = bool(BAS.search(titre)), bool(HAUT.search(titre))
    if bas == haut and typ == "date":
        return None
    return {"actif": a, "k": k, "type": typ, "au_dessus": (not bas) if bas != haut else True}


def estimer(titre: str, jour: str, fin: str) -> dict | None:
    """Probabilité du modèle pour une question de seuil de prix, à la date d'information `jour`, échéance `fin`
    (AAAA-MM-JJ). None si la question n'est pas reconnue ou si les prix manquent ou sont trop anciens."""
    q = lire(titre)
    if not q or not fin or fin <= jour or (q["actif"] in ACTIONS and not ACTIONS_DANS_LE_BOT):
        return None
    e = etat(q["actif"], jour, 30)
    pts = [j for j, _ in points(q["actif"]) if j < jour]
    if not e or not pts or (date.fromisoformat(jour) - date.fromisoformat(pts[-1])).days > FRAICHEUR_JOURS:
        return None
    s0, sigma = e
    t = max(annees(jour, fin), 1 / 365)
    p = p_a_la_date(s0, q["k"], sigma, t, q["au_dessus"]) if q["type"] == "date" else p_atteint_avant(s0, q["k"], sigma, t)
    return {**q, "p": min(0.99, max(0.01, p)), "dernier_prix": s0, "date_prix": pts[-1], "sigma_annuel": round(sigma, 4),
            "echeance": fin, "duree_ans": round(t, 4)}


MOIS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                      "september", "october", "november", "december"], 1)}


def echeance(t: str, jour: str) -> str | None:
    """Échéance écrite dans le titre (date complète, année, fin de mois), mêmes règles que le calibrage."""
    from datetime import timedelta
    import alphabet_pipeline as ap
    ds = [x for x in ap.dates_citees(t) if x >= jour]
    if ds:
        return min(ds)
    m = re.search(r"\bbefore (20\d\d)\b", t, re.I)
    if m:
        return f"{int(m.group(1)) - 1}-12-31"
    m = re.search(r"\b(?:by|in|end(?: of)?|during|close|end)\s+(?:the end of\s+)?(20\d\d)\b|(?<!\$)\b(20\d\d)\s*\??$", t, re.I)
    if m:
        return f"{m.group(1) or m.group(2)}-12-31"
    m = re.search(r"\b(?:by|before)\s+(?:the\s+)?end\s+of\s+([a-z]+)\b|\bby\s+([a-z]+)\s+\d{0,2}\b", t, re.I)
    mo = (m.group(1) or m.group(2) or "").lower() if m else ""
    if mo in MOIS:
        a = int(jour[:4]) + (1 if MOIS[mo] < int(jour[5:7]) else 0)
        return (date(a + (MOIS[mo] == 12), MOIS[mo] % 12 + 1, 1) - timedelta(days=1)).isoformat()
    return None


# ---- 0.10.401 : fourchettes pour les questions numériques de prix (même modèle log-normal sans dérive)
def quantile_normal(p: float) -> float:
    """Inverse de la loi normale (Acklam), précision suffisante pour des percentiles."""
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02,
         -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01,
         -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00,
         4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00]
    if p < 0.02425:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > 1 - 0.02425:
        return -quantile_normal(1 - p)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def quantiles(s0: float, sigma: float, t_ans: float, ps=(0.1, 0.2, 0.4, 0.6, 0.8, 0.9)) -> list[tuple[float, float]]:
    """Percentiles (p, valeur) du prix à la date, log-normal sans dérive."""
    e = sigma * math.sqrt(max(t_ans, 1 / 365))
    return [(p, s0 * math.exp(e * quantile_normal(p))) for p in ps]


CLOTURE = re.compile(r"\b(close|closing|settle|settlement|price)\b", re.I)
FAMILLE_FOURCHETTES = {"CBBTCUSD", "CBETHUSD", "DCOILBRENTEU", "NASDAQCOM", "SP500", "DJIA"}   # calibrées (0.10.401)
# 0.10.402 : actions calibrées (run 44800324868 : 80 % → 0,754 et 0,756 ; 60 % → 0,580 et 0,581), cours Twelve Data
FAMILLE_FOURCHETTES |= set(ACTIONS)


def fourchette(titre: str, jour: str, fin: str | None) -> dict | None:
    """Percentiles du prix de clôture pour une question numérique « à combien clôturera l'actif à telle date ? ».
    None si l'actif n'est pas dans la famille calibrée, si le titre porte un seuil, ou si les prix manquent."""
    a = actif(titre)
    if a not in FAMILLE_FOURCHETTES or not CLOTURE.search(titre or "") or not fin or fin <= jour:
        return None
    e = etat(a, jour, 30)
    pts = [j for j, _ in points(a) if j < jour]
    if not e or not pts or (date.fromisoformat(jour) - date.fromisoformat(pts[-1])).days > FRAICHEUR_JOURS:
        return None
    s0, sigma = e
    t = max(annees(pts[-1], fin), 1 / 365)
    return {"actif": a, "dernier_prix": s0, "date_prix": pts[-1], "sigma_annuel": round(sigma, 4), "echeance": fin,
            "percentiles": quantiles(s0, sigma, t)}
