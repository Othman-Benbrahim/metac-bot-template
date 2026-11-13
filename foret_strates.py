"""Forêt ou arbre ? Comptage des liens entre strates dans les lectures enregistrées (0.10.64, skill 0.7.76, §52).

Hypothèse de la forêt (feuille de route du skill) : une racine par strate, les strates reliées par des emprunts
déclarés, plutôt qu'un tronc dont tout descendrait. Ce que l'on compte, dans chaque lecture gardée par le rejeu (banc
ForecastBench, depuis 0.10.54) : les cartes ancrées HORS de la strate de l'événement, et parmi elles celles qu'une
liaison déclarée entre strates (transfert, écho, conflit, averti) relie à la strate de l'événement ou à l'événement.

Une part élevée dit que le lecteur passe d'une strate à l'autre par des emprunts nommés (la forêt décrit les lectures) ;
une part faible dit qu'il juxtapose des strates sans les relier (rien ne départage encore). Rien n'est écrit ; aucun p.

    python foret_strates.py [--version-min 0.10.54] [--json]
"""
from __future__ import annotations

import argparse
import collections
import json
import sys

import alphabet_pipeline as ap
import alphabet_retro as ar

ENTRE_STRATES = {"transfert", "echo", "écho", "conflit", "averti"}


def strate_de(k: str) -> str:
    return k.partition("@")[2]


def compter(lecture: dict, plan: dict) -> dict | None:
    ev = plan.get("evenement") or {}
    try:
        cible = ap.cle_normale(f"{ev.get('carte')}@{ev.get('strate')}")
    except Exception:
        return None
    s_e = strate_de(cible)
    mots = set()
    for m in lecture.get("mots") or []:
        if isinstance(m, dict) and m.get("carte") is not None:
            try:
                mots.add(ap.cle_normale(f"{m.get('carte')}@{m.get('strate')}"))
            except Exception:
                pass
    hors = {k for k in mots if strate_de(k) and strate_de(k) != s_e}
    relies = set()
    for li in lecture.get("liaisons") or []:
        if not (isinstance(li, str) and len(li.split()) == 3):
            continue
        a, t, b = li.split()
        if t.strip("—-→>") not in ENTRE_STRATES:
            continue
        try:
            a, b = ap.cle_normale(a), ap.cle_normale(b)
        except Exception:
            continue
        for x, y in ((a, b), (b, a)):
            if x in hors and (strate_de(y) == s_e or y == cible):
                relies.add(x)
    return {"strate_evenement": s_e, "mots": len(mots), "hors_strate": len(hors), "relies": len(relies)}


def principal(version_min: str, en_json: bool) -> int:
    f = ap.REGISTRE / ar.RETRO
    lignes = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()] if f.is_file() else []
    vmin = tuple(map(int, version_min.split(".")))
    par_lecteur: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for x in lignes:
        r = x.get("rejeu") or {}
        if not r.get("lectures") or tuple(map(int, str(x.get("version_bot", "0")).split("."))) < vmin:
            continue
        c = compter(r["lectures"][-1], r.get("plan") or {})
        if c is None:
            continue
        lecteur = (x.get("modeles") or {}).get("principal") or "?"
        acc = par_lecteur[lecteur]
        acc["lectures"] += 1
        acc["lectures_multistrates"] += c["hors_strate"] > 0
        acc["mots_hors_strate"] += c["hors_strate"]
        acc["mots_relies"] += c["relies"]
    sortie = {k: dict(v, part_reliee=round(v["mots_relies"] / v["mots_hors_strate"], 3) if v["mots_hors_strate"] else None)
              for k, v in par_lecteur.items()}
    print(json.dumps(sortie, ensure_ascii=False, indent=1 if en_json else None))
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--version-min", default="0.10.54")
    a.add_argument("--json", action="store_true")
    args = a.parse_args()
    sys.exit(principal(args.version_min, args.json))
