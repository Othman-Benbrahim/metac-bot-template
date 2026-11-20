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


def etat(serie: str, avant: str, fenetre: int = 30) -> tuple[float, float] | None:
    """(dernier prix connu strictement avant la date, volatilité annualisée sur `fenetre` rendements)."""
    pts = [v for j, v in series().get(serie, []) if j < avant and v > 0]
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
    if not q or not fin or fin <= jour:
        return None
    e = etat(q["actif"], jour, 30)
    pts = [j for j, _ in series().get(q["actif"], []) if j < jour]
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
