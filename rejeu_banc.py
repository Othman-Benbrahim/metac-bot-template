"""Rejeu du banc ForecastBench : les lectures stockées repassent par le réparateur et le moteur ACTUELS, sans modèle.

0.10.54. Chaque ligne du banc écrite depuis 0.10.54 garde ses lectures brutes (première et corrections), le plan et
l'événement. Le rejeu les réassemble avec le code d'aujourd'hui et appelle le moteur : il mesure l'effet d'une version
du réparateur ou du moteur sur les MÊMES lectures, sans coût et sans la variance du lecteur. Il distingue ainsi un
changement de règle d'un changement du lecteur (Shankar et al., 2024, « Who Validates the Validators? » : la notation
déplace les critères).

Limites, déclarées : le retrait des faits futurs est sauté (les textes des résultats restent hors registre) ; la boucle
de correction ne rejoue pas (elle demande le modèle) : on rejoue la première lecture, et la dernière s'il y en a eu
plusieurs ; les ombres du contradicteur, de la traduction et du programme génératif ne sont pas rejouées.

    python rejeu_banc.py [--version-min 0.10.54] [--json]
"""
from __future__ import annotations

import argparse
import collections
import copy
import json
import sys

import alphabet_pipeline as ap
import alphabet_retro as ar


def rejouer_lecture(lecture: dict, r: dict) -> dict:
    plan, evt = copy.deepcopy(r["plan"]), copy.deepcopy(r["evt"])
    d = ap.assembler(copy.deepcopy(lecture), plan, r.get("recherches") or [], evt, r["aujourdhui"], r["jours"])
    out = {"reparations": len(d.get("_reparations") or []), "mots": len(d.get("mots") or [])}
    if not d["mots"]:
        return dict(out, statut="etat_nul")
    erreur = ap.controle_etat(d, plan)
    if erreur and erreur.startswith(f"événement « {plan['evenement']['type']} » sur une carte absente"):
        return dict(out, statut="etat_nul")
    if erreur:
        return dict(out, statut="refuse", motif=erreur[:200])
    s = ap.appeler_moteur({**{k: v for k, v in d.items() if not k.startswith("_")},
                           "rejets_categories": dict(d.get("_categories_rejet") or {})}, d["etat"], r["evenement"],
                          r["semantique"], r["aujourdhui"], evt["vue_exterieure"], evt["temporalite"],
                          exploratoire=bool(r.get("hors_strate")))
    if s.get("erreur"):
        return dict(out, statut="refuse", motif=str(s["erreur"])[:200])
    return dict(out, statut="estime" if s.get("p") is not None else "non_estime", p=s.get("p"))


def statut_enregistre(x: dict) -> str | None:
    ex = x.get("exploratoire") or {}
    return ex.get("statut") or x.get("statut")


def principal(version_min: str, en_json: bool) -> int:
    f = ap.REGISTRE / ar.RETRO
    lignes = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()] if f.is_file() else []
    lignes = [x for x in lignes if x.get("banc") == "forecastbench" and x.get("rejeu")
              and tuple(map(int, str(x.get("version_bot", "0")).split("."))) >= tuple(map(int, version_min.split(".")))]
    res = []
    for x in lignes:
        r = x["rejeu"]
        lec = r.get("lectures") or []
        if not lec:
            continue
        un = {"question_id": x["question_id"], "version_lue": r.get("version_bot"),
              "enregistre": statut_enregistre(x), "premiere": rejouer_lecture(lec[0], r)}
        if len(lec) > 1:
            un["derniere"] = rejouer_lecture(lec[-1], r)
        res.append(un)
    bilan = {"n": len(res), "version_rejouee": ap.VERSION_BOT,
             "enregistre": dict(collections.Counter(u["enregistre"] for u in res)),
             "premiere_lecture": dict(collections.Counter(u["premiere"]["statut"] for u in res)),
             "reparations_moyennes": round(sum(u["premiere"]["reparations"] for u in res) / max(1, len(res)), 2)}
    if en_json:
        print(json.dumps({"bilan": bilan, "questions": res}, ensure_ascii=False, indent=1))
        return 0
    for u in res:
        p = u["premiere"]
        print(f"{u['question_id'][:50]:50} enregistré {u['enregistre']!s:12} · rejeu 1re lecture {p['statut']:10} "
              f"({p['reparations']} réparation(s)) {p.get('motif', '')[:80]}")
    print(json.dumps(bilan, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--version-min", default="0.10.54")
    a.add_argument("--json", action="store_true")
    args = a.parse_args()
    sys.exit(principal(args.version_min, args.json))
