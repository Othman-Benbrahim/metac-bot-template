"""Traduction algorithmique des règles sourcées en probabilités (décision de l'auteur du 2026-11-21, 15 h 09 : « comment
traduire algorithmiquement des faits et des mécanismes en probabilités »). Aucun appel de modèle, aucun jugement : du
code, à partir des paramètres écrits dans ecosystemes/regles-coutumieres.yaml et de l'horizon de la question.

Trois formes de traduction, fixées ici avant tout regard sur les issues :
- fréquence → probabilité sur l'horizon : un événement qui survient λ fois par an a une probabilité
  1 − exp(−λ·t) de survenir au moins une fois en t années (loi de Poisson) ; « ne pas survenir » = le complément ;
- part historique → probabilité directe (ex. 6 premiers titres sur 18 Coupes du monde depuis 1950) ;
- fenêtre de calendrier → probabilité selon que la fenêtre contient ou non l'échéance habituelle (Royal Mail).
Quand une période récente est désignée par la règle elle-même comme un changement de régime (« plus fréquente depuis
2021 », « la réussite remonte après 2003 »), c'est la période récente qui sert : l'état précède l'essence.
Une règle sans paramètre traduisible (procédure, calendrier sans taux, sondages sans chiffres) ne donne rien (None).
Les comptes nuls sont lissés à la manière de Jeffreys (k + 0,5) / (n + 1) pour ne jamais rendre 0 ou 1.

combiner(p_S, p_R) : moyenne des logits, à poids égaux (fixée d'avance) ; plusieurs règles : moyenne de leurs logits.
"""
from __future__ import annotations

import csv
import json
import math
import re
from bisect import bisect_right
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

ANNEES = 365.25


def _poisson(lam_par_an: float, jours: float) -> float:
    return 1 - math.exp(-lam_par_an * max(jours, 0) / ANNEES)


def _neg(t: str) -> bool:
    """La question demande que l'événement N'arrive PAS (ou qu'un état se maintienne)."""
    return bool(re.search(r"\b(not|no longer|refrain|fail to|remain\w*|still be|stay\w*)\b", t))


def _oriente(p: float, t: str) -> float:
    return 1 - p if _neg(t) else p


def _jours_jusqua(jeu: str, mois: int, jour: int, fin: str) -> bool:
    """La fenêtre ]jeu ; fin] contient-elle une date (mois, jour) ?"""
    d0, d1 = date.fromisoformat(jeu), date.fromisoformat(fin)
    for a in (d0.year, d0.year + 1):
        x = date(a, mois, jour)
        if d0 < x <= d1:
            return True
    return False


