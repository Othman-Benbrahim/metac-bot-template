"""Évaluation de la brique « un parmi N » (competitions_regle.py), décision de l'auteur du 2026-11-24, 15 h 48. Procédure
fixée AVANT tout calcul (règle et table de N relues sur les titres seuls), passée une fois ; décision sur ce seul passage.

Questions : corpus résolu, titres distincts, structure « compétition », reconnues par competitions_regle.n_concurrents.
Groupe : l'événement (motif reconnu) et les années citées dans le titre — les candidats d'une même compétition forment un
groupe, mis de côté ensemble.
Prévision de la règle : 1/N. Référence : part de oui de l'échantillon sans le groupe. Branchement si (1) la règle bat la
référence ET (2) le mélange d'un quart plafonné à 15 points (avec la référence à la place de la prévision du bot) la bat aussi.
"""
import json, math, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import competitions_regle as cr
import structures_questions as sq

def ll(p, y):
    p = min(max(p, .02), .98); return -math.log(p if y else 1 - p)

vus, X = set(), []
for l in Path("registre/jugement-questions.jsonl").read_text(encoding="utf-8").splitlines():
    q = json.loads(l); t = q["titre"]
    if t in vus or str(q.get("issue")) not in ("0", "1"):
        continue
    vus.add(t)
    if not sq.structure(t).startswith("compétition"):
        continue
    n = cr.n_concurrents(t)
    if n is None:
        continue
    ev = next(m.pattern for m, k in cr.MOTIFS if m.search(t))
    X.append({"titre": t, "y": int(q["issue"]), "n": n, "groupe": ev + "|" + "-".join(re.findall(r"\b20\d\d\b", t))})
pr, pe, pm = [], [], []
for x in X:
    S = [z for z in X if z["groupe"] != x["groupe"]]
    moy = sum(z["y"] for z in S) / len(S)
    e = cr.estimer(x["titre"], moy)
    pr.append(ll(moy, x["y"])); pe.append(ll(1 / x["n"], x["y"])); pm.append(ll(e["p"], x["y"]))
n = len(X)
res = {"n": n, "groupes": len({x["groupe"] for x in X}), "oui": sum(x["y"] for x in X),
       "somme_1_sur_N": round(sum(1 / x["n"] for x in X), 1),
       "perte_reference": round(sum(pr) / n, 4), "perte_regle": round(sum(pe) / n, 4), "perte_melange_plafonne": round(sum(pm) / n, 4)}
res["brancher"] = res["perte_regle"] < res["perte_reference"] and res["perte_melange_plafonne"] < res["perte_reference"]
Path("registre/un-parmi-n.json").write_text(json.dumps({"resume": res, "lignes": X}, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(res, ensure_ascii=False, indent=1))
