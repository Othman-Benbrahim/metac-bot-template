"""Émotions dans la formulation des questions (EmoAtlas, Stella et al.) — bot 0.10.367, ombre.

Préenregistrement : preenregistrements/emotions-questions.md (essai emotions_questions). Deux temps :
1. `python emotions_questions.py --extraire` (environnement qui a emoatlas, spaCy 3.7 et en_core_web_sm 3.7.1 ; voir
   le workflow) : pour chaque question de la cohorte, les huit émotions de Plutchik repérées par EmoAtlas dans le TITRE
   seul, écrites dans registre/emotions-questions.jsonl avec les versions des outils (reproductible).
2. `python emotions_questions.py` (environnement du dépôt) : le recalibrage des semblables avec et sans ces traits,
   réappris à chaque jeu sur le seul passé admis, comme le banc de proxémie. Écrit registre/banc-emotions-questions.json.
Le côté « dit » seulement : la forme de la question renseigne sur son rédacteur (forçage, saillance), pas sur les faits.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

REG = Path("registre")
CACHE = REG / "emotions-questions.jsonl"
SORTIE = REG / "banc-emotions-questions.json"
EMOTIONS = ("anger", "fear", "sadness", "disgust", "surprise", "anticipation", "trust", "joy")


def cohorte() -> list[dict]:
    import banc_jugement as bj
    import banc_proxemie as bp
    xs = [json.loads(l) for l in bj.REGISTRE.read_text(encoding="utf-8").splitlines() if l.strip()]
    xs = [x for x in xs if not bp.COMBINEE.search(x.get("titre") or "")]
    return bj.cohorte_complete(xs)


def extraire() -> int:
    import emoatlas
    import spacy
    from emoatlas import EmoScores
    e = EmoScores(language="english", spacy_model="en_core_web_sm")
    vus = set()
    with CACHE.open("w", encoding="utf-8") as f:
        for x in cohorte():
            t = x["titre"]
            if t in vus:
                continue
            vus.add(t)
            z = e.zscores(t)
            f.write(json.dumps({"titre": t, **{k: float(z.get(k, 0)) for k in EMOTIONS},
                                "outils": f"emoatlas {getattr(emoatlas, '__version__', '0.1.6')} ; spacy {spacy.__version__} ; en_core_web_sm"},
                               ensure_ascii=False) + "\n")
    print(f"{len(vus)} titres analysés.")
    return 0


def traits(em: dict) -> list[float]:
    """Les scores d'EmoAtlas sont des écarts au hasard (z), parfois négatifs : seule la part positive (émotion plus
    présente que le hasard) compte."""
    p = {k: max(0.0, em[k]) for k in EMOTIONS}
    neg = p["anger"] + p["fear"] + p["sadness"] + p["disgust"]
    pos = p["trust"] + p["joy"] + p["anticipation"]
    return [math.log1p(neg), math.log1p(pos), math.log1p(p["surprise"])]


def evaluer() -> int:
    import banc_jugement as bj
    import banc_redacteur as br
    import essais as es
    cb = bj.cb
    em = {}
    for l in CACHE.read_text(encoding="utf-8").splitlines():
        if l.strip():
            d = json.loads(l)
            em[d["titre"]] = d
    xs = cohorte()
    bj.calculer(xs)
    xs = [x for x in xs if x["titre"] in em]
    lg = lambda p: math.log(min(0.98, max(0.02, p)) / (1 - min(0.98, max(0.02, p))))
    XP = np.array([[1.0, lg(x["p_S"])] for x in xs])
    XE = np.array([[1.0, lg(x["p_S"])] + traits(em[x["titre"]]) for x in xs])
    y = np.array([x["issue"] for x in xs], dtype=float)
    fin = np.array([max(x["resolue_le"], x.get("cloture", "")) for x in xs])
    for jeu in sorted({x["jeu"] for x in xs}):
        ok = fin < jeu
        cibles = [i for i, x in enumerate(xs) if x["jeu"] == jeu]
        if ok.sum() < 50 or len(set(y[ok])) < 2:
            for i in cibles:
                xs[i]["p_P"] = xs[i]["p_E"] = xs[i]["p_S"]
            continue
        wp, we = br.ajuster(XP[ok], y[ok]), br.ajuster(XE[ok], y[ok])
        for i in cibles:
            xs[i]["p_P"] = float(min(0.98, max(0.02, 1 / (1 + np.exp(-XP[i] @ wp)))))
            xs[i]["p_E"] = float(min(0.98, max(0.02, 1 / (1 + np.exp(-XE[i] @ we)))))
    conf = [x for x in xs if x["jeu"] >= bj.COUPURE]
    pm = lambda s, k: round(sum(cb.pl(x[k], x["issue"]) for x in s) / len(s), 4) if s else None
    ec = [(f'{x["source"]}:{x["id"]}', cb.pl(x["p_E"], x["issue"]) - cb.pl(x["p_P"], x["issue"])) for x in conf]
    bas, haut = cb.bootstrap(ec, es.risque_corrige(1))
    charge = lambda x: traits(em[x["titre"]])[0] > 0
    groupes = {"chargee_negatif": [x for x in conf if charge(x)], "neutre": [x for x in conf if not charge(x)]}
    av = [x for x in xs if max(x["resolue_le"], x.get("cloture", "")) < bj.COUPURE]
    w = br.ajuster(np.array([[1.0, lg(x["p_S"])] + traits(em[x["titre"]]) for x in av]), np.array([x["issue"] for x in av], dtype=float))
    r = {"n_confirmation": len(conf), "questions_distinctes": len({k for k, _ in ec}),
         "perte": {k: pm(conf, k) for k in ("p_S", "p_P", "p_E")},
         "ecart_E_moins_P": round(sum(e for _, e in ec) / len(ec), 4), "intervalle_corrige": [round(bas, 4), round(haut, 4)],
         "verdict": "les émotions aident" if haut < 0 else ("les émotions nuisent" if bas > 0 else "non tranché"),
         "descriptif": {g: {"n": len(v), "part_oui": round(sum(x["issue"] for x in v) / len(v), 3) if v else None,
                            "p_S_moyen": round(sum(x["p_S"] for x in v) / len(v), 3) if v else None,
                            "perte_P": pm(v, "p_P"), "perte_E": pm(v, "p_E")} for g, v in groupes.items()},
         "coefficients_avant_coupure": dict(zip(["constante", "logit_S", "charge_negative", "charge_positive", "surprise"],
                                                [round(float(v), 3) for v in w])),
         "risque_corrige": es.risque_corrige(1),
         "note": "perte log, plus bas = mieux ; titres seuls ; émotions EmoAtlas (Plutchik, lexique NRC) ; ombre"}
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--extraire", action="store_true")
    o = a.parse_args()
    sys.exit(extraire() if o.extraire else evaluer())
