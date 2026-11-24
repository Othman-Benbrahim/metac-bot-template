"""Passage unique de la brique « compétitions : force mesurée (Elo) » (preenregistrements/elo-competitions.md).

    python mise_au_point/elo_competitions.py --lister   # reconnaissance sur les titres seuls (sans les issues)
    python mise_au_point/elo_competitions.py            # le passage (une fois)
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
from collections import Counter
from functools import lru_cache
from pathlib import Path

ICI = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ICI))
import elo_regle as er  # noqa: E402
from mise_au_point.procedure_inertie import groupe, ll, lg  # noqa: E402


def questions():
    vus, Q = set(), []
    for l in (ICI / "registre/jugement-questions.jsonl").read_text(encoding="utf-8").splitlines():
        q = json.loads(l)
        if q["titre"] in vus or str(q.get("issue")) not in ("0", "1"):
            continue
        vus.add(q["titre"])
        Q.append(q)
    return Q


def principal() -> int:
    rows, tir, nfl = er.resultats(), er.tirs(), er.matchs_nfl()
    noms = {r["home_team"] for r in rows} | {r["away_team"] for r in rows}
    Q = [q for q in questions() if er.reconnaitre(q["titre"], noms)]
    if "--lister" in sys.argv:
        for q in Q:
            print(q["jeu"], q["source"], er.reconnaitre(q["titre"], noms), "|", q["titre"][:100])
        print(len(Q), "questions reconnues")
        return 0

    @lru_cache(maxsize=None)
    def S_cdm(j):
        return er.cdm(rows, tir, j)

    @lru_cache(maxsize=None)
    def S_nfl(j):
        return er.nfl_saison(nfl, j)

    lignes = []
    for q in Q:
        j = dt.date.fromisoformat(q["jeu"])
        r = er.reconnaitre(q["titre"], noms)
        if r["comp"] == "cdm":
            if j > dt.date(2026, 7, 19):
                continue
            S = S_cdm(j)
            cle = {"poule": "premier", "sortie_poule": "sortie_poule", "quart": "quart", "demi": "demi",
                   "finale": "finale", "titre": "titre"}.get(r["forme"])
            p = S[r["forme"]] if r["forme"] in ("premier_vainqueur", "hote_demi") else S[cle].get(r["equipe"], 0.0)
        else:
            if not (dt.date(2025, 3, 1) <= j <= dt.date(2026, 2, 8)):
                continue
            if r["forme"] == "division" and r["equipe"] not in er.DIVISIONS.get(r["division"], []):
                continue
            S = S_nfl(j)
            p = S[r["forme"]].get(r["equipe"], 0.0)
        lignes.append({"titre": q["titre"], "jeu": q["jeu"], "source": q["source"], "forme": r["forme"],
                       "p": round(min(0.99, max(0.01, p)), 4), "y": int(q["issue"]), "groupe": groupe(q["titre"])})
    n = len(lignes)
    tot = sum(x["y"] for x in lignes)
    gr = Counter(x["groupe"] for x in lignes)
    go = Counter(x["groupe"] for x in lignes if x["y"])
    for x in lignes:
        x["ref"] = (tot - go[x["groupe"]]) / max(1, n - gr[x["groupe"]])
        m = 1 / (1 + math.exp(-(0.75 * lg(x["ref"]) + 0.25 * lg(x["p"]))))
        x["melange"] = min(max(m, x["ref"] - 0.15), x["ref"] + 0.15)

    def pertes(L):
        if not L:
            return None
        return {k: round(sum(ll(x[c], x["y"]) for x in L) / len(L), 4) for k, c in
                (("regle", "p"), ("reference", "ref"), ("melange", "melange"))} | {"n": len(L)}
    tout = pertes(lignes)
    a26 = pertes([x for x in lignes if x["jeu"] >= "2026"])
    c1 = tout["regle"] < tout["reference"]
    c2 = tout["melange"] < tout["reference"]
    c3 = bool(a26) and a26["regle"] < a26["reference"]
    res = {"procedure": "preenregistrements/elo-competitions.md", "passe_le": dt.date.today().isoformat(),
           "ensemble": tout, "questions_2026": a26, "criteres": {"regle_lt_ref": c1, "melange_lt_ref": c2,
                                                                  "regle_lt_ref_2026": c3},
           "branchee": c1 and c2 and c3,
           "par_competition": {k: pertes([x for x in lignes if (x["forme"] in ("division", "conference", "super_bowl")) == (k == "nfl")])
                               for k in ("cdm", "nfl")},
           "lignes": lignes}
    (ICI / "registre/elo-competitions.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "lignes"}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
