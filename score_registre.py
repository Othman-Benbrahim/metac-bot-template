"""Score du registre du bot : Brier et score logarithmique des bras A, B et C sur les questions résolues.

    python score_registre.py --metaculus               # récupère les issues sur Metaculus (METACULUS_TOKEN)
    python score_registre.py --resolutions issues.json # {"<question_id>": 0 ou 1, ...}, hors ligne

Le test qui compte est C contre B (l'apport des cartes au taux de base) et C contre A (l'alphabet contre le modèle
seul), sur les mêmes questions : seules les questions où les trois bras existent entrent dans la comparaison appariée.
Chaque ligne est vérifiée (sceau) avant d'être scorée ; une ligne retouchée est écartée et signalée.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path

import alphabet_pipeline as ap


def lignes(registre: Path) -> list[dict]:
    sortie = []
    for brut in (registre / "journal-bot.jsonl").read_text(encoding="utf-8").splitlines():
        if not brut.strip():
            continue
        x = json.loads(brut)
        s = x.pop("sceau", None)
        x["_intacte"] = s == ap.sceau(x)
        sortie.append(x)
    return sortie


def issues_metaculus(ids_urls: list[tuple[str, str]]) -> dict[str, int]:
    from forecasting_tools import MetaculusClient
    client, out = MetaculusClient(), {}
    for qid, url in ids_urls:
        try:
            q = client.get_question_by_url(url)
        except Exception:
            continue
        r = (q.resolution_string or "").lower()
        if r in ("yes", "no"):
            out[qid] = 1 if r == "yes" else 0
    return out


def brier(p: float, y: int) -> float:
    return (p - y) ** 2


def log_score(p: float, y: int) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return -math.log(p if y == 1 else 1 - p)


def scorer(registre: Path, issues: dict[str, int]) -> dict:
    tout = lignes(registre)
    retouchees = [x["question_id"] for x in tout if not x["_intacte"]]
    resolues = [x for x in tout if x["_intacte"] and x["question_id"] in issues]
    par_bras = {b: [] for b in "ABC"}
    apparies = []
    for x in resolues:
        y = issues[x["question_id"]]
        p = {"A": x["bras"]["A"].get("p"), "B": x["bras"]["B"].get("p"), "C": x["bras"]["C"].get("p_C")}
        for b, v in p.items():
            if v is not None:
                par_bras[b].append((v, y))
        if all(v is not None for v in p.values()):
            apparies.append((p, y))

    def resume(paires):
        if not paires:
            return None
        return {"n": len(paires), "brier": sum(brier(p, y) for p, y in paires) / len(paires),
                "log": sum(log_score(p, y) for p, y in paires) / len(paires)}

    comp = None
    if apparies:
        d_cb = [brier(p["C"], y) - brier(p["B"], y) for p, y in apparies]
        d_ca = [brier(p["C"], y) - brier(p["A"], y) for p, y in apparies]
        comp = {"n": len(apparies),
                "C_moins_B_brier": sum(d_cb) / len(d_cb), "C_bat_B": sum(d < 0 for d in d_cb),
                "C_moins_A_brier": sum(d_ca) / len(d_ca), "C_bat_A": sum(d < 0 for d in d_ca),
                "lecture": "négatif = C meilleur ; sur moins de quelques dizaines de questions, aucune conclusion"}
    statuts = {}
    for x in tout:
        s = x["bras"]["C"].get("statut")
        statuts[s] = statuts.get(s, 0) + 1
    return {"lignes": len(tout), "resolues": len(resolues), "retouchees": retouchees,
            "bras": {b: resume(v) for b, v in par_bras.items()}, "apparie_ABC": comp,
            "statuts_alphabet": statuts,
            "bras_poste": {b: sum(x["bras_poste"] == b for x in tout) for b in "AC"}}


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = a.add_mutually_exclusive_group(required=True)
    g.add_argument("--metaculus", action="store_true")
    g.add_argument("--resolutions")
    a.add_argument("--registre", default=os.environ.get("ALPHABET_REGISTRE", str(ap.REGISTRE)))
    args = a.parse_args()
    reg = Path(args.registre)
    if args.metaculus:
        iss = issues_metaculus([(x["question_id"], x["url"]) for x in lignes(reg)])
    else:
        iss = {str(k): int(v) for k, v in json.loads(Path(args.resolutions).read_text(encoding="utf-8")).items()}
    print(json.dumps(scorer(reg, iss), ensure_ascii=False, indent=2))
