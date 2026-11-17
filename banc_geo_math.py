"""Hypothèses géographiques et mathématiques contre la classe de référence pondérée (bot 0.10.238, en ombre).

Décision d'auteur du 2026-11-17 (19 h 47, « Oui, merci ») : tester M11 sous une forme juste et les pistes
mathématiques laissées en attente. Préenregistrement : preenregistrements/geo-math.md. Aucun modèle de langue ; gratuit ;
tout est calculé sur les comptes GDELT du dépôt (le test 3, Richardson, est dans banc_richardson.py).

TEST 1 — M11 EN GRAPPE (diffusion de proximité, Hägerstrand ; balayage spatial, Smida et al.). Questions du banc GDELT
« plus après qu'avant ? » (manifestations, émeutes), B = la classe pondérée adoptée (combinaisons_gdelt.questions).
État à d0 : pour chaque voisin terrestre (GeoNames) couvert, r = ln((14 j récents + 1) / (14 j précédents + 1)) sur le
même type d'événement ; voisin « en hausse » si r > 0,4. GRAPPE = au moins 2 voisins en hausse ET au moins la moitié
des voisins couverts. Sens attendu : plus de « oui » que B (δ > 0).

TEST 2 — SIGNES AVANT-COUREURS D'UN BASCULEMENT (Scheffer et al., Nature 2009). Questions d'ESCALADE fabriquées :
« au moins 2 × le niveau habituel dans les 30 jours après d0 ? » (niveau habituel = médiane des fenêtres disjointes
de 30 jours avant d0, au moins 5 ; posée si ce niveau ≥ 3) ; types manifestations, émeutes, force. B = classe pondérée
(z, m sur les fenêtres ; même source et même type, tous pays). État à d0 sur les 90 jours avant (au plus 6 jours
manquants) : variance et autocorrélation de rang 1 des comptes quotidiens sur [d0 − 45, d0) contre [d0 − 90, d0 − 45) ;
ALERTE = variance × 1,5 au moins ET autocorrélation + 0,1 au moins. Sens attendu : plus de « oui » que B.

Jugement commun : δ = ln((O + 0,5) / (E + 0,5)) sur la case « état présent » en exploration (d0 avant 2025-11-01),
appliqué en logit à B en confirmation ; jugé si au moins 10 questions aux deux étapes ; bootstrap par mois ; risque
es.risque_corrige(1) / k par test (k = cases jugées du test). Confirmé si la borne haute < 0.

    python banc_geo_math.py
"""
from __future__ import annotations

import json
import math
import os
import statistics
import sys
from datetime import date, timedelta
from pathlib import Path

import banc_classe_reference as bcr
import combinaisons as cb
import combinaisons_gdelt as cg

SORTIE = Path("registre") / "banc-geo-math.json"
VOISINS = Path("registre") / "voisins.json"
SEUIL_HAUSSE = 0.4
N_MIN = 10


def fenetre(serie: dict, debut: date, n: int, couverts: set[str], manque: int) -> int | None:
    jours = [(debut + timedelta(days=k)).isoformat() for k in range(n)]
    if sum(1 for j in jours if j not in couverts) > manque:
        return None
    return sum(serie.get(j, 0) for j in jours)


def grappe(cca2: str, typ: str, d0: date, comptes: dict, couverts: set[str], voisins: dict) -> int | None:
    rs = []
    for v in voisins.get(cca2, []):
        s = comptes.get((typ, v))
        if s is None:
            continue
        a = fenetre(s, d0 - timedelta(days=14), 14, couverts, 2)
        b = fenetre(s, d0 - timedelta(days=28), 14, couverts, 2)
        if a is None or b is None:
            continue
        rs.append(math.log((a + 1) / (b + 1)))
    if not rs:
        return None
    haut = sum(1 for r in rs if r > SEUIL_HAUSSE)
    return int(haut >= 2 and haut >= len(rs) / 2)


def ac1(xs: list[float]) -> float:
    m = sum(xs) / len(xs)
    den = sum((x - m) ** 2 for x in xs)
    return 0.0 if den == 0 else sum((xs[i] - m) * (xs[i + 1] - m) for i in range(len(xs) - 1)) / den


def alerte(serie: dict, d0: date, couverts: set[str]) -> int | None:
    jours = [(d0 - timedelta(days=k)).isoformat() for k in range(90, 0, -1)]
    if sum(1 for j in jours if j not in couverts) > 6:
        return None
    v = [float(serie.get(j, 0)) for j in jours if j in couverts]
    h = len(v) // 2
    a, b = v[:h], v[h:]
    if len(a) < 20 or len(b) < 20:
        return None
    va, vb = statistics.pvariance(a), statistics.pvariance(b)
    return int(vb >= 1.5 * va and vb > 0 and ac1(b) >= ac1(a) + 0.1)


