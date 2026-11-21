"""Carte de couverture : quelles RÈGLES SOURCÉES gouvernent les questions du banc de M (piste écosystémique).
Descriptif, rien dans le bot.

Historique : v1 (le modèle désignait une fiche) et v2 (il rédigeait une règle) inventaient toujours un rattachement ;
v3 (2026-11-21, 12 h 17 : il CHOISIT parmi les règles sourcées) a couvert 65 questions sur 119 mais avec environ 30 %
de rattachements pertinents à la relecture : le modèle se servait des règles comme d'un décor qui « influence »
l'issue (« Poutine restera au pouvoir, donc la rencontre reste possible », « la Fed influence le Bitcoin »).

v4 (décision de l'auteur du 2026-11-21, 12 h 43 : « je valide ») resserre par des choix fermés :
1. chaque règle sourcée porte un `objet` (l'événement qu'elle prédit) et un `perimetre` (pays ou régions, vocabulaire
   fermé de regles_coutumieres) ;
2. le modèle ne retient une règle que si l'événement de la question EST l'objet de la règle (identité, pas influence),
   et il recopie l'objet mot pour mot (le code rejette une copie inexacte) ;
3. il désigne les pays et régions en jeu dans une liste fermée ; le code rejette une règle hors périmètre ;
4. un identifiant à deux lettres près d'un identifiant réel est corrigé (faute de frappe) ; une invention reste rejetée.
Toute règle dont le texte cite une année de 2026 ou après est exclue en entier (les questions du banc datent de 2026).

    python couverture_regles.py
"""
from __future__ import annotations

import asyncio
import collections
import json
import re
import sys
from pathlib import Path

import alphabet_modeles as am
import alphabet_pipeline as ap
import banc_jugement_alphabet as bja
import regles_coutumieres as rc
from couverture_fiches import sans_dates_recentes

SORTIE = Path("registre") / "couverture-regles-banc-m-v4.json"     # la v3 reste à côté, pour comparer
MODELE = bja.MODELE
LONGUEUR = 300          # caractères de règle montrés par règle (l'objet décide, le texte éclaire)
VERSION = 4


def catalogue() -> dict[str, dict]:
    """id -> {ecosysteme, objet, perimetre, texte (sans faits de 2026 ou après), compartiments} ; règles sourcées."""
    out = {}
    for r in rc.regles():
        if r.get("statut") != "source":
            continue
        t = str(r.get("regle", ""))
        if sans_dates_recentes(t) != t.strip(" ;,"):   # la règle cite 2026 ou après : exclue en entier
            continue
        out[r["id"]] = {"ecosysteme": sans_dates_recentes(str(r.get("ecosysteme", ""))), "texte": t[:LONGUEUR],
                        "objet": str(r.get("objet", "")), "perimetre": list(r.get("perimetre") or ["monde"]),
                        "compartiments": r.get("compartiments") or []}
    return out


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "").replace("’", "'").replace("‑", "-")).strip(" .").lower()


def corriger_id(i: str, cat: dict) -> str | None:
    """Identifiant exact, ou à deux caractères près d'un seul identifiant réel (faute de frappe) ; sinon None."""
    if i in cat:
        return i
    proches = [k for k in cat if _distance(i, k) <= 2]
    return proches[0] if len(proches) == 1 else None


def _distance(a: str, b: str) -> int:
    if abs(len(a) - len(b)) > 2:
        return 3
    prec = list(range(len(b) + 1))
    for x, ca in enumerate(a, 1):
        cur = [x]
        for y, cb in enumerate(b, 1):
            cur.append(min(prec[y] + 1, cur[y - 1] + 1, prec[y - 1] + (ca != cb)))
        prec = cur
    return prec[-1]


def dans_perimetre(perimetre: list[str], pays: list[str], regions: list[str]) -> bool:
    if "monde" in perimetre:
        return True
    zones = set(regions) | set(pays) | {rc.PAYS[p] for p in pays if p in rc.PAYS}
    return bool(zones & set(perimetre))


