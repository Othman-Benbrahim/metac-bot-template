"""Décision d'une institution avant une échéance (preenregistrements/decision-institution.md, 2026-11-21).

Le modèle relève des faits datés (jamais une probabilité) ; le code les traduit en indicateurs et les combine à partir du
taux de départ des semblables par une régression logistique à a priori normal (0, 1).
"""
from __future__ import annotations

import hashlib
import math
import re

import numpy as np

MOTIF = re.compile(
    r"\b(senate|parliament|cabinet|council|court|congress|central bank|commission|government|ministry|minister|"
    r"house of representatives|assembly|federal reserve|fed|regulator|fda|ecb|approve|ratif|sign|pass|enact|agreement|"
    r"treaty|appoint|confirm|resign|impeach|legislat|bill)\b", re.I)
INDICATEURS = ("etape", "soutien", "regle", "confirmation_deux", "confirmation_une", "deja_decide")


def est_decision(titre: str, forme: str) -> bool:
    return forme != "election" and bool(MOTIF.search(titre or ""))


def consigne(q: dict, jeu: str, recherche: str, bloc) -> str:
    return f"""Nous sommes le {jeu}. Tu relèves des FAITS dans les recherches ci-dessous, pour une question sur une
décision d'institution. Tu NE DONNES PAS de probabilité. Un fait non trouvé dans les recherches = « inconnu ».

QUESTION : {q['titre']}
CRITÈRES DE RÉSOLUTION : {q['criteres'][:2500]}
CONTEXTE : {q['contexte'][:2500]}
ÉCHÉANCE : {q['cloture']}

RÉSULTATS DE RECHERCHE (antérieurs au {jeu}) :
{bloc(recherche, 6000)}

Relève :
- "etape_avant_echeance" : une séance, un vote, une réunion, une audience ou une signature capable de produire le OUI
  est-elle FIXÉE avant l'échéance ? "prevue" / "aucune" (on sait qu'il n'y en a pas) / "inconnu" ; et "date_etape".
- "regle" : qui doit dire oui ? "decideur_seul" / "majorite" / "majorite_qualifiee" / "consensus" / "deux_parties" /
  "inconnue".
- "soutien" : le soutien exigé par cette règle est-il acquis à la date du {jeu} (décideur favorable, majorité
  déclarée, les deux parties d'accord) ? "acquis" / "insuffisant" / "inconnu".
- "confirmation" : un accord ou une intention de faire est-il déclaré "les_deux" (par toutes les parties requises) /
  "une_partie" (par une seule) / "aucune" / "sans_objet" (une seule autorité décide).
- "deja_decide" : une décision qui suffit à résoudre la question par OUI est-elle déjà prise avant le {jeu} ?
  "oui" / "non" / "inconnu".
- "faits" : au plus trois faits cités, chacun avec sa date.
- "connait_issue" : true si tu connais déjà l'issue réelle de cette question.
Rends UNIQUEMENT un objet JSON avec ces clés."""


def indicateurs(f: dict) -> dict[str, float]:
    """Faits relevés → six indicateurs (0 = inconnu ou absent)."""
    g = lambda k: str(f.get(k) or "").strip().lower()
    return {"etape": {"prevue": 1.0, "aucune": -1.0}.get(g("etape_avant_echeance"), 0.0),
            "soutien": {"acquis": 1.0, "insuffisant": -1.0}.get(g("soutien"), 0.0),
            "regle": {"decideur_seul": 1.0, "consensus": -1.0, "deux_parties": -1.0}.get(g("regle"), 0.0),
            "confirmation_deux": 1.0 if g("confirmation") == "les_deux" else 0.0,
            "confirmation_une": 1.0 if g("confirmation") == "une_partie" else 0.0,
            "deja_decide": 1.0 if g("deja_decide") == "oui" else 0.0}


def utilisable(x: dict[str, float]) -> bool:
    return any(v != 0 for v in x.values())


def _logit(p: float) -> float:
    p = min(0.98, max(0.02, p))
    return math.log(p / (1 - p))


def ajuster(X: np.ndarray, y: np.ndarray, decalage: np.ndarray, sd: float = 1.0, iterations: int = 50) -> np.ndarray:
    """Maximum a posteriori d'une logistique à décalage fixe (logit p_S), a priori normal (0, sd²) ; Newton."""
    b = np.zeros(X.shape[1])
    for _ in range(iterations):
        p = 1 / (1 + np.exp(-(decalage + X @ b)))
        g = X.T @ (y - p) - b / sd ** 2
        H = -(X.T * (p * (1 - p))) @ X - np.eye(len(b)) / sd ** 2
        pas = np.linalg.solve(H, g)
        b = b - pas
        if np.max(np.abs(pas)) < 1e-8:
            break
    return b


def bloc_de(question_id: str, k: int = 10) -> int:
    return int(hashlib.sha1(question_id.encode()).hexdigest(), 16) % k


def validation_croisee(lignes: list[dict], k: int = 10) -> list[float]:
    """p prévu pour chaque ligne par le modèle ajusté sans son bloc. Lignes : p_S, issue, x (indicateurs), question_id."""
    X = np.array([[l["x"][i] for i in INDICATEURS] for l in lignes], dtype=float)
    y = np.array([l["issue"] for l in lignes], dtype=float)
    d = np.array([_logit(l["p_S"]) for l in lignes])
    blocs = np.array([bloc_de(l["question_id"], k) for l in lignes])
    out = np.zeros(len(lignes))
    for b in range(k):
        test = blocs == b
        if not test.any():
            continue
        beta = ajuster(X[~test], y[~test], d[~test])
        out[test] = 1 / (1 + np.exp(-(d[test] + X[test] @ beta)))
    return [float(min(0.98, max(0.02, p))) for p in out]


def coefficients(lignes: list[dict]) -> dict[str, float]:
    X = np.array([[l["x"][i] for i in INDICATEURS] for l in lignes], dtype=float)
    y = np.array([l["issue"] for l in lignes], dtype=float)
    d = np.array([_logit(l["p_S"]) for l in lignes])
    return {k: round(float(v), 3) for k, v in zip(INDICATEURS, ajuster(X, y, d))}
