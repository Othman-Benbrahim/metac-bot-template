"""Évolution de notre recherche, semaine par semaine (décision de l'auteur du 2026-11-22, 3 h 33 - 3 h 38 : décrire
l'écosystème de la recherche par ce qui a été fixé et produit, daté, plutôt que par des états d'âme ; intégré à la fiche
« L'observateur et la mesure »). Tout vient de l'historique Git du dépôt, rien n'est jugé :

  - commits par semaine ; versions du bot citées (0.x.y) ;
  - préenregistrements créés (fichiers ajoutés dans preenregistrements/) ;
  - fiches d'écosystèmes créées ; scripts de mise au point créés ;
  - vocabulaire du projet : nombre de messages de commit qui citent chaque terme d'une liste FIXÉE ici (choisie par
    Claude d'après les messages eux-mêmes ; elle se complète par décision d'auteur), et pour chaque terme la semaine
    de première apparition.

Sortie : registre/recherche-evolution.json.

    python recherche_evolution.py
"""
from __future__ import annotations

import json
import re
import os
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

# 2026-11-24 : RECHERCHE_EVOLUTION_SORTIE permet au générateur de la carte d'écrire ailleurs que dans le registre (sinon
# chaque génération locale laissait le fichier du registre modifié dans le dépôt).
SORTIE = Path(os.environ.get("RECHERCHE_EVOLUTION_SORTIE", "registre/recherche-evolution.json"))
VOCABULAIRE = ["alphabet", "carte", "strate", "ombre", "bras", "banc", "préenregistrement", "règle", "écosystème",
               "fiche", "compartiment", "situation", "ontologie", "indice", "émetteur", "terme", "collecte",
               "sondage", "GDELT", "Metaculus", "tournoi", "calibr", "Brier", "logarithm", "bootstrap", "permutation",
               "Kalman", "seuil", "taux de base", "causalit", "intention", "réseau", "proxémie", "modèle de langue",
               "lecteur", "Wikidata", "BigQuery", "ERA5", "FRED", "Telegram", "cyber"]


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def semaine(d: str) -> str:
    y, w, _ = date.fromisoformat(d[:10]).isocalendar()
    return f"{y}-S{w:02d}"


def ajouts(dossier: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    jour = None
    for l in git("log", "--diff-filter=A", "--name-only", "--format=@%ad", "--date=short", "--", dossier).splitlines():
        if l.startswith("@"):
            jour = l[1:]
        elif l.strip() and jour:
            out[semaine(jour)].append(Path(l).name)
    return out


def principal() -> int:
    commits = [l.split("\t", 1) for l in git("log", "--format=%ad\t%s", "--date=short").splitlines() if "\t" in l]
    par_semaine: dict[str, dict] = defaultdict(lambda: {"commits": 0, "registre": 0, "versions": set(), "termes": Counter()})
    premiere: dict[str, str] = {}
    for d, msg in sorted(commits):
        s = semaine(d)
        x = par_semaine[s]
        if msg.startswith("registre :") or msg.startswith("registre:"):
            x["registre"] += 1                     # commits automatiques des collectes
            continue
        x["commits"] += 1
        x["versions"].update(re.findall(r"\b0\.\d+\.\d+\b", msg))
        bas = msg.lower()
        for t in VOCABULAIRE:
            if t.lower() in bas:
                x["termes"][t] += 1
                premiere.setdefault(t, s)
    prereg, fiches, mises = ajouts("preenregistrements"), ajouts("ecosystemes"), ajouts("mise_au_point")
    semaines = sorted(set(par_semaine) | set(prereg) | set(fiches))
    res = {"genere": date.today().isoformat(), "vocabulaire": VOCABULAIRE,
           "premiere_apparition": dict(sorted(premiere.items(), key=lambda kv: kv[1])),
           "semaines": [{"semaine": s, "commits": par_semaine[s]["commits"], "commits_de_collecte": par_semaine[s]["registre"],
                         "versions": sorted(par_semaine[s]["versions"], key=lambda v: [int(p) for p in v.split(".")])[-1:]
                         if par_semaine[s]["versions"] else [],
                         "preenregistrements_crees": prereg.get(s, []), "fiches_creees": fiches.get(s, []),
                         "mises_au_point_creees": len(mises.get(s, [])),
                         "termes": dict(par_semaine[s]["termes"].most_common())} for s in semaines]}
    SORTIE.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for s in res["semaines"]:
        print(s["semaine"], s["commits"], "commits ;", len(s["preenregistrements_crees"]), "préenregistrements ;",
              len(s["fiches_creees"]), "fiches ;", list(s["termes"])[:6])
    return 0


if __name__ == "__main__":
    sys.exit(principal())
