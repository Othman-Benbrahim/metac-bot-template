"""« Un parmi N » avec saillance (décision de l'auteur, 2026-11-24, 15 h 51 : « on teste au maximum jusqu'à ce que ça
marche »). Garde contre le piège de l'essai répété (à force d'essais, l'un finit par réussir par hasard) :
- DÉVELOPPEMENT : questions jouées avant le 2026-01-01. On y essaie autant de variantes qu'on veut.
- CONFIRMATION : questions jouées à partir du 2026-01-01. Elles ne servent qu'une fois, pour la seule variante retenue sur
  le développement. Branchement si, sur la confirmation, (1) la règle bat la référence ET (2) le mélange d'un quart
  plafonné à 15 points la bat aussi. Référence : part de oui du développement.
Variantes : p = 1 − (1 − 1/N)^k (saillance k), k unique, ou k propre à trois familles (sport collectif, récompense,
tennis).
"""
import json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import competitions_regle as cr

def ll(p, y):
    p = min(max(p, .02), .98); return -math.log(p if y else 1 - p)

J = {}
for l in Path("registre/jugement-questions.jsonl").read_text(encoding="utf-8").splitlines():
    q = json.loads(l); J.setdefault(q["titre"], q.get("jeu"))
X = json.loads(Path("registre/un-parmi-n.json").read_text(encoding="utf-8"))["lignes"]
for x in X:
    x["jeu"] = J[x["titre"]]
    x["famille"] = "recompense" if x["n"] in (5, 6, 8, 10) else ("tennis" if x["n"] == 128 else "equipe")
DEV = [x for x in X if x["jeu"] < "2026-01-01"]
CONF = [x for x in X if x["jeu"] >= "2026-01-01"]
B = sum(x["y"] for x in DEV) / len(DEV)
K = [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8]

def p(x, k): return 1 - (1 - 1 / x["n"]) ** k
def perte(S, f): return sum(ll(f(x), x["y"]) for x in S) / len(S)

# développement : groupes mis de côté pour choisir k (pas de réutilisation d'un groupe pour lui-même)
def k_unique(S): return min(K, key=lambda k: sum(ll(p(x, k), x["y"]) for x in S))
def k_famille(S): return {f: k_unique([x for x in S if x["famille"] == f] or S) for f in ("equipe", "recompense", "tennis")}
dev = {}
for nom, choisir, f in [("k_unique", k_unique, lambda x, k: p(x, k)), ("k_famille", k_famille, lambda x, k: p(x, k[x["famille"]]))]:
    tot = 0
    for g in {x["groupe"] for x in DEV}:
        A = [x for x in DEV if x["groupe"] != g]; T = [x for x in DEV if x["groupe"] == g]
        k = choisir(A); tot += sum(ll(f(x, k), x["y"]) for x in T)
    dev[nom] = round(tot / len(DEV), 4)
dev["reference"] = round(perte(DEV, lambda x: B), 4)
dev["k=1"] = round(perte(DEV, lambda x: p(x, 1)), 4)
retenue = min(("k_unique", "k_famille"), key=lambda v: dev[v])
k = k_unique(DEV) if retenue == "k_unique" else k_famille(DEV)
f = (lambda x: p(x, k)) if retenue == "k_unique" else (lambda x: p(x, k[x["famille"]]))
def mel(x):
    lg = lambda v: math.log(min(max(v, .01), .99) / (1 - min(max(v, .01), .99)))
    v = 1 / (1 + math.exp(-(0.75 * lg(B) + 0.25 * lg(f(x)))))
    return min(max(v, B - .15), B + .15)
conf = {"n": len(CONF), "oui": sum(x["y"] for x in CONF), "reference": round(perte(CONF, lambda x: B), 4),
        "regle": round(perte(CONF, f), 4), "melange_plafonne": round(perte(CONF, mel), 4)}
res = {"developpement": {"n": len(DEV), "oui": sum(x["y"] for x in DEV), **dev}, "variante_retenue": retenue, "k": k,
       "confirmation": conf, "brancher": conf["regle"] < conf["reference"] and conf["melange_plafonne"] < conf["reference"]}
Path("registre/un-parmi-n-saillance.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(res, ensure_ascii=False, indent=1))
