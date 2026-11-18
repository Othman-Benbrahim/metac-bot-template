"""Banc de la tendance de l'attention GDELT sur Metaculus seul, jugée sur les questions d'avant 2026 (bot 0.10.293).

Décision d'auteur du 2026-11-18, 20 h 52 (« oui, aux deux »). Préenregistrement : preenregistrements/tendance-metaculus.md.
Le banc à grande échelle (run 44383204002) a montré un gain sur Metaculus (−0,010), vu APRÈS coup. Il est donc rejugé
ailleurs : β est appris sur les questions Metaculus de 2026 (déjà vues), puis appliqué TEL QUEL aux questions Metaculus
d'avant 2026 (jamais utilisées). Aucun modèle, aucune cote.

    python banc_tendance_metaculus.py
"""
from __future__ import annotations

import json
from pathlib import Path

import alphabet_pipeline as ap
import banc_attention_gdelt as ba
import banc_tendance_large as btl
import gdelt_bq as gq

RESUME = Path("registre/banc-tendance-metaculus.json")


def beta_appris(ls: list[dict]) -> float:
    g = ba.GRILLE_BETA
    return min(g, key=lambda b: (sum(ba._pl(ba.ajuste_tendance(x["p_S"], x["tendance"], b), x["issue"]) for x in ls), abs(b)))


def resumer(apprentissage: list[dict], test: list[dict]) -> dict:
    import profil_erreurs as pe
    import score_registre as sr
    out = {"version_bot": ap.VERSION_BOT, "questions_apprentissage_2026": len(apprentissage), "questions_test": len(test),
           "test_avec_articles": sum(1 for x in test if x["articles"]),
           "note": "β appris sur Metaculus 2026, appliqué tel quel à Metaculus avant 2026 ; base S"}
    if len(test) < 30 or len(apprentissage) < 30:
        return dict(out, verdict="en attente (gdelt_bq.py --mode comptes_metaculus_2025)")
    beta = beta_appris(apprentissage)
    p = [ba.ajuste_tendance(x["p_S"], x["tendance"], beta) for x in test]
    n = len(test)
    out.update({"beta_appris_2026": beta,
                "perte_S": round(sum(ba._pl(x["p_S"], x["issue"]) for x in test) / n, 4),
                "perte_ajustee": round(sum(ba._pl(q, x["issue"]) for x, q in zip(test, p)) / n, 4),
                "critere": sr.critere_ombre_b([dict(x, p_B=x["p_S"], o={"p": q}) for x, q in zip(test, p)], "o",
                                              "tendance_metaculus", exclure_vus=False, bloc_par="question",
                                              tout_juger=True),
                "profils": pe.profils([dict(x, p_aj=q) for x, q in zip(test, p)], {"S": "p_S", "ajuste": "p_aj"}),
                "unites": pe.unites(test)})
    avec = [x for x in test if x["articles"]]
    if len(avec) >= 10:
        import psychometrie_alphabet as ps
        out["spearman_tendance_issue_test"] = round(ps.spearman([x["tendance"] for x in avec], [x["issue"] for x in avec]), 3)
    return out


def principal() -> int:
    appr = [x for x in btl.donnees(gq.COMPTES_JEU) if x["source"] == "metaculus"]
    test = [x for x in btl.donnees(gq.COMPTES_META_2025) if x["source"] == "metaculus"]
    r = resumer(appr, test)
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
