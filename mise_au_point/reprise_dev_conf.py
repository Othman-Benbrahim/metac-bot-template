"""Reprise de la procédure et de l'état du conflit avec découpage développement / confirmation (décision de l'auteur,
2026-11-24, 15 h 54). Écrit avant le calcul, passé une fois.

RÉSERVE ÉCRITE D'AVANCE : les premiers essais (procedure_inertie.py, etat_conflit.py) ont porté sur toutes les questions,
2026 comprises ; leurs résultats d'ensemble ont été vus. La confirmation sur 2026 n'est donc pas vierge : un succès ici est
un indice, pas une preuve. Même réserve, plus légère, pour « un parmi N » (le premier essai sur tout l'échantillon avait été
vu avant le découpage).

Développement : questions jouées avant 2026 ; confirmation : à partir de 2026, un seul passage pour la variante retenue.
Référence : part de oui du développement. Branchement si, sur la confirmation, la variante ET le mélange d'un quart
plafonné à 15 points battent la référence.
- Procédure : variantes (a) trois classes statu quo / accord / changement ; (b) deux classes statu quo / autre.
- État du conflit : variantes (a) actif = événement dans les 2 mois lisibles ; (b) dans les 3 mois lisibles ;
  (c) dans les 6 mois lisibles (toujours avec le décalage d'un mois de la parution UCDP).
Les taux de chaque classe sont tirés vers la moyenne (poids 5).
"""
import json, math, sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent)); sys.path.insert(0, str(Path(__file__).resolve().parent))
import adaptateurs, evenements_regle as er, structures_questions as sq
import procedure_inertie as pi, etat_conflit as ec

def ll(p, y):
    p = min(max(p, .02), .98); return -math.log(p if y else 1 - p)
def lg(v):
    v = min(max(v, .01), .99); return math.log(v / (1 - v))
J = {}
for l in Path("registre/jugement-questions.jsonl").read_text(encoding="utf-8").splitlines():
    q = json.loads(l); J.setdefault(q["titre"], q)

def evaluer(X, variantes):
    DEV = [x for x in X if x["jeu"] < "2026-01-01"]; CONF = [x for x in X if x["jeu"] >= "2026-01-01"]
    B = sum(x["y"] for x in DEV) / len(DEV)
    def taux(S, cl, c):
        T = [x for x in S if cl(x) == c]; m = sum(x["y"] for x in S) / len(S)
        return (sum(x["y"] for x in T) + 5 * m) / (len(T) + 5)
    dev = {}
    for nom, cl in variantes.items():                      # groupes de développement mis de côté
        tot = 0
        for x in DEV:
            A = [z for z in DEV if z["groupe"] != x["groupe"]]
            tot += ll(taux(A, cl, cl(x)), x["y"])
        dev[nom] = round(tot / len(DEV), 4)
    dev["reference"] = round(sum(ll(B, x["y"]) for x in DEV) / len(DEV), 4)
    nom = min(variantes, key=lambda v: dev[v]); cl = variantes[nom]
    pr = lambda x: taux(DEV, cl, cl(x))
    def mel(x):
        v = 1 / (1 + math.exp(-(0.75 * lg(B) + 0.25 * lg(pr(x))))); return min(max(v, B - .15), B + .15)
    conf = {"n": len(CONF), "oui": sum(x["y"] for x in CONF),
            "reference": round(sum(ll(B, x["y"]) for x in CONF) / len(CONF), 4),
            "variante": round(sum(ll(pr(x), x["y"]) for x in CONF) / len(CONF), 4),
            "melange_plafonne": round(sum(ll(mel(x), x["y"]) for x in CONF) / len(CONF), 4)}
    return {"developpement": {"n": len(DEV), "oui": sum(x["y"] for x in DEV), **dev}, "retenue": nom, "confirmation": conf,
            "brancher": conf["variante"] < conf["reference"] and conf["melange_plafonne"] < conf["reference"]}

# procédure
P = json.loads(Path("registre/procedure-inertie.json").read_text(encoding="utf-8"))["lignes"]
for x in P:
    x["jeu"] = J[x["titre"]]["jeu"]
res = {"procedure": evaluer(P, {"trois_classes": lambda x: x["classe"],
                                "deux_classes": lambda x: "statu_quo" if x["classe"] == "statu_quo" else "autre"})}
# état du conflit
C = json.loads(Path("registre/etat-conflit.json").read_text(encoding="utf-8"))["lignes"]
cache = {}
def actif(x, n):
    if x["paire"] not in cache:
        cache[x["paire"]] = dict(adaptateurs.lire(x["paire"]))
    s = cache[x["paire"]]; d = date.fromisoformat(x["jeu"]).replace(day=1); ms = []
    for k in range(2, 2 + n):
        y, m = d.year, d.month - k
        while m <= 0:
            y, m = y - 1, m + 12
        ms.append(f"{y}-{m:02d}-01")
    return any(s.get(m, 0) >= 1 for m in ms)
for x in C:
    x["groupe"] = x["paire"]; x["a2"], x["a3"], x["a6"] = actif(x, 2), actif(x, 3), actif(x, 6)
res["etat_conflit"] = evaluer(C, {"deux_mois": lambda x: x["a2"], "trois_mois": lambda x: x["a3"], "six_mois": lambda x: x["a6"]})
Path("registre/reprise-dev-conf.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
