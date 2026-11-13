"""Banc des petites tâches (0.10.62) : jusqu'où un modèle (NVIDIA gratuit, d'abord) est-il fiable sur des tâches
courtes, à entrées identiques et contre une référence enregistrée ?

Référence : les questions ForecastBench d'une version passée du bot (par défaut 0.10.55, lues par Claude), dont le
registre garde, pour chaque question, la sonde de connaissance et le plan. Pour chaque modèle candidat, on soumet les
MÊMES consignes et on mesure :
  - la tenue : réponse, JSON lisible, temps, dépassements de délai ;
  - l'accord avec la référence : plan (hors alphabet ou non, carte, strate, type d'événement ; plan recevable par
    controle_plan) ; sonde (« connait »).
Les écarts sont listés un par un : un désaccord n'est pas forcément une erreur. Rien n'est écrit au registre ; le
rapport va dans le journal et dans un artefact JSON du workflow.

    python banc_petites_taches.py --modeles nvidia_nim/a,nvidia_nim/b [--version 0.10.55] [--taches plan,sonde]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from datetime import date

import alphabet_pipeline as ap
import alphabet_retro as ar
import banc_forecastbench as fb

DELAI = float(os.environ.get("ALPHABET_APPEL_DELAI") or "180")


def references(version: str) -> dict[str, dict]:
    f = ap.REGISTRE / ar.RETRO
    lignes = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()] if f.is_file() else []
    return {x["question_id"]: x for x in lignes if x.get("banc") == "forecastbench" and x.get("version_bot") == version
            and x.get("statut") != "panne"}


def plan_de_reference(x: dict) -> dict | None:
    r = x.get("rejeu") or {}
    if r.get("plan"):
        return r["plan"]
    ex = x.get("exploratoire") or {}
    return x.get("plan") or ex.get("plan")


def resume_plan(plan: dict | None) -> dict:
    """Ce qu'on compare d'un plan : recevable ? hors alphabet ? carte, strate, type."""
    if not isinstance(plan, dict):
        return {"lisible": False}

    def sur(f, *a):
        try:
            return f(*a)
        except Exception:
            return None
    try:
        motif = ap.controle_plan(plan)          # même jugement que la pipeline (hors alphabet = motif non corrigeable)
    except Exception as e:
        motif = f"plan illisible : {type(e).__name__}"
    ev = plan.get("evenement") if isinstance(plan.get("evenement"), dict) else {}
    return {"lisible": True, "recevable": motif is None,
            "hors_alphabet": bool(motif) and not ap.plan_corrigeable(motif),
            "carte": sur(ap.code_carte, ev.get("carte")), "strate": sur(ap.entier_strate, ev.get("strate")),
            "type": ev.get("type"), "motif": (motif or "")[:160]}


async def appeler(modele: str, consigne: str) -> tuple[str | None, float, str | None]:
    from forecasting_tools import GeneralLlm
    t0 = time.monotonic()
    try:
        texte = await asyncio.wait_for(GeneralLlm(model=modele, temperature=0, timeout=DELAI, allowed_tries=1)
                                       .invoke(consigne), DELAI)
        return texte, round(time.monotonic() - t0, 1), None
    except asyncio.TimeoutError:
        return None, round(time.monotonic() - t0, 1), f"délai dépassé ({DELAI:.0f} s)"
    except Exception as e:
        return None, round(time.monotonic() - t0, 1), f"{type(e).__name__}: {e}"[:200]


async def evaluer(modele: str, items: list[dict], refs: dict[str, dict], taches: list[str],
                  sortie_partielle: str | None = None) -> dict:
    res = {"modele": modele, "plan": [], "sonde": []}
    for x in items:
        ref = refs[x["qid"]]
        q = ap.Question(id=x["qid"], url=x["url"], titre=x["titre"], contexte=x["contexte"], criteres=x["criteres"],
                        precisions="", resolution=date.fromisoformat(x["resolution"]))
        if "plan" in taches:
            texte, s, err = await appeler(modele, ap.consigne_plan(q, "", x["jeu"]))
            try:
                plan = ap.extraire_json(texte) if texte else None
            except Exception:
                plan = None
            a, b = resume_plan(plan), resume_plan(plan_de_reference(ref))
            meme = (a.get("lisible") and b.get("lisible") and a.get("hors_alphabet") == b.get("hors_alphabet")
                    and (a.get("hors_alphabet") or (a.get("carte"), a.get("strate"), a.get("type"))
                         == (b.get("carte"), b.get("strate"), b.get("type"))))
            res["plan"].append({"qid": x["qid"], "secondes": s, "erreur": err, "modele": a, "reference": b,
                                "accord": bool(meme)})
            print(f"{modele[-28:]} plan  {x['qid'][14:56]} {s:6.1f} s {'accord' if meme else 'ÉCART'} {err or ''}",
                  flush=True)
        if "sonde" in taches:
            texte, s, err = await appeler(modele, ar.consigne_sonde(x["titre"], x["criteres"]))
            try:
                so = ap.extraire_json(texte) if texte else None
            except Exception:
                so = None
            ref_so = ref.get("sonde") or {}
            res["sonde"].append({"qid": x["qid"], "secondes": s, "erreur": err, "lisible": isinstance(so, dict),
                                 "connait": (so or {}).get("connait"), "reference": ref_so.get("connait"),
                                 "accord": isinstance(so, dict) and so.get("connait") == ref_so.get("connait")})
            print(f"{modele[-28:]} sonde {x['qid'][14:56]} {s:6.1f} s {err or ''}", flush=True)
        if sortie_partielle:                       # le rapport survit à une coupure du workflow
            with open(sortie_partielle, "w", encoding="utf-8") as f:
                json.dump(res, f, ensure_ascii=False)
    return res


def bilan(r: dict) -> dict:
    out = {"modele": r["modele"]}
    for t in ("plan", "sonde"):
        L = r[t]
        if not L:
            continue
        sec = [x["secondes"] for x in L if not x["erreur"]]
        lisibles = [x for x in L if (x["modele"].get("lisible") if t == "plan" else x["lisible"])]
        out[t] = {"n": len(L), "erreurs": sum(1 for x in L if x["erreur"]),
                  "delais_depasses": sum(1 for x in L if x["erreur"] and "délai" in x["erreur"]),
                  "json_lisible": len(lisibles), "accord": sum(1 for x in L if x["accord"]),
                  "secondes_mediane": statistics.median(sec) if sec else None,
                  "secondes_max": max(sec) if sec else None}
        if t == "plan":
            out[t]["recevables"] = sum(1 for x in L if x["modele"].get("recevable"))
    return out


async def principal(modeles: list[str], version: str, taches: list[str], sortie: str | None) -> int:
    refs = references(version)
    if not refs:
        print(f"Aucune question de référence pour la version {version}.")
        return 1
    jeux = sorted({q.split(":")[1] for q in refs})
    items = []
    for j in jeux:
        qs = await fb._json(f"{fb.DEPOT}/question_sets/{j}-llm.json")
        rs = await fb._json(f"{fb.DEPOT}/resolution_sets/{j}_resolution_set.json")
        items += [x for x in (fb.construire(i, j) for i in fb.apparier(qs, rs)) if x["qid"] in refs]
    for x in items:
        x["jeu"] = x["qid"].split(":")[1]
    print(f"Référence : version {version}, {len(items)} questions ; tâches : {', '.join(taches)} ; délai {DELAI:.0f} s.")
    tout = []
    for m in modeles:
        r = await evaluer(m, items, refs, taches, f"partiel_{len(tout)}.json")
        tout.append(r)
        b = bilan(r)
        print(json.dumps(b, ensure_ascii=False), flush=True)
        for t in taches:
            for x in r[t]:
                if not x["accord"] or x["erreur"]:
                    if t == "plan":
                        print(f"  plan  {x['qid'][14:60]} : {x['erreur'] or ''} modèle {json.dumps(x['modele'], ensure_ascii=False)[:220]}"
                              f" | référence {x['reference'].get('carte')}@{x['reference'].get('strate')} "
                              f"{x['reference'].get('type')} HA={x['reference'].get('hors_alphabet')}")
                    else:
                        print(f"  sonde {x['qid'][14:60]} : {x['erreur'] or ''} connait={x['connait']} (réf. {x['reference']})")
    if sortie:
        with open(sortie, "w", encoding="utf-8") as f:
            json.dump({"version": version, "taches": taches, "resultats": tout, "bilans": [bilan(r) for r in tout]},
                      f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--modeles", required=True)
    a.add_argument("--version", default="0.10.55")
    a.add_argument("--taches", default="plan,sonde")
    a.add_argument("--sortie", default="petites_taches.json")
    args = a.parse_args()
    sys.exit(asyncio.run(principal([m.strip() for m in args.modeles.split(",") if m.strip()], args.version,
                                   [t.strip() for t in args.taches.split(",") if t.strip()], args.sortie)))
