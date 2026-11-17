"""Loi de Richardson à la bonne échelle : la TAILLE DES ÉVÉNEMENTS, universelle, × la FRÉQUENCE locale (bot 0.10.240).

Décision d'auteur du 2026-11-17 (20 h 06) : adapter Richardson comme Hägerstrand, « la bonne mesure à la bonne
échelle ». Premier essai (banc_richardson.py, clos) : une loi à queue lourde ajustée sur les morts MENSUELS d'un pays ;
ce n'est pas ce que dit Richardson. Sa loi porte sur la taille des événements violents (une queue en puissance,
la même partout) ; ce qui varie d'un pays à l'autre, c'est leur fréquence. D'où, pour les questions de type Metaculus
« au moins un événement de T morts ou plus dans le pays dans les 30 jours ? » (attentat de masse, bataille meurtrière),
où le passé du pays seul compte souvent 0 cas sur n :
  B_bot : part des fenêtres disjointes de 30 jours passées du pays (depuis 2015) où un tel événement a eu lieu (règle de
          compter : k / n, bords 1/(2n) et 1 − 1/(2n)) ;
  B_rich : P = 1 − exp(−λ · 30 · S(T)) ; λ = événements par jour du pays sur les 365 jours avant d0 ; S(T) = part des
           événements de taille ≥ T, TOUS pays confondus, sur les 5 ans avant d0, par une loi de Pareto : S(T) =
           S(10) · (T / 10)^(−α), α estimé par Hill sur les tailles ≥ 10.
Unité : le plus grand événement d'un carreau PRIO-GRID un jour donné (registre/ucdp-cellules.csv.gz, max_morts).
Préenregistrement : preenregistrements/geo-math.md, « Richardson à la bonne échelle ». Aucun modèle de langue.

Critère : T = 100, questions de confirmation (d0 ≥ 2024-01-01), B_rich contre B_bot, bootstrap par mois, risque
es.risque_corrige(1) ; meilleur si la borne haute < 0. T = 25 et la variante empirique (S(T) comptée, sans loi) :
rapportées.

    python banc_richardson_evenements.py
"""
from __future__ import annotations

import bisect
import csv
import gzip
import json
import math
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import banc_cr_metaculus as bm
import combinaisons as cb
import combinaisons_gdelt as cg

ENTREE = Path("registre") / "ucdp-cellules.csv.gz"
SORTIE = Path("registre") / "banc-richardson-evenements.json"
COUPURE = "2024-01-01"
XMIN = 10


def charger(chemin: Path = ENTREE) -> tuple[dict, list[tuple[str, float]]]:
    """({pays: {jour: [tailles]}}, [(jour, taille)] trié pour tous les pays)."""
    par, tous = {}, []
    with gzip.open(chemin, "rt", encoding="utf-8") as f:
        for x in csv.DictReader(f):
            t = float(x.get("max_morts") or x["morts"])
            par.setdefault(x["pays"], {}).setdefault(x["jour"], []).append(t)
            tous.append((x["jour"], t))
    tous.sort()
    return par, tous


def hill(tailles: list[float], xmin: float = XMIN) -> float | None:
    q = [t for t in tailles if t >= xmin]
    if len(q) < 30:
        return None
    return len(q) / sum(math.log(t / xmin) for t in q)


def survie(tailles: list[float], seuil: float, loi: bool) -> float | None:
    if not tailles:
        return None
    s10 = sum(1 for t in tailles if t >= XMIN) / len(tailles)
    if not loi:
        return (sum(1 for t in tailles if t >= seuil) + 0.5) / (len(tailles) + 1)
    a = hill(tailles)
    return None if a is None else s10 * (seuil / XMIN) ** (-a)


