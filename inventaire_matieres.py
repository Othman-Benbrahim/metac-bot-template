"""Inventaire des matières stratégiques à documenter, par poids dans les questions et dans les fiches (bot 0.10.388).

Décision de l'auteur, 2026-11-20, 14 h 35. Compte, sans lire les issues, les questions (registre de jugement et
échantillon de mise au point, Manifold à part) dont le titre nomme chaque matière (motifs de collecte_rss.MATIERES), et
les fiches qui la mentionnent. `python inventaire_matieres.py` écrit registre/inventaire-matieres.md.
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import collecte_rss as cr

REG = Path("registre")
# noms français pour chercher dans les fiches (écrites en français)
FR = {"graphite": r"graphite", "lithium": r"lithium", "nickel": r"nickel", "cobalt": r"cobalt", "cuivre": r"cuivre",
      "terres_rares": r"terres rares", "uranium": r"uranium", "aluminium": r"aluminium", "acier": r"\bacier",
      "minerai_fer": r"minerai de fer", "petrole": r"pétrole|\bbrut\b", "gaz": r"\bgaz\b|\bgnl\b", "charbon": r"charbon",
      "electricite": r"électricité", "engrais": r"engrais", "ble": r"\bblé", "mais": r"\bmaïs", "soja": r"\bsoja",
      "fret_maritime": r"\bfret|porte-conteneurs|pétrolier", "carbone": r"marché du carbone|quotas d'émission",
      "hydrogene": r"hydrogène"}


def principal() -> int:
    qs = [json.loads(l) for l in (REG / "jugement-questions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    mp = REG / "mise-au-point" / "questions.jsonl"
    if mp.exists():
        qs += [json.loads(l) for l in mp.read_text(encoding="utf-8").splitlines() if l.strip()]
    vus, uniq = set(), []
    for q in qs:
        k = (q["source"], str(q["id"]))
        if k not in vus:
            vus.add(k)
            uniq.append(q)
    fiches = {Path(f).stem: Path(f).read_text(encoding="utf-8") for f in glob.glob("ecosystemes/*.yaml")}
    lignes = []
    for m, rx in cr.MATIERES.items():
        hors = sum(1 for q in uniq if q["source"] != "manifold" and rx.search(q.get("titre") or ""))
        mani = sum(1 for q in uniq if q["source"] == "manifold" and rx.search(q.get("titre") or ""))
        import re
        fi = sorted(f for f, t in fiches.items() if re.search(FR.get(m, "$^"), t, re.I))
        lignes.append((hors, mani, m, fi))
    lignes.sort(key=lambda t: (-t[0], -t[1]))
    L = ["# Inventaire des matières stratégiques (poids dans les questions et les fiches)", "",
         f"{len(uniq)} questions distinctes (registre de jugement et mise au point) ; issues non lues.", "",
         "| Matière | Questions (hors Manifold) | Manifold | Fiches qui la mentionnent |", "|---|---|---|---|"]
    L += [f"| {m} | {h} | {ma} | {', '.join(fi) or '—'} |" for h, ma, m, fi in lignes]
    (REG / "inventaire-matieres.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