def valider(r: dict, cat: dict) -> tuple[list[str], list[dict]]:
    """Règles gardées et rejets motivés, d'après la réponse du modèle."""
    pays = [p for p in (r.get("pays") or []) if p in rc.PAYS]
    regions = [x for x in (r.get("regions") or []) if x in rc.REGIONS]
    gardes, rejets = [], []
    for c in (r.get("regles") or [])[:3]:
        brut = str((c or {}).get("id", ""))
        i = corriger_id(brut, cat)
        if i is None:
            rejets.append({"id": brut, "motif": "identifiant inconnu"})
        elif (c or {}).get("est_l_objet") is not True:
            rejets.append({"id": i, "motif": "l'événement de la question n'est pas l'objet de la règle"})
        elif _norm(c.get("objet")) != _norm(cat[i]["objet"]):
            rejets.append({"id": i, "motif": "objet mal recopié"})
        elif not dans_perimetre(cat[i]["perimetre"], pays, regions):
            rejets.append({"id": i, "motif": f"hors périmètre ({cat[i]['perimetre']} ; question : {pays or regions})"})
        elif i not in gardes:
            gardes.append(i)
    return gardes, rejets


def consigne(titre: str, cat: dict[str, dict]) -> str:
    liste = "\n".join(f"- {i}\n  OBJET : {v['objet']}\n  périmètre : {', '.join(v['perimetre'])}\n  règle : {v['texte']}"
                      for i, v in cat.items())
    pays = ", ".join(rc.PAYS)
    regions = ", ".join(sorted(rc.REGIONS - {"monde"}))
    return f"""Voici une question de prévision et une liste de règles tirées de sources vérifiées. Chaque règle a un OBJET :
l'événement qu'elle prédit.

Règles strictes :
1. Dis d'abord quel est l'événement dont dépend la réponse à la question (une phrase).
2. Retiens une règle SEULEMENT si cet événement EST l'objet de la règle (même type d'événement). Une règle dont l'objet
   ne fait qu'influencer, permettre ou entourer l'événement ne compte pas. Exemples de rejets : une règle sur le
   maintien des dirigeants pour une question de rencontre entre dirigeants ; une règle sur les décisions de la banque
   centrale pour une question de prix du Bitcoin.
3. Pour chaque règle retenue, recopie son OBJET mot pour mot et mets "est_l_objet": true.
4. Au plus 3 règles. Si aucune règle n'a pour objet l'événement de la question, rends une liste vide : c'est une
   réponse normale et fréquente.
5. Indique les pays en jeu en les choisissant UNIQUEMENT dans cette liste (sinon liste vide) : {pays} ; et les
   régions en jeu UNIQUEMENT dans celle-ci : {regions}.

QUESTION : {titre}

RÈGLES :
{liste}

Rends UNIQUEMENT un objet JSON :
{{"evenement": "une phrase", "pays": [], "regions": [],
  "regles": [{{"id": "identifiant", "objet": "objet recopié", "est_l_objet": true}}]}}"""


async def principal() -> int:
    cat = catalogue()
    qs = {}
    for x in bja.lignes():
        if x.get("p_M") is not None and not x.get("exclue"):
            qs[x["question_id"].split(":")[1]] = x          # une ligne par question distincte
    print(f"{len(cat)} règles sourcées ; {len(qs)} questions distinctes du banc de M.")
    out = []
    for qid, x in sorted(qs.items()):
        try:
            r = ap.extraire_json(await am.llm(MODELE, temperature=0.2, timeout=180, allowed_tries=2).invoke(
                consigne(x["titre"], cat)))
            gardes, rejets = valider(r, cat)
            out.append({"question": qid, "titre": x["titre"], "issue": x["issue"], "evenement": str(r.get("evenement", ""))[:300],
                        "pays": r.get("pays") or [], "regions": r.get("regions") or [], "regles": gardes, "rejets": rejets,
                        "compartiments": sorted({c for i in gardes for c in cat[i]["compartiments"]})})
        except Exception as e:
            out.append({"question": qid, "titre": x["titre"], "erreur": f"{type(e).__name__}"})
    compte = collections.Counter(i for o in out for i in o.get("regles", []))
    motifs = collections.Counter(j["motif"].split(" (")[0] for o in out for j in o.get("rejets", []))
    res = {"version_bot": ap.VERSION_BOT, "version_selection": VERSION, "regles_au_catalogue": len(cat),
           "questions": len(out), "couvertes": sum(1 for o in out if o.get("regles")),
           "erreurs": sum(1 for o in out if "erreur" in o), "rejets_par_motif": dict(motifs),
           "par_regle": dict(compte.most_common()), "detail": out}
    SORTIE.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"couvertes : {res['couvertes']} sur {len(out)} ; rejets : {dict(motifs)} ; par règle : {dict(compte.most_common())}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(principal()))
