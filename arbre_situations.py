"""Maquette de l'arbre de la connaissance : graphe situation → événement tiré des règles sourcées (décision de l'auteur
du 2026-11-21, 13 h 56, option b ; motif UFO-B du catalogue OntoUML : une situation déclenche un événement, un
événement produit une situation). Descriptif, aucun appel de modèle, rien dans le bot.

Chaque règle sourcée donne une arête : sa `situation` de départ → son `objet` (type d'événement), avec son taux ou sa
procédure, son périmètre et ses compartiments de fiche. Le code ne crée aucun lien qui ne soit pas écrit dans une
règle : les situations PRODUITES par un événement ne sont pas encore renseignées (étape suivante, à sourcer).

    python arbre_situations.py     # écrit registre/arbre-situations.json et registre/arbre-situations.md
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

import regles_coutumieres as rc

SORTIE_JSON = Path("registre") / "arbre-situations.json"
SORTIE_MD = Path("registre") / "arbre-situations.md"


def graphe() -> dict:
    noeuds_s, noeuds_e, aretes = {}, {}, []
    for r in rc.regles():
        if r.get("statut") != "source" or not r.get("situation") or not r.get("objet"):
            continue
        s, e = r["situation"], r["objet"]
        fiches = sorted({str(c).split(":")[0] for c in r.get("compartiments") or []}) or ["(sans fiche)"]
        noeuds_s.setdefault(s, {"fiches": set()})["fiches"].update(fiches)
        noeuds_e.setdefault(e, {"fiches": set()})["fiches"].update(fiches)
        aretes.append({"regle": r["id"], "situation": s, "evenement": e, "structure": r.get("structure"),
                       "echelle": (r.get("echelle") or {}).get("tranche"), "perimetre": r.get("perimetre"),
                       "fiches": fiches, "parametres": r.get("parametres") or {}})
    return {"situations": {k: sorted(v["fiches"]) for k, v in noeuds_s.items()},
            "evenements": {k: sorted(v["fiches"]) for k, v in noeuds_e.items()}, "aretes": aretes}


def _id(prefixe: str, i: int) -> str:
    return f"{prefixe}{i}"


def mermaid(g: dict) -> str:
    sid = {s: _id("S", i) for i, s in enumerate(g["situations"])}
    eid = {e: _id("E", i) for i, e in enumerate(g["evenements"])}
    par_fiche = collections.defaultdict(list)
    for a in g["aretes"]:
        par_fiche[a["fiches"][0]].append(a)
    lignes = ["flowchart LR"]
    for f, aa in sorted(par_fiche.items()):
        lignes.append(f'  subgraph {f.replace("-", "_").replace("(", "").replace(")", "").replace(" ", "_")}["{f}"]')
        for a in aa:
            s, e = a["situation"].replace('"', "'"), a["evenement"].replace('"', "'")
            lignes.append(f'    {sid[a["situation"]]}(["{s}"]) -- "{a["regle"]}" --> {eid[a["evenement"]]}["{e}"]')
        lignes.append("  end")
    return "\n".join(lignes)


def principal() -> int:
    g = graphe()
    SORTIE_JSON.write_text(json.dumps(g, ensure_ascii=False, indent=1), encoding="utf-8")
    partages = {e: [a["regle"] for a in g["aretes"] if a["evenement"] == e] for e in g["evenements"]}
    partages = {e: v for e, v in partages.items() if len(v) > 1}
    md = ["# Maquette de l'arbre : situations → événements (règles sourcées)", "",
          f"{len(g['situations'])} types de situation, {len(g['evenements'])} types d'événement, "
          f"{len(g['aretes'])} arêtes (une par règle sourcée). Les situations produites par chaque événement restent à "
          "renseigner (à sourcer) : le graphe ne chaîne pas encore les règles entre elles.", "",
          "Événements atteints par plusieurs règles (plusieurs étalons pour le même événement) :", ""]
    md += [f"- {e} : {', '.join(v)}" for e, v in partages.items()] or ["- aucun"]
    md += ["", "```mermaid", mermaid(g), "```", ""]
    SORTIE_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"{len(g['situations'])} situations, {len(g['evenements'])} événements, {len(g['aretes'])} arêtes ; "
          f"événements partagés : {len(partages)}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
