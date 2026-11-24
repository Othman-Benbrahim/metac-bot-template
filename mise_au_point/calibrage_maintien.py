"""Calibrage de la brique du maintien sur les questions résolues reconnues (décision de l'auteur, 2026-11-24)."""
import json, math, sys
from datetime import date, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import maintien_regle as m

def ll(p, y):
    p = min(max(p, .02), .98); return -math.log(p if y else 1 - p)

vus, L = set(), []
for l in Path("registre/jugement-questions.jsonl").read_text(encoding="utf-8").splitlines():
    q = json.loads(l)
    if q["titre"] in vus or str(q.get("issue")) not in ("0", "1") or not q.get("jeu") or not str(q.get("horizon")).isdigit():
        continue
    vus.add(q["titre"])
    fin = (date.fromisoformat(q["jeu"]) + timedelta(days=int(q["horizon"]))).isoformat()
    e = m.estimer(q["titre"], q["jeu"], fin, 0.27)
    if e:
        L.append({"titre": q["titre"], "source": q["source"], "y": int(q["issue"]), "p_regle": e["p_regle"], "sens": e["sens"]})
B = 0.27
res = {"n": len(L), "oui": round(sum(x["y"] for x in L) / len(L), 3) if L else None,
       "perte_regle": round(sum(ll(x["p_regle"], x["y"]) for x in L) / len(L), 4) if L else None,
       "perte_base": round(sum(ll(B, x["y"]) for x in L) / len(L), 4) if L else None}
Path("registre/calibrage-maintien.json").write_text(json.dumps({"resume": res, "lignes": L}, ensure_ascii=False, indent=1), encoding="utf-8")
print(res)
for x in L: print(f"  y={x['y']} p={x['p_regle']:.2f} {x['sens']:6} {x['source']:10} {x['titre'][:80]}")