def p_regle(regle: str, titre: str, horizon: float, jeu: str, cloture: str, question: str = "",
            sondage: dict | None = None) -> float | None:
    """`sondage` : l'entrée de collecte de la question (bot, questions ouvertes) ; sinon lue dans le registre du banc."""
    t = titre.lower()
    if regle in ("sondages_erreur_comparee", "us_erreur_selon_temps_restant", "us_erreur_sondages_par_echelle"):
        return p_sondages(question, titre, horizon, sondage)
    h = float(horizon)
    if regle == "chefs_d_etat_sortie_irreguliere":                       # 0,17 % des pays-mois (2001-2014)
        if re.search(r"\b(election\w*|vote|referendum|resign\w*)\b", t):   # « sauf échéance électorale » (texte de la
            return None                                                  # règle) ; une démission est une sortie régulière
        return _oriente(1 - (1 - 0.0017) ** (h / 30.44), t)
    if regle == "coups_d_etat_frequence":                                # réussite remontée après 2003 : 12/18 en 8 ans,
        lam = 12 / 8 * (0.365 + 0.319)                                   # part Afrique + Amériques
        return _oriente(_poisson(lam, h), t) if re.search(r"\b(africa|latin america|americas)\b", t) else None
    if regle == "sommets_etats_unis_russie":                             # 8 sommets en 26 ans
        return _oriente(_poisson(8 / 26, h), t)
    if regle == "dow_jones_changements":                                 # 14 changements en 26 ans
        return _oriente(_poisson(14 / 26, h), t)
    if regle == "opep_departs":                                          # 4 départs en 8 ans
        return _oriente(_poisson(4 / 8, h), t)
    if regle == "coree_du_nord_essais_nucleaires":                       # aucun essai depuis le 3 sept. 2017
        ans = (date.fromisoformat(jeu) - date(2017, 9, 3)).days / ANNEES
        return _oriente(_poisson(0.5 / (ans + 1), h), t)
    if regle == "papes_voyages":                                         # François : 40 voyages en 10 ans
        return _oriente(_poisson(40 / 10, h), t)
    if regle == "us_chambre_sanctions_disciplinaires":                   # « plus fréquente depuis 2021 » : 2021-2025,
        return _oriente(_poisson(6 / 5, h), t)                           # 5 censures + 1 réprimande en 5 ans
    if regle == "royaume_uni_niveau_menace":                             # baisses depuis « grave » : 2009, 2011, 2016
        if re.search(r"\b(reduc\w*|lower\w*|decreas\w*|downgrad\w*)\b", t):    # sur 2006-08 → 2018-03
            return _poisson(3 / 11.6, h)
        return None
    if regle == "royal_mail_hausses_tarifs":                             # hausses en avril et en octobre (4 sur 4)
        dedans = _jours_jusqua(jeu, 4, 7, cloture) or _jours_jusqua(jeu, 10, 1, cloture)
        return (4 + 0.5) / (4 + 1) if dedans else 0.5 / (4 + 1)
    if regle == "us_ouragans_atterrissage":                              # premiers atterrissages 1950-2005 par mois
        if not cloture[5:10] <= "09-01":
            return None
        mois = {6: 4, 7: 7, 8: 18, 9: 11, 10: 3}
        m0 = int(jeu[5:7])
        restant = sum(v for k, v in mois.items() if k >= m0 and k <= 8)
        deja = sum(v for k, v in mois.items() if k < m0)
        return (restant + 0.5) / (56 - deja + 1)
    if regle == "calendriers_annonces_glissent":                         # 1 grand projet sur 10 dans les délais :
        if re.search(r"\b(repair\w*|construct\w*|complet\w*|finish\w*|built)\b", t):   # chantiers seulement (homologie)
            return 0.1
        return None
    if regle == "us_fed_calendrier":
        return p_fed(titre, jeu, cloture)
    if regle == "coupe_du_monde_vainqueurs_hotes":                       # premier titre : 6 éditions sur 18 depuis 1950
        if re.search(r"\b(never won|first[- ]time (winner|champion))\b", t):
            return (6 + 0.5) / (18 + 1)
        return None
    return None


# ---------------------------------------------------------------------------------------------------------------
# Décisions de la Fed (2026-11-21, 15 h 19 : « commencer par la Fed, les données sont déjà là »).
# Réunions programmées du FOMC 2021-2026 (dernier jour), d'après le calendrier officiel :
# https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm (consulté le 2026-11-21).
FOMC = ("2021-01-27 2021-03-17 2021-04-28 2021-06-16 2021-07-28 2021-09-22 2021-11-03 2021-12-15 2022-01-26 2022-03-16 "
        "2022-05-04 2022-06-15 2022-07-27 2022-09-21 2022-11-02 2022-12-14 2023-02-01 2023-03-22 2023-05-03 2023-06-14 "
        "2023-07-26 2023-09-20 2023-11-01 2023-12-13 2024-01-31 2024-03-20 2024-05-01 2024-06-12 2024-07-31 2024-09-18 "
        "2024-11-07 2024-12-18 2025-01-29 2025-03-19 2025-05-07 2025-06-18 2025-07-30 2025-09-17 2025-10-29 2025-12-10 "
        "2026-01-28 2026-03-18 2026-04-29 2026-06-17 2026-07-29 2026-09-16 2026-10-28 2026-12-09").split()
ETATS = ("baisse", "pause", "hausse")
MOIS = {m: i for i, m in enumerate(("january february march april may june july august september october november "
                                     "december").split(), 1)}


@lru_cache(maxsize=1)
def _dff() -> tuple[list[str], dict[str, float]]:
    s = sorted((r["jour"], float(r["valeur"])) for r in csv.DictReader(open(Path("registre") / "fred.csv", encoding="utf-8"))
               if r["serie"] == "DFF")
    return [a for a, _ in s], dict(s)


