"""Évaluation de « accords selon l'état de la guerre » (preenregistrements/accords-guerre.md). Une seule passe.

Questions : celles de la famille accords (mêmes filtres que mise_au_point/accords.py) des sous-familles cessez_le_feu,
accord_paix, tenue, pour lesquelles accords_guerre.probabilite ne s'abstient pas.
Référence : part de oui de TOUTE la famille accords (58 questions de l'essai précédent) hors groupe.
Branchement par sous-famille : (1) règle < référence ; (2) mélange plafonné < référence ; (3) règle < référence sur 2026.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import accords_guerre as ag  # noqa: E402
import accords_regle as ar  # noqa: E402
import structures_questions as sq  # noqa: E402
from mise_au_point.procedure_inertie import groupe  # noqa: E402


def ll(p, y):
    p = min(max(p, .02), .98)
    return -math.log(p if y else 1 - p)


def principal() -> int:
    EP, E = ag.episodes(), ag.evenements()
    vus, F = set(), []
    for l in Path("registre/jugement-questions.jsonl").read_text(encoding="utf-8").splitlines():
        q = json.loads(l)
        t = q["titre"]
        if t in vus or str(q.get("issue")) not in ("0", "1"):
            continue
        vus.add(t)
        if not sq.structure(t).startswith("procédure"):
            continue
        c = ar.classe(t)
        if c is None:
            continue
        F.append({"titre": t, "jeu": q["jeu"], "y": int(q["issue"]), "classe": c, "groupe": groupe(t)})
    X = []
    for x in F:
        if x["classe"] not in ("cessez_le_feu", "accord_paix", "tenue"):
            continue
        jeu = dt.date.fromisoformat(x["jeu"])
        p = ag.probabilite(x["classe"], x["titre"], jeu, EP, E)
        if p is None:
            continue
        S = [z for z in F if z["groupe"] != x["groupe"]]
        ref = sum(z["y"] for z in S) / len(S)
        s = ag.etat(ag.guerre(x["titre"]), jeu, E)
        X.append(x | {"p": round(p, 4), "ref": round(ref, 4), "mel": round(ar.melanger(ref, p), 4),
                      "guerre": ag.guerre(x["titre"]), "etat": s[0], "age": s[1], "type": s[2]})
    m = lambda L, k: round(sum(ll(x[k], x["y"]) for x in L) / len(L), 4) if L else None
    res = {"n": len(X), "famille": len(F), "classes": {}}
    for c in ("cessez_le_feu", "accord_paix", "tenue"):
        C = [x for x in X if x["classe"] == c]
        if not C:
            continue
        K = [x for x in C if x["jeu"] >= "2026-01-01"]
        r = {"n": len(C), "oui": sum(x["y"] for x in C), "perte_reference": m(C, "ref"), "perte_regle": m(C, "p"),
             "perte_melange": m(C, "mel"), "n_2026": len(K), "perte_reference_2026": m(K, "ref"),
             "perte_regle_2026": m(K, "p")}
        r["brancher"] = (r["perte_regle"] < r["perte_reference"] and r["perte_melange"] < r["perte_reference"]
                         and (not K or r["perte_regle_2026"] < r["perte_reference_2026"]))
        res["classes"][c] = r
    j = dt.date(2026, 11, 24)
    res["taux_par_an"] = {
        "cessez_inter": [round(v * 365.25, 3) for v in ag.taux_fin(EP, j, "inter", ("1", "2"))[0]],
        "cessez_interne": [round(v * 365.25, 3) for v in ag.taux_fin(EP, j, "interne", ("1", "2"))[0]],
        "paix_inter": [round(v * 365.25, 3) for v in ag.taux_fin(EP, j, "inter", ("1",))[0]],
        "paix_interne": [round(v * 365.25, 3) for v in ag.taux_fin(EP, j, "interne", ("1",))[0]],
        "reprise": [round(v * 365.25, 3) for v in ag.taux_reprise(EP, j)[0]],
        "evenements_expositions": {"cessez_inter": ag.taux_fin(EP, j, "inter", ("1", "2"))[1:],
                                   "reprise": ag.taux_reprise(EP, j)[1:]}}
    branchees = [c for c, r in res["classes"].items() if r["brancher"]]
    Path("registre/accords-guerre.json").write_text(json.dumps({"resume": res, "lignes": X}, ensure_ascii=False, indent=1),
                                                    encoding="utf-8")
    Path("ecosystemes/accords-guerre-branchees.json").write_text(json.dumps({"branchees": branchees}), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
