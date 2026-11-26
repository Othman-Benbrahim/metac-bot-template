"""Brique « tennis : force mesurée (Elo) » pour « X gagnera-t-il <grand tournoi> ? » (décision de l'auteur, 2026-11-26,
12 h 36 ; méthode retenue par le duel pré-enregistré, preenregistrements/duel-tennis.md : l'Elo bat 1/N dans 16 saisons
sur 16 et la forme récente sur l'ensemble).

Notes : registre/elo/tennis_<atp|wta>.csv.gz (Sackmann jusqu'en mai 2026, puis grands tournois lus sur Wikipédia).
Le tableau réel n'est pas connu avant le tirage : on simule (4 000 tirages) un tableau de 128 places (Grand Chelem) ou de
96 joueurs avec 32 exemptés (Masters 1000 / WTA 1000), formé des meilleures notes parmi les joueurs actifs (un match
dans les 12 derniers mois), têtes de série 1 à 32 placées selon l'Elo (1 et 2 dans des moitiés opposées, 3-4 dans les
autres quarts, etc.), le reste tiré au hasard. Approximation déclarée : ni forfaits, ni blessures, ni surface, ni format
au meilleur des cinq manches ; le contradicteur couvre les questions hors domaine.
Abstention : aucun match connu du joueur depuis 90 jours (blessure ou retrait probable) ; autre forme que « gagner » (atteindre un tour, finale, demi-finale), joueur introuvable ou inactif, tournoi
non reconnu.
"""
from __future__ import annotations

import csv
import datetime as dt
import gzip
import random
import re
from functools import lru_cache
from pathlib import Path

ICI = Path(__file__).resolve().parent
REG = ICI / "registre" / "elo"
GAGNER = re.compile(r"\bwins?\b|\bwin the\b|\bbe the (winner|champion)\b", re.I)
AUTRES = re.compile(r"\b(reach|final|semifinal|semi-final|quarterfinal|quarter-final|round|set|match|vs\.?|beat|iff|if |"
                    r"doubles|mixed|qualif)\w*", re.I)
CHELEMS = re.compile(r"Australian Open|French Open|Roland[- ]Garros|Wimbledon|US Open", re.I)
MILLE = re.compile(r"Indian Wells|Miami Open|Monte[- ]Carlo|Madrid Open|Italian Open|Rome|Canadian Open|National Bank|"
                   r"Cincinnati|Shanghai|Paris Masters|China Open|Wuhan|Dubai|Doha|Qatar Open", re.I)
FEMMES = re.compile(r"women|wta|ladies", re.I)
HOMMES = re.compile(r"\bmen'?s\b|\batp\b|gentlemen", re.I)


@lru_cache(2)
def notes(circuit: str) -> dict[str, tuple[str, float]]:
    """Dernière note et date par joueur."""
    out = {}
    f = REG / f"tennis_{circuit}.csv.gz"
    if not f.exists():
        return out
    with gzip.open(f, "rt", encoding="utf-8") as g:
        for r in csv.DictReader(g):
            e, d = r["entite"], r["date"]
            if e not in out or d >= out[e][0]:
                out[e] = (d, float(r["elo"]))
    return out


def _joueur(titre: str, N: dict) -> str | None:
    t = titre.lower()
    c = [e for e in N if len(e) > 5 and e.lower() in t]
    if not c:   # nom de famille seul, s'il est unique parmi les joueurs
        fam = {}
        for e in N:
            fam.setdefault(e.split()[-1].lower(), []).append(e)
        c = [v[0] for k, v in fam.items() if len(v) == 1 and len(k) > 3 and re.search(r"\b" + re.escape(k) + r"\b", t)]
    return max(c, key=len) if len(c) == 1 or (c and all(x in max(c, key=len) for x in c)) else None


def _tableau(champ: list[str], R: dict, taille: int, rnd: random.Random) -> list[str | None]:
    """Places du tableau (128) : têtes de série aux places d'usage, exemptions (None) si moins de 128 joueurs."""
    t = 128
    places = [None] * t
    graines = champ[:32]
    reste = champ[32:]
    # places d'usage des têtes de série dans un tableau de 128 (1 en haut, 2 en bas, 3-4 aux quarts, 5-8, 9-16, 17-32)
    pos = [0, 127, 32, 95, 64, 31, 96, 63, 16, 111, 48, 79, 15, 112, 47, 80, 8, 119, 40, 87, 24, 103, 56, 71, 7, 120,
           39, 88, 23, 104, 55, 72]
    groupes = [(0, 2), (2, 4), (4, 8), (8, 16), (16, 32)]
    for a, b in groupes:
        g = graines[a:b]
        p = pos[a:b]
        rnd.shuffle(p) if a >= 2 else None
        for s, q in zip(g, p):
            places[q] = s
    libres = [i for i in range(t) if places[i] is None]
    if taille == 96:   # exemptions : l'adversaire du 1er tour de chaque tête de série est vide
        exemptes = {q ^ 1 for q in pos}
        libres = [i for i in libres if i not in exemptes]
    rnd.shuffle(reste)
    for i, s in zip(libres, reste):
        places[i] = s
    return places


def probabilite(joueur: str, N: dict, taille: int, jour: dt.date, tirages: int = 4000, graine: int = 20261126) -> float:
    limite = (jour - dt.timedelta(days=365)).isoformat()
    actifs = {e: v for e, (d, v) in N.items() if d >= limite}
    champ = sorted(actifs, key=lambda e: -actifs[e])[:taille]
    if joueur not in champ:
        champ = champ[:-1] + [joueur]
    R = {e: actifs.get(e, N[e][1]) for e in champ}
    champ.sort(key=lambda e: -R[e])
    rnd = random.Random(graine)
    gagne = 0
    for _ in range(tirages):
        P = _tableau(champ, R, taille, rnd)
        while len(P) > 1:
            Q = []
            for i in range(0, len(P), 2):
                a, b = P[i], P[i + 1]
                if a is None or b is None:
                    Q.append(a or b)
                    continue
                pa = 1 / (1 + 10 ** ((R[b] - R[a]) / 400))
                Q.append(a if rnd.random() < pa else b)
            P = Q
        gagne += P[0] == joueur
    return gagne / tirages


def estimer(titre: str, jour: dt.date | None = None) -> dict | None:
    jour = jour or dt.date.today()
    if not GAGNER.search(titre) or AUTRES.search(titre):
        return None
    taille = 128 if CHELEMS.search(titre) else (96 if MILLE.search(titre) else None)
    if taille is None:
        return None
    circuits = ["wta"] if FEMMES.search(titre) else (["atp"] if HOMMES.search(titre) else ["atp", "wta"])
    for c in circuits:
        N = notes(c)
        j = _joueur(titre, N)
        if j is None:
            continue
        if N[j][0] < (jour - dt.timedelta(days=90)).isoformat():
            # aucun match connu depuis 3 mois : blessure ou retrait probable (cas de Sinner, forfait à l'US Open 2026
            # sur blessure au genou) ; l'Elo ne le voit pas : abstention, le raisonnement du modèle reprend la main
            return None
        p = probabilite(j, N, taille, jour)
        return {"p_regle": max(p, 0.002), "joueur": j, "circuit": c, "elo": round(N[j][1]), "date_elo": N[j][0],
                "taille_tableau": taille, "p": max(p, 0.002)}
    return None
