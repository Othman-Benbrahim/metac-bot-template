"""Classes de référence par signature de l'alphabet (0.10.110 ; pré-enregistrement classes-par-signature.md, décision
d'auteur du 2026-11-15). L'alphabet ne prédit pas lui-même : il organise la mémoire des cas. Pour chaque question lue
au banc (registre/retro.jsonl), signature = (carte de l'événement, type, strate) du plan ; parmi les questions des jeux
ANTÉRIEURS de même signature, k OUI sur n : B_sig = (k + 10·B)/(n + 10). Aucun modèle de langue. Sortie :
registre/classes-signature.json.

    python classes_signature.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import score_registre as sr

M = 10                                     # pseudo-compte fixé au pré-enregistrement
JEUX_TEST = ("2026-10-11", "2026-10-25")


def signature(x: dict) -> tuple | None:
    ev = ((x.get("rejeu") or {}).get("plan") or {}).get("evenement") or {}
    if not ev.get("carte") or not ev.get("type") or ev.get("strate") in (None, ""):
        return None
    return (str(ev["carte"]), str(ev["type"]), str(ev["strate"]))


def questions(registre: Path) -> list[dict]:
    """Une ligne par question : la plus ancienne lecture qui a une signature, une issue et un B."""
    vues: dict[str, dict] = {}
    for l in registre.read_text(encoding="utf-8").splitlines():
        if not l.strip():
            continue
        x = json.loads(l)
        if x.get("banc") != "forecastbench" or x.get("issue") not in (0, 1) or x.get("p_B") is None:
            continue
        sg = signature(x)
        if sg is None or x["question_id"] in vues:
            continue
        vues[x["question_id"]] = {"question_id": x["question_id"], "jeu": x.get("jeu") or x["question_id"].split(":")[1],
                                  "source_question": x["question_id"].split(":")[2], "issue": x["issue"],
                                  "p_B": float(x["p_B"]), "signature": list(sg)}
    return list(vues.values())


def calculer(qs: list[dict]) -> list[dict]:
    out = []
    for q in qs:
        if q["jeu"] not in JEUX_TEST:
            continue
        cas = [y for y in qs if y["jeu"] < q["jeu"] and y["signature"] == q["signature"]]
        n, k = len(cas), sum(y["issue"] for y in cas)
        out.append(dict(q, n_cas=n, k_cas=k, p_sig=(k + M * q["p_B"]) / (n + M)))
    rang: dict[str, int] = {}
    for j in JEUX_TEST:
        for r, y in enumerate(sorted((y for y in out if y["jeu"] == j),
                                     key=lambda y: hashlib.sha1(y["question_id"].encode()).hexdigest())):
            rang[y["question_id"]] = r
    return sorted(out, key=lambda y: (rang[y["question_id"]], y["jeu"]))


def resumer(ls: list[dict]) -> dict:
    avec = [y for y in ls if y["n_cas"] >= 1]
    pl = sr.log_score
    n = len(avec)
    return {"note": "perte log, plus bas = mieux ; B_sig = (k + 10·B)/(n + 10) sur les jeux antérieurs de même signature",
            "questions_test": len(ls), "avec_cas_comparables": n,
            "B": round(sum(pl(y["p_B"], y["issue"]) for y in avec) / n, 4) if n else None,
            "B_sig": round(sum(pl(y["p_sig"], y["issue"]) for y in avec) / n, 4) if n else None,
            "par_source": {s: {"n": len(v), "B": round(sum(pl(y["p_B"], y["issue"]) for y in v) / len(v), 4),
                               "B_sig": round(sum(pl(y["p_sig"], y["issue"]) for y in v) / len(v), 4)}
                           for s in sorted({y["source_question"] for y in avec})
                           for v in [[y for y in avec if y["source_question"] == s]]},
            "critere": sr.critere_ombre_b([dict(y, ombre_sig={"p": y["p_sig"]}) for y in avec], "ombre_sig",
                                          "classes_signature", exclure_vus=False)}


def principal() -> int:
    ls = calculer(questions(Path("registre/retro.jsonl")))
    r = resumer(ls)
    Path("registre/classes-signature.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
