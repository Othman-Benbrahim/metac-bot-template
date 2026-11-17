"""Front de diffusion (Hägerstrand à la bonne échelle) contre la classe de référence pondérée, UCDP (bot 0.10.239).

Décision d'auteur du 2026-11-17 (20 h 00). Préenregistrement : preenregistrements/front-diffusion.md. Aucun modèle de
langue ; gratuit. Données : registre/ucdp-cellules.csv.gz (collecte_ucdp_grille.py).

Questions par pays (25 pays en conflit), premier de chaque mois d0 de 2016-01-01 au dernier mois complet : « plus
d'événements UCDP dans les 30 jours après d0 que dans les 30 jours avant ? », posée si au moins 1 événement avant.
B = classe de référence pondérée (z, m ; largeurs 1 ; 1 ; tous les pays, questions finies avant d0), la méthode adoptée.
FRONT à d0 : carreaux actifs dans les 30 jours avant d0 qui ne l'étaient pas dans les 150 jours précédents
([d0 − 180, d0 − 30)) ET qui touchent (8 voisins) un carreau actif de cette période : les carreaux « gagnés de proche en
proche ». FRONT = 1 si leur nombre ≥ max(2, ¼ des carreaux actifs des 30 derniers jours).
Jugement : δ = ln((O + 0,5) / (E + 0,5)) sur FRONT = 1 en exploration (d0 avant 2024-01-01), appliqué en logit à B en
confirmation (d0 à partir de 2024-01-01) ; bootstrap par mois ; risque es.risque_corrige(1) ; confirmé si la borne haute
< 0. Sens attendu : δ > 0 (un front qui avance annonce plus d'événements).

    python banc_front.py
"""
from __future__ import annotations

import csv
import gzip
import json
import math
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import banc_classe_reference as bcr
import combinaisons as cb
import combinaisons_gdelt as cg

ENTREE = Path("registre") / "ucdp-cellules.csv.gz"
SORTIE = Path("registre") / "banc-front.json"
DEBUT_DONNEES = date(2015, 1, 1)
DEBUT_Q = date(2016, 1, 1)
COUPURE = "2024-01-01"
N_MIN = 10


def voisins_cellule(g: int) -> set[int]:
    r, c = divmod(g - 1, 720)
    out = set()
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr or dc:
                rr, cc = r + dr, (c + dc) % 720
                if 0 <= rr < 360:
                    out.add(rr * 720 + cc + 1)
    return out


def charger(chemin: Path = ENTREE) -> tuple[dict, dict]:
    """({pays: {jour: événements}}, {pays: {jour: set(carreaux)}})."""
    ev, cel = {}, {}
    with gzip.open(chemin, "rt", encoding="utf-8") as f:
        for x in csv.DictReader(f):
            ev.setdefault(x["pays"], {})
            ev[x["pays"]][x["jour"]] = ev[x["pays"]].get(x["jour"], 0) + int(x["evenements"])
            cel.setdefault(x["pays"], {}).setdefault(x["jour"], set()).add(int(x["cellule"]))
    return ev, cel


def somme(c: dict, a: date, b: date) -> int:
    d, s = a, 0
    while d < b:
        s += c.get(d.isoformat(), 0)
        d += timedelta(days=1)
    return s


def actifs(cel: dict, a: date, b: date) -> set[int]:
    d, s = a, set()
    while d < b:
        s |= cel.get(d.isoformat(), set())
        d += timedelta(days=1)
    return s


def front(cel: dict, d0: date) -> int:
    recents = actifs(cel, d0 - timedelta(days=30), d0)
    anciens = actifs(cel, d0 - timedelta(days=180), d0 - timedelta(days=30))
    gagnes = [g for g in recents - anciens if voisins_cellule(g) & anciens]
    return int(len(gagnes) >= max(2, len(recents) / 4))


