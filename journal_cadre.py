"""Cadre écosystémique + lecture du bot, sur le journal d'ombre (bot 0.10.380, ombre).

Préenregistrement : preenregistrements/journal-cadre.md (essai journal_cadre, ouvert le jour du lancement seulement).
Le bot ne poste rien sur Metaculus (décision de l'auteur) ; ses prévisions binaires d'ombre sont scellées dans
registre/journal-bot.jsonl et leurs issues relevées par score_registre.py (registre/issues.jsonl). Ici : la lecture
du bot (bras A, modèle de langue avec recherche) mise en commun avec le point de départ structurel (p_S, questions
semblables du registre, calculé avec les seules questions résolues avant la date d'information), à poids égaux en
log-cotes, SANS aucun ajustement sur les issues.

0.10.383 (décision de l'auteur, 2026-11-20, 11 h 37, avant toute résolution) : suivi SÉQUENTIEL valable à tout instant
(e-processus par pari, Waudby-Smith et Ramdas, JRSS B 2024). On peut regarder après chaque résolution sans gonfler le
risque : le cadre est déclaré utile dès que la richesse du pari atteint 1/α (α = risque corrigé du jour) ; le suivi
s'arrête sans verdict positif à MAX_QUESTIONS questions résolues.

    python journal_cadre.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import score_registre as sr

REG = Path("registre")
SORTIE = REG / "test-journal-cadre.json"
MAX_QUESTIONS = 100                     # arrêt du suivi sans verdict positif
BORNE = 0.01                            # probabilités bornées à [0,01 ; 0,99] pour le pari : |écart de perte| ≤ ln 99
POIDS_CADRE = 0.5                       # fixé d'avance : poids égaux, aucun réglage


def lg(p: float) -> float:
    p = min(0.999, max(0.001, p))
    return math.log(p / (1 - p))


def commun(p_bot: float, p_cadre: float, w: float = POIDS_CADRE) -> float:
    return 1 / (1 + math.exp(-((1 - w) * lg(p_bot) + w * lg(p_cadre))))


def e_processus(ecarts: list[float], alpha: float) -> dict:
    """Pari contre H0 « la mise en commun n'améliore pas le bot » (espérance de l'écart de perte ≥ 0). Chaque écart
    d = perte(commun) − perte(bot) est ramené à x = −d / B dans [−1, 1] ; richesse K = Π (1 + λ·x), λ prévisible
    (calculé sur les écarts précédents seulement, borné à [0 ; 0,5]). Sous H0, K est une sur-martingale positive :
    P(K atteint un jour 1/α) ≤ α (inégalité de Ville), quel que soit le moment où l'on regarde."""
    B = math.log((1 - BORNE) / BORNE)
    k, xs, trajet = 1.0, [], []
    for d in ecarts:
        if xs:
            m = sum(xs) / len(xs)
            v = sum((x - m) ** 2 for x in xs) / len(xs)
            lam = min(0.5, max(0.0, m / (v + m * m))) if (v + m * m) > 0 else 0.0
        else:
            lam = 0.0
        x = max(-1.0, min(1.0, -d / B))
        k *= 1 + lam * x
        xs.append(x)
        trajet.append(round(k, 4))
    seuil = 1 / alpha
    atteint = next((i + 1 for i, w in enumerate(trajet) if w >= seuil), None)
    return {"richesse": trajet[-1] if trajet else 1.0, "seuil": round(seuil, 2), "atteint_a": atteint, "trajet": trajet}


def questions() -> list[dict]:
    """Dernière ligne intacte par question, avec la probabilité du bras A et la date d'information."""
    par = {}
    for x in sr.lignes(REG):
        pa = ((x.get("bras") or {}).get("A") or {}).get("p")
        if x.get("_intacte") and pa is not None:
            par[x["question_id"]] = {"id": x["question_id"], "titre": x["titre"], "jeu": x["date_information"], "p_A": float(pa)}
    return list(par.values())


def cadre(qs: list[dict]) -> None:
    import banc_jugement as bj
    reg = [json.loads(l) for l in bj.REGISTRE.read_text(encoding="utf-8").splitlines() if l.strip()]
    reg = bj.cohorte_complete(reg)
    cibles = [{"source": "journal", "id": q["id"], "jeu": q["jeu"], "titre": q["titre"], "horizon": 30,
               "resolue_le": "9999-12-31", "cloture": "9999-12-31", "issue": 0} for q in qs]
    xs = reg + cibles                      # les cibles ne servent jamais de voisines (résolues « en 9999 »)
    bj.calculer(xs)
    for q, c in zip(qs, xs[len(reg):]):
        q["p_S"] = c["p_S"]


def principal() -> int:
    qs = questions()
    issues = sr.issues_enregistrees(REG)
    res = [q for q in qs if q["id"] in issues]
    if not res:
        print(json.dumps({"questions_binaires": len(qs), "resolues": 0, "statut": "en attente : aucune question résolue"},
                         ensure_ascii=False))
        return 0
    import banc_jugement as bj
    import essais as es
    cadre(res)
    borne = lambda p: min(1 - BORNE, max(BORNE, p))
    perte = lambda p, y: -math.log(borne(p) if y else 1 - borne(p))
    for q in res:
        q["issue"], q["p_C"] = issues[q["id"]], commun(q["p_A"], q["p_S"])
        q["fin"] = q.get("resolue_le") or ""
    res.sort(key=lambda q: (q["fin"], q["id"]))                         # ordre des résolutions
    res = res[:MAX_QUESTIONS]
    ec = [perte(q["p_C"], q["issue"]) - perte(q["p_A"], q["issue"]) for q in res]
    alpha = es.risque_corrige(1)
    e = e_processus(ec, alpha)
    pm = lambda k: round(sum(perte(q[k], q["issue"]) for q in res) / len(res), 4)
    verdict = ("le cadre améliore le bot (seuil du pari atteint)" if e["atteint_a"]
               else "non tranché (suivi arrêté à 100 questions)" if len(res) >= MAX_QUESTIONS else "suivi en cours")
    r = {"n": len(res), "perte": {"bot": pm("p_A"), "cadre": pm("p_S"), "commun": pm("p_C")},
         "ecart_moyen_commun_moins_bot": round(sum(ec) / len(ec), 4), "e_processus": e, "alpha": alpha, "verdict": verdict,
         "note": "perte log (probabilités bornées à [0,01 ; 0,99]), plus bas = mieux ; poids égaux fixés d'avance ; ombre"}
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
