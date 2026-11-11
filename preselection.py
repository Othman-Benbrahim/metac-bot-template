"""Présélection des cartes par plongement multilingue, EN OMBRE (bot 0.10.15).

Un modèle de plongement léger et multilingue (fastembed, ONNX sur CPU, sans carte graphique ;
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, 384 dimensions) place la question (souvent en anglais)
et la définition de chacune des 16 cartes (en français, index du skill) dans un même espace ; les cartes sont rangées
par similarité cosinus. On enregistre au registre (bras C, clé `preselection`) les k premières, k étant le nombre de
cartes distinctes que le planificateur a retenues, et leur recouvrement avec ces cartes.

Rien ne change dans le plan ni dans la lecture : c'est une mesure. Si le recouvrement est durablement haut, une
présélection pourrait un jour réduire le coût ou l'arbitraire du plan ; si elle est basse, le planificateur voit autre
chose que le texte de la question (ou se trompe). L'adoption éventuelle passe par une décision d'auteur datée.
En cas d'échec (bibliothèque absente, modèle non téléchargeable), la clé vaut {"statut": "indisponible", "motif": …}.

Variables : ALPHABET_PRESELECTION ("1" par défaut dans le workflow, « 0 » l'éteint), ALPHABET_PLONGEMENT (modèle).
"""
from __future__ import annotations

import math
import os
from typing import Callable

import alphabet_pipeline as ap

MODELE = os.environ.get("ALPHABET_PLONGEMENT") or "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
ACTIVE = os.environ.get("ALPHABET_PRESELECTION", "0") in ("1", "oui", "true")

Plongeur = Callable[[list[str]], list[list[float]]]
_PLONGEUR: dict = {}


def plongeur_fastembed() -> Plongeur:
    """Chargé une fois par processus. Lève une exception si fastembed ou le modèle manque."""
    if "f" not in _PLONGEUR:
        from fastembed import TextEmbedding
        modele = TextEmbedding(MODELE)
        _PLONGEUR["f"] = lambda textes: [list(map(float, v)) for v in modele.embed(textes)]
    return _PLONGEUR["f"]


def textes_cartes() -> dict[str, str]:
    """{abréviation : « NOM : définition (structure) »} d'après cartes-index.md (sans voisines ni matrice)."""
    import reconstruction_matrice as rm
    m = ap._moteur()
    out = {}
    for d in rm.definitions():
        try:
            c = m.carte_id(d["carte"])
        except ValueError:
            continue
        out[c] = f"{m.NOMS[c]} : {d['definition']} ({d['structure']})"
    return out


def _cos(a: list[float], b: list[float]) -> float:
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
    return sum(x * y for x, y in zip(a, b)) / (na * nb) if na and nb else 0.0


def cartes_du_plan(plan: dict) -> list[str]:
    m = ap._moteur()
    out = set()
    for k in list(plan.get("candidats") or []) + list(plan.get("contre_candidate") or []):
        try:
            out.add(m.carte_id(str(k).split("@")[0]))
        except ValueError:
            continue
    return sorted(out)


def preselectionner(q: ap.Question, plan: dict, plongeur: Plongeur | None = None) -> dict:
    try:
        plongeur = plongeur or plongeur_fastembed()
        cartes = textes_cartes()
        noms = sorted(cartes)
        question = f"{q.titre}\n{(q.criteres or '')[:600]}"
        vecs = plongeur([question] + [cartes[c] for c in noms])
        if len(vecs) != len(noms) + 1:
            raise ValueError("nombre de vecteurs inattendu")
    except Exception as e:  # ombre : jamais bloquante
        return {"statut": "indisponible", "modele": MODELE, "motif": f"{type(e).__name__}: {e}"[:200]}
    sims = {c: _cos(vecs[0], v) for c, v in zip(noms, vecs[1:])}
    rang = sorted(noms, key=lambda c: -sims[c])
    choisies = cartes_du_plan(plan)
    k = max(1, len(choisies)) if choisies else 5
    top = rang[:k]
    communes = set(top) & set(choisies)
    m = ap._moteur()
    ev = None
    try:
        ev = m.carte_id(str((plan.get("evenement") or {}).get("carte")))
    except ValueError:
        pass
    return {"statut": "calcule", "modele": MODELE, "k": k, "top_k": top,
            "similarites": {c: round(sims[c], 4) for c in rang},
            "cartes_du_plan": choisies, "communes": sorted(communes),
            "recouvrement": round(len(communes) / len(choisies), 4) if choisies else None,
            "jaccard": round(len(communes) / len(set(top) | set(choisies)), 4) if choisies else None,
            "rangs_du_plan": {c: rang.index(c) + 1 for c in choisies},
            "rang_evenement": (rang.index(ev) + 1) if ev in rang else None}
