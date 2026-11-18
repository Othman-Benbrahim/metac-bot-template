"""Banc de la tendance de l'attention GDELT à grande échelle (bot 0.10.290).

Décision d'auteur du 2026-11-18, 19 h 53 (« le but c'est de grappiller ; à tester sur une plus grande échelle »).
Préenregistrement : preenregistrements/tendance-attention-large.md. Le premier banc (119 questions, M) allait dans le
sens attendu sans conclure. Ici : toutes les questions distinctes de 2026 du jeu de données (environ 890, quatre
plateformes), avec pour base le taux des semblables S (sans modèle). Aucun appel à un modèle, aucune cote.

    python banc_tendance_large.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import alphabet_pipeline as ap
import banc_attention_gdelt as ba
import banc_jugement as bj

COMPTES = Path("registre/gdelt-bq-comptes-jeu.json")
RESUME = Path("registre/banc-tendance-large.json")


def donnees(fichier: Path = COMPTES) -> list[dict]:
    cpt = json.loads(fichier.read_text(encoding="utf-8")) if fichier.exists() else {}
    xs = bj.cohorte_complete([json.loads(l) for l in bj.REGISTRE.read_text(encoding="utf-8").splitlines() if l.strip()])
    bj.calculer(xs)
    out = []
    for x in xs:
        qid = f'{x["source"]}:{x["id"]}:{x["jeu"]}'
        if qid not in cpt:
            continue                       # seule la première date de jeu de chaque question a ses comptes
        s = ba.serie(cpt[qid])
        out.append({"question_id": qid, "source": x["source"], "issue": x["issue"], "p_S": x["p_S"], "p_R1": x["p_R1"],
                    "articles": sum(s) if s else 0, "tendance": ba.tendance(s)})
    return sorted(out, key=lambda x: x["question_id"])


def loo(ls: list[dict], base: str) -> tuple[list[float], float]:
    """β appris sans la question jugée (grille −1 à 1, pas 0,05). Sommes précalculées : rapide sur ~900 questions."""
    g = ba.GRILLE_BETA
    pertes = [[ba._pl(ba.ajuste_tendance(x[base], x["tendance"], b), x["issue"]) for b in g] for x in ls]
    tot = [sum(col) for col in zip(*pertes)]
    out = []
    for x, pq in zip(ls, pertes):
        j = min(range(len(g)), key=lambda i: (tot[i] - pq[i], abs(g[i])))
        out.append(ba.ajuste_tendance(x[base], x["tendance"], g[j]))
    j_tout = min(range(len(g)), key=lambda i: (tot[i], abs(g[i])))
    return out, g[j_tout]


def resumer(ls: list[dict]) -> dict:
    import profil_erreurs as pe
    import score_registre as sr
    out = {"version_bot": ap.VERSION_BOT, "questions": len(ls), "avec_articles": sum(1 for x in ls if x["articles"]),
           "note": "questions distinctes de 2026 (première date de jeu) ; base S ; β appris sans la question jugée"}
    if len(ls) < 50:
        return dict(out, verdict="en attente (gdelt_bq.py --mode comptes_jeu)")
    avec = [x for x in ls if x["articles"]]
    import psychometrie_alphabet as ps
    out["spearman_tendance_issue"] = round(ps.spearman([x["tendance"] for x in avec], [x["issue"] for x in avec]), 3)
    for base in ("p_S", "p_R1"):
        p_aj, beta = loo(ls, base)
        n = len(ls)
        lignes = [dict(x, p_B=x[base], o={"p": p}) for x, p in zip(ls, p_aj)]
        out[f"base_{base[2:]}"] = {
            "perte_base": round(sum(ba._pl(x[base], x["issue"]) for x in ls) / n, 4),
            "perte_ajustee": round(sum(ba._pl(p, x["issue"]) for x, p in zip(ls, p_aj)) / n, 4),
            "beta_sur_tout": beta,
            "critere": sr.critere_ombre_b(lignes, "o", "tendance_attention_large", exclure_vus=False,
                                          bloc_par="question", tout_juger=True),
            "par_source": {s: {"n": len(v), "base": round(sum(ba._pl(x[base], x["issue"]) for x, _ in v) / len(v), 4),
                               "ajustee": round(sum(ba._pl(p, x["issue"]) for x, p in v) / len(v), 4)}
                           for s in sorted({x["source"] for x in ls})
                           for v in [[(x, p) for x, p in zip(ls, p_aj) if x["source"] == s]]},
            "profils": pe.profils([dict(x, p_aj=p) for x, p in zip(ls, p_aj)], {"base": base, "ajuste": "p_aj"})}
        if base == "p_S":
            out["critere_principal"] = out["base_S"]["critere"]
    out["unites"] = pe.unites(ls)
    return out


def principal() -> int:
    r = resumer(donnees())
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
