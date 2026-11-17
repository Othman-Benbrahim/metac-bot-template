"""Classe de référence pondérée, questions à la FORME DU BOT (« au moins N événements ? »), bot 0.10.237, en ombre.

Décision d'auteur du 2026-11-17 (19 h 42, « D'accord, on y va »). La classe pondérée bat le compte sur UCDP (questions
« plus qu'avant ? ») ; domaine retenu par l'auteur : conflits (UCDP), sanctions (OFAC), coupures d'Internet (IODA).
Avant l'entrée dans le bot : la tester sur la forme des questions que le bot rencontre sur Metaculus et sur le taux de
base qu'il calcule vraiment (alphabet_compte.compter : fenêtres DISJOINTES de la durée de la question, comptées à rebours
depuis la date, fréquence k / n ramenée à 1/(2n) ou 1 − 1/(2n) aux bords, au moins 5 fenêtres).
Préenregistrement : preenregistrements/classe-reference.md, partie « forme du bot ». Aucun modèle de langue ; gratuit.

Questions fabriquées, pour chaque groupe (pays, programme) et chaque premier du mois d0 depuis 2024-09-01 :
  « au moins N événements dans les h jours à partir de d0 ? », N = max(1, ⌈médiane des fenêtres passées⌉) (le niveau
  habituel du groupe à d0 : la forme typique d'une question Metaculus sur un compte).
  B (le bot) : part des fenêtres disjointes passées du même groupe qui atteignent N (règle de compter).
  B_noyau : questions passées de la même source (tous groupes, fenêtre finie avant d0), pondérées par la ressemblance
  à d0 : z = ln((dernière fenêtre + 1) / (moyenne des fenêtres antérieures + 1)), m = ln((dernière + 1) /
  (avant-dernière + 1)) ; largeurs 1 ; 1 (banc_classe_reference.noyau).
Sources : UCDP depuis 2023-01-01 (25 pays), IODA depuis 2022-06-01 (20 pays), OFAC (8 programmes) ; un relevé au
plafond de l'API est retiré (série tronquée).
Critère : par source, h = 30 jours, au moins 30 questions de confirmation (d0 ≥ 2025-11-01) ; écart de perte log
B_noyau − B, bootstrap par mois, risque es.risque_corrige(1) / k. h = 7 et 90 jours : rapportés, non jugés.

    python banc_cr_metaculus.py
"""
from __future__ import annotations

import asyncio
import json
import math
import os
import statistics
import sys
from datetime import date, timedelta
from pathlib import Path

import banc_classe_reference as bcr
import banc_cr_sources as bs
import combinaisons_gdelt as cg

SORTIE = Path("registre") / "banc-cr-metaculus.json"
SOURCES = {"ucdp": "2023-01-01", "coupures_internet": "2022-06-01", "sanctions_us": "2021-01-01"}


def groupes() -> list[tuple[str, str, dict, str]]:
    out = []
    for src, grp, params, _ in bs.groupes():
        if src in SOURCES:
            p = dict(params)
            if "debut" in p:
                p["debut"] = SOURCES[src]
            out.append((src, grp, p, SOURCES[src]))
    return out


def frequence_bot(fenetres: list[int], n_seuil: int) -> float:
    k, n = sum(1 for f in fenetres if f >= n_seuil), len(fenetres)
    return 1 / (2 * n) if k == 0 else 1 - 1 / (2 * n) if k == n else k / n


def cas_seuil(comptes: dict, debuts: dict[str, str], dernier: date, h: int) -> list[dict]:
    ancres = cg.mois(cg.DEBUT, dernier - timedelta(days=h))
    out = []
    for (src, grp), c in sorted(comptes.items()):
        debut = date.fromisoformat(debuts[src])

        def somme(a: date, b: date) -> int:
            d, s = a, 0
            while d < b:
                s += c.get(d.isoformat(), 0)
                d += timedelta(days=1)
            return s
        for d0 in ancres:
            fen, b = [], d0
            while b - timedelta(days=h) >= debut:
                fen.append(somme(b - timedelta(days=h), b))
                b -= timedelta(days=h)
            if len(fen) < 5:
                continue
            n_seuil = max(1, math.ceil(statistics.median(fen)))
            x = {"jeu": d0.isoformat(), "type": src, "pays": grp, "seuil": n_seuil,
                 "issue": int(somme(d0, d0 + timedelta(days=h)) >= n_seuil),
                 "p_B": frequence_bot(fen, n_seuil), "fin": (d0 + timedelta(days=h)).isoformat(),
                 "z": math.log((fen[0] + 1) / (sum(fen[1:]) / len(fen[1:]) + 1)),
                 "m": math.log((fen[0] + 1) / (fen[1] + 1))}
            out.append(x)
    return out


async def collecter(avant: date) -> tuple[dict, list[str]]:
    import alphabet_puits as apz
    comptes, journal = {}, []
    for src, grp, params, debut in groupes():
        try:
            r = await apz.appeler(src, params, avant)
        except Exception as e:
            journal.append(f"{src}/{grp} : {type(e).__name__}: {apz.masquer(str(e))[:120]}")
            continue
        n_brut = len(r.get("points") or [])
        if n_brut >= bs.PLAFONDS.get(src, 10 ** 9):
            journal.append(f"{src}/{grp} : {n_brut} événements, plafond de l'API atteint : groupe retiré (tronqué)")
            continue
        comptes[(src, grp)] = bs.comptes_jour(r.get("points") or [], debut)
        journal.append(f"{src}/{grp} : {sum(comptes[(src, grp)].values())} événements")
        await asyncio.sleep(0.5)
    return comptes, journal


def principal() -> int:
    avant = date.today()
    comptes, journal = asyncio.run(collecter(avant))
    print("\n".join(journal))
    dernier = avant - timedelta(days=1)
    res = {"note": "perte log, plus bas = mieux ; B = taux du bot (fenêtres disjointes) ; aucun modèle de langue",
           "releve": avant.isoformat(), "journal": journal, "par_echelle": {}}
    for h in (30, 7, 90):
        xs = cas_seuil(comptes, SOURCES, dernier, h)
        bcr.noyau(xs)
        par = {s: [x for x in xs if x["type"] == s] for s in sorted({x["type"] for x in xs})}
        k = (sum(1 for v in par.values() if sum(1 for x in v if "p_K" in x and x["jeu"] >= bs.COUPURE) >= bs.N_MIN)
             if h == 30 else 0)
        res["par_echelle"][f"{h} jours"] = {"k_juges": k, "sources": {s: bs.juger(v, k) for s, v in par.items()}}
    SORTIE.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    lignes = [f"| {e} | {s} | {r['n_confirmation']} | {r.get('oui', '—')} | {r.get('perte_B', '—')} | "
              f"{r.get('perte_noyau', '—')} | {r.get('intervalle_corrige', '—')} | {r.get('verdict', 'non jugé')} |"
              for e, d in res["par_echelle"].items() for s, r in d["sources"].items()]
    texte = ("| Échelle | Source | Questions (conf.) | Part de oui | B du bot | B_noyau | Intervalle corrigé | Verdict |\n"
             "|---|---|---|---|---|---|---|---|\n" + "\n".join(lignes))
    print(texte)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fo:
            fo.write("## Classe de référence pondérée, forme des questions du bot\n\n" + texte + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
