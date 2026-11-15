"""Jugement des essais `recalibrage_conflits` et `silence` (0.10.123 ; pré-enregistrement
preenregistrements/silence-et-calibrage.md). Aucun appel de modèle : lit registre/banc-a.jsonl (A, B) et
registre/banc-l.jsonl (nombre d'extraits de presse trouvés), garde les questions ACLED NOUVELLES (absentes de
preenregistrements/silence-vus.txt), dans l'ordre du banc du bras A.

Paramètres FIGÉS avant ces questions (appris sur les 150 questions ACLED antérieures) :
  A recalibré : logit p = −1,354 + 0,775·logit(A)
  silence     : logit p = logit(A recalibré) − 0,4405·S, S = 1 si aucun extrait de presse n'a été trouvé avant la date

    python juge_silence.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import banc_a as ba
import score_registre as sr

A_PLATT, B_PLATT, GAMMA = -1.354, 0.775, -0.4405
MODELE = "azure_ai/gpt-5-mini"


def lg(p: float) -> float:
    p = min(max(p, 1e-3), 1 - 1e-3)
    return math.log(p / (1 - p))


def sig(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def recal(p_a: float) -> float:
    return sig(A_PLATT + B_PLATT * lg(p_a))


def silence(p_a: float, n_extraits: int) -> float:
    return sig(A_PLATT + B_PLATT * lg(p_a) + GAMMA * (1.0 if n_extraits == 0 else 0.0))


def lignes_nouvelles() -> list[dict]:
    vus = {l.strip() for l in Path("preenregistrements/silence-vus.txt").read_text(encoding="utf-8").splitlines()
           if l.strip() and not l.startswith("#")}
    extraits = {}
    fl = Path("registre/banc-l.jsonl")
    if fl.exists():
        for l in fl.read_text(encoding="utf-8").splitlines():
            if l.strip():
                x = json.loads(l)
                if x.get("n_extraits") is not None:
                    extraits.setdefault(x["question_id"], x["n_extraits"])
    out, vu = [], set()
    for x in sorted(ba.lignes(), key=lambda x: (x.get("ordre") or [10 ** 6, x["jeu"]])):
        q = x["question_id"]
        if (x.get("source_question") != "acled" or q in vus or q in vu or x.get("modeles_A") != MODELE
                or x.get("p_A") is None or x.get("exclue") or x.get("issue") not in (0, 1)):
            continue
        vu.add(q)
        out.append(dict(x, n_extraits=extraits.get(q), p_recal=recal(x["p_A"])))
    return out


def principal() -> int:
    ls = lignes_nouvelles()
    r = {"n_nouvelles": len(ls), "note": "perte log, plus bas = mieux ; paramètres figés avant ces questions"}
    if ls:
        pl = sr.log_score
        r["recalibrage"] = {"n": len(ls), "A": round(sum(pl(x["p_A"], x["issue"]) for x in ls) / len(ls), 4),
                            "A_recalibre": round(sum(pl(x["p_recal"], x["issue"]) for x in ls) / len(ls), 4),
                            "critere": sr.critere_ombre_b([dict(x, p_B=x["p_A"], o={"p": x["p_recal"]}) for x in ls],
                                                          "o", "recalibrage_conflits", exclure_vus=False)}
        s = [dict(x, p_sil=silence(x["p_A"], x["n_extraits"])) for x in ls if x.get("n_extraits") is not None]
        if s:
            r["silence"] = {"n": len(s), "sans_extrait": sum(x["n_extraits"] == 0 for x in s),
                            "A_recalibre": round(sum(pl(x["p_recal"], x["issue"]) for x in s) / len(s), 4),
                            "silence": round(sum(pl(x["p_sil"], x["issue"]) for x in s) / len(s), 4),
                            "critere": sr.critere_ombre_b([dict(x, p_B=x["p_recal"], o={"p": x["p_sil"]}) for x in s],
                                                          "o", "silence", exclure_vus=False)}
    Path("registre/juge-silence.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
