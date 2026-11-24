"""Règle des événements comptés, branchée dans le bot (décision de l'auteur, 2026-11-24, 15 h 15).

Calibrage : mise_au_point/calibrage_evenements.py, registre/calibrage-evenements.json (54 questions résolues ; règle
seule 0,653, taux de base 0,554, mélange un quart règle 0,511). Le poids a été choisi sur ces mêmes questions : pari
encadré, pas gain mesuré. La règle ne remplace jamais la prévision du bot : elle la déplace d'un quart en log-cote.

Cas couverts (restrictions écrites après le calibrage, pour ne garder que ce que la série mesure) :
- violence entre deux gouvernements : exactement deux pays nommés, sans « or » entre des pays, un verbe d'affrontement
  (strike, attack, military action, clash, war), sans invasion ni opération terrestre, sans acteur non étatique nommé
  (État islamique, Hamas, Hezbollah, Houthis, JNIM…) ; série ucdp_dyade (UCDP, événements meurtriers seulement) ;
- séismes : magnitude 6 (ou « 6.0 ») explicitement demandée ; série seismes:m6.
Garde : déplacement plafonné à 15 points. Probabilité : h = (k + 0,5) / (n + 1) sur les 24 derniers mois (365 jours pour les séismes) ; p = 1 − (1 − h)^m.
"""
from __future__ import annotations

import csv
import math
import re
from datetime import date
from pathlib import Path

POIDS = 0.25
ECART_MAX = 0.15     # le mélange ne déplace jamais la prévision du bot de plus de 15 points (garde contre une série
                     # qui mesure mal le lieu : Israël-Iran compte aussi les affrontements en Syrie)
ICI = Path(__file__).resolve().parent
VERBES = re.compile(r"\b(strikes?|airstrikes?|attacks?|military action|military clash|clash(es)?|war)\b", re.I)
EXCLUS = re.compile(r"\b(invade|invasion|invades|ground (invasion|operation|troops)|occupy|blockade)\b", re.I)
NON_ETATIQUES = re.compile(r"\b(islamic state|isis|isil|hamas|hezbollah|houthis?|jnim|al-qaeda|al qaeda|taliban|wagner|cartels?|militants?|rebels?)\b", re.I)
SEISME6 = re.compile(r"\bearthquake\b.*\b(magnitude\s*)?6(\.0)?\b(?!\.\d)", re.I)
EXTRA = {"US": "USA", "U.S.": "USA", "USA": "USA", "United States": "USA", "America": "USA", "American": "USA",
         "UK": "GBR", "U.K.": "GBR", "Britain": "GBR", "British": "GBR", "Russia": "RUS", "Russian": "RUS",
         "Iran": "IRN", "Iranian": "IRN", "Israel": "ISR", "Israeli": "ISR", "Ukraine": "UKR", "Ukrainian": "UKR",
         "China": "CHN", "Chinese": "CHN", "Taiwan": "TWN", "South Korea": "KOR", "North Korea": "PRK",
         "Venezuela": "VEN", "India": "IND", "Indian": "IND", "Pakistan": "PAK", "Pakistani": "PAK", "Turkey": "TUR",
         "Saudi Arabia": "SAU", "Saudi": "SAU", "UAE": "ARE", "United Arab Emirates": "ARE", "Syria": "SYR",
         "Lebanon": "LBN", "Yemen": "YEM", "Thailand": "THA", "Cambodia": "KHM", "Philippines": "PHL",
         "Afghanistan": "AFG", "Cuba": "CUB", "Mexico": "MEX", "Japan": "JPN", "Egypt": "EGY", "Iraq": "IRQ",
         "Qatar": "QAT", "Azerbaijan": "AZE", "Armenia": "ARM", "Ethiopia": "ETH", "Eritrea": "ERI", "Sudan": "SDN"}


def _pays_motifs():
    noms = dict(EXTRA)
    f = ICI / "ecosystemes" / "codes-pays-fips.csv"
    for r in csv.DictReader(l for l in f.read_text(encoding="utf-8").splitlines() if l and not l.startswith("#")):
        if r.get("nom") and len(r["nom"]) > 3:
            noms.setdefault(r["nom"], r["iso3"])
    return [(re.compile(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])"), i) for n, i in sorted(noms.items(), key=lambda x: -len(x[0]))]


_MOTIFS = None


def pays(titre: str) -> list[str]:
    global _MOTIFS
    _MOTIFS = _MOTIFS or _pays_motifs()
    out, reste = [], titre
    for m, i in _MOTIFS:                      # noms longs d'abord ; un nom trouvé est retiré du titre
        if m.search(reste):
            reste = m.sub(" ", reste)
            if i not in out:
                out.append(i)
    return out


def reconnaitre(titre: str) -> dict | None:
    if SEISME6.search(titre) and not re.search(r"\b[7-9](\.\d)?\b", titre):
        return {"type": "séisme de magnitude 6 ou plus", "serie": "seismes:m6", "pas": "jour"}
    if not VERBES.search(titre) or EXCLUS.search(titre) or NON_ETATIQUES.search(titre):
        return None
    ps = pays(titre)
    if len(ps) != 2:
        return None
    return {"type": "violence entre deux gouvernements", "serie": f"ucdp_dyade:{ps[0]}:{ps[1]}", "pas": "mois"}


def probabilite(serie: list, pas: str, jour: str, echeance: str) -> dict | None:
    n = 24 if pas == "mois" else 365
    avant = [v for j, v in serie if j < jour]
    if len(avant) < n:
        return None
    k = sum(1 for v in avant[-n:] if v >= 1)
    h = (k + 0.5) / (n + 1)
    jours = (date.fromisoformat(echeance) - date.fromisoformat(jour)).days
    if jours <= 0:
        return None
    m = max(1, math.ceil(jours / 30.44)) if pas == "mois" else jours
    return {"k": k, "n": n, "m": m, "h": round(h, 4), "p_regle": 1 - (1 - h) ** m}


def melanger(p_bot: float, p_regle: float, poids: float = POIDS) -> float:
    def lg(p):
        p = min(max(p, 0.01), 0.99)
        return math.log(p / (1 - p))
    x = (1 - poids) * lg(p_bot) + poids * lg(p_regle)
    return 1 / (1 + math.exp(-x))


def estimer(titre: str, jour: str, echeance: str, p_bot: float) -> dict | None:
    r = reconnaitre(titre)
    if r is None:
        return None
    import adaptateurs
    try:
        s = adaptateurs.lire(r["serie"])
    except Exception:
        return None
    pr = probabilite(s, r["pas"], jour, echeance)
    if pr is None:
        return None
    p = melanger(p_bot, pr["p_regle"])
    p = min(max(p, p_bot - ECART_MAX), p_bot + ECART_MAX)
    return {**r, **pr, "p_bot": p_bot, "p": p, "poids": POIDS, "ecart_max": ECART_MAX}
