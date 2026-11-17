"""Balayage exhaustif des combinaisons de mécanismes, comparé au hasard (bot 0.10.228, en ombre).

Décision d'auteur du 2026-11-17 (14 h 30). Le banc des combinaisons (0.10.226) ne jugeait que les 15 paires de six
mécanismes : « rien de confirmé » pouvait signifier « rien à trouver » ou « trop peu pour voir ». Ici, AUCUN tri
préalable : tous les indicateurs seuls, toutes les paires et tous les triplets de huit indicateurs, sur les trois types
de questions fabriquées à partir de GDELT (combinaisons_gdelt.questions : manifestations, émeutes, démonstrations de
force). Puis le même calcul après avoir redistribué au hasard les indicateurs entre pays du même mois (200 tirages) :
on sait alors combien de « réussites » le hasard produit. La force brute trouve ; le bon sens explique ensuite
(méthode de l'auteur). Aucun modèle de langue : gratuit.

Indicateurs (état « présent », fixés avant tout passage ; données antérieures à la date) :
  M10 élection nationale dans les 30 jours                      M11 voisins en hausse (log > 0,4)
  M14 date de mémoire dans les 14 jours                         M17 alignement_rival ≥ 2
  FC  force_chinoise ≥ 1 (14 jours)                             SC  contre-mesures chinoises ≥ 3 (90 jours)
  HR  actes hostiles russes envers le pays ≥ 3 (30 jours ; agressions, combats, violence de masse, GDELT)
  EL  élan propre : manifestations du pays, 14 derniers jours contre 14 précédents, log > 0,4

Pour chaque combinaison (1, 2 ou 3 indicateurs) et chaque type : cellule « tous présents » ; δ = ln((O + 0,5) /
(E + 0,5)) sur l'exploration (avant le 2025-11-01, au moins 10 questions), appliqué en logit à B sur la confirmation
(au moins 10 questions). Statistique : gain moyen de perte log (ajusté − B ; négatif = mieux). « Réussite » : gain < 0.
Hasard : 200 redistributions des états entre pays du même mois (graine 0), qui gardent la structure jointe des
indicateurs et le lien B-issue. Sorties : nombre de réussites et gain total, réels contre la loi du hasard
(p = (1 + tirages au moins aussi bons) / 201) ; pour chaque combinaison, p corrigé par le maximum (Westfall-Young :
part des tirages dont le MEILLEUR gain bat le gain observé).

Registre : registre/combinaisons-balayage.json.

    python combinaisons_balayage.py [--tirages 200]
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

import combinaisons as cb
import combinaisons_gdelt as cg
import indicateurs_niche as ni

RESUME = Path("registre") / "combinaisons-balayage.json"
HOSTILITES = Path("registre") / "gdelt-hostilites-ru.csv"
HOSTILITES_JOURS = Path("registre") / "gdelt-hostilites-jours.txt"
INDICATEURS = ("M10", "M11", "M14", "M17", "FC", "SC", "HR", "EL")
TYPES = ("manifestations", "emeutes", "force")
N_MIN = 10


def charger_hostilites() -> tuple[dict, set[str]]:
    par: dict = {}
    if HOSTILITES.exists():
        for x in csv.DictReader(HOSTILITES.open(encoding="utf-8")):
            par.setdefault(x["pays"], {})[x["jour"]] = int(x["agressions"]) + int(x["combats"]) + int(x["violence_masse"])
    jours = set(HOSTILITES_JOURS.read_text(encoding="utf-8").split()) if HOSTILITES_JOURS.exists() else set()
    return par, jours


def hostilites(par: dict, jours: set[str], cca2: str, d0: date, fenetre: int = 30) -> int | None:
    js = [(d0 - timedelta(days=k)).isoformat() for k in range(1, fenetre + 1)]
    if sum(j not in jours for j in js) > 3:
        return None
    return 1 if sum(par.get(cca2, {}).get(j, 0) for j in js) >= 3 else 0


def etats_complets(cca2: str, d0: date, debut_el: str | None, host: tuple) -> dict:
    e = cb.etats(cca2, "", d0, debut_el)
    e.pop("M4", None)
    sc = ni.contremesures_chine(cca2, d0)
    e["SC"] = (1 if sc["valeur"] >= 3 else 0) if sc.get("present") else None
    e["HR"] = hostilites(host[0], host[1], cca2, d0)
    g = ni.gdelt(cca2, d0)
    e["EL"] = (1 if g["valeur"] > 0.4 else 0) if g.get("present") else None
    return e


def pl(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-3, 1 - 1e-3)
    return -np.log(np.where(y == 1, p, 1 - p))


def evaluer(etat_q: np.ndarray, typ: np.ndarray, explo: np.ndarray, pb: np.ndarray, y: np.ndarray,
            combis: list[tuple[int, ...]]) -> list[dict]:
    """etat_q : (questions × indicateurs), 1 présent, 0 absent, −1 non mesurable."""
    lb = np.log(np.clip(pb, 1e-6, 1 - 1e-6) / (1 - np.clip(pb, 1e-6, 1 - 1e-6)))
    perte_b = pl(pb, y)
    out = []
    for t_i, t in enumerate(TYPES):
        mt = typ == t_i
        for c in combis:
            cell = mt & np.all(etat_q[:, list(c)] == 1, axis=1)
            ce, cc = cell & explo, cell & ~explo
            ne, nc = int(ce.sum()), int(cc.sum())
            r = {"type": t, "combi": c, "n_exploration": ne, "n_confirmation": nc}
            if ne >= N_MIN and nc >= N_MIN:
                d = float(np.log((y[ce].sum() + 0.5) / (pb[ce].sum() + 0.5)))
                padj = 1 / (1 + np.exp(-(lb[cc] + d)))
                r.update(delta=d, gain=float((pl(padj, y[cc]) - perte_b[cc]).mean()))
            out.append(r)
    return out


def principal(tirages: int) -> int:
    if not ni.GDELT_COMPTES.exists() or not ni.PAIRES_JOUR.exists():
        print("Comptes GDELT absents.")
        return 1
    cache_riv: dict = {}
    brut = ni.rivalites
    ni.rivalites = lambda d0: cache_riv.setdefault((d0.year, d0.month), brut(d0))
    comptes, jm, jp = cg.charger()
    qs = cg.questions(comptes, jm, jp, date.fromisoformat(max(jm)))
    debut_el = None
    if ni.ELECTIONS.exists():
        ds = [x["date"] for x in csv.DictReader(ni.ELECTIONS.open(encoding="utf-8"))]
        debut_el = min(ds) if ds else None
    host = charger_hostilites()
    cles = sorted({(x["cca2"], x["jeu"]) for x in qs})
    index = {k: i for i, k in enumerate(cles)}
    table = np.full((len(cles), len(INDICATEURS)), -1, dtype=np.int8)
    for i, (c, j) in enumerate(cles):
        e = etats_complets(c, date.fromisoformat(j), debut_el, host)
        table[i] = [-1 if e.get(k) is None else e[k] for k in INDICATEURS]
    print(f"{len(qs)} questions, {len(cles)} couples pays × mois ; présence par indicateur : "
          + ", ".join(f"{k} {int((table[:, n] == 1).sum())}" for n, k in enumerate(INDICATEURS)))
    qi = np.array([index[(x["cca2"], x["jeu"])] for x in qs])
    typ = np.array([TYPES.index(x["type"]) for x in qs])
    explo = np.array([x["jeu"] < cg.COUPURE for x in qs])
    pb = np.array([x["p_B"] for x in qs], dtype=float)
    y = np.array([x["issue"] for x in qs], dtype=float)
    combis = [c for k in (1, 2, 3) for c in itertools.combinations(range(len(INDICATEURS)), k)]

    def statistiques(res: list[dict]) -> tuple[int, float, int, float]:
        g = [r["gain"] for r in res if "gain" in r]
        return sum(v < 0 for v in g), float(sum(g)), len(g), (min(g) if g else 0.0)

    reel = evaluer(table[qi], typ, explo, pb, y, combis)
    n_reussites, total, n_juges, meilleur = statistiques(reel)
    # hasard : redistribution des lignes de la table entre pays d'un même mois
    mois = np.array([j for _, j in cles])
    groupes = [np.where(mois == m)[0] for m in sorted(set(mois))]
    rng = np.random.default_rng(0)
    nul_reussites, nul_total, nul_meilleur = [], [], []
    for _ in range(tirages):
        perm = np.arange(len(cles))
        for g in groupes:
            perm[g] = rng.permutation(g)
        r, t, _, m = statistiques(evaluer(table[perm][qi], typ, explo, pb, y, combis))
        nul_reussites.append(r)
        nul_total.append(t)
        nul_meilleur.append(m)
    nul_reussites, nul_total, nul_meilleur = map(np.array, (nul_reussites, nul_total, nul_meilleur))
    noms = lambda c: " × ".join(INDICATEURS[i] for i in c)
    juges = sorted((r for r in reel if "gain" in r), key=lambda r: r["gain"])
    for r in juges:
        r["p_corrige"] = round(float((1 + (nul_meilleur <= r["gain"]).sum()) / (tirages + 1)), 4)
        r["combi"] = noms(r["combi"])
        r["delta"], r["gain"] = round(r["delta"], 4), round(r["gain"], 4)
    res = {"note": "gain = perte log ajustée − perte log de B sur la confirmation (négatif = mieux) ; hasard : "
                   f"{tirages} redistributions des indicateurs entre pays du même mois",
           "questions": len(qs), "combinaisons_par_type": len(combis), "tests_juges": n_juges,
           "reussites": {"reel": n_reussites, "hasard_moyenne": round(float(nul_reussites.mean()), 2),
                         "hasard_95e_centile": float(np.percentile(nul_reussites, 95)),
                         "p": round(float((1 + (nul_reussites >= n_reussites).sum()) / (tirages + 1)), 4)},
           "gain_total": {"reel": round(total, 4), "hasard_moyenne": round(float(nul_total.mean()), 4),
                          "p": round(float((1 + (nul_total <= total).sum()) / (tirages + 1)), 4)},
           "meilleur_gain": {"reel": round(meilleur, 4), "hasard_moyenne": round(float(nul_meilleur.mean()), 4)},
           "presence": {k: int((table[:, n] == 1).sum()) for n, k in enumerate(INDICATEURS)},
           "juges": juges,
           "non_juges": len([r for r in reel if "gain" not in r])}
    RESUME.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    texte = ["## Balayage exhaustif des combinaisons, comparé au hasard\n",
             f"{len(qs)} questions ; {len(combis)} combinaisons × 3 types ; {n_juges} jugeables.\n",
             f"- Réussites (gain < 0) : **{n_reussites}** ; le hasard en donne {res['reussites']['hasard_moyenne']} en "
             f"moyenne (95e centile {res['reussites']['hasard_95e_centile']}) ; p = {res['reussites']['p']}.",
             f"- Gain total : **{res['gain_total']['reel']}** ; hasard {res['gain_total']['hasard_moyenne']} ; "
             f"p = {res['gain_total']['p']}.\n",
             "| Combinaison | Type | n expl. / conf. | δ | Gain | p corrigé |", "|---|---|---|---|---|---|"]
    for r in juges[:20]:
        texte.append(f"| {r['combi']} | {r['type']} | {r['n_exploration']} / {r['n_confirmation']} | {r['delta']} | "
                     f"{r['gain']} | {r['p_corrige']} |")
    print("\n".join(texte))
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fo:
            fo.write("\n".join(texte) + "\n")
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--tirages", type=int, default=200)
    o = a.parse_args()
    sys.exit(principal(o.tirages))
