"""Évaluation de la brique « accords » (preenregistrements/accords.md). Passée une seule fois, après la collecte PA-X.

Questions : corpus résolu, titres distincts, structure « procédure », sous-famille reconnue par accords_regle.classe.
Groupe : mots à majuscule du titre (procedure_inertie.groupe) — les variantes d'un même dossier tombent ensemble.
Référence : part de oui de la famille hors groupe.
Règle : PA-X pour cessez_le_feu, accord_paix, tenue (calculée à la date de la question, accords antérieurs seulement) ;
part de oui de la sous-famille hors groupe, tirée vers la référence (poids 5), pour rencontre et autre.
Une question PA-X sans échéance lisible : abstention (hors calcul).
Branchement PAR SOUS-FAMILLE si : (1) règle < référence ; (2) mélange d'un quart plafonné à 15 points < référence ;
(3) règle < référence sur les questions de 2026 de la sous-famille, quand il y en a.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import accords_regle as ar  # noqa: E402
import structures_questions as sq  # noqa: E402
from mise_au_point.procedure_inertie import groupe  # noqa: E402

CLASSES = ("cessez_le_feu", "accord_paix", "tenue", "rencontre", "autre")


def ll(p, y):
    p = min(max(p, .02), .98)
    return -math.log(p if y else 1 - p)


def principal() -> int:
    A = ar.charger_pax()
    vus, X = set(), []
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
        jeu = dt.date.fromisoformat(q["jeu"])
        p = ar.probabilite_pax(c, t, jeu, A) if c in ("cessez_le_feu", "accord_paix", "tenue") else None
        if c in ("cessez_le_feu", "accord_paix", "tenue") and p is None:
            continue
        X.append({"titre": t, "jeu": q["jeu"], "y": int(q["issue"]), "classe": c, "groupe": groupe(t), "p_pax": p})
    for x in X:
        S = [z for z in X if z["groupe"] != x["groupe"]]
        ref = sum(z["y"] for z in S) / len(S)
        if x["p_pax"] is None:
            T = [z for z in S if z["classe"] == x["classe"]]
            p = (sum(z["y"] for z in T) + ar.POIDS_PRIOR * ref) / (len(T) + ar.POIDS_PRIOR)
        else:
            p = x["p_pax"]
        x.update({"ref": round(ref, 4), "p": round(p, 4), "mel": round(ar.melanger(ref, p), 4)})
    res = {"n": len(X), "groupes": len({x["groupe"] for x in X}), "pax_accords": len(A),
           "pax_derniere_date": A[-1][0].isoformat() if A else None, "classes": {}}
    for c in CLASSES:
        C = [x for x in X if x["classe"] == c]
        if not C:
            continue
        K = [x for x in C if x["jeu"] >= "2026-01-01"]
        m = lambda L, k: round(sum(ll(x[k], x["y"]) for x in L) / len(L), 4) if L else None
        r = {"n": len(C), "oui": sum(x["y"] for x in C), "groupes": len({x["groupe"] for x in C}),
             "perte_reference": m(C, "ref"), "perte_regle": m(C, "p"), "perte_melange": m(C, "mel"),
             "n_2026": len(K), "perte_reference_2026": m(K, "ref"), "perte_regle_2026": m(K, "p")}
        r["brancher"] = (r["perte_regle"] < r["perte_reference"] and r["perte_melange"] < r["perte_reference"]
                         and (not K or r["perte_regle_2026"] < r["perte_reference_2026"]))
        res["classes"][c] = r
    toutes = {c: [x for x in X if x["classe"] == c] for c in ("rencontre", "autre")}
    taux = {c: (sum(x["y"] for x in L) + ar.POIDS_PRIOR * (sum(z["y"] for z in X) / len(X))) / (len(L) + ar.POIDS_PRIOR)
            for c, L in toutes.items() if L}
    pax = {"lambda_cea_par_an": round(ar.taux_conclusion(A, dt.date(2026, 11, 24), ("Cea",)) * 365.25, 4),
           "lambda_accord_par_an": round(ar.taux_conclusion(A, dt.date(2026, 11, 24), ("SubComp", "SubPar")) * 365.25, 4),
           "lambda_rupture_par_an": round(ar.taux_rupture(A, dt.date(2026, 11, 24)) * 365.25, 4)}
    res["taux_pax_au_2026_11_24"] = pax
    sortie = {"branchees": [c for c, r in res["classes"].items() if r["brancher"]],
              "taux": {c: round(v, 4) for c, v in taux.items()}, "source": "mise_au_point/accords.py, passage unique"}
    Path("registre/accords.json").write_text(json.dumps({"resume": res, "lignes": X}, ensure_ascii=False, indent=1),
                                             encoding="utf-8")
    Path(ar.TAUX_CLASSES).write_text(json.dumps(sortie, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps(sortie, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
