"""Banc du graphe des questions : les erreurs récentes de S sur la même entité, en correction finale à porte (0.10.305).

Décision d'auteur du 2026-11-19, 1 h 22. Idée : GraFT (Pham et al., Spatial-as-Refinement). Préenregistrement :
preenregistrements/graphe-questions.md. Aucun appel à un modèle, aucune cote, aucune clé.

    python banc_graphe_questions.py
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import alphabet_pipeline as ap
import banc_jugement as bj
import banc_porte as bp
import banc_wikipedia as bw

RESUME = Path("registre/banc-graphe-questions.json")
FENETRE_JOURS = 180
K = 3
GRILLE_ALPHA = [round(-2 + 0.2 * i, 1) for i in range(31)]


def une_par_question(xs: list[dict]) -> list[dict]:
    vus, out = set(), []
    for x in sorted(xs, key=lambda x: x["jeu"]):
        k = f'{x["source"]}:{x["id"]}'
        if k not in vus:
            vus.add(k)
            out.append(x)
    return out


def corrections(xs: list[dict]) -> list[dict]:
    """Ajoute à chaque question c (erreurs récentes de S sur ses entités) et n (nombre de voisines)."""
    ent = [set(bw.entites(x["titre"])) for x in xs]
    fin = [max(x["resolue_le"], x.get("cloture", "")) for x in xs]
    index: dict[str, list[int]] = {}
    for j, es in enumerate(ent):
        for e in es:
            index.setdefault(e, []).append(j)
    out = []
    for i, x in enumerate(xs):
        debut = (date.fromisoformat(x["jeu"][:10]) - timedelta(days=FENETRE_JOURS)).isoformat()
        cle = f'{x["source"]}:{x["id"]}'
        voisines = {j for e in ent[i] for j in index[e]
                    if f'{xs[j]["source"]}:{xs[j]["id"]}' != cle and debut <= fin[j] < x["jeu"]}
        r = sum(int(xs[j]["issue"]) - xs[j]["p_S"] for j in voisines)
        out.append({"question_id": f'{cle}:{x["jeu"]}', "source": x["source"], "issue": int(x["issue"]),
                    "p_S": x["p_S"], "n": len(voisines), "c": r / (len(voisines) + K)})
    return out


def resumer(ls: list[dict]) -> dict:
    import profil_erreurs as pe
    import score_registre as sr
    out = {"version_bot": ap.VERSION_BOT, "questions": len(ls), "avec_voisines": sum(1 for x in ls if x["n"]),
           "note": ("questions distinctes (première date de jeu), toutes années ; base S ; voisines = même entité, "
                    f"résolues dans les {FENETRE_JOURS} jours avant le jeu ; α appris sans la question jugée")}
    if len(ls) < 50:
        return dict(out, verdict="trop peu de questions")
    p, alpha, _ = bp.loo_porte(ls, "p_S", "c", GRILLE_ALPHA)
    avec = [(x, pp) for x, pp in zip(ls, p) if x["n"]]
    out.update({"perte_S": bp.perte(ls, "p_S"), "perte_corrigee": bp.perte(ls, ps=p), "alpha_sur_tout": alpha,
                "critere": sr.critere_ombre_b([dict(x, p_B=x["p_S"], o={"p": pp}) for x, pp in zip(ls, p)], "o",
                                              "graphe_questions", exclure_vus=False, bloc_par="question", tout_juger=True),
                "descriptif_questions_avec_voisines": {"n": len(avec),
                                                       "perte_S": bp.perte([x for x, _ in avec], "p_S"),
                                                       "perte_corrigee": bp.perte([x for x, _ in avec], ps=[pp for _, pp in avec])},
                "par_source": {s: {"n": len(v), "S": bp.perte([x for x, _ in v], "p_S"),
                                   "corrigee": bp.perte([x for x, _ in v], ps=[pp for _, pp in v])}
                               for s in sorted({x["source"] for x in ls})
                               for v in [[(x, pp) for x, pp in zip(ls, p) if x["source"] == s]]},
                "profils": pe.profils([dict(x, p_c=pp) for x, pp in zip(ls, p)], {"S": "p_S", "corrige": "p_c"}),
                "unites": pe.unites(ls)})
    return out


def donnees() -> list[dict]:
    xs = bj.cohorte_complete([json.loads(l) for l in bj.REGISTRE.read_text(encoding="utf-8").splitlines() if l.strip()])
    bj.calculer(xs)
    return corrections(une_par_question(xs))


def principal() -> int:
    r = resumer(donnees())
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
