"""Banc des questions de JUGEMENT : questions semblables déjà résolues contre le statu quo (bot 0.10.241, en ombre).

Décisions d'auteur du 2026-11-17 (20 h 33 à 20 h 53) : changer de terrain d'après le diagnostic des pertes
(claude/diagnostic-pertes-2026-11-17.md) ; mesurer d'abord ce que tout le monde fait (référence), puis ce qui peut
nous distinguer ; cadre validé à 20 h 53. Préenregistrement : preenregistrements/jugement-semblables.md.
Aucun modèle de langue ; gratuit.

Données : questions de jugement redistribuées par ForecastBench (sources metaculus, manifold, polymarket, infer ;
Forecasting Research Institute, CC BY-SA 4.0), RÉSOLUES (resolved = vrai, issue 0 ou 1), une ligne par (question,
jeu). La valeur au gel (prévision de la foule ou cote du marché) n'est JAMAIS une entrée ; elle n'est lue qu'à la fin,
pour situer la foule (descriptif), et n'est pas enregistrée.
Garde-fous : horizon = date de clôture prévue − date du jeu (la date RÉELLE de résolution, qui trahit l'issue, n'est
jamais utilisée sauf pour dire si une voisine était déjà résolue) ; une voisine ne compte que si elle était résolue avant
la date du jeu de la question jugée, et jamais la même question.

R0 : part de « oui » de la même plateforme (questions résolues avant le jeu), lissée (k + 1) / (n + 2).
R1 (la référence) : par plateforme × forme × horizon ; (k + 5·R0) / (n + 5). Formes, règles fixes sur le texte, dans
  cet ordre : élection, justice, seuil, échéance, autre. Horizons : ≤ 30 jours, 31-90, > 90.
SEMBLABLES (le candidat) : les 50 questions résolues les plus proches par le texte (TF-IDF des mots, cosinus), toutes
  plateformes, pondérées par le cosinus ; p = (Σ w·issue + 5·R1) / (Σ w + 5).
Jugement : perte log de SEMBLABLES − R1 sur les questions des jeux de 2026, bootstrap par question (une question
reposée dans plusieurs jeux forme un bloc), risque es.risque_corrige(1). Rapportés : R0, discrimination (moyenne de p
sur les « oui » − sur les « non »), par plateforme, et la foule (descriptif).

    python banc_jugement.py
"""
from __future__ import annotations

import asyncio
import json
import math
import os
import re
import sys
from datetime import date
from pathlib import Path

import combinaisons as cb

REGISTRE = Path("registre") / "jugement-questions.jsonl"
SORTIE = Path("registre") / "banc-jugement.json"
SOURCES = ("metaculus", "manifold", "polymarket", "infer")
COUPURE = "2026-01-01"
K_VOISINES = 50
M = 5.0
FORMES = [
    ("election", r"\b(win|wins|won|elected|election|elections|primary|nominee|nomination|vote share|seats|electoral|reelected|re-elected)\b"),
    ("justice", r"\b(court|courts|supreme court|judge|ruling|rule|convicted|indicted|indictment|sentenced|lawsuit|trial|plead|pardon)\b"),
    ("seuil", r"\b(above|below|more than|less than|greater than|at least|at most|exceed|exceeds|surpass|reach|reaches|higher than|lower than|over|under)\b|[\$%]"),
    ("echeance", r"\b(before|by)\b"),
]


def forme(titre: str) -> str:
    t = (titre or "").lower()
    for nom, rx in FORMES:
        if re.search(rx, t):
            return nom
    return "autre"


def tranche(h: int | None) -> str:
    return "?" if h is None else "<=30" if h <= 30 else "31-90" if h <= 90 else ">90"


async def recolter(depuis: date) -> tuple[list[dict], dict]:
    import banc_forecastbench as fb
    jeux = sorted(fb.jeux_candidats(date.today(), depuis, n_max=80))
    lignes, foule = {}, {}
    for j in jeux:
        try:
            qs = await fb._json(f"{fb.DEPOT}/question_sets/{j}-llm.json")
            rs = await fb._json(f"{fb.DEPOT}/resolution_sets/{j}_resolution_set.json")
        except Exception:
            continue
        par_id = {str(q["id"]): q for q in qs.get("questions", []) if q.get("source") in SOURCES}
        for r in rs.get("resolutions", []):
            q = par_id.get(str(r.get("id")))
            if not q or not r.get("resolved") or r.get("resolved_to") not in (0, 1, 0.0, 1.0):
                continue
            cle = (q["source"], str(q["id"]), j)
            fin = str(q.get("market_info_close_datetime") or "")[:10]
            try:
                h = (date.fromisoformat(fin) - date.fromisoformat(j)).days
            except ValueError:
                h = None
            res = str(r.get("resolution_date") or "")[:10]
            if cle not in lignes or res < lignes[cle]["resolue_le"]:
                lignes[cle] = {"source": q["source"], "id": str(q["id"]), "jeu": j, "titre": q.get("question", ""),
                               "horizon": h, "resolue_le": res, "issue": int(r["resolved_to"]),
                               "licence": "ForecastBench, Forecasting Research Institute, CC BY-SA 4.0"}
            try:
                foule[cle] = float(q.get("freeze_datetime_value"))
            except (TypeError, ValueError):
                pass
    return sorted(lignes.values(), key=lambda x: (x["jeu"], x["source"], x["id"])), foule


