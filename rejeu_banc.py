"""Rejeu du banc ForecastBench : les lectures stockées repassent par le réparateur et le moteur ACTUELS, sans modèle.

0.10.54. Chaque ligne du banc écrite depuis 0.10.54 garde ses lectures brutes (première et corrections), le plan et
l'événement. Le rejeu les réassemble avec le code d'aujourd'hui et appelle le moteur : il mesure l'effet d'une version
du réparateur ou du moteur sur les MÊMES lectures, sans coût et sans la variance du lecteur. Il distingue ainsi un
changement de règle d'un changement du lecteur (Shankar et al., 2024, « Who Validates the Validators? » : la notation
déplace les critères).

Limites, déclarées : le retrait des faits futurs n'est rejoué que pour les lignes qui gardent les dates des résultats
(0.10.57 et après ; le texte, lui, reste hors registre) ; la boucle
de correction ne rejoue pas (elle demande le modèle) : on rejoue la première lecture, et la dernière s'il y en a eu
plusieurs ; les ombres du contradicteur, de la traduction et du programme génératif ne sont pas rejouées.

    python rejeu_banc.py [--version-min 0.10.54] [--json]
    python rejeu_banc.py --bascules [--version-min 0.10.54] [--json]

0.10.85 (règle écrite, 2026-11-14 ; billet « eval harness » : une notation retouchée a fait passer un score de 57 à 86
sans que l'agent change). Nos règles de validation (réparateur, moteur) sont un juge que l'on retouche. Toute version
qui touche le réparateur ou le moteur publie, dans sa demande de fusion et son historique, la TABLE DES BASCULES :
pour chaque ligne rejouable, le statut et le p de C enregistrés contre ceux que donne le code de la version, sur la
DERNIÈRE lecture (celle qui a produit la ligne). Une ligne enregistrée « état nul » n'est pas comparable quand le rejeu
dit autre chose (la relance d'état nul demande le modèle) : elle est comptée à part, jamais comme une bascule.
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
    if "dates_corpus" in r:        # 0.10.57 : retrait des faits futurs, rejoué sur les dates des résultats
        out["faits_futurs_retires"] = ap.retirer_faits_futurs(d, " ".join(r["dates_corpus"]), r["aujourdhui"], r["jours"])
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


def bascules(lignes: list[dict], tol: float = 1e-9) -> dict:
    """Table des bascules : statut ou p de C qui changent entre l'enregistrement et le code actuel (dernière lecture)."""
    table, non_comparables, n = [], 0, 0
    for x in lignes:
        r = x.get("rejeu") or {}
        lec = r.get("lectures") or []
        if x.get("banc") != "forecastbench" or not lec:
            continue
        n += 1
        avant = statut_enregistre(x)
        o = rejouer_lecture(lec[-1], r)
        if o["statut"] != avant:
            if avant == "etat_nul":
                non_comparables += 1
                continue
            table.append({"question_id": x["question_id"], "version": x.get("version_bot"), "avant": avant,
                          "apres": o["statut"], "p_avant": x.get("p_C"), "p_apres": o.get("p"),
                          "motif_avant": str(x.get("motif") or (x.get("exploratoire") or {}).get("motif") or "")[:120],
                          "motif_apres": o.get("motif", "")})
        elif avant == "estime" and x.get("p_C") is not None and o.get("p") is not None and abs(o["p"] - x["p_C"]) > tol:
            table.append({"question_id": x["question_id"], "version": x.get("version_bot"), "avant": avant,
                          "apres": o["statut"], "p_avant": x["p_C"], "p_apres": o["p"]})
    sens = collections.Counter(f"{b['avant']} → {b['apres']}" for b in table)
    return {"version_rejouee": ap.VERSION_BOT, "lignes": n, "bascules": len(table),
            "par_sens": dict(sens), "etat_nul_non_comparables": non_comparables, "table": table}


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--version-min", default="0.10.54")
    a.add_argument("--json", action="store_true")
    a.add_argument("--bascules", action="store_true", help="table des bascules (règle 0.10.85)")
    args = a.parse_args()
    if args.bascules:
        f_ = ap.REGISTRE / ar.RETRO
        L_ = [json.loads(l) for l in f_.read_text(encoding="utf-8").splitlines() if l.strip()] if f_.is_file() else []
        vm = tuple(map(int, args.version_min.split(".")))
        L_ = [x for x in L_ if tuple(map(int, str(x.get("version_bot", "0")).split("."))) >= vm]
        t = bascules(L_)
        if args.json:
            print(json.dumps(t, ensure_ascii=False, indent=1))
        else:
            for b in t["table"]:
                pa = "" if b.get("p_avant") is None else f"{b['p_avant']:.3f}"
                pb = "" if b.get("p_apres") is None else f"{b['p_apres']:.3f}"
                print(f"{b['question_id'][:52]:52} {b['version']:8} {b['avant']:>10} → {b['apres']:10} {pa:>6} → {pb:6}")
            print(json.dumps({k: v for k, v in t.items() if k != "table"}, ensure_ascii=False))
        sys.exit(0)
    sys.exit(principal(args.version_min, args.json))
