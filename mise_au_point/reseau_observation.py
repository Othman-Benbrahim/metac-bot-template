"""Observation (pas un test) : le réseau d'acteurs tel que Metaculus et GJOpen le posent (2026-11-20, accord de
l'auteur 18 h 31 : « le réseau est complexe et dépend de l'écosystème correspondant, mais je te suis »).

Acteurs : pays (acteurs_de_veto.pays) et organisations nommées (ORGS). Lien : deux acteurs dans une même question.
1. Propagation : pour une question sur A, part de OUI des questions résolues dans les 180 jours avant, sur les acteurs
   LIÉS à A (lien vu au moins 3 fois AVANT la date), comparée au même acteur (« rappel ») et au taux général.
2. Position : part de OUI selon la centralité (nombre de partenaires) de l'acteur.
Par écosystème (classes_homologues) quand la question y entre. Aucun modèle de langue.

    python mise_au_point/reseau_observation.py   # écrit registre/mise-au-point/reseau-observation.json
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import acteurs_de_veto as av
import classes_homologues as ch

SORTIE = Path("registre") / "mise-au-point" / "reseau-observation.json"
ORGS = {"EU": r"\b(EU|European Union|European Commission|European Council)\b", "NATO": r"\bNATO\b",
        "UN": r"\b(UN|United Nations|Security Council)\b", "Hamas": r"\bHamas\b", "Hezbollah": r"\bHezbollah\b",
        "Houthis": r"\bHouthis?\b", "Taliban": r"\bTaliban\b", "ISIS": r"\b(ISIS|ISIL|Islamic State)\b",
        "OPEC": r"\bOPEC", "WHO": r"(?-i:\bWHO\b)|World Health Organization", "Fed": r"\b(Federal Reserve|the Fed|FOMC)\b",
        "IAEA": r"\bIAEA\b"}
ORX = {k: re.compile(v, re.I) for k, v in ORGS.items()}
FEN, MIN_LIEN = 180, 3


def acteurs(t: str) -> set[str]:
    return av.pays(t) | {k for k, r in ORX.items() if r.search(t)}


def part(xs):
    return (round(sum(xs) / len(xs), 3), len(xs)) if xs else (None, 0)


def principal() -> int:
    qs = []
    for l in Path("registre/mise-au-point/questions.jsonl").read_text(encoding="utf-8").splitlines():
        d = json.loads(l)
        if d["source"] not in ("metaculus", "gjopen", "cset"):
            continue
        a = acteurs(d["titre"])
        if a:
            k = ch.classe(d["titre"], d.get("horizon", 30))
            qs.append({"jeu": d["jeu"], "fin": d["resolue_le"], "y": int(d["issue"]), "a": a,
                       "eco": k["fiche"] if k else None})
    qs.sort(key=lambda q: q["jeu"])
    base = sum(q["y"] for q in qs) / len(qs)
    # 1. propagation
    lignes = []
    for i, q in enumerate(qs):
        d0 = q["jeu"]
        debut = (date.fromisoformat(d0) - timedelta(days=FEN)).isoformat()
        liens = Counter()
        for p in qs[:i]:
            if p["fin"] < d0 and len(p["a"]) > 1:
                for x in p["a"]:
                    for z in p["a"]:
                        if x != z and x in q["a"]:
                            liens[z] += 1
        voisins = {z for z, n in liens.items() if n >= MIN_LIEN} - q["a"]
        meme, lies = [], []
        for p in qs[:i]:
            if debut <= p["fin"] < d0:
                if p["a"] & q["a"]:
                    meme.append(p["y"])
                elif p["a"] & voisins:
                    lies.append(p["y"])
        lignes.append({"y": q["y"], "eco": q["eco"], "meme": sum(meme) / len(meme) if len(meme) >= 3 else None,
                       "lies": sum(lies) / len(lies) if len(lies) >= 3 else None})

    def tableau(cle, ls):
        out = {}
        for nom, f in (("bas (< 20 % de oui récents)", lambda v: v < 0.2), ("moyen (20-40 %)", lambda v: 0.2 <= v < 0.4),
                       ("haut (≥ 40 %)", lambda v: v >= 0.4)):
            out[nom] = part([x["y"] for x in ls if x[cle] is not None and f(x[cle])])
        return out
    prop = {"tous": {"même acteur (rappel)": tableau("meme", lignes), "acteurs liés": tableau("lies", lignes)}}
    for e in sorted({x["eco"] for x in lignes if x["eco"]}):
        ls = [x for x in lignes if x["eco"] == e]
        if len(ls) >= 60:
            prop[e] = {"même acteur (rappel)": tableau("meme", ls), "acteurs liés": tableau("lies", ls)}
    # 2. position (centralité calculée sur tout l'échantillon : descriptif)
    part_ = defaultdict(set)
    for q in qs:
        for x in q["a"]:
            part_[x] |= q["a"] - {x}
    deg = {x: len(v) for x, v in part_.items()}
    pos = defaultdict(list)
    for q in qs:
        m = max(deg.get(x, 0) for x in q["a"])
        pos["central (≥ 20 partenaires)" if m >= 20 else "intermédiaire (5-19)" if m >= 5 else "périphérique (< 5)"].append(q["y"])
    r = {"questions_avec_acteur": len(qs), "taux_general": round(base, 3), "fenetre_jours": FEN, "lien_min": MIN_LIEN,
         "propagation_part_oui_selon_oui_recents": prop,
         "position_part_oui": {k: part(v) for k, v in pos.items()},
         "acteurs_les_plus_centraux": sorted(deg.items(), key=lambda kv: -kv[1])[:12],
         "note": "observation, pas un test : (part de oui, nombre de questions) ; rien n'entre dans le bot"}
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
