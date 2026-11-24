"""Calibrage de la règle « événement compté » sur les questions résolues couvertes (décision de l'auteur, 2026-11-24,
15 h 11 : pas d'ombre ; calibrer pour ne pas trop se tromper, puis appliquer).

Règle : h = (k + 0,5) / (n + 1), k = pas avec occurrence parmi les n derniers pas avant la date de la question (24 mois,
ou 365 jours) ; p = 1 − (1 − h)^m, m = nombre de pas jusqu'à l'échéance. Seuils qNN : quantile des pas de la fenêtre.
"""
from __future__ import annotations

import json
import math
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evenements_comptes import couvrir, OCCURRENCE, sq, adaptateurs, ICI  # noqa: E402
from lecture_mecanique import Carte  # noqa: E402

FENETRE = {"mois": 24, "jour": 365}


def regle(serie: list, seuil, pas: str, jour: str, horizon_j: float) -> dict | None:
    avant = [(j, v) for j, v in serie if j < jour]
    n = FENETRE[pas]
    if len(avant) < n:
        return None
    vals = [v for _, v in avant[-n:]]
    s = sorted(vals)[int(int(str(seuil)[1:]) / 100 * (len(vals) - 1))] if str(seuil).startswith("q") else float(seuil)
    k = sum(1 for v in vals if v >= s) if not str(seuil).startswith("q") else sum(1 for v in vals if v > s)
    h = (k + 0.5) / (n + 1)
    m = max(1, math.ceil(horizon_j / (30.44 if pas == "mois" else 1)))
    return {"h": h, "k": k, "n": n, "m": m, "p": 1 - (1 - h) ** m}


def ll(p, y):
    p = min(max(p, 0.02), 0.98)
    return -math.log(p if y else 1 - p)


def principal() -> int:
    carte, cache, vus, L = Carte(), {}, set(), []
    for l in (ICI / "registre/jugement-questions.jsonl").read_text(encoding="utf-8").splitlines():
        q = json.loads(l)
        if q["titre"] in vus or str(q.get("issue")) not in ("0", "1") or not q.get("jeu") or not str(q.get("horizon")).isdigit():
            continue
        vus.add(q["titre"])
        if sq.structure(q["titre"]).split(" (")[0] not in OCCURRENCE:
            continue
        for c in couvrir(carte, q["titre"]):
            if c["serie"] not in cache:
                try:
                    cache[c["serie"]] = adaptateurs.lire(c["serie"])
                except Exception:
                    cache[c["serie"]] = []
            r = regle(cache[c["serie"]], c["seuil"], c["pas"], q["jeu"], float(q["horizon"]))
            if r:
                L.append({"titre": q["titre"], "source": q["source"], "jeu": q["jeu"], "y": int(q["issue"]),
                          "serie": c["serie"], **r})
                break
    B = 0.268
    res = {"n": len(L), "oui": round(sum(x["y"] for x in L) / len(L), 3), "p_moyen_regle": round(sum(x["p"] for x in L) / len(L), 3),
           "perte_regle": round(sum(ll(x["p"], x["y"]) for x in L) / len(L), 4),
           "perte_base_0268": round(sum(ll(B, x["y"]) for x in L) / len(L), 4)}
    for w in (0.25, 0.5):
        res[f"perte_melange_{w}"] = round(sum(ll(1 / (1 + math.exp(-(w * math.log(max(min(x['p'], .98), .02) / (1 - max(min(x['p'], .98), .02))) + (1 - w) * math.log(B / (1 - B))))), x["y"]) for x in L) / len(L), 4)
    tr = {}
    for lo, hi in [(0, .1), (.1, .3), (.3, .6), (.6, 1.01)]:
        S = [x for x in L if lo <= x["p"] < hi]
        tr[f"{lo}-{hi}"] = (len(S), round(sum(x["y"] for x in S) / len(S), 2) if S else None)
    res["par_tranche_p"] = tr
    (ICI / "registre/calibrage-evenements.json").write_text(json.dumps({"resume": res, "lignes": L}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    for x in L:
        print(f"  y={x['y']} p={x['p']:.2f} k={x['k']}/{x['n']} m={x['m']} {x['serie']:26} {x['titre'][:70]}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
