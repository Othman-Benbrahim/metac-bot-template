"""Ontologie, étape 1 (décision de l'auteur du 2026-11-22, 1 h 35 : « OUI ») : le graphe des TYPES, tiré tel quel des
règles coutumières (ecosystemes/regles-coutumieres.yaml), sur le motif UFO-B : un type de situation (champ
« situation ») mène à un type d'événement (champ « objet ») par une règle (taux, structure, sources). Aucune catégorie
n'est inventée ; rien n'est fusionné : les doublons probables sont seulement signalés, l'auteur décide.

Sorties : registre/ontologie-graphe.json (noeuds, arêtes, manques) et registre/ontologie-graphe.md (lecture).

    python ontologie.py
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import yaml

REGLES = Path("ecosystemes/regles-coutumieres.yaml")
SORTIE_JSON = Path("registre/ontologie-graphe.json")
SORTIE_MD = Path("registre/ontologie-graphe.md")


def cle(texte: str) -> str:
    t = "".join(c for c in unicodedata.normalize("NFD", texte.lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def graphe(regles: list[dict]) -> dict:
    situations, evenements, aretes, manques = {}, {}, [], []
    for r in regles:
        s, e = (r.get("situation") or "").strip(), (r.get("objet") or "").strip()
        if not s or not e:
            manques.append({"regle": r["id"], "manque": "situation ou événement non écrit",
                            "statut": r.get("statut")})
            continue
        ks, ke = "S:" + cle(s), "E:" + cle(e)
        situations.setdefault(ks, {"id": ks, "texte": s, "regles": []})["regles"].append(r["id"])
        evenements.setdefault(ke, {"id": ke, "texte": e, "regles": []})["regles"].append(r["id"])
        aretes.append({"regle": r["id"], "de": ks, "vers": ke, "structure": r.get("structure"),
                       "ecosysteme": r.get("ecosysteme"), "echelle": r.get("echelle"),
                       "perimetre": r.get("perimetre") or [], "compartiments": r.get("compartiments") or [],
                       "parametres": r.get("parametres") or {}, "statut": r.get("statut"),
                       "indices": r.get("indices") or [],
                       # 2026-11-22 (correction après le test 1) : exclusions et fenêtres de dates de la situation
                       "exclure": r.get("exclure") or [], "periodes": r.get("periodes") or [],
                       "mois": r.get("mois") or [],
                       "sources": [x.get("url") for x in r.get("sources") or [] if isinstance(x, dict)]})
        if not r.get("compartiments"):
            manques.append({"regle": r["id"], "manque": "aucun compartiment : la situation ne peut pas être "
                            "reconnue dans les situations observées", "statut": r.get("statut")})
    doublons = []
    for groupe in (situations, evenements):
        vals = list(groupe.values())
        for i, a in enumerate(vals):
            for b in vals[i + 1:]:
                ratio = SequenceMatcher(None, cle(a["texte"]), cle(b["texte"])).ratio()
                if ratio >= 0.75:
                    doublons.append({"a": a["texte"], "b": b["texte"], "ressemblance": round(ratio, 2),
                                     "regles": [a["regles"], b["regles"]]})
    return {"situations": list(situations.values()), "evenements": list(evenements.values()), "aretes": aretes,
            "manques": manques, "doublons_probables": doublons}


def lecture(g: dict) -> str:
    t = ["# Graphe des types (ontologie, étape 1)", "",
         "Tiré tel quel des règles coutumières : un type de situation mène à un type d'événement par une règle. "
         "Rien n'est inventé ni fusionné.", "",
         f"- {len(g['situations'])} types de situation, {len(g['evenements'])} types d'événement, "
         f"{len(g['aretes'])} règles reliées",
         f"- {len(g['manques'])} manques, {len(g['doublons_probables'])} doublons probables (à trancher par l'auteur)",
         "", "## Doublons probables (formulations proches)", ""]
    t += [f"- « {d['a']} » / « {d['b']} » ({d['ressemblance']}) — règles {d['regles'][0]} / {d['regles'][1]}"
          for d in g["doublons_probables"]] or ["- aucun"]
    t += ["", "## Manques", ""] + [f"- {m['regle']} : {m['manque']} (statut {m['statut']})" for m in g["manques"]]
    t += ["", "## Arêtes", "", "| type de situation | → type d'événement | règle | structure | compartiments |",
          "|---|---|---|---|---|"]
    noms = {n["id"]: n["texte"] for n in g["situations"] + g["evenements"]}
    t += [f"| {noms[a['de']]} | {noms[a['vers']]} | {a['regle']} | {a['structure']} | {', '.join(a['compartiments'])} |"
          for a in g["aretes"]]
    return "\n".join(t) + "\n"


def principal() -> int:
    regles = yaml.safe_load(REGLES.read_text(encoding="utf-8"))["regles"]
    g = graphe(regles)
    SORTIE_JSON.write_text(json.dumps(g, ensure_ascii=False, indent=1), encoding="utf-8")
    SORTIE_MD.write_text(lecture(g), encoding="utf-8")
    print(lecture(g)[:1800])
    return 0


if __name__ == "__main__":
    sys.exit(principal())