def questions(ev: dict, cel: dict, dernier: date) -> list[dict]:
    ancres = cg.mois(DEBUT_DONNEES + timedelta(days=60), dernier - timedelta(days=30))
    out = []
    for pays in sorted(ev):
        c, avants, histo = ev[pays], [], []
        for d0 in ancres:
            avant = somme(c, d0 - timedelta(days=30), d0)
            apres = somme(c, d0, d0 + timedelta(days=30))
            prec = somme(c, d0 - timedelta(days=60), d0 - timedelta(days=30))
            issue = int(apres > avant)
            if avant >= 1 and d0 >= DEBUT_Q:
                anciens = [a for t, a in avants if t <= d0]
                connus = [y for fin, y in histo if fin <= d0]
                x = {"jeu": d0.isoformat(), "type": "ucdp", "pays": pays, "issue": issue,
                     "p_B_compte": (sum(connus) + 1) / (len(connus) + 2), "fin": (d0 + timedelta(days=30)).isoformat(),
                     "front": front(cel[pays], d0)}
                if len(anciens) >= 3:
                    x["z"] = math.log((avant + 1) / (sum(anciens) / len(anciens) + 1))
                    x["m"] = math.log((avant + 1) / (prec + 1))
                out.append(x)
                histo.append((d0 + timedelta(days=30), issue))
            avants.append((d0, avant))
    bcr.noyau(out)
    for x in out:
        if "p_K" in x:
            x["p_B"] = x["p_K"]
    return [x for x in out if "p_B" in x]


def juger(xs: list[dict]) -> dict:
    import essais as es
    ex = [x for x in xs if x["front"] == 1 and x["jeu"] < COUPURE]
    co = [x for x in xs if x["front"] == 1 and x["jeu"] >= COUPURE]
    conf = [x for x in xs if x["jeu"] >= COUPURE]
    r = {"questions": len(xs), "presence_front": round(sum(x["front"] for x in xs) / len(xs), 3) if xs else None,
         "n_exploration": len(ex), "n_confirmation": len(co),
         "reference_confirmation": {"n": len(conf), "perte_B_compte": round(sum(cb.pl(x["p_B_compte"], x["issue"]) for x in conf) / len(conf), 4) if conf else None,
                                    "perte_classe_ponderee": round(sum(cb.pl(x["p_B"], x["issue"]) for x in conf) / len(conf), 4) if conf else None}}
    if len(ex) >= N_MIN:
        r["delta"] = round(cb.ratio(ex), 4)
        r["oui_front_exploration"] = [sum(x["issue"] for x in ex), round(sum(x["p_B"] for x in ex), 1)]
    if "delta" in r and len(co) >= N_MIN:
        d = r["delta"]
        ec = [(x["jeu"][:7], cb.pl(cb.sig(cb.logit(x["p_B"]) + d), x["issue"]) - cb.pl(x["p_B"], x["issue"])) for x in co]
        bas, haut = cb.bootstrap(ec, es.risque_corrige(1))
        r.update(oui_front_confirmation=[sum(x["issue"] for x in co), round(sum(x["p_B"] for x in co), 1)],
                 perte_B=round(sum(cb.pl(x["p_B"], x["issue"]) for x in co) / len(co), 4),
                 perte_ajustee=round(sum(cb.pl(cb.sig(cb.logit(x["p_B"]) + d), x["issue"]) for x in co) / len(co), 4),
                 ecart_moyen=round(sum(e for _, e in ec) / len(ec), 4), intervalle_corrige=[round(bas, 4), round(haut, 4)],
                 verdict="confirmé" if haut < 0 else "non confirmé")
    return r


def principal() -> int:
    if not ENTREE.exists():
        print("registre/ucdp-cellules.csv.gz absent : lancer d'abord la collecte.")
        return 1
    ev, cel = charger()
    dernier = max(date.fromisoformat(j) for c in ev.values() for j in c)
    r = juger(questions(ev, cel, dernier))
    r["note"] = "perte log, plus bas = mieux ; B = classe de référence pondérée ; données UCDP GED (CC BY 4.0)"
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    texte = json.dumps(r, ensure_ascii=False, indent=1)
    print(texte)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fo:
            fo.write("## Front de diffusion (UCDP, PRIO-GRID)\n\n```\n" + texte + "\n```\n")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
