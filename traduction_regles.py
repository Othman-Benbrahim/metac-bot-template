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

import math
import re
from datetime import date

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


def p_regle(regle: str, titre: str, horizon: float, jeu: str, cloture: str) -> float | None:
    t = titre.lower()
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
    if regle == "coupe_du_monde_vainqueurs_hotes":                       # premier titre : 6 éditions sur 18 depuis 1950
        if re.search(r"\b(never won|first[- ]time (winner|champion))\b", t):
            return (6 + 0.5) / (18 + 1)
        return None
    return None


def _logit(p: float) -> float:
    p = min(0.98, max(0.02, p))
    return math.log(p / (1 - p))


def combiner(p_s: float, ps_regles: list[float]) -> float:
    if not ps_regles:
        return p_s
    lr = sum(_logit(p) for p in ps_regles) / len(ps_regles)
    z = (_logit(p_s) + lr) / 2
    return 1 / (1 + math.exp(-z))
