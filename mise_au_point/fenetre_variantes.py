"""Mise au point (pas un verdict) : variantes d'usage de la brique « fenêtre » (bot 0.10.385, ombre).

Décision de l'auteur, 2026-11-20, 12 h 02 : tester des variantes de l'hypothèse de la brique, notamment comme
ADJUVANT (correction des semblables) et non comme base de calcul, comme pour l'alphabet. Règle du 2026-11-20 :
ici on essaie librement, sur l'échantillon de mise au point (forecasting_raw 2015-2024 + registre de jugement avant
le 2026-11-20) ; la variante retenue passera UNE fois en confirmation sur les questions ForecastBench postérieures.

Tout est chronologique : chaque probabilité n'utilise que des questions résolues et closes avant la date jugée ;
les coefficients des adjuvants sont réappris chaque mois sur le passé seulement.

    python mise_au_point/fenetre_variantes.py     # écrit registre/mise-au-point/fenetre-variantes.json
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

import banc_jugement as bj
import banc_proxemie as bp
import banc_redacteur as br
import brique_fenetre as bf
import essais as es
import structures_questions as sq

REG = Path("registre")
SORTIE = REG / "mise-au-point" / "fenetre-variantes.json"
MIN_APPRENTISSAGE = 300


def charger() -> list[dict]:
    fr = [json.loads(l) for l in (REG / "mise-au-point" / "questions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    for x in fr:
        x["source"] = "fr_" + x["source"]                 # ne pas confondre avec les sources du registre
    rg = [json.loads(l) for l in bj.REGISTRE.read_text(encoding="utf-8").splitlines() if l.strip()]
    rg = [x for x in rg if x["jeu"] < es.CONFIRMATION_DEPUIS]
    xs = [x for x in fr + rg if not bp.COMBINEE.search(x.get("titre") or "")]
    xs = bj.cohorte_complete(xs)
    for x in xs:
        x["structure"] = sq.structure(x["titre"])
        x["acteur"], x["fenetre"] = bf.acteur(x["titre"]), bf.fenetre(x["horizon"])
    return sorted(xs, key=lambda x: (x["jeu"], x["source"], str(x["id"])))


def lg(p: float) -> float:
    p = min(0.98, max(0.02, p))
    return math.log(p / (1 - p))


def adjuvants(xs: list[dict]) -> None:
    """Variantes C, D, E : régressions logistiques réapprises chaque mois sur le passé."""
    occ = [x for x in xs if x["structure"] in bf.OCCURRENCE]
    acteurs = sorted({x["acteur"] for x in occ})
    def traits(x, v):
        dev = lg(x["p_F"]) - lg(x["p_R1"])
        if v == "C":
            return [1.0, lg(x["p_S"]), dev]
        if v == "D":
            return [1.0, lg(x["p_S"]), dev if x["acteur"] == "chef" else 0.0]
        return [1.0, lg(x["p_S"])] + [dev if x["acteur"] == a else 0.0 for a in acteurs]
    fin = np.array([max(x["resolue_le"], x.get("cloture", "")) for x in occ])
    y = np.array([x["issue"] for x in occ], dtype=float)
    mois = sorted({x["jeu"][:7] for x in occ})
    for v in ("C", "D", "E"):
        X = np.array([traits(x, v) for x in occ])
        for m in mois:
            ok = fin < m + "-01"
            cibles = [i for i, x in enumerate(occ) if x["jeu"][:7] == m]
            if ok.sum() < MIN_APPRENTISSAGE:
                for i in cibles:
                    occ[i]["p_" + v] = occ[i]["p_S"]
                continue
            w = br.ajuster(X[ok], y[ok])
            for i in cibles:
                occ[i]["p_" + v] = float(min(0.98, max(0.02, 1 / (1 + math.exp(-X[i] @ w)))))
    # variante G : logit p = logit p_S + c·écart, seul c est appris (les semblables ne sont pas recalibrés)
    dev = np.array([lg(x["p_F"]) - lg(x["p_R1"]) for x in occ])
    off = np.array([lg(x["p_S"]) for x in occ])
    for m in mois:
        ok = fin < m + "-01"
        cibles = [i for i, x in enumerate(occ) if x["jeu"][:7] == m]
        c = 0.0
        if ok.sum() >= MIN_APPRENTISSAGE:
            for _ in range(25):                                   # Newton à une dimension, pénalité L2 légère
                p_ = 1 / (1 + np.exp(-(off[ok] + c * dev[ok])))
                g = float(((p_ - y[ok]) * dev[ok]).sum() + 1.0 * c)
                h = float((p_ * (1 - p_) * dev[ok] ** 2).sum() + 1.0)
                c -= g / h
        for i in cibles:
            occ[i]["p_G"] = float(min(0.98, max(0.02, 1 / (1 + math.exp(-(off[i] + c * dev[i]))))))
            occ[i]["c_G"] = c
    for x in occ:
        x["p_H"] = 1 / (1 + math.exp(-(0.9 * lg(x["p_S"]) + 0.1 * lg(x["p_F"]))))   # variante H : poids fixe 90/10
        x["p_I"] = 1 / (1 + math.exp(-(0.8 * lg(x["p_S"]) + 0.2 * lg(x["p_R1"]))))  # témoin : même mélange, taux de base
        x["p_F2"] = 1 / (1 + math.exp(-(0.8 * lg(x["p_S"]) + 0.2 * lg(x["p_F"]))))   # variante F : poids fixe


def principal() -> int:
    xs = charger()
    bj.calculer(xs)
    bf.calculer(xs)
    adjuvants(xs)
    occ = [x for x in xs if x["structure"] in bf.OCCURRENCE and "p_C" in x]
    groupes = {"tout": occ,
               "metaculus_gjopen_cset (2015-2024)": [x for x in occ if x["source"] in ("fr_metaculus", "fr_gjopen", "fr_cset")],
               "manifold (2015-2024)": [x for x in occ if x["source"] == "fr_manifold"],
               "registre ForecastBench (2024-2026)": [x for x in occ if not x["source"].startswith("fr_")]}
    noms = {"p_S": "A semblables (base)", "p_F": "B brique comme base", "p_C": "C adjuvant (écart brique − taux de base)",
            "p_D": "D adjuvant « chef » seulement", "p_E": "E adjuvant par acteur", "p_F2": "F mélange fixe 80/20",
            "p_G": "G écart appris, semblables non recalibrés", "p_H": "H mélange fixe 90/10",
            "p_I": "I témoin : mélange 80/20 avec le taux de base au lieu de la brique"}
    pl = bj.cb.pl
    r = {"questions_occurrence": len(occ), "groupes": {}}
    for g, s in groupes.items():
        if not s:
            continue
        r["groupes"][g] = {"n": len(s), "pertes": {noms[k]: round(sum(pl(x[k], x["issue"]) for x in s) / len(s), 4) for k in noms}}
        for k in ("p_C", "p_D", "p_E", "p_F2", "p_G", "p_H", "p_I"):
            ec = [(f'{x["source"]}:{x["id"]}', pl(x[k], x["issue"]) - pl(x["p_S"], x["issue"])) for x in s]
            bas, haut = bj.cb.bootstrap(ec, 0.05)
            r["groupes"][g].setdefault("ecart_contre_A_intervalle_90", {})[noms[k]] = [round(bas, 4), round(haut, 4)]
    cs = [x["c_G"] for x in occ if "c_G" in x]
    r["coefficient_G_dernier"] = round(cs[-1], 3) if cs else None
    r["note"] = "mise au point, pas un verdict ; perte log, plus bas = mieux ; intervalles bilatéraux à 90 %, sans correction"
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
