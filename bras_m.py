"""Bras M du bot : l'alphabet en matriochka, posté sur les questions binaires de jugement (bot 0.10.253).

Décision d'auteur du 2026-11-18, 5 h 55 (« Oui, je valide »), après le banc des questions de jugement Metaculus
(claude/resultat-jugement-alphabet-2026-11-18.md) : sur 309 questions, M 0,362 contre A 0,381 et la foule 0,384, sans
atteindre le critère préenregistré (intervalle corrigé [−0,075 ; +0,031]). Adoption assumée par l'auteur : le pari est
favorable et le pire cas plausible est petit. Contrepartie : A reste calculé et scellé à côté (il l'est déjà, avant
toute carte), et une RÈGLE D'ARRÊT fixée d'avance (preenregistrements/m-officiel.md) : après 100 questions résolues où
M a été posté, si la perte log moyenne de M dépasse celle de A de plus de 0,03, on revient en arrière.

Ce que fait le bras M, exactement comme dans le banc (mêmes consignes, banc_jugement_alphabet) :
  1. un taux de départ : les questions semblables déjà résolues (TF-IDF sur le registre ForecastBench,
     registre/jugement-questions.jsonl, résolues avant aujourd'hui) ;
  2. sept notes séparées de 1 à 4, une par carte, sans probabilité ;
  3. le jugement final, qui voit le taux de départ, les notes et la recherche du bot.
Différences avec le banc, dites ici : le modèle est le modèle principal du bot (gpt-5-mini dans le banc) et la recherche
est celle du bot. Le bras M n'est pas posté quand B vient d'un compte calculé ou d'une vue fixée par un banc (les
taux calculés ont leurs propres essais) ; il ne remplace que A, et B tiré de la seule vue du modèle.
"""
from __future__ import annotations

import json
import math
from datetime import date
from functools import lru_cache

import alphabet_pipeline as ap
import banc_jugement as bj
import banc_jugement_alphabet as bja

POSTER_M = True
METHODES_GARDEES = ("compte_", "fixee")      # B calculé : M ne le remplace pas
SEUIL_ARRET, N_ARRET = 0.03, 100


@lru_cache(maxsize=1)
def _historique() -> tuple[dict, ...]:
    if not bj.REGISTRE.exists():
        return ()
    xs = [json.loads(l) for l in bj.REGISTRE.read_text(encoding="utf-8").splitlines() if l.strip()]
    return tuple(xs)


def semblables(titre: str, cloture: date, aujourdhui: date) -> float | None:
    """Taux de OUI des questions semblables résolues avant aujourd'hui (même calcul que p_S du banc)."""
    # cohorte complète (clôture passée depuis 30 jours) : la même parade au biais de censure que le banc
    hist = bj.cohorte_complete([dict(x) for x in _historique()], aujourdhui)
    if not hist:
        return None
    vive = {"source": "metaculus", "id": "__vive__", "jeu": aujourdhui.isoformat(), "titre": titre,
            "horizon": max(0, (cloture - aujourdhui).days), "resolue_le": "9999-12-31", "cloture": "9999-12-31",
            "issue": 0}
    xs = hist + [vive]
    bj.calculer(xs)
    return float(xs[-1]["p_S"])


async def prevoir_m(llm: ap.Llm, titre: str, criteres: str, contexte: str, cloture: date, recherche: str,
                    aujourdhui: date) -> dict:
    """Rend {"statut", "p_depart", "notes", "p", "raison"} ; statut « erreur » avec motif si une étape échoue."""
    try:
        p_b = semblables(titre, cloture, aujourdhui)
    except Exception as e:
        return {"statut": "erreur", "motif": f"semblables : {type(e).__name__}: {e}"[:300]}
    if p_b is None:
        return {"statut": "erreur", "motif": "registre des questions semblables absent"}
    q = {"titre": titre, "criteres": criteres or "", "contexte": contexte or "", "cloture": cloture.isoformat()}
    jeu = aujourdhui.isoformat()
    try:
        notes = bja.lire_notes(ap.extraire_json(await llm(bja.consigne_notes(q, p_b, recherche, jeu))))
        if len(notes) < 4:
            return {"statut": "erreur", "p_depart": round(p_b, 4), "motif": f"notes illisibles ({len(notes)} sur 7)"}
        r = ap.extraire_json(await llm(bja.consigne_finale(q, p_b, notes, recherche, jeu)))
        p = float(r["p"])
    except Exception as e:
        return {"statut": "erreur", "p_depart": round(p_b, 4), "motif": f"{type(e).__name__}: {e}"[:300]}
    if not 0 < p < 1:
        return {"statut": "erreur", "p_depart": round(p_b, 4), "notes": notes, "motif": f"probabilité hors bornes : {p}"}
    return {"statut": "estime", "p_depart": round(p_b, 4), "notes": notes, "p": round(min(0.99, max(0.01, p)), 4),
            "raison": str(r.get("raison", ""))[:500]}


