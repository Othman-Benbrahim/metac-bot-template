"""Chaînes de valeur des matières stratégiques (ecosystemes/chaines/*.yaml) (bot 0.10.388, ombre).

Cas d'école : le graphite (décision de l'auteur, 2026-11-20). Valide que chaque maillon a ses quatre axes, que chaque
variable a une valeur (ou « non renseigné »), une unité, un statut temporel et une source déclarée, que chaque lien
vers une fiche existe. `python chaines.py` valide et écrit registre/chaines.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

DOSSIER = Path("ecosystemes") / "chaines"
SORTIE = Path("registre") / "chaines.md"
AXES = ("espace", "temps", "vitesse", "taille")


def chaines() -> dict[str, dict]:
    return {f.stem: yaml.safe_load(f.read_text(encoding="utf-8")) for f in sorted(DOSSIER.glob("*.yaml"))}


def _compartiment_existe(ref: str) -> bool:
    fiche, _, comp = ref.partition(":")
    f = Path("ecosystemes") / f"{fiche}.yaml"
    return f.exists() and any(c.get("id") == comp for c in (yaml.safe_load(f.read_text(encoding="utf-8")) or {}).get("compartiments") or [])


def valider() -> list[str]:
    err = []
    for nom, c in chaines().items():
        src = set((c.get("sources") or {}).keys())
        for m in c.get("maillons") or []:
            if any(not (m.get("axes") or {}).get(a) for a in AXES):
                err.append(f"{nom}:{m.get('id')} : axe manquant")
            for v in m.get("variables") or []:
                if v.get("temps") not in ("structurel", "conjoncturel"):
                    err.append(f"{nom}:{m.get('id')} : {v.get('nom')} sans statut temporel")
                if v.get("source") not in src:
                    err.append(f"{nom}:{m.get('id')} : {v.get('nom')} sans source déclarée")
                if v.get("valeur") in (None, ""):
                    err.append(f"{nom}:{m.get('id')} : {v.get('nom')} sans valeur (écrire « non renseigné »)")
        for ref in c.get("liens_fiches") or []:
            if not _compartiment_existe(ref):
                err.append(f"{nom} : compartiment introuvable {ref}")
    return err


def principal() -> int:
    err = valider()
    if err:
        print("\n".join(err))
        return 1
    L = ["# Chaînes de valeur des matières stratégiques", ""]
    for nom, c in chaines().items():
        L += [f"## {c.get('nom', nom)}", "", "| Maillon | Espace | Temps | Vitesse | Taille | Variables | Bascules |", "|---|---|---|---|---|---|---|"]
        for m in c["maillons"]:
            a = m["axes"]
            L.append(f"| {m['nom']} | {a['espace']} | {a['temps']} | {a['vitesse']} | {a['taille']} | {len(m.get('variables') or [])} | {len(m.get('bascules') or [])} |")
        L += ["", "Lacunes : " + " ; ".join(c.get("lacunes") or ["aucune"]) + ".", ""]
    SORTIE.write_text("\n".join(L), encoding="utf-8")
    print(f"{len(chaines())} chaîne(s) valide(s)")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
