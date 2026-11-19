"""Banc du rédacteur de questions (bot 0.10.336, ombre). Préenregistrement : preenregistrements/redacteur-questions.md.

La forme d'une question (plateforme, seuil, échéance, mots du statu quo ou du changement) porte-t-elle de l'information
sur son issue, au-delà des questions semblables (S) ? Régression logistique L2 réapprise à chaque jeu sur le passé admis
(clôture prévue et résolution avant le jeu). Aucun modèle de langue ; aucune entrée de la foule.

    python banc_redacteur.py        # lit registre/jugement-questions.jsonl, écrit registre/banc-redacteur.json
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

import numpy as np

import banc_jugement as bj

SORTIE = Path("registre") / "banc-redacteur.json"
LAMBDA = 1.0
BORNES = (0.02, 0.98)
STATU_QUO = r"\b(remain|remains|still|continue|continues|stay|stays|keep|keeps|maintain|maintains)\b"
CHANGEMENT = (r"\b(first|new|again|resign|resigns|leave|leaves|launch|launches|release|releases|announce|announces|sign|"
              r"signs|pass|passes|ban|bans|ceasefire|deal|agreement|invade|invades|attack|attacks)\b")
NEGATION = r"\b(not|no|without)\b"
SEUIL = r"\b(at least|more than|exceed|exceeds|greater than|above)\b"
ECHEANCE = r"\b(before|by)\b"
FORMES = ("election", "justice", "seuil", "echeance", "autre")
TRANCHES = ("<=30", "31-90", ">90")


def traits(x: dict) -> list[float]:
    t = (x.get("titre") or "").lower()
    h = x.get("horizon") or 0
    v = [1.0]
    v += [1.0 if x["source"] == s else 0.0 for s in bj.SOURCES[1:]]          # metaculus = référence
    f = bj.forme(x.get("titre", ""))
    v += [1.0 if f == k else 0.0 for k in FORMES[:-1]]
    tr = bj.tranche(x.get("horizon"))
    v += [1.0 if tr == k else 0.0 for k in TRANCHES[1:]]
    v += [math.log1p(max(h, 0)) / 6]
    v += [1.0 if re.search(r"\d", t) else 0.0]
    v += [1.0 if re.search(rx, t) else 0.0 for rx in (STATU_QUO, CHANGEMENT, NEGATION, SEUIL, ECHEANCE)]
    v += [math.log1p(len(t.split())) / 4]
    return v


def ajuster(X: np.ndarray, y: np.ndarray, lam: float = LAMBDA, iters: int = 50) -> np.ndarray:
    """Régression logistique L2 par Newton (l'ordonnée à l'origine n'est pas pénalisée)."""
    w = np.zeros(X.shape[1])
    R = np.eye(X.shape[1]) * lam
    R[0, 0] = 0.0
    for _ in range(iters):
        p = 1 / (1 + np.exp(-X @ w))
        g = X.T @ (p - y) + R @ w
        H = (X * (p * (1 - p))[:, None]).T @ X + R
        pas = np.linalg.solve(H, g)
        w -= pas
        if np.abs(pas).max() < 1e-8:
            break
    return w


def predire(xs: list[dict]) -> None:
    """Ajoute p_R à chaque ligne : modèle appris, pour chaque jeu, sur les questions admises (closes et résolues avant)."""
    X = np.array([traits(x) for x in xs])
    y = np.array([x["issue"] for x in xs], dtype=float)
    fin = np.array([max(x["resolue_le"], x.get("cloture", "")) for x in xs])
    ids = np.array([f'{x["source"]}:{x["id"]}' for x in xs])
    for jeu in sorted({x["jeu"] for x in xs}):
        ok = fin < jeu
        cibles = [i for i, x in enumerate(xs) if x["jeu"] == jeu]
        if ok.sum() < 50 or len(set(y[ok])) < 2:
            for i in cibles:
                xs[i]["p_R"] = xs[i]["p_R1"]
            continue
        w = ajuster(X[ok], y[ok])
        for i in cibles:
            if ids[i] in set(ids[ok]):                    # jamais la même question (déjà exclue par la date, par sûreté)
                m = ok & (ids != ids[i])
                wi = ajuster(X[m], y[m])
            else:
                wi = w
            p = float(1 / (1 + np.exp(-X[i] @ wi)))
            xs[i]["p_R"] = min(BORNES[1], max(BORNES[0], p))


def juger(xs: list[dict]) -> dict:
    import essais as es
    cb = bj.cb
    conf = [x for x in xs if x["jeu"] >= bj.COUPURE]
    pm = lambda s, k: round(sum(cb.pl(x[k], x["issue"]) for x in s) / len(s), 4) if s else None

    def disc(s, k):
        o = [x[k] for x in s if x["issue"] == 1]
        n = [x[k] for x in s if x["issue"] == 0]
        return round(sum(o) / len(o) - sum(n) / len(n), 3) if o and n else None
    for x in conf:
        x["p_RS"] = (x["p_R"] + x["p_S"]) / 2
    ec = [(f'{x["source"]}:{x["id"]}', cb.pl(x["p_R"], x["issue"]) - cb.pl(x["p_S"], x["issue"])) for x in conf]
    bas, haut = cb.bootstrap(ec, es.risque_corrige(1))
    e1 = [(f'{x["source"]}:{x["id"]}', cb.pl(x["p_R"], x["issue"]) - cb.pl(x["p_R1"], x["issue"])) for x in conf]
    b1, h1 = cb.bootstrap(e1, es.risque_corrige(1))
    return {"n_confirmation": len(conf), "questions_distinctes": len({k for k, _ in ec}),
            "perte": {k: pm(conf, k) for k in ("p_R1", "p_S", "p_R", "p_RS")},
            "discrimination": {k: disc(conf, k) for k in ("p_R1", "p_S", "p_R", "p_RS")},
            "ecart_R_moins_S": round(sum(e for _, e in ec) / len(ec), 4), "intervalle_corrige": [round(bas, 4), round(haut, 4)],
            "verdict": "rédacteur meilleur que les semblables" if haut < 0 else
                       ("rédacteur moins bon que les semblables" if bas > 0 else "non tranché"),
            "R_contre_R1": {"ecart": round(sum(e for _, e in e1) / len(e1), 4), "intervalle_corrige": [round(b1, 4), round(h1, 4)]},
            "risque_corrige": es.risque_corrige(1),
            "par_source": {s: {"n": len(v), **{k: pm(v, k) for k in ("p_R1", "p_S", "p_R", "p_RS")}}
                           for s in bj.SOURCES for v in [[x for x in conf if x["source"] == s]] if v}}


def coefficients(xs: list[dict]) -> dict:
    """Descriptif : le modèle appris sur toutes les questions admises avant la coupure (ce que « pense » le rédacteur)."""
    noms = (["constante"] + [f"source={s}" for s in bj.SOURCES[1:]] + [f"forme={f}" for f in FORMES[:-1]]
            + [f"horizon={t}" for t in TRANCHES[1:]] + ["log_horizon", "nombre", "statu_quo", "changement", "negation",
                                                        "seuil", "echeance", "longueur"])
    av = [x for x in xs if max(x["resolue_le"], x.get("cloture", "")) < bj.COUPURE]
    w = ajuster(np.array([traits(x) for x in av]), np.array([x["issue"] for x in av], dtype=float))
    return {"n": len(av), "poids": {n: round(float(v), 3) for n, v in zip(noms, w)}}


def principal() -> int:
    xs = [json.loads(l) for l in bj.REGISTRE.read_text(encoding="utf-8").splitlines() if l.strip()]
    xs = bj.cohorte_complete(xs)
    bj.calculer(xs)
    predire(xs)
    r = juger(xs)
    r["coefficients_avant_coupure"] = coefficients(xs)
    r["note"] = "perte log, plus bas = mieux ; aucun modèle de langue ; ombre : rien dans le bot avant le tournoi"
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
