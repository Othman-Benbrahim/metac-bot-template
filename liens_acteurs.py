"""Validation des liens propres aux acteurs (ecosystemes/liens-acteurs.yaml) (bot 0.10.387, ombre).

Chaque lien doit : désigner deux acteurs existants des fiches (« fiche:début du nom ») ; avoir une relation connue ;
un domaine ; un champ temps (structurel, ou conjoncturel avec cycle et phase) ; au moins une source avec adresse.
`python liens_acteurs.py` valide et écrit registre/liens-acteurs.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

FICHIER = Path("ecosystemes") / "liens-acteurs.yaml"
SORTIE = Path("registre") / "liens-acteurs.md"
RELATIONS = {"depend_de", "peut_bloquer", "nomme", "confirme", "ne_depend_pas_de"}


def liens() -> list[dict]:
    return (yaml.safe_load(FICHIER.read_text(encoding="utf-8")) or {}).get("liens") or []


def acteur_existe(ref: str) -> bool:
    fiche, _, debut = ref.partition(":")
    f = Path("ecosystemes") / f"{fiche}.yaml"
    if not f.exists():
        return False
    d = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
    return any(isinstance(a, dict) and a.get("nom", "").startswith(debut)
               for c in d.get("compartiments") or [] for a in c.get("acteurs") or [])


def valider() -> list[str]:
    err, ids = [], set()
    for l in liens():
        i = l.get("id", "?")
        if i in ids:
            err.append(f"{i} : identifiant en double")
        ids.add(i)
        for cote in ("de", "vers"):
            if not acteur_existe(str(l.get(cote))):
                err.append(f"{i} : acteur introuvable ({cote} = {l.get(cote)})")
        if l.get("relation") not in RELATIONS:
            err.append(f"{i} : relation inconnue")
        if not l.get("domaine"):
            err.append(f"{i} : domaine manquant")
        t = l.get("temps") or {}
        if t.get("statut") not in ("structurel", "conjoncturel"):
            err.append(f"{i} : temps.statut manquant")
        if t.get("statut") == "conjoncturel" and not (t.get("cycle") and t.get("phase")):
            err.append(f"{i} : conjoncturel sans cycle ou phase")
        if not any(s.get("url") for s in l.get("sources") or []):
            err.append(f"{i} : aucune source avec adresse")
    return err


def principal() -> int:
    err = valider()
    if err:
        print("\n".join(err))
        return 1
    L = ["# Liens propres aux acteurs", "", "| Lien | De | Relation | Vers | Domaine | Temps |", "|---|---|---|---|---|---|"]
    for l in liens():
        t = l["temps"]
        tt = t["statut"] + (f" ({t['cycle']} : {t['phase']})" if t["statut"] == "conjoncturel" else (f" depuis {t['depuis']}" if t.get("depuis") else ""))
        L.append(f"| {l['id']} | {l['de'].split(':')[1]} | {l['relation']} | {l['vers'].split(':')[1]} | {l['domaine']} | {tt} |")
    SORTIE.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"{len(liens())} liens valides")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
