"""Type d'inconnu de chaque compartiment des fiches (taxonomie de Smithson) — bot 0.10.366, ombre.

Décision d'auteur du 2026-11-19 (20 h 50). À côté de « mesuré / non mesuré », chaque compartiment dit QUEL type
d'inconnu le concerne. Deux sources :
- manuelle : ecosystemes/inconnus.yaml (types et raison, un fait ou une source) ;
- déduite : « absence » pour tout compartiment sans trace collectée (statut « collecte ») ni adaptateur.
Un compartiment marqué tabou ou indécidable se lit, il ne se mesure pas : aucune série ne doit lui être collée par
défaut. Sortie : registre/inconnus.md.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import yaml

import ecosystemes as ec

FICHIER = ec.DOSSIER / "inconnus.yaml"
SORTIE = Path("registre") / "inconnus.md"
TYPES = {"confusion", "inexactitude", "absence", "probabilite", "ambiguite", "flou", "conflictuel", "hors_sujet",
         "tabou", "indecidable"}
NE_SE_MESURENT_PAS = {"tabou", "indecidable"}


def manuels() -> dict[str, dict]:
    if not FICHIER.exists():
        return {}
    return (yaml.safe_load(FICHIER.read_text(encoding="utf-8")) or {}).get("compartiments") or {}


def valider(fiches: dict | None = None) -> list[str]:
    fiches = fiches or ec.charger(ec.DOSSIER)
    ids = {f"{t}:{c['id']}" for t, f in fiches.items() for c in f.get("compartiments", [])}
    err = []
    for cle, v in manuels().items():
        if cle not in ids:
            err.append(f"inconnus.yaml : compartiment inconnu {cle}")
        mauvais = set(v.get("types") or []) - TYPES
        if mauvais or not v.get("types"):
            err.append(f"inconnus.yaml : {cle} types invalides {sorted(mauvais) or 'vides'}")
        if not str(v.get("raison") or "").strip():
            err.append(f"inconnus.yaml : {cle} sans raison")
    return err


def mesure(c: dict) -> bool:
    return any(isinstance(t, dict) and (t.get("adaptateur") or t.get("statut") == "collecte") for t in c.get("traces") or [])


def table(fiches: dict | None = None) -> dict[str, dict]:
    fiches = fiches or ec.charger(ec.DOSSIER)
    man = manuels()
    out = {}
    for t, f in sorted(fiches.items()):
        for c in f.get("compartiments", []):
            cle = f"{t}:{c['id']}"
            types = list((man.get(cle) or {}).get("types") or [])
            if not mesure(c) and "absence" not in types:
                types.append("absence")
            out[cle] = {"types": types, "raison": (man.get(cle) or {}).get("raison", "déduit : aucune trace collectée"
                                                                           if types == ["absence"] else ""),
                        "mesure": mesure(c), "manuel": cle in man,
                        "conflit": mesure(c) and bool(set(types) & NE_SE_MESURENT_PAS)}
    return out


def principal() -> int:
    err = valider()
    if err:
        print("\n".join(err))
        return 1
    t = table()
    cpt = Counter(x for v in t.values() for x in v["types"])
    lignes = ["# Type d'inconnu par compartiment (Smithson)", "",
              f"{len(t)} compartiments ; " + ", ".join(f"{k} {n}" for k, n in cpt.most_common()) + ".", "",
              "Les entrées manuelles viennent d'`ecosystemes/inconnus.yaml` ; « absence » est déduite quand aucune trace "
              "n'est collectée. **À lire, pas à mesurer** : un compartiment tabou ou indécidable qui porte pourtant une "
              "série est signalé.", "", "| compartiment | types | mesuré | raison |", "|---|---|---|---|"]
    for k, v in t.items():
        if v["manuel"] or v["conflit"]:
            lignes.append(f"| `{k}` | {', '.join(v['types'])}{' ⚠' if v['conflit'] else ''} | {'oui' if v['mesure'] else 'non'} | {v['raison']} |")
    lignes += ["", f"Compartiments en absence déduite (aucune trace collectée) : {sum(1 for v in t.values() if v['types'] == ['absence'] and not v['manuel'])}."]
    SORTIE.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print("\n".join(lignes[:4]))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
