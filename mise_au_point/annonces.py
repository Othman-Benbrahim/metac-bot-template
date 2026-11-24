"""Évaluation de la brique « annonces » (preenregistrements/annonces.md). Une seule passe.

Questions : corpus résolu, titres distincts contenant « announce » (annonces_regle.classe), polarité inversée exclue.
Groupe : mots à majuscule du titre. Référence : part de oui de TOUT le corpus résolu hors groupe.
Niveau 1 : part de oui des questions « announce » hors groupe, tirée vers la référence (poids 5).
Niveau 2 : part de oui de l'annonceur (nomination, entreprise, gouvernement) hors groupe, tirée vers le niveau 1 (poids 5).
Critères (chaque niveau) : (1) règle < référence ; (2) mélange d'un quart plafonné à 15 points < référence ;
(3) règle < référence sur les questions de 2026. On branche le niveau le plus fin qui passe les trois.
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import accords_regle as ar  # noqa: E402
import annonces_regle as an  # noqa: E402
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
        c = an.classe(t)
        if c and re.search(r"\b(not|refrain)\b", t, re.I):
            c = None
        TOUT.append({"titre": t, "jeu": q["jeu"], "y": int(q["issue"]), "classe": c, "groupe": groupe(t)})
    A = [x for x in TOUT if x["classe"]]
    for x in A:
        S = [z for z in TOUT if z["groupe"] != x["groupe"]]
        ref = sum(z["y"] for z in S) / len(S)
        SA = [z for z in A if z["groupe"] != x["groupe"]]
        n1 = (sum(z["y"] for z in SA) + 5 * ref) / (len(SA) + 5)
        SC = [z for z in SA if z["classe"] == x["classe"]]
        n2 = (sum(z["y"] for z in SC) + 5 * n1) / (len(SC) + 5)
        x.update({"ref": round(ref, 4), "n1": round(n1, 4), "n2": round(n2, 4),
                  "mel1": round(ar.melanger(ref, n1), 4), "mel2": round(ar.melanger(ref, n2), 4)})
    m = lambda L, k: round(sum(ll(x[k], x["y"]) for x in L) / len(L), 4) if L else None
    K = [x for x in A if x["jeu"] >= "2026-01-01"]
    res = {"n": len(A), "oui": sum(x["y"] for x in A), "par_classe": {c: [sum(1 for x in A if x["classe"] == c),
           sum(x["y"] for x in A if x["classe"] == c)] for c in ("nomination", "entreprise", "gouvernement")},
           "perte_reference": m(A, "ref"), "n_2026": len(K), "perte_reference_2026": m(K, "ref")}
    for niv in ("1", "2"):
        r = {"perte_regle": m(A, "n" + niv), "perte_melange": m(A, "mel" + niv), "perte_regle_2026": m(K, "n" + niv)}
        r["passe"] = (r["perte_regle"] < res["perte_reference"] and r["perte_melange"] < res["perte_reference"]
                      and r["perte_regle_2026"] < res["perte_reference_2026"])
        res["niveau_" + niv] = r
    niveau = 2 if res["niveau_2"]["passe"] else 1 if res["niveau_1"]["passe"] else 0
    ref_tout = sum(z["y"] for z in TOUT) / len(TOUT)
    t1 = (sum(z["y"] for z in A) + 5 * ref_tout) / (len(A) + 5)
    taux = {"annonce": round(t1, 4)}
    for c in ("nomination", "entreprise", "gouvernement"):
        C = [z for z in A if z["classe"] == c]
        taux[c] = round((sum(z["y"] for z in C) + 5 * t1) / (len(C) + 5), 4)
    res["niveau_branche"] = niveau
    Path("registre/annonces.json").write_text(json.dumps({"resume": res, "lignes": A}, ensure_ascii=False, indent=1),
                                              encoding="utf-8")
    Path("ecosystemes/annonces-taux.json").write_text(json.dumps({"niveau": niveau, "taux": taux}), encoding="utf-8")
    print(json.dumps(res | {"taux": taux}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