def choisir_m(poste: str, p_poste: float, methode_b: str | None, m: dict | None) -> tuple[str, float]:
    """M remplace A, ou B tiré de la seule vue du modèle ; jamais un taux calculé."""
    if not POSTER_M or not m or m.get("statut") != "estime":
        return poste, p_poste
    if poste == "B" and str(methode_b or "").startswith(METHODES_GARDEES):
        return poste, p_poste
    if poste == "C":
        return poste, p_poste
    return "M", ap.borner(m["p"])


def texte_cartes(m: dict) -> str:
    """Les cartes dans le commentaire posté (en anglais, comme le reste du commentaire)."""
    noms = {"tendance": "GROWTH (recent trend)", "engagements": "RECIPROCITY (dated commitments)",
            "decideurs": "HIERARCHY (decision-makers)", "declencheur": "THRESHOLD (scheduled trigger)",
            "freins": "CONSTRAINT (obstacles; 4 = strong)", "duree": "PERIODICITY (time left vs. usual time)",
            "proportion": "PROPORTION (distance to resolution)"}
    lignes = ["Situational-alphabet cards, each scored separately from 1 to 4 before any probability "
              "(the scorer explains in French):"]
    for k, _, _ in bja.CRITERES:
        n = (m.get("notes") or {}).get(k)
        if n:
            lignes.append(f"- {noms[k]}: {n['note']}/4 — {n.get('pourquoi', '')}")
    return "\n".join(lignes)


def commentaire_m(p_A: float, m: dict, a_raison: str) -> str:
    return "\n".join([
        "Situational-alphabet bot. Posted arm: M, the alphabet as nested simple situations (\"matriochka\").",
        f"Starting point: share of YES among similar resolved questions: {m['p_depart']:.3f}.",
        texte_cartes(m),
        f"Final judgment from the starting point and the cards: {m['p']:.3f}. {m.get('raison', '')}",
        f"Arm A, model alone, sealed before the alphabet and NOT posted: {p_A:.3f}.",
        "Why M is posted: on 309 resolved Metaculus questions (pre-registered benchmark), M scored 0.362 in log loss "
        "against 0.381 for the model alone; the gain is not statistically established, so A is kept alongside and a "
        "pre-registered stop rule applies (author decision, 2026-11-18).",
        f"\nModel-alone reasoning:\n{a_raison}"])


def regle_arret(paires: list[tuple[float, float, int]]) -> dict:
    """paires (p_M, p_A, issue) des questions résolues où M a été posté."""
    pl = lambda p, y: -math.log(min(0.99, max(0.01, p)) if y else 1 - min(0.99, max(0.01, p)))
    n = len(paires)
    if not n:
        return {"n": 0, "verdict": f"en attente (0 sur {N_ARRET})"}
    ecart = sum(pl(m, y) - pl(a, y) for m, a, y in paires) / n
    out = {"n": n, "M": round(sum(pl(m, y) for m, _, y in paires) / n, 4),
           "A": round(sum(pl(a, y) for _, a, y in paires) / n, 4), "ecart_M_moins_A": round(ecart, 4)}
    if n < N_ARRET:
        out["verdict"] = f"en attente ({n} sur {N_ARRET})"
    else:
        out["verdict"] = ("ARRÊT : M derrière A de plus de 0,03 ; revenir en arrière (décision d'auteur à dater)"
                          if ecart > SEUIL_ARRET else "M maintenu")
    return out
