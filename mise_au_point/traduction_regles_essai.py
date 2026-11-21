"""Examen de la traduction algorithmique des règles (traduction_regles.py) sur les questions de jugement de 2026
couvertes par la carte robot. Aucun appel de modèle. Préenregistrement : preenregistrements/traduction-regles.md.

Pour chaque question (une par question, son premier jeu) dont au moins une règle retenue par la carte robot se
traduit en probabilité : p_S (taux des semblables), p_R (la règle seule), p_C = combiner(p_S, p_R). Perte log de
chacun, écarts C − S et R − S, intervalles à 90 % par bootstrap par question.

    python mise_au_point/traduction_regles_essai.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import banc_jugement as bj
import score_registre as sr
import traduction_regles as tr
import verification_a_priori as va

CARTE = Path("registre") / "carte-robot-jugement2026.json"
SORTIE = Path("registre") / "mise-au-point" / "traduction-regles.json"
# Retraits fixés avant tout regard sur les issues (préenregistrement, ajout de 16 h 15) : lecture de page défaillante.
RETIREES = {"manifold:Q9gNdcP2lc": "Hongrie : en-têtes de la page illisibles (logos), Orbán lu à 2,3 % dans un tableau marginal"}


def lignes() -> list[dict]:
    carte = {o["question"]: o for o in json.loads(CARTE.read_text(encoding="utf-8"))["detail"] if o["regles"]}
    xs = bj.cohorte_complete([json.loads(l) for l in bj.REGISTRE.read_text(encoding="utf-8").splitlines() if l.strip()])
    bj.calculer(xs)
    vus, out = set(), []
    for x in sorted(xs, key=lambda x: x["jeu"]):
        k = f'{x["source"]}:{x["id"]}'
        if k in RETIREES or k not in carte or k in vus or x["jeu"] != carte[k]["jeu"]:
            continue
        vus.add(k)
        ps = {r: p for r in carte[k]["regles"] if (p := tr.p_regle(r, x["titre"], x["horizon"], x["jeu"], x["cloture"], k)) is not None}
        if ps:
            lr = sum(tr._logit(p) for p in ps.values()) / len(ps)          # la règle seule : moyenne des logits
            p_r = 1 / (1 + 2.718281828459045 ** (-lr))
            out.append({"question": k, "titre": x["titre"], "issue": x["issue"], "p_S": x["p_S"], "p_R": p_r,
                        "p_C": tr.combiner(x["p_S"], list(ps.values())), "regles": ps})
    return out


def principal() -> int:
    ls = lignes()
    pl = sr.log_score
    perte = {k: np.array([pl(x[k], x["issue"]) for x in ls]) for k in ("p_S", "p_R", "p_C")}
    rng = np.random.default_rng(sum(map(ord, "traduction-regles")))

    def ic(d):
        b = np.array([d[rng.integers(0, len(d), len(d))].mean() for _ in range(5000)])
        return [round(float(v), 4) for v in np.percentile(b, [5, 95])]
    dc, dr = perte["p_C"] - perte["p_S"], perte["p_R"] - perte["p_S"]
    r = {"n": len(ls), "S": round(float(perte["p_S"].mean()), 4), "R": round(float(perte["p_R"].mean()), 4),
         "C": round(float(perte["p_C"].mean()), 4), "C_moins_S": round(float(dc.mean()), 4), "intervalle_90_C_S": ic(dc),
         "R_moins_S": round(float(dr.mean()), 4), "intervalle_90_R_S": ic(dr), "puissance": va.puissance(dc.tolist()),
         "adopte": bool(ic(dc)[1] < 0), "retirees": RETIREES, "detail": ls,
         "note": "perte log, plus bas = mieux ; adopté si l'intervalle à 90 % de C − S est entièrement sous 0"}
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in r.items() if k != "detail"}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
