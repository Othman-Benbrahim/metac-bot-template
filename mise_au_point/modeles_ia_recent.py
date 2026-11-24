"""Évaluation de « modèles d IA : cadence récente (365 jours) » (preenregistrements/modeles-ia-recent.md). Une seule passe.
Questions : sous-famille modele_ia (produits_regle.classe), cible lisible (modeles_ia_regle.cible), polarité inversée
exclue. Référence : part de oui de tout le corpus résolu hors groupe. Mélange d'un quart plafonné à 15 points.
Branchement : (1) règle < référence ; (2) mélange < référence ; (3) règle < référence sur 2026.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import accords_regle as ar  # noqa: E402
import modeles_ia_regle as mi  # noqa: E402
import produits_regle as pr  # noqa: E402
from mise_au_point.procedure_inertie import groupe  # noqa: E402


def ll(p, y):
    p = min(max(p, .02), .98)
    return -math.log(p if y else 1 - p)


def principal() -> int:
    vus, TOUT = set(), []
    for l in Path("registre/jugement-questions.jsonl").read_text(encoding="utf-8").splitlines():
        q = json.loads(l)
        t = q["titre"]
        if t in vus or str(q.get("issue")) not in ("0", "1"):
            continue
        vus.add(t)
        TOUT.append({"titre": t, "jeu": q["jeu"], "y": int(q["issue"]), "groupe": groupe(t)})
    X = []
    for x in TOUT:
        t = x["titre"]
        if pr.classe(t) != "modele_ia" or re.search(r"\b(not|no|doesn't)\b", t, re.I):
            continue
        p = mi.probabilite(t, dt.date.fromisoformat(x["jeu"]), fenetre=365)
        if p is None:
            continue
        S = [z for z in TOUT if z["groupe"] != x["groupe"]]
        ref = sum(z["y"] for z in S) / len(S)
        X.append(x | {"p": round(p, 4), "ref": round(ref, 4), "mel": round(ar.melanger(ref, p), 4)})
    m = lambda L, k: round(sum(ll(x[k], x["y"]) for x in L) / len(L), 4) if L else None
    K = [x for x in X if x["jeu"] >= "2026-01-01"]
    r = {"n": len(X), "oui": sum(x["y"] for x in X), "perte_reference": m(X, "ref"), "perte_regle": m(X, "p"),
         "perte_melange": m(X, "mel"), "n_2026": len(K), "perte_reference_2026": m(K, "ref"),
         "perte_regle_2026": m(K, "p")}
    j = dt.date(2026, 11, 24)
    V = mi.versions(jusqua=j)
    r["taux_par_an_entieres"] = [round(v * 365.25, 3) for v in mi.taux(V, j, True, 365)[0]]
    r["taux_par_an_toutes"] = [round(v * 365.25, 3) for v in mi.taux(V, j, False, 365)[0]]
    r["brancher"] = (r["perte_regle"] < r["perte_reference"] and r["perte_melange"] < r["perte_reference"]
                     and (not K or r["perte_regle_2026"] < r["perte_reference_2026"]))
    Path("registre/modeles-ia-recent.json").write_text(json.dumps({"resume": r, "lignes": X}, ensure_ascii=False, indent=1),
                                                encoding="utf-8")
    Path("ecosystemes/modeles-ia-recent-branchee.json").write_text(json.dumps({"branchee": r["brancher"]}), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
