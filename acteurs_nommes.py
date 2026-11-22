"""Acteurs nommés et leurs réseaux (ecosystemes/acteurs-nommes.yaml) (bot 0.10.444, ombre).

Décision de l'auteur du 2026-11-22 (7 h 41, 7 h 49) : à côté des mécanismes durables des fiches, les acteurs
conjoncturels nommés (dirigeants, patrons), leurs réseaux et ce qui les relie à la population. Le niveau d'un lien
(1 proche, 2 voisin, 3 éloigné) est la distance dans le graphe, calculée ici et sur la carte, jamais écrite à la main.
`python acteurs_nommes.py` valide et écrit registre/acteurs-nommes.md.
"""
from __future__ import annotations

import sys
from collections import deque
from pathlib import Path

import yaml

import ecosystemes as ec

FICHIER = Path("ecosystemes") / "acteurs-nommes.yaml"
SORTIE = Path("registre") / "acteurs-nommes.md"
SORTES = {"dirigeant", "patron", "autre"}
ENTRE_ACTEURS = {"nomme", "commande", "allie", "rival", "negocie_avec", "finance", "associe", "fournit", "desaccord_public", "proche"}
VERS_POPULATION = {"gouverne", "elu_par", "informe", "influence_documentee"}
LECTURES = {"lu", "titre"}
NIVEAUX = {1: "proche", 2: "voisin", 3: "éloigné"}


def charger(f: Path = FICHIER) -> dict:
    return yaml.safe_load(f.read_text(encoding="utf-8")) or {}


def valider(d: dict | None = None, fiches: dict | None = None) -> list[str]:
    d = d if d is not None else charger()
    fiches = fiches if fiches is not None else ec.charger()
    comps = {f"{t}:{c['id']}" for t, x in fiches.items() for c in x.get("compartiments") or []}
    err, ids = [], set()
    def sources(x, qui):
        ss = x.get("sources") or []
        if not any(isinstance(s, dict) and s.get("url") for s in ss):
            err.append(f"{qui} : aucune source avec adresse")
        for s in ss:
            if isinstance(s, dict) and s.get("lecture") not in LECTURES:
                err.append(f"{qui} : lecture de la source manquante ou inconnue ({s.get('lecture')!r})")
    for a in d.get("acteurs") or []:
        i = a.get("id", "?")
        if i in ids:
            err.append(f"{i} : identifiant en double")
        ids.add(i)
        for k in ("nom", "role", "depuis", "cycle"):
            if not a.get(k):
                err.append(f"{i} : {k} manquant")
        if a.get("sorte") not in SORTES:
            err.append(f"{i} : sorte inconnue")
        if not a.get("compartiments"):
            err.append(f"{i} : aucun compartiment de rattachement")
        for c in a.get("compartiments") or []:
            if c not in comps:
                err.append(f"{i} : compartiment inconnu {c}")
        sources(a, i)
    lids = set()
    for l in d.get("liens") or []:
        i = l.get("id", "?")
        if i in lids:
            err.append(f"lien {i} : identifiant en double")
        lids.add(i)
        if l.get("de") not in ids:
            err.append(f"lien {i} : acteur inconnu {l.get('de')}")
        r = l.get("relation")
        if r in ENTRE_ACTEURS:
            if l.get("vers") not in ids:
                err.append(f"lien {i} : acteur inconnu {l.get('vers')}")
        elif r in VERS_POPULATION:
            if l.get("vers") not in comps:
                err.append(f"lien {i} : compartiment inconnu {l.get('vers')}")
        else:
            err.append(f"lien {i} : relation inconnue {r!r}")
        if not l.get("domaine"):
            err.append(f"lien {i} : domaine manquant")
        t = l.get("temps") or {}
        if t.get("statut") not in ("structurel", "conjoncturel"):
            err.append(f"lien {i} : temps.statut manquant")
        if t.get("statut") == "conjoncturel" and not (t.get("cycle") and t.get("phase")):
            err.append(f"lien {i} : conjoncturel sans cycle ou phase")
        sources(l, f"lien {i}")
    return err


def niveaux(d: dict, depart: str, max_: int = 3) -> dict[str, int]:
    """Distance (1 proche, 2 voisin, 3 éloigné) de chaque acteur à `depart`, liens entre acteurs pris dans les deux sens."""
    voisins: dict[str, set[str]] = {}
    for l in d.get("liens") or []:
        if l.get("relation") in ENTRE_ACTEURS:
            voisins.setdefault(l["de"], set()).add(l["vers"])
            voisins.setdefault(l["vers"], set()).add(l["de"])
    dist, file = {depart: 0}, deque([depart])
    while file:
        x = file.popleft()
        if dist[x] >= max_:
            continue
        for y in voisins.get(x, ()):
            if y not in dist:
                dist[y] = dist[x] + 1
                file.append(y)
    dist.pop(depart)
    return dist


def principal() -> int:
    d = charger()
    err = valider(d)
    if err:
        print("\n".join(err))
        return 1
    noms = {a["id"]: a["nom"] for a in d["acteurs"]}
    L = ["# Acteurs nommés et leurs réseaux", "", "| Acteur | Rôle | Depuis | Proches (1) | Voisins (2) | Éloignés (3) |", "|---|---|---|---|---|---|"]
    for a in d["acteurs"]:
        n = niveaux(d, a["id"])
        L.append(f"| {a['nom']} | {a['role']} | {a['depuis']} | " + " | ".join(", ".join(sorted(noms[x] for x, k in n.items() if k == j)) or "—" for j in (1, 2, 3)) + " |")
    SORTIE.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"{len(d['acteurs'])} acteurs, {len(d.get('liens') or [])} liens valides")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
