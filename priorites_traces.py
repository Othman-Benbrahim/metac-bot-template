"""Ordre des prochaines collectes : quelles traces brancher d'abord (bot 0.10.337).

Décision d'auteur du 2026-11-19, 11 h 43, d'après la fiche sur Gallagher, Hasko et Webb (Nature Computational Science,
18 novembre 2026 ; « mieux plutôt que plus ») : couvrir d'abord les compartiments VIDES, et de préférence ceux des
niveaux d'organisation peu mesurés, plutôt qu'ajouter une série à un compartiment déjà lu.

Pour chaque compartiment sans série utilisable (aucune trace dont l'adaptateur rende au moins calibrer.N_MIN relevés) :
- débloque : relations et ponts dont l'AUTRE bout a déjà une série (mesurables dès que celui-ci l'est) ;
- en attente : relations et ponts dont l'autre bout est vide aussi (compte pour moitié) ;
- rareté du niveau : 1 − part des compartiments déjà mesurés dans son niveau d'organisation.
Score = (débloque + 0,5 × en attente) × (1 + rareté du niveau). Puis choix glouton : après chaque choix, le niveau
choisi compte comme un peu plus couvert, pour que la liste alterne les niveaux (la diversité de la fiche).

    python priorites_traces.py [--n 25]     # écrit registre/priorites-traces.md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import calibrer as cb
import ecosystemes as ec

SORTIE = Path("registre") / "priorites-traces.md"


def classer(dossier: Path = ec.DOSSIER, reg: Path = cb.ad.REG, n: int = 25) -> list[dict]:
    s = ec.assembler(ec.charger(dossier))
    noeuds = {x["id"]: x for x in s["noeuds"]}
    mesure = {nid: bool(cb.premiere_serie(x, reg)[0]) for nid, x in noeuds.items()}
    liens = [(r["de"], r["vers"]) for r in s["relations"] if r["de"] != r["vers"] and not r.get("module")]
    liens += [(p["de"], p["vers"]) for p in s["ponts"] if p.get("resolu") and p["de"] != p["vers"]]
    par_niveau: dict[str, list[bool]] = {}
    for nid, x in noeuds.items():
        par_niveau.setdefault(x.get("organisation") or "?", []).append(mesure[nid])
    couverts = {k: sum(v) for k, v in par_niveau.items()}
    totaux = {k: len(v) for k, v in par_niveau.items()}
    cands = []
    for nid, x in noeuds.items():
        if mesure[nid]:
            continue
        autres = [b if a == nid else a for a, b in liens if nid in (a, b)]
        deb = sum(1 for o in autres if mesure.get(o))
        att = sum(1 for o in autres if not mesure.get(o))
        sources = [t.get("source") for t in x.get("traces") or [] if t.get("statut") == "a_brancher"]
        cands.append({"compartiment": nid, "nom": x.get("nom"), "niveau": x.get("organisation") or "?",
                      "debloque": deb, "en_attente": att, "a_brancher": sources,
                      "fermee": all(t.get("statut") == "fermee" for t in x.get("traces") or []) and bool(x.get("traces"))})
    choix = []
    restants = [c for c in cands if not c["fermee"]]   # une trace « fermée » est sans source non intrusive : on ne la cherche pas
    while restants and len(choix) < n:
        for c in restants:
            rare = 1 - couverts[c["niveau"]] / max(totaux[c["niveau"]], 1)
            c["rarete_niveau"] = round(rare, 2)
            c["score"] = round((c["debloque"] + 0.5 * c["en_attente"]) * (1 + rare), 2)
        meilleur = max(restants, key=lambda c: (c["score"], c["debloque"], c["compartiment"]))
        choix.append(dict(meilleur))
        restants.remove(meilleur)
        couverts[meilleur["niveau"]] += 1                # le niveau compte comme un peu plus couvert
    return choix


def rapport(choix: list[dict]) -> str:
    l = ["# Ordre des prochaines collectes (compartiments vides, niveaux rares d'abord)", "",
         "Calculé par `priorites_traces.py` ; score = (relations débloquées + ½ × en attente) × (1 + rareté du niveau).", "",
         "| # | compartiment | niveau | débloque | en attente | score | sources à brancher |", "|---|---|---|---|---|---|---|"]
    for i, c in enumerate(choix, 1):
        l.append(f"| {i} | `{c['compartiment']}` | {c['niveau']} | {c['debloque']} | {c['en_attente']} | {c['score']} | "
                 f"{' ; '.join(c['a_brancher']) or '(aucune source écrite)'} |")
    return "\n".join(l) + "\n"


def principal() -> int:
    a = argparse.ArgumentParser()
    a.add_argument("--n", type=int, default=25)
    args = a.parse_args()
    t = rapport(classer(n=args.n))
    SORTIE.write_text(t, encoding="utf-8")
    print(t)
    return 0


if __name__ == "__main__":
    sys.exit(principal())
