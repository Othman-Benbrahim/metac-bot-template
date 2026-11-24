"""Lacunes de la carte (sans aucun score) : sur le corpus résolu, ce que la couche écosystème n'a pas pu lire, compté par
type et par compartiment → registre/carte-lacunes.json, affiché sur la carte (« où la carte reste muette »).
À relancer après chaque complément de la carte (décision de l'auteur du 2026-11-24, 20 h 48)."""
from __future__ import annotations

import datetime as dt
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ecosysteme_couche as ecc  # noqa: E402


def principal() -> int:
    C = ecc.Couche()
    vus, typ, comp = set(), Counter(), Counter()
    for l in Path("registre/jugement-questions.jsonl").read_text(encoding="utf-8").splitlines():
        q = json.loads(l)
        if q["titre"] in vus or str(q.get("issue")) not in ("0", "1"):
            continue
        vus.add(q["titre"])
        L = C.lire(q["titre"], float(q.get("horizon") or 90), dt.date.fromisoformat(q["jeu"]))
        for m in L["lacunes"]:
            typ[m.split(" : ")[-1].split(" (")[0]] += 1
            if " : " in m:
                comp[m.split(" : ")[0]] += 1
    Path("registre/carte-lacunes.json").write_text(json.dumps(
        {"genere_le": dt.date.today().isoformat(), "questions": len(vus), "par_type": typ.most_common(),
         "par_compartiment": comp.most_common(200),
         "note": "ce que la carte n'a pas pu lire sur le corpus résolu : à compléter petit à petit"},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(typ.most_common(6))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
