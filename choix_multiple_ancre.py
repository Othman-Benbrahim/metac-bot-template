"""Choix multiple : le mélange 85 % bot + 15 % répartition égale fait-il mieux que le bot ? (préenregistrement
preenregistrements/choix-multiple-ancre-uniforme.md, 2026-11-20).

Calcul après coup, sur les prévisions scellées du journal d'ombre (registre/journal-autres.jsonl) et les issues brutes
relevées par score_registre.py (registre/issues-autres.jsonl). Aucun changement du bot.

    python choix_multiple_ancre.py      # écrit registre/choix-multiple-ancre.json
"""
from __future__ import annotations

import ast
import json
import math
import sys
from pathlib import Path

import alphabet_pipeline as ap
import score_registre as sr

REG = Path("registre")
SORTIE = REG / "choix-multiple-ancre.json"
W, BORNE, ALPHA, MAX_QUESTIONS = 0.15, 0.001, 0.05, 100


def options(x: dict) -> dict[str, float]:
    p = x["prediction"]
    p = p if isinstance(p, dict) else ast.literal_eval(p)
    return {str(o["option_name"]): float(o["probability"]) for o in p["predicted_options"]}


def melange(p: dict[str, float], w: float = W) -> dict[str, float]:
    n = len(p)
    return {k: (1 - w) * v + w / n for k, v in p.items()}


def perte(p: float) -> float:
    return -math.log(min(1 - BORNE, max(BORNE, p)))


def gagnante(p: dict[str, float], issue) -> str | None:
    if not isinstance(issue, str):
        return None
    cle = {k.strip().lower(): k for k in p}
    return cle.get(issue.strip().lower())


def e_processus(ecarts: list[float], alpha: float = ALPHA) -> dict:
    """Même pari que journal_cadre.e_processus, avec la borne du choix multiple (0,001)."""
    b = math.log((1 - BORNE) / BORNE)
    k, xs, trajet = 1.0, [], []
    for d in ecarts:
        if xs:
            m = sum(xs) / len(xs)
            v = sum((x - m) ** 2 for x in xs) / len(xs)
            lam = min(0.5, max(0.0, m / (v + m * m))) if (v + m * m) > 0 else 0.0
        else:
            lam = 0.0
        x = max(-1.0, min(1.0, -d / b))
        k *= 1 + lam * x
        xs.append(x)
        trajet.append(round(k, 4))
    seuil = 1 / alpha
    return {"richesse": trajet[-1] if trajet else 1.0, "seuil": seuil,
            "atteint_a": next((i + 1 for i, w in enumerate(trajet) if w >= seuil), None), "trajet": trajet}


def lignes() -> tuple[dict, dict]:
    derniere, issues = {}, {}
    f, fi = REG / "journal-autres.jsonl", REG / "issues-autres.jsonl"
    for x in map(json.loads, filter(str.strip, f.read_text(encoding="utf-8").splitlines())):
        s = x.pop("sceau", None)
        if x.get("type") == "choix_multiple" and s == ap.sceau(x) and not sr.est_essai(x):
            derniere[x["question_id"]] = x
    if fi.is_file():
        for y in map(json.loads, filter(str.strip, fi.read_text(encoding="utf-8").splitlines())):
            issues[y["question_id"]] = (y.get("issue"), y.get("constatee_le", ""))
    return derniere, issues


def principal() -> int:
    derniere, issues = lignes()
    resolues = []
    for qid, x in derniere.items():
        if qid not in issues:
            continue
        p = options(x)
        g = gagnante(p, issues[qid][0])
        if g is None:
            continue                                   # annulée, ou option introuvable : exclue
        m = melange(p)
        resolues.append({"question_id": qid, "titre": x["titre"][:90], "n_options": len(p), "constatee_le": issues[qid][1],
                         "p_bot_gagnante": round(p[g], 4), "p_melange_gagnante": round(m[g], 4),
                         "ecart": round(perte(m[g]) - perte(p[g]), 4)})
    resolues.sort(key=lambda r: (r["constatee_le"], r["question_id"]))
    resolues = resolues[:MAX_QUESTIONS]
    ep = e_processus([r["ecart"] for r in resolues])
    r = {"w": W, "questions_au_journal": len(derniere), "resolues": len(resolues),
         "ecart_moyen": round(sum(x["ecart"] for x in resolues) / len(resolues), 4) if resolues else None,
         "e_processus": ep,
         "verdict": "positif : le mélange entre dans le bot (décision de l'auteur)" if ep["atteint_a"] else
                    ("arrêt sans verdict positif" if len(resolues) >= MAX_QUESTIONS else "en cours"),
         "detail": resolues,
         "note": "écart = perte(mélange) − perte(bot) sur l'option gagnante ; négatif : le mélange aide"}
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in r.items() if k != "detail"}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
