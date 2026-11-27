"""Grille des familles de situation (2026-11-27, demande de l'auteur : « établir une grille pour chaque famille et
ratisser le plus large possible »).

Sans modèle de langue, sans appel réseau : mots du titre seulement. Chaque question reçoit une famille principale (la
première qui reconnaît le titre, dans l'ordre de FAMILLES) et la liste de toutes celles qui la reconnaissent.

Sorties (registre/grille-familles.json) :
- par famille : nombre de questions (Metaculus et toutes sources), part de « oui » (descriptif, NON causal : biais des
  rédacteurs), part couverte par au moins une brique (audit des briques du 2026-11-26) ;
- associations suspectes : brique déclenchée sur une question dont aucune famille n'est compatible avec elle
  (candidates « hors domaine », à relire, pas à corriger automatiquement) ;
- questions restées sans famille (pour compléter la grille au fil de l'eau).

    python mise_au_point/grille_familles.py
"""
from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
REG = RACINE / "registre"

from familles_situation import FAMILLES, REGEX, COMPATIBLE, COMBINAISON, familles  # noqa: E402


def principal() -> int:
    qs = {}
    for l in open(REG / "jugement-questions.jsonl", encoding="utf-8"):
        d = json.loads(l)
        if (d.get("titre") or "").startswith(COMBINAISON):     # questions combinées de ForecastBench : écartées
            continue
        qs[(d["source"], d["titre"].strip())] = d             # une question compte une fois (même titre)
    briq = collections.defaultdict(set)
    for l in open(REG / "audit-briques-2026-11-26.jsonl", encoding="utf-8"):
        a = json.loads(l)
        briq[(a["source"], a["titre"].strip())].add(a["fam"])

    stats = {s: collections.defaultdict(lambda: {"n": 0, "oui": 0, "jugees": 0, "brique": 0})
             for s in ("metaculus", "toutes")}
    suspectes, sans = [], []
    for k, d in qs.items():
        fs = familles(d["titre"])
        fp = fs[0] if fs else "sans_famille"
        y = d.get("issue")
        y = int(y) if str(y) in ("0", "1") else None
        for s in ("metaculus", "toutes"):
            if s == "metaculus" and d["source"] != "metaculus":
                continue
            c = stats[s][fp]
            c["n"] += 1
            if y is not None:
                c["jugees"] += 1
                c["oui"] += y
            if briq.get(k):
                c["brique"] += 1
        for b in briq.get(k, ()):
            if not (COMPATIBLE.get(b, set()) & set(fs)):
                suspectes.append({"source": d["source"], "id": d["id"], "titre": d["titre"][:160],
                                  "brique": b, "familles": fs})
        if not fs:
            sans.append({"source": d["source"], "titre": d["titre"][:160]})

    def tab(s):
        tot = sum(c["n"] for c in stats[s].values())
        out = []
        for f, c in sorted(stats[s].items(), key=lambda x: -x[1]["n"]):
            out.append({"famille": f, "n": c["n"], "part": round(c["n"] / tot, 3),
                        "oui": round(c["oui"] / c["jugees"], 3) if c["jugees"] else None,
                        "couverte_brique": round(c["brique"] / c["n"], 3)})
        return {"total": tot, "familles": out}

    res = {"date": "2026-11-27", "methode": "mots du titre, famille principale = première reconnue ; descriptif",
           "dynamique": {f: d for f, _, d in FAMILLES},
           "metaculus": tab("metaculus"), "toutes": tab("toutes"),
           "associations_suspectes": {"n": len(suspectes),
                                      "par_brique": dict(collections.Counter(x["brique"] for x in suspectes)),
                                      "exemples": suspectes[:60]},
           "sans_famille": {"n": len(sans), "exemples": sans[:40]}}
    (REG / "grille-familles.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for s in ("metaculus", "toutes"):
        print(f"== {s} ({res[s]['total']})")
        for x in res[s]["familles"]:
            print(f"  {x['famille']:28s} {x['n']:5d} {x['part']:6.1%}  oui {x['oui']}  brique {x['couverte_brique']:.0%}")
    print("associations suspectes", res["associations_suspectes"]["n"], res["associations_suspectes"]["par_brique"])
    print("sans famille", len(sans))
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
