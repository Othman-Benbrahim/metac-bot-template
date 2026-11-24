"""Brique « état du conflit » (décision de l'auteur, 2026-11-24, 15 h 38). Procédure fixée AVANT tout calcul, passée une fois.

Questions : corpus résolu (titres distincts), exactement deux pays reconnus (evenements_regle.pays), un verbe de conflit
(strike, attack, military action, clash, war, invade, invasion, blockade), aucun acteur non étatique nommé ; date du jeu et
horizon connus.
État à la date du jeu, sans regarder l'avenir : la GED d'UCDP paraît avec environ un mois de retard, donc on ne lit que les
mois terminés AVANT le mois qui précède le jeu (décalage d'un mois). Actif = au moins un événement meurtrier entre les deux
gouvernements dans les deux derniers mois ainsi lisibles ; sinon dormant.
Probabilité : part de oui de l'état, tirée vers la part de oui de l'échantillon (poids 5).
Évaluation : en laissant de côté chaque paire de pays (taux et moyenne recalculés sans elle), perte log contre la part de oui
de l'échantillon calculée de la même façon. Branchement seulement si (1) l'état bat la référence ET (2) le mélange d'un quart
plafonné à 15 points bat aussi la référence. Décision prise sur ce seul passage.
"""
from __future__ import annotations

import json
import math
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import adaptateurs  # noqa: E402
import evenements_regle as er  # noqa: E402

CONFLIT = re.compile(r"\b(strikes?|airstrikes?|attacks?|military action|military clash|clash(es)?|war|invade[sd]?|invasion|blockade)\b", re.I)
POIDS_PRIOR = 5


def mois_lisibles(jeu: str) -> list[str]:
    """Les deux mois terminés avant le mois qui précède le jeu (AAAA-MM-01)."""
    d = date.fromisoformat(jeu).replace(day=1)
    out = []
    for k in (2, 3):                                  # mois M-2 et M-3 par rapport au mois du jeu M
        y, m = d.year, d.month - k
        while m <= 0:
            y, m = y - 1, m + 12
        out.append(f"{y}-{m:02d}-01")
    return out


def ll(p, y):
    p = min(max(p, .02), .98)
    return -math.log(p if y else 1 - p)


def principal() -> int:
    vus, X, cache = set(), [], {}
    for l in Path("registre/jugement-questions.jsonl").read_text(encoding="utf-8").splitlines():
        q = json.loads(l)
        t = q["titre"]
        if t in vus or str(q.get("issue")) not in ("0", "1") or not q.get("jeu") or not str(q.get("horizon")).isdigit():
            continue
        vus.add(t)
        if not CONFLIT.search(t) or er.NON_ETATIQUES.search(t):
            continue
        ps = er.pays(t)
        if len(ps) != 2:
            continue
        serie = f"ucdp_dyade:{min(ps)}:{max(ps)}"
        if serie not in cache:
            cache[serie] = dict(adaptateurs.lire(serie))
        s = cache[serie]
        ms = mois_lisibles(q["jeu"])
        if not all(m in s for m in ms):
            continue
        X.append({"titre": t, "source": q["source"], "jeu": q["jeu"], "y": int(q["issue"]), "paire": serie,
                  "actif": any(s[m] >= 1 for m in ms), "mois_lus": ms})
    n = len(X)
    def taux(S, actif):
        moy = sum(x["y"] for x in S) / len(S)
        T = [x for x in S if x["actif"] == actif]
        return (sum(x["y"] for x in T) + POIDS_PRIOR * moy) / (len(T) + POIDS_PRIOR), moy
    pe, pr, pm = [], [], []
    for x in X:
        S = [z for z in X if z["paire"] != x["paire"]]
        p, moy = taux(S, x["actif"])
        lg = lambda v: math.log(min(max(v, .01), .99) / (1 - min(max(v, .01), .99)))
        mel = 1 / (1 + math.exp(-(0.75 * lg(moy) + 0.25 * lg(p))))
        mel = min(max(mel, moy - .15), moy + .15)
        pe.append(ll(p, x["y"])); pr.append(ll(moy, x["y"])); pm.append(ll(mel, x["y"]))
    A = [x for x in X if x["actif"]]; D = [x for x in X if not x["actif"]]
    res = {"n": n, "paires": len({x["paire"] for x in X}),
           "actif": {"n": len(A), "oui": round(sum(x["y"] for x in A) / len(A), 3) if A else None, "paires": len({x["paire"] for x in A})},
           "dormant": {"n": len(D), "oui": round(sum(x["y"] for x in D) / len(D), 3) if D else None},
           "perte_reference": round(sum(pr) / n, 4), "perte_etat": round(sum(pe) / n, 4),
           "perte_melange_plafonne": round(sum(pm) / n, 4)}
    res["brancher"] = res["perte_etat"] < res["perte_reference"] and res["perte_melange_plafonne"] < res["perte_reference"]
    Path("registre/etat-conflit.json").write_text(json.dumps({"resume": res, "lignes": X}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    for x in X:
        print(f"  y={x['y']} {'ACTIF  ' if x['actif'] else 'dormant'} {x['jeu']} {x['mois_lus']} {x['paire']:22} {x['titre'][:60]}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
