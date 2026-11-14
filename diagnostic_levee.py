"""Diagnostic de la levée de C au-dessus de B, par rejeu des lectures du banc (0.10.79 ; sans appel de modèle).

À refaire à chaque palier de questions résolues (diagnostic contrastif du 2026-11-14, projet :
diagnostic-surconfiance-C). Rien n'est écrit au registre.
  1. multiplicateurs réduits : λ' = 1 + (λ − 1)·s, s ∈ {1 ; 0,75 ; 0,5 ; 0,25 ; 0} (copie du skill dans un dossier
     temporaire, rejeu dans un processus séparé) ;
  2. levée et issues selon le nombre de cartes ancrées, et par lien carte ancrée → carte de l'événement ;
  3. fond ou dynamique (ombres_auto.est_fond) : C recalculé sans les faits de fond, pour les événements « apparaît ».

    python diagnostic_levee.py [--sans-echelle]
"""
from __future__ import annotations

import argparse
import collections
import copy
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import alphabet_pipeline as ap
import alphabet_retro as ar
import ombres_auto as oa
import rejeu_banc as rb


def lignes() -> dict:
    f = ap.REGISTRE / ar.RETRO
    L = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()] if f.is_file() else []
    der = {}
    for x in L:
        if x.get("banc") == "forecastbench" and (x.get("rejeu") or {}).get("lectures") and x.get("issue") in (0, 1):
            der[(x["question_id"], (x.get("modeles") or {}).get("principal"))] = x
    return der


def perte(p, y):
    p = min(max(p, 0.001), 0.999)
    return -math.log(p if y else 1 - p)


def rejouer_tout(der: dict) -> list[dict]:
    out = []
    for (q, lect), x in der.items():
        r = x["rejeu"]
        lec = copy.deepcopy(r["lectures"][-1])
        ev = (r.get("plan") or {}).get("evenement") or {}
        a = rb.rejouer_lecture(copy.deepcopy(lec), r)
        fond = []
        if ev.get("type") == "apparait":
            garde = []
            for m in lec.get("mots") or []:
                (fond.append(m) if isinstance(m, dict) and oa.est_fond(m, r["aujourdhui"], r["jours"]) else garde.append(m))
            lec["mots"] = garde
        b = rb.rejouer_lecture(lec, r) if fond else a
        cartes = set()
        for m in r["lectures"][-1].get("mots") or []:
            try:
                cartes.add((ap.code_carte(m.get("carte")), str(m.get("strate"))))
            except Exception:
                pass
        out.append({"q": q, "lecteur": lect, "y": x["issue"], "B": x["p_B"], "p": a.get("p"), "p_sans_fond": b.get("p"),
                    "statut_sans_fond": b.get("statut"), "mots": a.get("mots"), "fond": len(fond),
                    "evenement": f"{ev.get('carte')}@{ev.get('strate')}", "type": ev.get("type"), "cartes": sorted(cartes)})
    return out


def echelle(s: float) -> list[dict]:
    """Rejeu dans un processus séparé, sur une copie du skill aux multiplicateurs réduits."""
    with tempfile.TemporaryDirectory() as t:
        dst = Path(t) / "skill"
        shutil.copytree(ap.DOSSIER_SKILL, dst)
        pf = dst / "assets/parametres.json"
        P = json.loads(pf.read_text(encoding="utf-8"))
        for k in ("F", "M", "f"):
            P["lambda"][k] = 1 + (P["lambda"][k] - 1) * s
        pf.write_text(json.dumps(P, ensure_ascii=False), encoding="utf-8")
        env = dict(os.environ, ALPHABET_SKILL_DIR=str(dst))
        r = subprocess.run([sys.executable, __file__, "--interne-rejeu"], capture_output=True, text=True, env=env,
                           timeout=3000)
        return json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip() else []


def principal(sans_echelle: bool) -> int:
    der = lignes()
    R = [r for r in rejouer_tout(der) if r["p"] is not None]
    n = len(R)
    if not n:
        print("Aucune lecture rejouable.")
        return 1
    rap = {"lectures": n, "oui": sum(r["y"] for r in R),
           "perte_log": {"B": sum(perte(r["B"], r["y"]) for r in R) / n, "C": sum(perte(r["p"], r["y"]) for r in R) / n,
                         "C_sans_fond": sum(perte(r["p_sans_fond"] if r["p_sans_fond"] is not None else r["B"], r["y"])
                                            for r in R) / n}}
    g = collections.defaultdict(list)
    for r in R:
        g[min(r["mots"] or 0, 4)].append(r)
    rap["par_nombre_de_cartes"] = {k: {"n": len(v), "levee": sum(r["p"] - r["B"] for r in v) / len(v),
                                       "ecart_observe": sum(r["y"] - r["B"] for r in v) / len(v)} for k, v in sorted(g.items())}
    M = ap._moteur()
    e = collections.defaultdict(list)
    for r in R:
        c_ev, s_ev = r["evenement"].split("@")
        if r["type"] == "apparait":
            for c, s in r["cartes"]:
                if s == s_ev:
                    e[f"{c}→{c_ev} ({M.P['matrice'].get(c, {}).get(c_ev)})"].append(r)
    rap["par_lien"] = {k: {"n": len(v), "levee": round(sum(r["p"] - r["B"] for r in v) / len(v), 3),
                           "ecart_observe": round(sum(r["y"] - r["B"] for r in v) / len(v), 3)}
                       for k, v in sorted(e.items(), key=lambda t: -len(t[1])) if len(v) >= 3}
    if not sans_echelle:
        rap["multiplicateurs_reduits"] = {}
        for s in (1.0, 0.75, 0.5, 0.25, 0.0):
            Rs = {(x["q"], x["lecteur"]): x for x in echelle(s)}
            ps = [(Rs.get((r["q"], r["lecteur"])) or {}).get("p") for r in R]
            ok = [(p, r) for p, r in zip(ps, R) if p is not None]
            rap["multiplicateurs_reduits"][str(s)] = sum(perte(p, r["y"]) for p, r in ok) / max(1, len(ok))
    print(json.dumps(rap, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    if "--interne-rejeu" in sys.argv:
        print(json.dumps([{k: r[k] for k in ("q", "lecteur", "p")} for r in rejouer_tout(lignes())]))
        sys.exit(0)
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--sans-echelle", action="store_true")
    sys.exit(principal(a.parse_args().sans_echelle))