def decisions_connues(jeu: str) -> list[tuple[str, float]]:
    """(réunion, variation du taux effectif en points, arrondie au quart) pour les réunions dont l'effet est visible
    avant le jeu : médiane des 5 jours ouvrés après moins médiane des 5 jours avant (série DFF de FRED)."""
    import statistics
    jours, d = _dff()
    out = []
    for m in FOMC:
        if (date.fromisoformat(m) + timedelta(days=9)).isoformat() >= jeu:
            break
        i = bisect_right(jours, m)
        av, ap = jours[max(0, i - 6):i - 1], jours[i + 1:i + 6]
        if len(av) < 3 or len(ap) < 3:
            continue
        out.append((m, round((statistics.median(d[j] for j in ap) - statistics.median(d[j] for j in av)) * 4) / 4))
    return out


def _etat(v: float) -> int:
    return 0 if v < 0 else (2 if v > 0 else 1)


def _transitions(dec: list[tuple[str, float]]) -> list[list[float]]:
    n = [[0.5] * 3 for _ in range(3)]                          # Jeffreys
    for (_, a), (_, b) in zip(dec[:-1], dec[1:]):
        n[_etat(a)][_etat(b)] += 1
    return [[x / sum(r) for x in r] for r in n]


def _part_taille(dec: list[tuple[str, float]], sens: int, grand: bool) -> float:
    """Part des mouvements de ce sens qui font ≥ 0,5 point (grand) ou exactement 0,25 (petit), lissée."""
    v = [abs(x) for _, x in dec if _etat(x) == sens]
    k = sum(1 for x in v if (x >= 0.5) == grand)
    return (k + 0.5) / (len(v) + 1)


def p_fed(titre: str, jeu: str, cloture: str) -> float | None:
    t = titre.lower()
    if re.search(r"\bnext (two|three|four) decisions\b|–|-pause", t):
        return None
    dec = decisions_connues(jeu)
    if len(dec) < 8:
        return None
    T = _transitions(dec)
    avenir = [m for m in FOMC if m >= jeu]
    m_cible = None
    mm = re.search(r"\b(" + "|".join(MOIS) + r")\b(?:\s+(20\d\d))?\s+meeting", t)
    if mm:
        mois, an = MOIS[mm.group(1)], int(mm.group(2) or jeu[:4])
        if not mm.group(2) and mois < int(jeu[5:7]):
            an += 1
        m_cible = next((m for m in avenir if m.startswith(f"{an}-{mois:02d}")), None)
    elif re.search(r"\bbefore\b", t):
        m_cible = max((m for m in avenir if m <= cloture), default=None)
    if m_cible is None:
        return None
    k = avenir.index(m_cible) + 1                               # nombre de réunions jusqu'à la cible incluse
    sens = 1 if re.search(r"\bno change|pause|hold|unchanged\b", t) else (
        0 if re.search(r"\b(decrease\w*|cut\w*|lower\w*)\b", t) else (
            2 if re.search(r"\b(increase\w*|raise\w*|hike\w*)\b", t) else None))
    if sens is None:
        return None
    depart = _etat(dec[-1][1])
    au_moins_une = re.search(r"\b(by|before)\b", t) and not re.search(r"\bafter the\b", t)
    if au_moins_une and sens != 1:                              # au moins un mouvement de ce sens en k réunions
        ok = [i for i in range(3) if i != sens]
        v = {i: (1.0 if i == depart else 0.0) for i in ok} if depart != sens else None
        if v is None:
            v = {i: T[depart][i] for i in ok}
            k -= 1
        for _ in range(k):
            v = {j: sum(v[i] * T[i][j] for i in ok) for j in ok}
        p = 1 - sum(v.values())
    else:                                                       # issue de la réunion cible
        v = [1.0 if i == depart else 0.0 for i in range(3)]
        for _ in range(k):
            v = [sum(v[i] * T[i][j] for i in range(3)) for j in range(3)]
        p = v[sens]
        if sens != 1:
            if re.search(r"\b50\+|\b50 ?bps|\b75\b", t):
                p *= _part_taille(dec, sens, True)
            elif re.search(r"\b25 ?bps\b", t) and not re.search(r"\b25\+", t):
                p *= _part_taille(dec, sens, False)
    return min(0.99, max(0.01, p))