def calculer(xs: list[dict]) -> None:
    from sklearn.feature_extraction.text import TfidfVectorizer
    import numpy as np
    for x in xs:
        x["forme"], x["tranche"] = forme(x["titre"]), tranche(x["horizon"])
    vec = TfidfVectorizer(stop_words="english", min_df=2, sublinear_tf=True)
    X = vec.fit_transform([x["titre"] for x in xs])
    res = np.array([x["resolue_le"] for x in xs])
    ids = np.array([f'{x["source"]}:{x["id"]}' for x in xs])
    y = np.array([x["issue"] for x in xs], dtype=float)
    src = np.array([x["source"] for x in xs])
    cle1 = np.array([f'{x["source"]}|{x["forme"]}|{x["tranche"]}' for x in xs])
    for i, x in enumerate(xs):
        ok = (res < x["jeu"]) & (ids != ids[i])
        o0 = ok & (src == x["source"])
        r0 = (y[o0].sum() + 1) / (o0.sum() + 2)
        o1 = ok & (cle1 == cle1[i])
        r1 = (y[o1].sum() + M * r0) / (o1.sum() + M)
        x["p_R0"], x["p_R1"] = float(r0), float(r1)
        if ok.sum() == 0:
            x["p_S"] = float(r1)
            continue
        sims = (X[ok] @ X[i].T).toarray().ravel()
        idx = np.argsort(-sims)[:K_VOISINES]
        w = np.clip(sims[idx], 0, None)
        x["p_S"] = float((w @ y[ok][idx] + M * r1) / (w.sum() + M))
        x["sim_max"] = round(float(sims[idx[0]]), 3)


def resumer(xs: list[dict], foule: dict | None = None) -> dict:
    import essais as es
    conf = [x for x in xs if x["jeu"] >= COUPURE]
    pm = lambda s, k: round(sum(cb.pl(x[k], x["issue"]) for x in s) / len(s), 4) if s else None

    def disc(s, k):
        o = [x[k] for x in s if x["issue"] == 1]
        n = [x[k] for x in s if x["issue"] == 0]
        return round(sum(o) / len(o) - sum(n) / len(n), 3) if o and n else None
    r = {"questions": len(xs), "n_confirmation": len(conf),
         "oui_confirmation": round(sum(x["issue"] for x in conf) / len(conf), 3) if conf else None,
         "perte": {k: pm(conf, k) for k in ("p_R0", "p_R1", "p_S")},
         "discrimination": {k: disc(conf, k) for k in ("p_R0", "p_R1", "p_S")},
         "par_source": {s: {"n": len(v), "oui": round(sum(x["issue"] for x in v) / len(v), 3),
                            **{k: pm(v, k) for k in ("p_R0", "p_R1", "p_S")}}
                        for s in SOURCES for v in [[x for x in conf if x["source"] == s]] if v},
         "par_forme": {f: {"n": len(v), "oui": round(sum(x["issue"] for x in v) / len(v), 3),
                           **{k: pm(v, k) for k in ("p_R1", "p_S")}}
                       for f in ("election", "justice", "seuil", "echeance", "autre")
                       for v in [[x for x in conf if x["forme"] == f]] if v}}
    if len(conf) >= 30:
        ec = [(f'{x["source"]}:{x["id"]}', cb.pl(x["p_S"], x["issue"]) - cb.pl(x["p_R1"], x["issue"])) for x in conf]
        bas, haut = cb.bootstrap(ec, es.risque_corrige(1))
        r.update(ecart_moyen=round(sum(e for _, e in ec) / len(ec), 4), intervalle_corrige=[round(bas, 4), round(haut, 4)],
                 verdict="semblables meilleures que R1" if haut < 0 else
                 ("semblables moins bonnes que R1" if bas > 0 else "non tranché"))
    if foule:
        fc = [(x, foule[(x["source"], x["id"], x["jeu"])]) for x in conf if (x["source"], x["id"], x["jeu"]) in foule]
        fc = [(x, f) for x, f in fc if 0 <= f <= 1]
        if fc:
            r["foule_descriptif"] = {"n": len(fc), "perte_foule": round(sum(cb.pl(f, x["issue"]) for x, f in fc) / len(fc), 4),
                                     "perte_R1_memes": round(sum(cb.pl(x["p_R1"], x["issue"]) for x, _ in fc) / len(fc), 4),
                                     "perte_S_memes": round(sum(cb.pl(x["p_S"], x["issue"]) for x, _ in fc) / len(fc), 4)}
    return r


def principal() -> int:
    xs, foule = asyncio.run(recolter(date(2024, 7, 1)))
    REGISTRE.parent.mkdir(exist_ok=True)
    with REGISTRE.open("w", encoding="utf-8") as fo:
        for x in xs:
            fo.write(json.dumps(x, ensure_ascii=False) + "\n")
    calculer(xs)
    r = resumer(xs, foule)
    r["note"] = "perte log, plus bas = mieux ; aucun modèle de langue ; la foule n'est qu'un repère descriptif"
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    texte = json.dumps(r, ensure_ascii=False, indent=1)
    print(texte)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fo:
            fo.write("## Questions de jugement : semblables contre statu quo\n\n```\n" + texte + "\n```\n")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