def questions(par: dict, tous: list[tuple[str, float]], dernier: date, seuil: float) -> list[dict]:
    ancres = cg.mois(date(2016, 1, 1), dernier - timedelta(days=30))
    jours_tous = [j for j, _ in tous]
    cache: dict = {}
    out = []
    for pays, c in sorted(par.items()):
        def maxi(a: date, b: date) -> float:
            d, m = a, 0.0
            while d < b:
                m = max([m] + c.get(d.isoformat(), []))
                d += timedelta(days=1)
            return m

        def nombre(a: date, b: date) -> int:
            d, n = a, 0
            while d < b:
                n += len(c.get(d.isoformat(), []))
                d += timedelta(days=1)
            return n
        for d0 in ancres:
            fen, b = [], d0
            while b - timedelta(days=30) >= date(2015, 1, 1):
                fen.append(maxi(b - timedelta(days=30), b))
                b -= timedelta(days=30)
            if len(fen) < 5:
                continue
            k = sum(1 for m in fen if m >= seuil)
            n = len(fen)
            if d0 not in cache:
                i0 = bisect.bisect_left(jours_tous, (d0 - timedelta(days=5 * 365)).isoformat())
                i1 = bisect.bisect_left(jours_tous, d0.isoformat())
                tl = [t for _, t in tous[i0:i1]]
                cache[d0] = {"loi": survie(tl, seuil, True), "emp": survie(tl, seuil, False)}
            lam = nombre(d0 - timedelta(days=365), d0) / 365
            x = {"jeu": d0.isoformat(), "pays": pays, "issue": int(maxi(d0, d0 + timedelta(days=30)) >= seuil),
                 "p_bot": 1 / (2 * n) if k == 0 else 1 - 1 / (2 * n) if k == n else k / n}
            for nom, s in cache[d0].items():
                if s is not None:
                    x[f"p_{nom}"] = min(max(1 - math.exp(-lam * 30 * s), 1e-4), 1 - 1e-4)
            out.append(x)
    return [x for x in out if "p_loi" in x and "p_emp" in x]


def resumer(xs: list[dict], juge: bool) -> dict:
    import essais as es
    pm = lambda s, k: round(sum(cb.pl(x[k], x["issue"]) for x in s) / len(s), 4) if s else None
    conf = [x for x in xs if x["jeu"] >= COUPURE]
    ex = [x for x in xs if x["jeu"] < COUPURE]
    r = {"questions": len(xs), "n_confirmation": len(conf),
         "oui": round(sum(x["issue"] for x in conf) / len(conf), 3) if conf else None,
         "confirmation": {k: pm(conf, f"p_{k}") for k in ("bot", "loi", "emp")},
         "exploration": {k: pm(ex, f"p_{k}") for k in ("bot", "loi", "emp")}}
    if juge and len(conf) >= 30:
        ec = [(x["jeu"][:7], cb.pl(x["p_loi"], x["issue"]) - cb.pl(x["p_bot"], x["issue"])) for x in conf]
        bas, haut = cb.bootstrap(ec, es.risque_corrige(1))
        r.update(ecart_moyen=round(sum(e for _, e in ec) / len(ec), 4), intervalle_corrige=[round(bas, 4), round(haut, 4)],
                 verdict="Richardson meilleur que le bot" if haut < 0 else
                 ("Richardson moins bon que le bot" if bas > 0 else "non tranché"))
    return r


def principal() -> int:
    if not ENTREE.exists():
        print("registre/ucdp-cellules.csv.gz absent.")
        return 1
    par, tous = charger()
    dernier = max(date.fromisoformat(j) for j, _ in tous)
    alpha = hill([t for _, t in tous])
    res = {"note": "perte log, plus bas = mieux ; aucun modèle de langue ; données UCDP GED (CC BY 4.0)",
           "alpha_hill_tout": round(alpha, 3) if alpha else None,
           "seuil_100": resumer(questions(par, tous, dernier, 100), True),
           "seuil_25": resumer(questions(par, tous, dernier, 25), False)}
    SORTIE.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    texte = json.dumps(res, ensure_ascii=False, indent=1)
    print(texte)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fo:
            fo.write("## Richardson à la bonne échelle (UCDP)\n\n```\n" + texte + "\n```\n")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