# ---------------------------------------------------------------------------------------------------------------
# Sondages électoraux (2026-11-21, 15 h 24) : moyennes collectées par collecte_sondages.py, erreur historique des
# règles sourcées. Erreur absolue moyenne par candidat (élections nationales, 45 pays) : environ 4 points à 150-200
# jours, 3 points à 50 jours, 2 la dernière semaine (us_erreur_selon_temps_restant, sondages_erreur_comparee) ; pour
# les primaires américaines, erreur sur l'écart 8,7 points (us_erreur_sondages_par_echelle), soit 8,7/√2 par candidat.
# Écart-type = 1,25 × erreur absolue moyenne (loi normale). Tirages indépendants par candidat, 4 000, graine fixe.
SONDAGES = Path("registre") / "sondages-questions.json"


@lru_cache(maxsize=1)
def _sondages() -> dict:
    try:
        return json.loads(SONDAGES.read_text(encoding="utf-8")).get("questions", {})
    except Exception:
        return {}


def _erreur_par_candidat(jours: float, primaire: bool) -> float:
    if primaire:
        return 8.7 / math.sqrt(2)
    pts = [(0, 2.0), (7, 2.0), (50, 3.0), (175, 4.0)]
    if jours >= 175:
        return 4.0
    for (a, ea), (b, eb) in zip(pts[:-1], pts[1:]):
        if a <= jours <= b:
            return ea + (eb - ea) * (jours - a) / (b - a)
    return 4.0


def p_sondages(question: str, titre: str, horizon: float, entree: dict | None = None) -> float | None:
    import numpy as np
    q = entree if entree is not None else (_sondages().get(question) or {})
    moy, col = q.get("moyennes") or {}, q.get("colonne_sujet")
    if q.get("statut") != "ok" or not col or col not in moy or len(moy) < 2:
        return None
    if "verification" in q and not str(q["verification"]).startswith("confirme"):
        return None                                            # lecture non confirmée : les sondages ne servent pas
    t = titre.lower()
    noms = list(moy)
    mu = np.array([moy[n]["moyenne"] for n in noms])
    sd = 1.25 * _erreur_par_candidat(float(horizon), bool(re.search(r"\bprimar(y|ies)\b", t)))
    rng = np.random.default_rng(sum(map(ord, question)))
    tirs = rng.normal(mu, sd, size=(4000, len(noms)))
    i = noms.index(col)
    rang = (tirs > tirs[:, [i]]).sum(axis=1) + 1                 # 1 = en tête
    if re.search(r"\bby (more than |at least )?\d+(\.\d+)?\s*(%|points?)", t):   # écart de voix : non traduit
        return None
    m = re.search(r"\bat least (\d{1,2}(?:\.\d+)?)\s*%", t)
    if m:
        p = float((tirs[:, i] >= float(m.group(1))).mean())
    elif re.search(r"\b(second[- ]most|second place|second)\b", t):
        p = float((rang == 2).mean())
    elif re.search(r"\b(third[- ]most|third place|third)\b", t):
        p = float((rang == 3).mean())
    elif re.search(r"\b(advance|runoff|qualify|top two|top-two)\b", t):
        p = float((rang <= 2).mean())
    elif re.search(r"\b(win|wins|most votes|most seats|first round|become)\b", t) and not re.search(
            r"\b(majority|supermajority|seats? \d|\d+-\d+ seats|by \d+%|every)\b", t):
        p = float((rang == 1).mean())
    else:
        return None
    return min(0.99, max(0.01, p))


def _logit(p: float) -> float:
    p = min(0.98, max(0.02, p))
    return math.log(p / (1 - p))


def combiner(p_s: float, ps_regles: list[float]) -> float:
    if not ps_regles:
        return p_s
    lr = sum(_logit(p) for p in ps_regles) / len(ps_regles)
    z = (_logit(p_s) + lr) / 2
    return 1 / (1 + math.exp(-z))
