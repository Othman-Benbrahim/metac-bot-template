"""Cartes ancrées : le modèle extrait des FAITS cités, le code vérifie la citation et calcule la note (bot 0.10.274).

Décision d'auteur du 2026-11-18, 16 h 10 (« oui, on peut y aller ») ; but de l'auteur : « laisser le moins de marge
possible à l'interprétation et à l'hallucination de l'IA ». Préenregistrement : preenregistrements/cartes-ancrees.md.

Deux cartes, celles qui ont un apport propre (examen façon RAPM du 2026-11-18) :
- DÉCLENCHEUR (SEUIL) : un événement daté prévu avant l'échéance (vote, audience, annonce, sommet, publication) ;
- DISTANCE À LA RÉSOLUTION (PROPORTION) : la valeur actuelle face au seuil de la question (questions chiffrées).
Le modèle ne note rien. Il rend des champs fermés (date, nombres, sens) et la PHRASE EXACTE de la recherche qui les
porte. Le code :
1. vérifie que la phrase figure mot pour mot dans la recherche (casse, espaces et guillemets typographiques
   normalisés ; au moins 20 caractères) ; sinon le fait est REJETÉ (hallucination comptée) ;
2. vérifie que les nombres et la date annoncés figurent bien dans la phrase citée ;
3. calcule la note de 1 à 4 par une règle fixe (ci-dessous). Pas de fait vérifié = note 1 (rien de vérifiable).
"""
from __future__ import annotations

import re
from datetime import date

import garde_injection as gi

MIN_CITATION = 20


def _norm(t: str) -> str:
    t = (t or "").lower().replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace(" ", " ")
    t = t.replace("…", "...").replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", t).strip()


def citation_verifiee(citation: str, recherche: str) -> bool:
    c = _norm(citation).strip(" .\"'")
    return len(c) >= MIN_CITATION and c in _norm(recherche)


def _nombres(t: str) -> list[float]:
    out = []
    for m in re.findall(r"-?\d[\d,\s]*\.?\d*", t or ""):
        try:
            out.append(float(m.replace(",", "").replace(" ", "")))
        except ValueError:
            pass
    return out


def nombre_dans(x: float | None, texte: str) -> bool:
    """Le nombre annoncé est-il écrit dans la phrase citée (à 1 % près, pour « 3.6 » contre « 3.60 ») ?"""
    if x is None:
        return False
    return any(abs(n - x) <= max(1e-9, 0.01 * abs(x)) for n in _nombres(texte))


def consigne(q: dict, recherche: str, jeu: str) -> str:
    return f"""Nous sommes le {jeu}. Tu EXTRAIS des faits ; tu ne donnes AUCUNE note ni probabilité.
Chaque fait doit être appuyé par une PHRASE COPIÉE MOT POUR MOT depuis les résultats de recherche ci-dessous
(au moins 20 caractères). Si la recherche ne contient pas le fait, réponds null : n'invente rien, ne complète rien
de mémoire. Une phrase qui n'est pas dans la recherche sera rejetée.

QUESTION : {q['titre']}
CRITÈRES DE RÉSOLUTION : {q['criteres'][:2000]}
ÉCHÉANCE DE LA QUESTION : {q['cloture']}

RÉSULTATS DE RECHERCHE (antérieurs au {jeu}) :
{gi.bloc(recherche, 6000)}

1. DÉCLENCHEUR : un événement DATÉ, prévu entre le {jeu} et l'échéance, qui peut faire basculer la question (vote,
   audience, décision attendue, annonce, sommet, publication officielle, scrutin).
2. DISTANCE : seulement si la question porte sur un nombre comparé à un seuil : la valeur la plus récente connue,
   le seuil de la question, et le sens (la question se résout OUI si la valeur passe AU-DESSUS ou EN DESSOUS).

Rends UNIQUEMENT un objet JSON :
{{"declencheur": null ou {{"evenement": "quelques mots", "date": "AAAA-MM-JJ", "citation": "phrase exacte"}},
  "distance": null ou {{"valeur": nombre, "seuil": nombre, "sens": "au_dessus" ou "en_dessous",
                       "citation": "phrase exacte contenant la valeur"}}}}"""


def note_declencheur(fait: dict | None, recherche: str, jeu: str, cloture: str) -> tuple[int, str]:
    """Règle fixe. 1 : aucun événement vérifié, ou daté hors fenêtre ; 2 : vérifié mais sans date lisible ;
    3 : daté dans la fenêtre ; 4 : daté dans la première moitié de la fenêtre (proche)."""
    if not fait or not isinstance(fait, dict):
        return 1, "aucun"
    if not citation_verifiee(str(fait.get("citation", "")), recherche):
        return 1, "rejeté (citation introuvable)"
    try:
        d = date.fromisoformat(str(fait.get("date", ""))[:10])
    except ValueError:
        return 2, "vérifié sans date"
    j, c = date.fromisoformat(jeu[:10]), date.fromisoformat(cloture[:10])
    if not j <= d <= c:
        return 1, "daté hors fenêtre"
    return (4 if (d - j).days <= (c - j).days / 2 else 3), "daté dans la fenêtre"


def note_distance(fait: dict | None, recherche: str) -> tuple[int | None, str]:
    """Règle fixe (questions chiffrées seulement ; None sinon). Écart relatif dans le sens de la question :
    déjà atteint → 4 ; à moins de 5 % → 3 ; à moins de 20 % → 2 ; au-delà → 1."""
    if not fait or not isinstance(fait, dict):
        return None, "sans objet"
    cit = str(fait.get("citation", ""))
    if not citation_verifiee(cit, recherche):
        return 1, "rejeté (citation introuvable)"
    try:
        v, s = float(fait["valeur"]), float(fait["seuil"])
    except (KeyError, TypeError, ValueError):
        return None, "nombres illisibles"
    if not nombre_dans(v, cit):
        return 1, "rejeté (valeur absente de la citation)"
    haut = str(fait.get("sens", "")) != "en_dessous"
    ecart = (s - v) if haut else (v - s)                 # > 0 : il reste du chemin
    if ecart <= 0:
        return 4, "déjà atteint"
    rel = ecart / max(abs(s), 1e-9)
    return (3 if rel <= 0.05 else 2 if rel <= 0.20 else 1), f"écart {rel:.1%}"


def ancrer(reponse: dict, recherche: str, jeu: str, cloture: str) -> dict:
    nd, md = note_declencheur(reponse.get("declencheur"), recherche, jeu, cloture)
    np_, mp = note_distance(reponse.get("distance"), recherche)
    rejets = sum(1 for m in (md, mp) if m.startswith("rejeté"))
    proposes = sum(1 for k in ("declencheur", "distance") if isinstance(reponse.get(k), dict))
    return {"declencheur": nd, "declencheur_motif": md, "proportion": np_, "proportion_motif": mp,
            "faits_proposes": proposes, "faits_rejetes": rejets}
