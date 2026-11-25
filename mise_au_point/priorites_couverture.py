"""2026-11-25 (décision d'auteur, 18 h 07) : où brancher des séries en priorité. Descriptif, sans modèle de langue.

Par compartiment : questions ouvertes du bot qui s'y rattachent (dossier_interne.rattachement), questions résolues du
corpus (registre/inventaire-rendement.json), briefs qui le touchent (briefs/journal.jsonl), et état de ses séries
terrain (hors séries d'attention, recoupement_briefs.ATTENTION) : fraîche (dernier point ≤ 45 jours), ancienne, aucune.
Score = 3 × questions ouvertes + Metaculus résolues + 0,2 × autres résolues + briefs ; classé pour les compartiments
sans série fraîche. Écrit registre/priorites-couverture.json.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import adaptateurs as ad  # noqa: E402
import briefs_questions as bq  # noqa: E402
import ecosystemes as ec  # noqa: E402
import recoupement_briefs as rb  # noqa: E402

REG = ad.REG


def principal() -> int:
    auj = dt.date.today().isoformat()
    import dossier_interne as di
    ouvertes = Counter()
    for q in bq.questions_ouvertes(auj).values():
        comps, _ = di.rattachement(q["titre"])
        for c in comps:
            ouvertes[c] += 1
    inv = {l["compartiment"]: l for l in json.loads((REG / "inventaire-rendement.json").read_text(encoding="utf-8"))["lignes"]}
    briefs = Counter(c for l in bq._jsonl(Path(rb.JOURNAL)) if l.get("statut") == "ok" for c in l.get("compartiments") or [])
    s = ec.assembler(ec.charger(ec.DOSSIER))
    lignes = []
    for n in s["noeuds"]:
        c = n["id"]
        terrain = [t["adaptateur"] for t in n.get("traces") or [] if isinstance(t, dict) and t.get("statut") == "collecte"
                   and t.get("adaptateur") and t["adaptateur"].split(":")[0] not in rb.ATTENTION]
        derniere = None
        for a in terrain:
            try:
                pts = ad.lire(a, REG) or []
            except Exception:
                pts = []
            if pts:
                derniere = max(derniere or pts[-1][0][:10], pts[-1][0][:10])
        etat = "aucune" if not derniere else ("fraiche" if (dt.date.fromisoformat(auj) - dt.date.fromisoformat(derniere)).days <= 45 else "ancienne")
        i = inv.get(c, {})
        score = 3 * ouvertes[c] + i.get("metaculus", 0) + 0.2 * (i.get("questions", 0) - i.get("metaculus", 0)) + briefs[c]
        lignes.append({"compartiment": c, "nom": n.get("nom"), "ouvertes": ouvertes[c], "resolues": i.get("questions", 0),
                       "metaculus": i.get("metaculus", 0), "briefs": briefs[c], "series": terrain, "etat": etat,
                       "derniere": derniere, "score": round(score, 1)})
    lignes.sort(key=lambda x: -x["score"])
    sortie = {"genere_le": auj, "a_brancher": [x for x in lignes if x["etat"] != "fraiche" and x["score"] > 0],
              "deja_couverts": [x for x in lignes if x["etat"] == "fraiche" and x["score"] > 0]}
    (REG / "priorites-couverture.json").write_text(json.dumps(sortie, ensure_ascii=False, indent=1), encoding="utf-8")
    for x in sortie["a_brancher"][:30]:
        print(f"{x['score']:6.1f} | {x['compartiment']:48} | ouv {x['ouvertes']:3} | rés {x['resolues']:3} (M {x['metaculus']:2}) | br {x['briefs']} | {x['etat']} {x['series'][:2]}")
    print("déjà couverts (fraîche) :", [(x["compartiment"], x["score"]) for x in sortie["deja_couverts"][:12]])
    return 0


if __name__ == "__main__":
    sys.exit(principal())