def questions_escalade(comptes: dict, jm: set[str], jp: set[str], dernier: date) -> list[dict]:
    ancres = cg.mois(cg.DEBUT, dernier - timedelta(days=30))
    debut_donnees = date(2024, 7, 1)
    out = []
    for (typ, pays), serie in sorted(comptes.items()):
        couverts = jp if typ == "force" else jm
        for d0 in ancres:
            fen, b = [], d0
            while b - timedelta(days=30) >= debut_donnees:
                f = fenetre(serie, b - timedelta(days=30), 30, couverts, 3)
                if f is not None:
                    fen.append(f)
                b -= timedelta(days=30)
            if len(fen) < 5:
                continue
            niveau = statistics.median(fen)
            apres = fenetre(serie, d0, 30, couverts, 3)
            if niveau < 3 or apres is None:
                continue
            out.append({"jeu": d0.isoformat(), "type": typ, "pays": pays, "fin": (d0 + timedelta(days=30)).isoformat(),
                        "issue": int(apres >= 2 * niveau),
                        "z": math.log((fen[0] + 1) / (sum(fen[1:]) / len(fen[1:]) + 1)),
                        "m": math.log((fen[0] + 1) / (fen[1] + 1)),
                        "alerte": alerte(serie, d0, couverts)})
    bcr.noyau(out)
    for x in out:
        if "p_K" in x:
            x["p_B"] = x["p_K"]
    return [x for x in out if "p_B" in x]


def juger(xs: list[dict], cle: str, cellules: list[str]) -> dict:
    import essais as es
    res, jug = [], []
    for c in cellules:
        ex = [x for x in xs if x["cellule"] == c and x.get(cle) == 1 and x["jeu"] < cg.COUPURE]
        co = [x for x in xs if x["cellule"] == c and x.get(cle) == 1 and x["jeu"] >= cg.COUPURE]
        tous = [x for x in xs if x["cellule"] == c and x.get(cle) is not None]
        ligne = {"cellule": c, "n_exploration": len(ex), "n_confirmation": len(co),
                 "presence": round(sum(x[cle] for x in tous) / len(tous), 3) if tous else None}
        if len(ex) >= N_MIN:
            ligne["delta"] = round(cb.ratio(ex), 4)
            if len(co) >= N_MIN:
                jug.append((ligne, co))
        res.append(ligne)
    k = max(1, len(jug))
    risque = es.risque_corrige(1) / k
    for ligne, co in jug:
        d = ligne["delta"]
        ec = [(x["jeu"][:7], cb.pl(cb.sig(cb.logit(x["p_B"]) + d), x["issue"]) - cb.pl(x["p_B"], x["issue"])) for x in co]
        bas, haut = cb.bootstrap(ec, risque)
        ligne.update(perte_B=round(sum(cb.pl(x["p_B"], x["issue"]) for x in co) / len(co), 4),
                     perte_ajustee=round(sum(cb.pl(cb.sig(cb.logit(x["p_B"]) + d), x["issue"]) for x in co) / len(co), 4),
                     ecart_moyen=round(sum(e for _, e in ec) / len(ec), 4), intervalle_corrige=[round(bas, 4), round(haut, 4)],
                     verdict="confirmé" if haut < 0 else "non confirmé")
    return {"k_juges": len(jug), "risque_corrige": round(risque, 6), "cellules": res}


def principal() -> int:
    comptes, jm, jp = cg.charger()
    dernier = date.fromisoformat(max(jm))
    voisins = json.loads(VOISINS.read_text(encoding="utf-8"))
    qs = [x for x in cg.questions(comptes, jm, jp, dernier) if x["type"] in ("manifestations", "emeutes")]
    for x in qs:
        x["grappe"] = grappe(x["pays"], x["type"], date.fromisoformat(x["jeu"]), comptes, jm, voisins)
        x["cellule"] = x["type"]
    t1 = juger(qs, "grappe", ["manifestations", "emeutes"])
    esc = questions_escalade(comptes, jm, jp, dernier)
    for x in esc:
        x["cellule"] = x["type"]
    t2 = juger(esc, "alerte", ["manifestations", "emeutes", "force"])
    t2["questions"] = len(esc)
    t2["oui"] = round(sum(x["issue"] for x in esc) / len(esc), 3) if esc else None
    res = {"note": "perte log, plus bas = mieux ; B = classe de référence pondérée ; aucun modèle de langue",
           "m11_grappe": dict(t1, questions=len(qs)), "alerte_precoce": t2}
    SORTIE.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fo:
            fo.write("## Hypothèses géographiques et mathématiques\n\n```\n" + json.dumps(res, ensure_ascii=False, indent=1) + "\n```\n")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
