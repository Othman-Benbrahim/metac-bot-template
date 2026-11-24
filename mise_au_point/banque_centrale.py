"""Évaluation de la brique « banque centrale » (preenregistrements/banque-centrale.md). Passée une seule fois.

Questions : corpus résolu (registre/jugement-questions.jsonl), titres distincts, reconnus par
banque_centrale_regle.reconnaitre ; probabilité calculée à la date « jeu » de la question, avec les seules décisions
antérieures.
Groupe : la période visée (mois de la réunion, ou année) — les barreaux d'une même réunion forment un groupe.
Référence : part de oui des questions reconnues hors groupe (le biais du questionneur, mesuré sur ces seules questions).
Mélange : un quart (log-odds) de la règle avec la référence, plafonné à 15 points.
Branchement si les trois conditions tiennent : (1) perte de la règle < perte de la référence sur l'ensemble ;
(2) perte du mélange plafonné < perte de la référence ; (3) perte de la règle < perte de la référence sur les questions
de 2026 (confirmation).
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import banque_centrale_regle as bc  # noqa: E402


def ll(p, y):
    p = min(max(p, .02), .98)
    return -math.log(p if y else 1 - p)


def groupe(f: dict) -> str:
    for k in ("reunion", "jusqua_reunion"):
        if k in f:
            return f"{f[k][1]}-{f[k][0]:02d}"
    if "avant" in f:
        return f"{f['avant'].year}-{f['avant'].month:02d}"
    if "mois" in f:
        return "seq-" + "-".join(map(str, f["mois"]))
    return str(f.get("annee"))


def principal() -> int:
    R, C = bc.charger()
    vus, X = set(), []
    for l in Path("registre/jugement-questions.jsonl").read_text(encoding="utf-8").splitlines():
        q = json.loads(l)
        t = q["titre"]
        if t in vus or str(q.get("issue")) not in ("0", "1"):
            continue
        vus.add(t)
        f = bc.reconnaitre(t)
        if f is None:
            continue
        jeu = dt.date.fromisoformat(q["jeu"])
        p = bc.probabilite(f, jeu, R, C)
        if p is None:
            continue
        X.append({"titre": t, "jeu": q["jeu"], "y": int(q["issue"]), "p": round(p, 4), "groupe": groupe(f),
                  "type": f["type"]})
    pr, pe, pm = [], [], []
    for x in X:
        S = [z for z in X if z["groupe"] != x["groupe"]]
        ref = sum(z["y"] for z in S) / len(S)
        m = bc.melanger(ref, x["p"])
        x["ref"] = round(ref, 4)
        pr.append(ll(ref, x["y"])); pe.append(ll(x["p"], x["y"])); pm.append(ll(m, x["y"]))
    n = len(X)
    conf = [i for i, x in enumerate(X) if x["jeu"] >= "2026-01-01"]
    res = {"n": n, "groupes": len({x["groupe"] for x in X}), "oui": sum(x["y"] for x in X),
           "par_type": {t: sum(1 for x in X if x["type"] == t) for t in sorted({x["type"] for x in X})},
           "perte_reference": round(sum(pr) / n, 4), "perte_regle": round(sum(pe) / n, 4),
           "perte_melange_plafonne": round(sum(pm) / n, 4),
           "confirmation_2026": {"n": len(conf), "perte_reference": round(sum(pr[i] for i in conf) / len(conf), 4),
                                 "perte_regle": round(sum(pe[i] for i in conf) / len(conf), 4)}}
    _, comptes = bc.table(R, C, dt.date(2026, 11, 24))
    res["comptes_par_etat_au_2026_11_24"] = comptes
    res["brancher"] = (res["perte_regle"] < res["perte_reference"]
                       and res["perte_melange_plafonne"] < res["perte_reference"]
                       and res["confirmation_2026"]["perte_regle"] < res["confirmation_2026"]["perte_reference"])
    Path("registre/banque-centrale.json").write_text(json.dumps({"resume": res, "lignes": X}, ensure_ascii=False, indent=1),
                                                     encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
