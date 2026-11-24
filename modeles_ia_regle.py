"""Sous-famille « modèles d'IA » des produits — échelle des versions par laboratoire (Epoch AI). Décision de l'auteur,
2026-11-24 (16 h 52 « On commence » ; source Epoch validée à 14 h 35). Procédure : preenregistrements/modeles-ia.md.

Mécanisme (carte : sciences et techniques, sorties de modèles) : chaque laboratoire monte une échelle de versions
(GPT, Claude, Gemini, Grok, Llama) ; l'écart entre deux barreaux suit une cadence mesurable.
- Version visée entière (Claude 5, Gemini 4, GPT-6) : échelle des versions entières ; âge = jours depuis la première
  sortie de la version entière précédente.
- Version visée décimale (GPT-5.5) : échelle de toutes les versions ; âge = jours depuis le dernier barreau inférieur.
- Taux par jour, par tranche d'âge (< 180 jours, 180-364, ≥ 365), sur les écarts de toutes les familles avant la date de
  la question (écart en cours censuré). P = 1 − exp(−Σ λ·jours parcourus pendant h) ; version déjà sortie = 1.
- Abstention : variante nommée (Flash, Pro, mini, Sonnet, Opus, Haiku…), modèle sans numéro, « claim », course entre
  deux événements, échéance illisible.
"""
from __future__ import annotations

import csv
import datetime as dt
import math
import os
import re
from pathlib import Path

import accords_regle as ar

ICI = Path(__file__).resolve().parent
EPOCH = Path(os.environ.get("ALPHABET_REGISTRE", ICI / "registre")) / "epoch-modeles.csv"
LABO = {"gpt": "openai", "claude": "anthropic", "gemini": "google", "grok": "xai", "llama": "meta"}
NOM = re.compile(r"\b(gpt|claude|gemini|grok|llama)\b[- ]?(?:(?:opus|sonnet|haiku|pro|flash|ultra)\s+)?(\d{1,2}(?:\.\d+)?)",
                 re.I)
VARIANTE = re.compile(r"\b(flash|pro|mini|nano|sonnet|opus|haiku|ultra|turbo|codex)\b", re.I)
TRANCHES = (180, 365)
J = dt.date.fromisoformat


def versions(chemin: Path = EPOCH, jusqua: dt.date | None = None):
    V = {}
    for r in csv.DictReader(chemin.open(encoding="utf-8")):
        m = NOM.search(r["Model"] or "")
        try:
            d = J((r["Publication date"] or "")[:10])
        except ValueError:
            continue
        if not m or (jusqua and d >= jusqua):
            continue
        fam, v = m.group(1).lower(), float(m.group(2))
        if v >= 10 or LABO[fam] not in (r["Organization"] or "").lower().replace(" ", ""):
            continue
        k = (fam, v)
        if k not in V or d < V[k]:
            V[k] = d
    return V


def _echelle(V, fam, entiere: bool):
    L = sorted((v, d) for (f, v), d in V.items() if f == fam and (not entiere or v == int(v)))
    out, dmax = [], None
    for v, d in L:                                    # un barreau compte à sa première date, dans l'ordre des versions
        if dmax is None or d >= dmax:
            out.append((v, d))
            dmax = d
    return out


def taux(V, jeu: dt.date, entiere: bool):
    ev, ex = [0, 0, 0], [0, 0, 0]
    lim = [0, *TRANCHES, 10 ** 9]
    for fam in LABO:
        E = _echelle(V, fam, entiere)
        for i, (v, d) in enumerate(E):
            fin = E[i + 1][1] if i + 1 < len(E) else jeu
            duree = (fin - d).days
            for k in range(3):
                ex[k] += max(0, min(duree, lim[k + 1]) - lim[k])
            if i + 1 < len(E):
                ev[sum(duree >= t for t in TRANCHES)] += 1
    return [ev[k] / ex[k] if ex[k] else 0.0 for k in range(3)], ev, ex


def cible(titre: str):
    t = titre or ""
    if re.search(r"\bclaim\b|\bthan\b|\bbefore (gta|grand theft)\b", t, re.I):
        return None
    m = NOM.search(t)
    if not m or VARIANTE.search(t):
        return None
    return m.group(1).lower(), float(m.group(2))


def probabilite(titre: str, jeu: dt.date, chemin: Path = EPOCH) -> float | None:
    c = cible(titre)
    e = ar.echeance(titre, jeu)
    if re.search(r"this decade", titre or "", re.I):
        e = dt.date(2029, 12, 31)
    m = re.search(r"\bq([1-4]) (\d{4})", titre or "", re.I)
    if m:
        e = dt.date(int(m.group(2)), 3 * int(m.group(1)), 1) + dt.timedelta(days=31)
        e = e.replace(day=1) - dt.timedelta(days=1)
    if c is None or e is None or e <= jeu:
        return None
    V = versions(chemin, jeu)
    fam, v = c
    if any(f == fam and x >= v for (f, x) in V):
        return 1.0
    entiere = v == int(v)
    precedents = [d for (f, x), d in V.items() if f == fam and x < v and (not entiere or x == int(x))]
    if not precedents:
        return None
    age = (jeu - max(precedents)).days
    lam, _, _ = taux(V, jeu, entiere)
    lim = [0, *TRANCHES, 10 ** 9]
    h = (e - jeu).days
    cumul = sum(lam[k] * max(0, min(age + h, lim[k + 1]) - max(age, lim[k])) for k in range(3))
    return 1 - math.exp(-cumul)
