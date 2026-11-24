"""Évaluation de la couche écosystème avec l échelle « objet » (preenregistrements/couche-ecosysteme-objet.md). Une seule passe.

Corpus résolu, titres distincts ; date = « jeu », horizon = champ « horizon » (jours prévus par la source).
Base p0 = part de oui du corpus hors groupe (mots à majuscule). Couche : p = σ(logit p0 + k·d·sens).
Questions « lues » : direction d ≠ 0 et sens lisible.
k : maximum de vraisemblance sur les questions lues de développement (jeu < 2026), grille −3 à 3 par pas de 0,1.
Confirmation : questions lues de 2026, avec ce k.
Branchement si : k > 0 (la carte pousse dans le sens qu'elle écrit) ; perte(couche) < perte(p0) sur la confirmation ;
et, si au moins 5 questions de confirmation ont |d| ≥ 0,3, perte(couche) < perte(p0) sur celles-ci (là où la carte
pousse fort).
Lacunes : ce que la carte n'a pas pu lire, compté par type et par compartiment → registre/carte-lacunes-objet.json.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ecosysteme_couche as ecc  # noqa: E402
from mise_au_point.procedure_inertie import groupe  # noqa: E402


def ll(p, y):
    p = min(max(p, .02), .98)
    return -math.log(p if y else 1 - p)


def principal() -> int:
    C = ecc.Couche()
    vus, T = set(), []
    for l in Path("registre/jugement-questions.jsonl").read_text(encoding="utf-8").splitlines():
        q = json.loads(l)
        t = q["titre"]
        if t in vus or str(q.get("issue")) not in ("0", "1"):
            continue
        vus.add(t)
        T.append({"titre": t, "jeu": q["jeu"], "y": int(q["issue"]), "groupe": groupe(t),
                  "horizon": float(q.get("horizon") or 90)})
    tot = sum(x["y"] for x in T)
    par_g = Counter(x["groupe"] for x in T)
    oui_g = Counter(x["groupe"] for x in T if x["y"])
    lac_type, lac_comp = Counter(), Counter()
    X = []
    for x in T:
        x["p0"] = (tot - oui_g[x["groupe"]]) / (len(T) - par_g[x["groupe"]])
        L = C.lire(x["titre"], x["horizon"], dt.date.fromisoformat(x["jeu"]), objet=True)
        for m in L["lacunes"]:
            lac_type[m.split(" : ")[-1].split(" (")[0]] += 1
            if " : " in m:
                lac_comp[m.split(" : ")[0]] += 1
        if L.get("direction") and L["sens"] is not None:
            X.append(x | {"d": L["direction"], "sens": L["sens"], "n_contrib": len(L["contributions"]),
                          "contrib": L["contributions"][:4]})
    dev = [x for x in X if x["jeu"] < "2026-01-01"]
    conf = [x for x in X if x["jeu"] >= "2026-01-01"]
    perte = lambda L, k: sum(ll(ecc.deplacer(x["p0"], x["d"], x["sens"], k), x["y"]) for x in L) / len(L) if L else None
    grille = [round(-3 + 0.1 * i, 1) for i in range(61)]
    k = min(grille, key=lambda kk: perte(dev, kk)) if dev else 0.0
    fort = [x for x in conf if abs(x["d"]) >= 0.3]
    r = {"corpus": len(T), "lues": len(X), "lues_dev": len(dev), "lues_2026": len(conf), "k": k,
         "perte_dev_p0": perte(dev, 0), "perte_dev_couche": perte(dev, k),
         "perte_conf_p0": perte(conf, 0), "perte_conf_couche": perte(conf, k),
         "fort_2026": len(fort), "perte_fort_p0": perte(fort, 0), "perte_fort_couche": perte(fort, k)}
    r = {a: (round(b, 4) if isinstance(b, float) else b) for a, b in r.items()}
    r["brancher"] = bool(k > 0 and conf and r["perte_conf_couche"] < r["perte_conf_p0"]
                         and (len(fort) < 5 or r["perte_fort_couche"] < r["perte_fort_p0"]))
    Path("registre/couche-ecosysteme-objet.json").write_text(json.dumps({"resume": r, "lignes": X}, ensure_ascii=False,
                                                                  indent=1), encoding="utf-8")
    Path("registre/carte-lacunes-objet.json").write_text(json.dumps(
        {"par_type": lac_type.most_common(), "par_compartiment": lac_comp.most_common(60),
         "note": "ce que la carte n'a pas pu lire sur le corpus résolu : à compléter petit à petit"},
        ensure_ascii=False, indent=1), encoding="utf-8")
    Path("ecosystemes/couche-ecosysteme-objet.json").write_text(json.dumps({"branchee": r["brancher"], "k": k}),
                                                          encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    print("lacunes :", lac_type.most_common(8))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
