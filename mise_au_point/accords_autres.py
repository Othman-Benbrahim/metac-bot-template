"""Sous-famille « autres accords » : nombre de consentements requis (accords_requis.accords, règles écrites sur le titre,
2026-11-20). Procédure : preenregistrements/accords-autres.md, versée avant le calcul ; une passe.

Questions : famille accords (mêmes filtres que mise_au_point/accords.py), sous-famille « autre ».
Mesure : part de oui, sur TOUT le corpus résolu (titres distincts) HORS famille accords, des questions de la même tranche
de consentements (« 1 », « 2 », « 3+ »), tirée vers la part de oui de ce corpus (poids 5). Mesure extérieure aux
11 questions évaluées.
Référence : part de oui de la famille accords hors groupe. Mélange d'un quart plafonné à 15 points.
Branchement : (1) règle < référence ; (2) mélange < référence ; (3) règle < référence sur 2026.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import accords_regle as ar  # noqa: E402
import accords_requis as rq  # noqa: E402
import structures_questions as sq  # noqa: E402
from mise_au_point.procedure_inertie import groupe  # noqa: E402


def ll(p, y):
    p = min(max(p, .02), .98)
    return -math.log(p if y else 1 - p)


def principal() -> int:
    vus, F, H = set(), [], []
    for l in Path("registre/jugement-questions.jsonl").read_text(encoding="utf-8").splitlines():
        q = json.loads(l)
        t = q["titre"]
        if t in vus or str(q.get("issue")) not in ("0", "1"):
            continue
        vus.add(t)
        c = ar.classe(t) if sq.structure(t).startswith("procédure") else None
        x = {"titre": t, "jeu": q["jeu"], "y": int(q["issue"]), "classe": c, "groupe": groupe(t), "tranche": rq.accords(t)}
        (F if c is not None else H).append(x)
    moy = sum(z["y"] for z in H) / len(H)
    taux = {}
    for k in ("1", "2", "3+"):
        T = [z for z in H if z["tranche"] == k]
        taux[k] = {"n": len(T), "oui": sum(z["y"] for z in T),
                   "p": (sum(z["y"] for z in T) + 5 * moy) / (len(T) + 5)}
    X = []
    for x in F:
        if x["classe"] != "autre":
            continue
        S = [z for z in F if z["groupe"] != x["groupe"]]
        ref = sum(z["y"] for z in S) / len(S)
        p = taux[x["tranche"]]["p"]
        X.append(x | {"p": round(p, 4), "ref": round(ref, 4), "mel": round(ar.melanger(ref, p), 4)})
    m = lambda L, k: round(sum(ll(x[k], x["y"]) for x in L) / len(L), 4) if L else None
    K = [x for x in X if x["jeu"] >= "2026-01-01"]
    r = {"n": len(X), "oui": sum(x["y"] for x in X), "perte_reference": m(X, "ref"), "perte_regle": m(X, "p"),
         "perte_melange": m(X, "mel"), "n_2026": len(K), "perte_reference_2026": m(K, "ref"),
         "perte_regle_2026": m(K, "p"), "taux_hors_famille": {k: {**v, "p": round(v["p"], 4)} for k, v in taux.items()},
         "corpus_hors_famille": len(H)}
    r["brancher"] = (r["perte_regle"] < r["perte_reference"] and r["perte_melange"] < r["perte_reference"]
                     and (not K or r["perte_regle_2026"] < r["perte_reference_2026"]))
    Path("registre/accords-autres.json").write_text(json.dumps({"resume": r, "lignes": X}, ensure_ascii=False, indent=1),
                                                    encoding="utf-8")
    Path("ecosystemes/accords-autres.json").write_text(json.dumps(
        {"branchee": r["brancher"], "taux": {k: round(v["p"], 4) for k, v in taux.items()}}), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
