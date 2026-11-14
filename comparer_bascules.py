"""Ce qu'une modification change sur les lectures enregistrées (0.10.85, règle écrite du 2026-11-14).

Prend deux tables de bascules (`rejeu_banc.py --bascules --json`), l'une calculée avec le code de la base, l'autre avec
celui de la branche, sur les MÊMES lignes du registre. Une ligne dont le verdict rejoué diffère entre les deux est une
bascule DUE À LA MODIFICATION. Sortie en Markdown (résumé du contrôle, demande de fusion, historique).

    python comparer_bascules.py base.json branche.json
"""
from __future__ import annotations

import json
import sys


def verdicts(t: dict) -> dict[str, tuple]:
    """Question → (statut rejoué, p rejoué), pour les lignes qui basculent par rapport à l'enregistrement."""
    return {b["question_id"]: (b["apres"], None if b.get("p_apres") is None else round(b["p_apres"], 6))
            for b in t.get("table") or []}


def comparer(base: dict, branche: dict) -> list[dict]:
    """Une ligne absente d'une table rejoue comme elle est enregistrée ; on compare donc chaque côté à l'enregistré."""
    vb, vh = verdicts(base), verdicts(branche)
    enreg = {b["question_id"]: (b["avant"], None if b.get("p_avant") is None else round(b["p_avant"], 6))
             for t in (base, branche) for b in t.get("table") or []}
    out = []
    for q in sorted(set(vb) | set(vh)):
        a, h = vb.get(q, enreg[q]), vh.get(q, enreg[q])
        if a != h:
            out.append({"question_id": q, "base": a, "branche": h})
    return out


def markdown(base: dict, branche: dict) -> str:
    if base.get("indisponible"):
        return "### Table des bascules\n\nCode de la base sans table des bascules (avant 0.10.85) : rien à comparer.\n"
    diff = comparer(base, branche)
    lignes = [f"### Table des bascules ({branche.get('version_rejouee')} contre la base)", "",
              f"{branche.get('lignes')} lignes rejouées ; **{len(diff)} verdict(s) changé(s) par cette modification**.", ""]
    if diff:
        lignes += ["| question | base | branche |", "|---|---|---|"]
        f = lambda v: f"{v[0]}" + ("" if v[1] is None else f" ({v[1]:.3f})")
        lignes += [f"| `{d['question_id'][:60]}` | {f(d['base'])} | {f(d['branche'])} |" for d in diff]
    return "\n".join(lignes) + "\n"


if __name__ == "__main__":
    b, h = (json.loads(open(p, encoding="utf-8").read()) for p in sys.argv[1:3])
    print(markdown(b, h))
