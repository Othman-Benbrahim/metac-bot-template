"""Applique les branchements proposés (ecosystemes/branchements-*.yml) aux fiches : ajoute à chaque compartiment visé une
trace « collecte » portant son adaptateur, sans doublon (0.10.324). Les propositions « a_definir » sont listées, pas
appliquées. Réécrit les fiches touchées (yaml.safe_dump, ordre des clés gardé).

    python appliquer_branchements.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

import adaptateurs as ad

DOSSIER = Path("ecosystemes")


def main() -> int:
    props = []
    for f in sorted(DOSSIER.glob("branchements-*.yml")):
        d = yaml.safe_load(f.read_text(encoding="utf-8")) or []
        props += d.get("branchements", []) if isinstance(d, dict) else d
    fiches = {}
    for f in DOSSIER.glob("*.yaml"):
        d = yaml.safe_load(f.read_text(encoding="utf-8"))
        if isinstance(d, dict) and "theme" in d:
            fiches[d["theme"]] = (f, d)
    appliques, a_definir, refus, touchees = 0, [], [], set()
    for p in props:
        nom, th, cp = p.get("adaptateur"), p.get("fiche"), p.get("compartiment")
        if cp in (None, "a_definir"):
            a_definir.append(p)
            continue
        if th not in fiches or nom.split(":")[0] not in ad.ADAPTATEURS:
            refus.append((p, "fiche ou adaptateur inconnu"))
            continue
        f, d = fiches[th]
        c = next((c for c in d["compartiments"] if c["id"] == cp), None)
        if c is None:
            refus.append((p, "compartiment inconnu"))
            continue
        traces = c.setdefault("traces", [])
        if any(t.get("adaptateur") == nom for t in traces):
            continue
        traces.append({"source": p.get("source") or nom, "statut": "collecte", "adaptateur": nom})
        appliques += 1
        touchees.add(th)
    for th in touchees:
        f, d = fiches[th]
        f.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False, width=200), encoding="utf-8")
    print(f"{appliques} branchement(s) appliqué(s) dans {len(touchees)} fiche(s) ; {len(a_definir)} à définir ; {len(refus)} refusé(s)")
    for p in a_definir:
        print("  à définir :", p.get("adaptateur"), "→", p.get("fiche"), "·", p.get("raison", "")[:90])
    for p, r in refus:
        print("  refusé :", p.get("adaptateur"), "→", p.get("fiche"), p.get("compartiment"), "·", r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
