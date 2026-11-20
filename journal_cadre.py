"""Cadre écosystémique + lecture du bot, sur le journal d'ombre (bot 0.10.380, ombre).

Préenregistrement : preenregistrements/journal-cadre.md (essai journal_cadre, ouvert le jour du lancement seulement).
Le bot ne poste rien sur Metaculus (décision de l'auteur) ; ses prévisions binaires d'ombre sont scellées dans
registre/journal-bot.jsonl et leurs issues relevées par score_registre.py (registre/issues.jsonl). Ici : la lecture
du bot (bras A, modèle de langue avec recherche) mise en commun avec le point de départ structurel (p_S, questions
semblables du registre, calculé avec les seules questions résolues avant la date d'information), à poids égaux en
log-cotes, SANS aucun ajustement sur les issues. Le test ne se calcule qu'à partir de MIN_QUESTIONS questions
distinctes résolues ; en dessous, le script compte et s'arrête sans rien noter.

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
MIN_QUESTIONS = 100
POIDS_CADRE = 0.5                       # fixé d'avance : poids égaux, aucun réglage


def lg(p: float) -> float:
    p = min(0.999, max(0.001, p))
    return math.log(p / (1 - p))


def commun(p_bot: float, p_cadre: float, w: float = POIDS_CADRE) -> float:
    return 1 / (1 + math.exp(-((1 - w) * lg(p_bot) + w * lg(p_cadre))))


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
    if len(res) < MIN_QUESTIONS:
        print(json.dumps({"questions_binaires": len(qs), "resolues": len(res), "minimum": MIN_QUESTIONS,
                          "statut": "en attente : rien n'est noté"}, ensure_ascii=False))
        return 0
    import banc_jugement as bj
    import essais as es
    cadre(res)
    for q in res:
        q["issue"], q["p_C"] = issues[q["id"]], commun(q["p_A"], q["p_S"])
    pm = lambda k: round(sum(bj.cb.pl(q[k], q["issue"]) for q in res) / len(res), 4)
    ec = [(q["id"], bj.cb.pl(q["p_C"], q["issue"]) - bj.cb.pl(q["p_A"], q["issue"])) for q in res]
    bas, haut = bj.cb.bootstrap(ec, es.risque_corrige(1))
    r = {"n": len(res), "perte": {"bot": pm("p_A"), "cadre": pm("p_S"), "commun": pm("p_C")},
         "ecart_commun_moins_bot": round(sum(e for _, e in ec) / len(ec), 4), "intervalle_corrige": [round(bas, 4), round(haut, 4)],
         "verdict": "le cadre améliore le bot" if haut < 0 else "le cadre dégrade le bot" if bas > 0 else "non tranché",
         "note": "perte log, plus bas = mieux ; poids égaux fixés d'avance ; ombre"}
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
