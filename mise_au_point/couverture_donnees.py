"""Couverture en données de la carte (décision de l'auteur du 2026-11-24, 23 h 11 et 23 h 14 : compléter la carte au fil de
l'eau, combler visuellement les manques de données quand c'est possible ; les sondes continuent de tourner).

Pour chaque compartiment : statut de sa série
  - « fraiche » : série collectée, dernière donnée à 45 jours au plus ;
  - « ancienne » : série collectée, plus vieille ;
  - « vide » : trace déclarée mais aucune donnée lue ;
  - « a_trouver » : aucune série ;
  - « non_mesurable » : déclaré par nature sans série dans la fiche (trace statut « non_mesurable », avec motif).
Pour chaque relation : testable (série aux deux bouts) et verdict du contrôle par les séries.
Priorités : amonts sans série classés par le nombre de lectures manquées sur les questions résolues
(registre/carte-lacunes.json), puis par le nombre de relations sortantes.
Écrit registre/carte-couverture.json (affiché sur la carte : couche « couverture », tableau d'avancement).
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from collections import Counter
from pathlib import Path

ICI = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ICI))
import ecosysteme_couche as ecc  # noqa: E402

FRAICHEUR = 45


def statut(C: ecc.Couche, comp: str, jour: dt.date) -> dict:
    n = C.noeuds.get(comp, {})
    for t in n.get("traces") or []:
        if isinstance(t, dict) and t.get("statut") == "non_mesurable":
            return {"statut": "non_mesurable", "motif": t.get("motif")}
    a = C.serie_de(comp)
    if not a:
        return {"statut": "a_trouver"}
    L = C._lire(a)
    if not L:
        return {"statut": "vide", "serie": a}
    der = L[-1][0]
    return {"statut": "fraiche" if (jour - der).days <= FRAICHEUR else "ancienne", "serie": a, "derniere": der.isoformat()}


def principal() -> int:
    jour = dt.date.today()
    C = ecc.Couche()
    comps = {c: statut(C, c, jour) for c in C.noeuds}
    try:
        verif = json.loads((ICI / "registre/verification-relations.json").read_text(encoding="utf-8"))["relations"]
    except (OSError, ValueError, KeyError):
        verif = []
    V = {(f"{x['fiche']}:{x['de']}", f"{x['fiche']}:{x['vers']}"): x.get("verdict") for x in verif}
    rel, sortants = [], Counter()
    for c, rs in C.carte.entrants.items():
        for r in rs:
            sortants[r["de"]] += 1
            a, b = comps.get(r["de"], {}).get("statut"), comps.get(c, {}).get("statut")
            ok = a in ("fraiche", "ancienne") and b in ("fraiche", "ancienne")
            rel.append({"de": r["de"], "vers": c, "testable": ok, "verdict": V.get((r["de"], c))})
    try:
        lac = json.loads((ICI / "registre/carte-lacunes.json").read_text(encoding="utf-8"))["par_compartiment"]
    except (OSError, ValueError, KeyError):
        lac = []
    manques = Counter()
    for k, n in lac:
        if " → " in k:
            manques[k.split(" → ")[0]] += n
    prio = sorted((c for c, s in comps.items() if s["statut"] == "a_trouver" and sortants[c]),
                  key=lambda c: (-manques[c], -sortants[c], c))
    st = Counter(s["statut"] for s in comps.values())
    out = {"genere_le": jour.isoformat(), "fraicheur_jours": FRAICHEUR,
           "avancement": {"compartiments": len(comps), "par_statut": dict(st),
                          "relations": len(rel), "relations_testables": sum(r["testable"] for r in rel),
                          "relations_par_verdict": dict(Counter(r["verdict"] or "non_controlee" for r in rel))},
           "compartiments": comps,
           "relations": rel,
           "priorites": [{"compartiment": c, "lectures_manquees": manques[c], "relations_sortantes": sortants[c]}
                         for c in prio[:100]],
           "procedure": "mise_au_point/couverture_donnees.py"}
    (ICI / "registre/carte-couverture.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out["avancement"], ensure_ascii=False, indent=1))
    print("priorités :", [(p["compartiment"], p["lectures_manquees"], p["relations_sortantes"]) for p in out["priorites"][:25]])
    return 0


if __name__ == "__main__":
    sys.exit(principal())
