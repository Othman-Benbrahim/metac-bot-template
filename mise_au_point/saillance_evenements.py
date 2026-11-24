"""Coefficient de saillance pour la règle des événements comptés (décision de l'auteur, 2026-11-24, 15 h 33).
Questions résolues reconnues par evenements_regle.reconnaitre (restrictions du bot) ; k appris en laissant de côté
chaque question, puis chaque paire de pays (ou série)."""
import json, math, sys
from datetime import date, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import adaptateurs
import evenements_regle as er

def ll(p, y):
    p = min(max(p, .02), .98); return -math.log(p if y else 1 - p)

cache, vus, X = {}, set(), []
for l in Path("registre/jugement-questions.jsonl").read_text(encoding="utf-8").splitlines():
    q = json.loads(l)
    if q["titre"] in vus or str(q.get("issue")) not in ("0", "1") or not q.get("jeu") or not str(q.get("horizon")).isdigit():
        continue
    vus.add(q["titre"])
    r = er.reconnaitre(q["titre"])
    if not r:
        continue
    if r["serie"] not in cache:
        try:
            cache[r["serie"]] = adaptateurs.lire(r["serie"])
        except Exception:
            cache[r["serie"]] = []
    fin = (date.fromisoformat(q["jeu"]) + timedelta(days=int(q["horizon"]))).isoformat()
    pr = er.probabilite(cache[r["serie"]], r["pas"], q["jeu"], fin)
    if pr:
        X.append({"p": pr["p_regle"], "y": int(q["issue"]), "serie": r["serie"], "titre": q["titre"], "source": q["source"]})

def pk(p, k): return 1 - (1 - p) ** k
K = [0.25, 0.5, 1, 1.5, 2, 3, 4, 6]
best = lambda S: min(K, key=lambda k: sum(ll(pk(x["p"], k), x["y"]) for x in S))
n = len(X)
loo_q = sum(ll(pk(X[i]["p"], best(X[:i] + X[i + 1:])), X[i]["y"]) for i in range(n)) / n
loo_s = sum(ll(pk(x["p"], best([z for z in X if z["serie"] != x["serie"]])), x["y"]) for x in X) / n
res = {"n": n, "series": len({x["serie"] for x in X}), "oui": round(sum(x["y"] for x in X) / n, 3), "k": best(X),
       "perte_base_027": round(sum(ll(.27, x["y"]) for x in X) / n, 4),
       "perte_k1": round(sum(ll(x["p"], x["y"]) for x in X) / n, 4),
       "perte_loo_question": round(loo_q, 4), "perte_loo_serie": round(loo_s, 4)}
Path("registre/saillance-evenements.json").write_text(json.dumps({"resume": res, "lignes": X}, ensure_ascii=False, indent=1), encoding="utf-8")
print(res)
for x in X: print(f"  y={x['y']} p={x['p']:.2f} {x['serie']:24} {x['titre'][:75]}")
