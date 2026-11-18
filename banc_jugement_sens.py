"""Questions semblables trouvées par le SENS (embeddings) plutôt que par les mots (TF-IDF) — bot 0.10.259, en ombre.

Décision d'auteur du 2026-11-18, 12 h 20 (« c'est de l'ingénierie, ça ne coûte rien, et ça pourrait nous permettre de
gagner en fluidité ») après lecture du dépôt lioneldreyfuss-ui/recherche_semantique (recherche par le sens avec un
petit modèle d'embeddings sur processeur). Préenregistrement : preenregistrements/jugement-sens.md.

Aucun modèle de langue génératif, aucun appel payant : un modèle d'embeddings local (BAAI/bge-small-en-v1.5, 384
dimensions, ONNX via fastembed ; les titres ForecastBench sont en anglais). Même registre, même cohorte complète,
mêmes règles anti-fuite que banc_jugement (voisines closes et résolues avant le jeu), même algorithme que p_S : les 50
voisines les plus proches, pondérées par leur similarité (bornée à 0), ramenées vers R1 (M = 5). Seule change la
mesure de ressemblance.

    uv run --with fastembed==0.9.1 python banc_jugement_sens.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import banc_jugement as bj
import combinaisons as cb

MODELE = "BAAI/bge-small-en-v1.5"
SORTIE = Path("registre/banc-jugement-sens.json")


def vecteurs(titres: list[str]):
    import numpy as np
    from fastembed import TextEmbedding
    m = TextEmbedding(MODELE)
    v = np.array(list(m.embed(titres, batch_size=256)), dtype=np.float32)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def calculer_sens(xs: list[dict], V) -> None:
    """p_SE : même calcul que p_S (banc_jugement.calculer, déjà appelé), ressemblance = cosinus des embeddings."""
    import numpy as np
    res = np.array([max(x["resolue_le"], x.get("cloture", "")) for x in xs])
    ids = np.array([f'{x["source"]}:{x["id"]}' for x in xs])
    y = np.array([x["issue"] for x in xs], dtype=float)
    for i, x in enumerate(xs):
        ok = (res < x["jeu"]) & (ids != ids[i])
        if ok.sum() == 0:
            x["p_SE"] = x["p_R1"]
            continue
        sims = (V[ok] @ V[i]).astype(float)
        idx = np.argsort(-sims, kind="stable")[:bj.K_VOISINES]
        w = np.clip(sims[idx], 0, None)
        x["p_SE"] = float((w @ y[ok][idx] + bj.M * x["p_R1"]) / (w.sum() + bj.M))
        x["sim_max_sens"] = round(float(sims[idx[0]]), 3)


def comparer(s: list[dict], risque: float) -> dict:
    if not s:
        return {"n": 0}
    pm = lambda k: round(sum(cb.pl(x[k], x["issue"]) for x in s) / len(s), 4)
    e = [(f'{x["source"]}:{x["id"]}', cb.pl(x["p_SE"], x["issue"]) - cb.pl(x["p_S"], x["issue"])) for x in s]
    bas, haut = cb.bootstrap(e, risque)
    return {"n": len(s), "perte_R1": pm("p_R1"), "perte_S_mots": pm("p_S"), "perte_SE_sens": pm("p_SE"),
            "ecart_moyen": round(sum(v for _, v in e) / len(e), 4), "intervalle": [round(bas, 4), round(haut, 4)],
            "verdict": "sens meilleur" if haut < 0 else ("sens moins bon" if bas > 0 else "non tranché")}


def resumer(xs: list[dict]) -> dict:
    import essais as es
    conf = [x for x in xs if x["jeu"] >= bj.COUPURE]
    repl = [x for x in xs if x["jeu"] < bj.COUPURE]
    r = {"modele": MODELE, "questions": len(xs),
         "confirmation_2026": comparer(conf, es.risque_corrige(1)),
         "replique_2025": comparer(repl, 0.05),
         "par_source_2026": {so: comparer([x for x in conf if x["source"] == so], 0.05) for so in bj.SOURCES
                             if any(x["source"] == so for x in conf)},
         "note": "perte log, plus bas = mieux ; écart = sens − mots ; aucun modèle génératif"}
    c, p = r["confirmation_2026"], r["replique_2025"]
    r["verdict_final"] = ("sens retenu en ombre (critère atteint et même sens en 2025)"
                          if c.get("verdict") == "sens meilleur" and p.get("ecart_moyen", 1) < 0
                          else "sens non retenu")
    return r


def principal() -> int:
    xs = [json.loads(l) for l in bj.REGISTRE.read_text(encoding="utf-8").splitlines() if l.strip()]
    xs = bj.cohorte_complete(xs)
    bj.calculer(xs)
    calculer_sens(xs, vecteurs([x["titre"] for x in xs]))
    r = resumer(xs)
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    texte = json.dumps(r, ensure_ascii=False, indent=1)
    print(texte)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write("## Questions semblables : le sens contre les mots\n\n```\n" + texte + "\n```\n")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
