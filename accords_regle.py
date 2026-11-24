"""Brique « accords » (décision de l'auteur, 2026-11-24, 16 h 16 : « Je valide les trois points » ; découpage voulu
en poupées russes, testé sur le terrain). Procédure : preenregistrements/accords.md, versée avant tout calcul.

Sous-familles (titre seul, dans cet ordre) :
- tenue : « ceasefire … broken by » (oui = rompu) / « ceasefire … continues through » (oui = tient) ;
- rencontre : meet, meeting, attend ;
- cessez_le_feu : ceasefire, cease-fire, truce (conclure) ;
- accord_paix : peace deal, nuclear deal, deal / agreement entre États (conclure) ;
- autre : le reste (accords commerciaux, traités, signatures…).
Mesures :
- cessez_le_feu, accord_paix : PA-X. Taux λ d'accords du stade visé (Cea ; SubComp ou SubPar) signés dans un processus
  de paix déjà actif (un accord dans les 365 jours précédents), par jour de processus actif ; P = 1 − exp(−λ·h).
- tenue : PA-X. Après un cessez-le-feu, un nouveau cessez-le-feu dans le même processus vaut rupture du précédent
  (indicateur indirect, déclaré). Taux λr par jour d'exposition (jusqu'au cessez-le-feu suivant, 365 jours au plus) ;
  P(rupture avant h) = 1 − exp(−λr·h).
- rencontre, autre : pas de mesure extérieure ; part de oui de la sous-famille, tirée vers celle de la famille (poids 5).
Horizon h : de la date de la question à l'échéance lue dans le titre ; échéance illisible = abstention.
"""
from __future__ import annotations

import csv
import datetime as dt
import math
import os
import re
from pathlib import Path

ICI = Path(__file__).resolve().parent
PAX = Path(os.environ.get("ALPHABET_REGISTRE", ICI / "registre")) / "pax-accords.csv"
TAUX_CLASSES = ICI / "ecosystemes" / "accords-taux-classes.json"
POIDS = 0.25
ECART_MAX = 0.15
POIDS_PRIOR = 5
ACTIF = 365
J = dt.date.fromisoformat
MOIS = {m: i + 1 for i, m in enumerate(("january", "february", "march", "april", "may", "june", "july", "august",
                                        "september", "october", "november", "december"))}
_M = "|".join(MOIS)

TENUE = re.compile(r"cease-?fire\b.*\b(broken|continues?)\b", re.I)
RENCONTRE = re.compile(r"\b(meet|meets|meeting|attend)\b", re.I)
CESSEZ = re.compile(r"\b(cease-?fire|truce)\b", re.I)
PAIX = re.compile(r"\b(peace deal|nuclear deal|peace agreement|agreement restricting iran|sign a [\w. ]+ deal)\b", re.I)
FAMILLE = re.compile(r"\b(deal|agreement|ceasefire|cease-fire|truce|treaty|peace|talks|summit|meet\w*|sign\w*|"
                     r"negotiat\w*)\b", re.I)
EXCLURE = re.compile(r"\b(fed|fomc|federal reserve|powell|ecb|bank of england|central bank|interest rates?)\b", re.I)
SORTIE = re.compile(r"\b(leave|withdraw\w*|exit)\b", re.I)          # quitter un accord n'est pas le conclure
NEGATION = re.compile(r"\bnot (meet|sign|agree)\b", re.I)            # polarité inversée : abstention


def classe(titre: str) -> str | None:
    t = titre or ""
    if EXCLURE.search(t) or not FAMILLE.search(t):
        return None
    if NEGATION.search(t):
        return None
    if TENUE.search(t):
        return "tenue"
    if RENCONTRE.search(t):
        return "rencontre"
    if CESSEZ.search(t):
        return "cessez_le_feu"
    if PAIX.search(t) and not SORTIE.search(t):
        return "accord_paix"
    return "autre"


def _prochaine(mois: int, jour: int, jeu: dt.date) -> dt.date:
    d = dt.date(jeu.year, mois, jour)
    return d if d >= jeu else dt.date(jeu.year + 1, mois, jour)


def _fin_mois(a: int, m: int) -> dt.date:
    return (dt.date(a + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1))


