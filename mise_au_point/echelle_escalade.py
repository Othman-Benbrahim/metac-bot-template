"""Brique « échelle de l'escalade » pour les questions de conflit entre États (décision de l'auteur, 2026-11-24, 15 h 40 :
« il faut résoudre ce problème »). Procédure fixée AVANT tout calcul, passée une seule fois ; décision de branchement
prise sur ce seul passage.

Mécanisme (carte, fiche Militaire, doctrines) : l'escalade est une échelle. Un acte léger (frappe, attaque, action militaire,
accrochage) se produit souvent dans une crise ; un acte lourd (invasion, opération terrestre, blocus, quarantaine,
occupation, guerre déclarée) est rare, car il coûte beaucoup plus et franchit un seuil. La question dit elle-même le
barreau demandé : c'est l'information mécanique que la fréquence passée ne donnait pas.

Questions : corpus résolu, titres distincts ; un verbe de conflit ; au moins un pays reconnu (evenements_regle.pays) ;
aucun acteur non étatique nommé ; titres qui ne portent pas sur la fin d'un conflit (end, ceasefire, peace, deal, agree).
Classe : LOURD si le titre contient invade/invasion/ground/occupy/blockade/quarantine/« go to war »/« at war »/« war with » ;
sinon LÉGER.
Probabilité : part de oui de la classe, tirée vers la part de oui de l'échantillon (poids 5).
Évaluation : chaque groupe de pays (ensemble des pays cités) mis de côté à son tour ; perte log contre la part de oui de
l'échantillon calculée sans ce groupe. Branchement si (1) la classe bat la référence ET (2) le mélange d'un quart plafonné
à 15 points la bat aussi.
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import evenements_regle as er  # noqa: E402

CONFLIT = re.compile(r"\b(strikes?|airstrikes?|attacks?|military action|military clash|clash(es)?|war|invade[sd]?|invasion|blockade|quarantine|occupy)\b", re.I)
LOURD = re.compile(r"\b(invade[sd]?|invasion|ground|occupy|occupation|blockade|quarantine|go to war|at war|war with)\b", re.I)
FIN = re.compile(r"\b(end|ends|ending|ceasefire|cease-fire|peace|deal|agree\w*|truce)\b", re.I)
POIDS_PRIOR = 5


def ll(p, y):
    p = min(max(p, .02), .98)
    return -math.log(p if y else 1 - p)


def lg(v):
    v = min(max(v, .01), .99)
    return math.log(v / (1 - v))


def principal() -> int:
    vus, X = set(), []
    for l in Path("registre/jugement-questions.jsonl").read_text(encoding="utf-8").splitlines():
        q = json.loads(l)
        t = q["titre"]
        if t in vus or str(q.get("issue")) not in ("0", "1"):
            continue
        vus.add(t)
        if not CONFLIT.search(t) or er.NON_ETATIQUES.search(t) or FIN.search(t):
            continue
        ps = er.pays(t)
        if not ps:
            continue
        X.append({"titre": t, "source": q["source"], "y": int(q["issue"]), "groupe": ":".join(sorted(ps)),
                  "classe": "lourd" if LOURD.search(t) else "leger"})
    n = len(X)
    pe, pr, pm = [], [], []
    for x in X:
        S = [z for z in X if z["groupe"] != x["groupe"]]
        moy = sum(z["y"] for z in S) / len(S)
        T = [z for z in S if z["classe"] == x["classe"]]
        p = (sum(z["y"] for z in T) + POIDS_PRIOR * moy) / (len(T) + POIDS_PRIOR)
        mel = 1 / (1 + math.exp(-(0.75 * lg(moy) + 0.25 * lg(p))))
        mel = min(max(mel, moy - .15), moy + .15)
        pe.append(ll(p, x["y"])); pr.append(ll(moy, x["y"])); pm.append(ll(mel, x["y"]))
    par = {c: {"n": len([x for x in X if x["classe"] == c]),
               "oui": round(sum(x["y"] for x in X if x["classe"] == c) / max(1, len([x for x in X if x["classe"] == c])), 3),
               "groupes": len({x["groupe"] for x in X if x["classe"] == c})} for c in ("lourd", "leger")}
    res = {"n": n, "groupes": len({x["groupe"] for x in X}), "classes": par,
           "perte_reference": round(sum(pr) / n, 4), "perte_classe": round(sum(pe) / n, 4),
           "perte_melange_plafonne": round(sum(pm) / n, 4)}
    res["brancher"] = res["perte_classe"] < res["perte_reference"] and res["perte_melange_plafonne"] < res["perte_reference"]
    Path("registre/echelle-escalade.json").write_text(json.dumps({"resume": res, "lignes": X}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    for x in sorted(X, key=lambda x: (x["classe"], x["y"])):
        print(f"  y={x['y']} {x['classe']:5} {x['groupe']:16} {x['titre'][:80]}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
