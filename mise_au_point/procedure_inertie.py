"""Brique « procédure : inertie et accord » (décision de l'auteur, 2026-11-24, 15 h 45 : « on continue »). Procédure fixée
AVANT tout calcul (les classes ont été définies en lisant 70 titres tirés au hasard, sans leurs issues), passée une fois ;
décision de branchement prise sur ce seul passage.

Mécanisme (carte : coutumes et habitus, calendriers, négociations) : une procédure en cours a de l'inertie.
- STATU_QUO : la question demande si l'état présent tient (continues, no change, remain, still, hold, extended…) :
  l'inertie joue pour le oui.
- ACCORD : la question demande qu'un accord se conclue ou qu'une rencontre ait lieu (deal, agreement, ceasefire sans
  « continues », agree, sign, meet, talks, summit, withdraw from par accord…) : il faut l'accord de deux parties.
- CHANGEMENT : rupture d'un état présent (broken, collapse, end…) et toute autre procédure (décision, vote, confirmation, publication, sortie d'un produit…).
Questions : corpus résolu, titres distincts, structure « procédure » (structures_questions).
Groupe (pour l'évaluation) : ensemble des mots à majuscule du titre, hors mots de calendrier et mots d'interrogation —
les variantes d'une même question (même réunion de la Fed, même cessez-le-feu) tombent dans le même groupe.
Probabilité : part de oui de la classe, tirée vers la part de oui de l'échantillon (poids 5).
Évaluation : chaque groupe mis de côté ; référence = part de oui sans ce groupe. Branchement si (1) la classe bat la
référence ET (2) le mélange d'un quart plafonné à 15 points la bat aussi.
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import structures_questions as sq  # noqa: E402

RUPTURE = re.compile(r"\b(broken|breaks?|collapse[sd]?|violat\w*|ends?|resume[sd]? (fighting|strikes))\b", re.I)
STATU_QUO = re.compile(r"\b(continues?|continuing|no change|remains?|still|holds?|hold up|extended|stays?|not (meet|change))\b", re.I)
ACCORD = re.compile(r"\b(deal|agreement|agree[sd]?|ceasefire|cease-fire|truce|sign\w*|meet|meeting with|talks|summit|negotiat\w*|treaty|peace)\b", re.I)
CALENDRIER = {"Will", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
              "November", "December", "Q1", "Q2", "Q3", "Q4", "By", "Before", "After", "In", "The", "On", "No", "Fed"}
POIDS_PRIOR = 5


def classe(titre: str) -> str:
    if RUPTURE.search(titre):                        # rompre un état présent est un changement
        return "changement"
    if STATU_QUO.search(titre):
        return "statu_quo"
    if ACCORD.search(titre):
        return "accord"
    return "changement"


def groupe(titre: str) -> str:
    mots = {m for m in re.findall(r"\b[A-Z][A-Za-z0-9\-]+", titre) if m not in CALENDRIER}
    return " ".join(sorted(mots)) or titre


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
        if not sq.structure(t).startswith("procédure"):
            continue
        X.append({"titre": t, "source": q["source"], "y": int(q["issue"]), "classe": classe(t), "groupe": groupe(t)})
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
    par = {}
    for c in ("statu_quo", "accord", "changement"):
        C = [x for x in X if x["classe"] == c]
        par[c] = {"n": len(C), "oui": sum(x["y"] for x in C), "groupes": len({x["groupe"] for x in C})}
    res = {"n": n, "groupes": len({x["groupe"] for x in X}), "oui_total": sum(x["y"] for x in X), "classes": par,
           "perte_reference": round(sum(pr) / n, 4), "perte_classe": round(sum(pe) / n, 4),
           "perte_melange_plafonne": round(sum(pm) / n, 4)}
    res["brancher"] = res["perte_classe"] < res["perte_reference"] and res["perte_melange_plafonne"] < res["perte_reference"]
    Path("registre/procedure-inertie.json").write_text(json.dumps({"resume": res, "lignes": X}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