def echeance(titre: str, jeu: dt.date) -> dt.date | None:
    t = (titre or "").lower()
    m = re.search(r"first (\d+) days", t)
    if m and "trump" in t:
        return dt.date(2025, 1, 20) + dt.timedelta(days=int(m.group(1)))
    m = re.search(r"\b(\d{1,2}) (" + _M + r") (\d{4})", t)
    if m:
        return dt.date(int(m.group(3)), MOIS[m.group(2)], int(m.group(1)))
    m = re.search(r"(" + _M + r") (\d{1,2}),? (\d{4})", t)
    if m:
        return dt.date(int(m.group(3)), MOIS[m.group(1)], int(m.group(2)))
    m = re.search(r"(" + _M + r") (\d{1,2})\b", t)
    if m:
        return _prochaine(MOIS[m.group(1)], int(m.group(2)), jeu)
    m = re.search(r"(?:end of|eoy) ?(\d{4})", t) or re.search(r"\bin (\d{4})\b", t)
    if m:
        return dt.date(int(m.group(1)), 12, 31)
    m = re.search(r"before (\d{4})\b", t)
    if m:
        return dt.date(int(m.group(1)), 1, 1)
    m = re.search(r"(?:by end of|by the end of|through|by) (" + _M + r")\b", t)
    if m:
        d = _fin_mois(jeu.year, MOIS[m.group(1)])
        return d if d >= jeu else _fin_mois(jeu.year + 1, MOIS[m.group(1)])
    m = re.search(r"before (" + _M + r")\b", t)
    if m:
        d = dt.date(jeu.year, MOIS[m.group(1)], 1)
        return d if d >= jeu else dt.date(jeu.year + 1, MOIS[m.group(1)], 1)
    return None


def charger_pax(chemin: Path = PAX) -> list[tuple[dt.date, str, str]]:
    out = []
    for r in csv.DictReader(chemin.open(encoding="utf-8")):
        try:
            out.append((J(r["date"]), r["processus"] or r.get("pays", ""), (r["stade"] or "").strip()))
        except (ValueError, KeyError):
            continue
    return sorted(out)


def taux_conclusion(A, jeu: dt.date, stades: tuple[str, ...]) -> float:
    """Accords des `stades` signés dans un processus actif, par jour de processus actif, avant `jeu`."""
    A = [a for a in A if a[0] < jeu]
    if not A:
        return 0.0
    fin = min(jeu, A[-1][0])                                   # au-delà de la couverture du jeu de données : non compté
    par = {}
    for d, p, s in A:
        par.setdefault(p, []).append((d, s))
    evts, jours = 0, 0
    for p, L in par.items():
        L.sort()
        actif_jusqua = None
        for d, s in L:
            if actif_jusqua is not None and d < actif_jusqua and s in stades:
                evts += 1
            debut = max(d, actif_jusqua) if actif_jusqua is not None else d
            fin_d = d + dt.timedelta(days=ACTIF)
            if fin_d > debut:
                jours += max(0, (min(fin_d, fin) - min(debut, fin)).days)
            actif_jusqua = max(actif_jusqua or d, fin_d)
    return evts / jours if jours else 0.0


def taux_rupture(A, jeu: dt.date) -> float:
    A = [a for a in A if a[0] < jeu]
    if not A:
        return 0.0
    fin = min(jeu, A[-1][0])
    par = {}
    for d, p, s in A:
        if s == "Cea":
            par.setdefault(p, []).append(d)
    evts, jours = 0, 0
    for L in par.values():
        L.sort()
        for i, d in enumerate(L):
            suiv = L[i + 1] if i + 1 < len(L) else None
            borne = min(d + dt.timedelta(days=ACTIF), fin)
            if suiv is not None and suiv <= borne:
                evts += 1
                jours += (suiv - d).days
            else:
                jours += max(0, (borne - d).days)
    return evts / jours if jours else 0.0


def probabilite_pax(cl: str, titre: str, jeu: dt.date, A) -> float | None:
    e = echeance(titre, jeu)
    if e is None or e <= jeu:
        return None
    h = (e - jeu).days
    if cl == "cessez_le_feu":
        return 1 - math.exp(-taux_conclusion(A, jeu, ("Cea",)) * h)
    if cl == "accord_paix":
        return 1 - math.exp(-taux_conclusion(A, jeu, ("SubComp", "SubPar")) * h)
    if cl == "tenue":
        r = 1 - math.exp(-taux_rupture(A, jeu) * h)
        return r if re.search(r"\bbroken\b", titre, re.I) else 1 - r
    return None


def _lg(p: float) -> float:
    p = min(max(p, .01), .99)
    return math.log(p / (1 - p))


def melanger(p_bot: float, p_regle: float) -> float:
    m = 1 / (1 + math.exp(-((1 - POIDS) * _lg(p_bot) + POIDS * _lg(p_regle))))
    return min(max(m, p_bot - ECART_MAX), p_bot + ECART_MAX)


def estimer(titre: str, jeu: dt.date | None = None, branchees: tuple[str, ...] = ()) -> dict | None:
    """Dans le bot : seules les sous-familles branchées (fichier des taux) s'appliquent."""
    import json
    cl = classe(titre)
    if cl is None:
        return None
    try:
        T = json.loads(TAUX_CLASSES.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if cl not in T.get("branchees", []):
        return None
    jeu = jeu or dt.date.today()
    if cl in ("rencontre", "autre"):
        p = T["taux"][cl]
    else:
        try:
            p = probabilite_pax(cl, titre, jeu, charger_pax())
        except (OSError, KeyError):
            return None
    if p is None:
        return None
    return {"classe": cl, "p": min(max(p, .01), .99)}
