"""Questions couvertes par les « événements comptés » des compartiments (0.10.492). Compte seulement, sans les issues.

Une question est couverte si : elle demande une occurrence avant une date (structure d'occurrence) ; un compartiment
rattaché porte un événement dont un terme figure dans le titre ; les gabarits de la série se remplissent avec les pays
cités (deux pays pour {ISO2_A}/{ISO2_B}) ; la série a au moins 12 mois d'historique avant la date du jeu.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lecture_mecanique import Carte, ICI  # noqa: E402
import adaptateurs  # noqa: E402
import structures_questions as sq  # noqa: E402

ISO2 = {r["iso3"]: r["iso2"] for r in csv.DictReader(
    l for l in (ICI / "ecosystemes/codes-pays-fips.csv").read_text(encoding="utf-8").splitlines() if l and not l.startswith("#"))}
OCCURRENCE = {"autre", "événement rare", "evenement_rare", "maintien"}


def remplir(gabarit: str, pays: list[str]) -> str | None:
    if "{ISO3_A}" in gabarit or "{ISO3_B}" in gabarit:
        if len(pays) < 2:
            return None
        return gabarit.replace("{ISO3_A}", pays[0]).replace("{ISO3_B}", pays[1])
    if "{ISO2_A}" in gabarit or "{ISO2_B}" in gabarit:
        if len(pays) < 2 or not all(ISO2.get(p) for p in pays[:2]):
            return None
        return gabarit.replace("{ISO2_A}", ISO2[pays[0]]).replace("{ISO2_B}", ISO2[pays[1]])
    if "{ISO3}" in gabarit:
        return gabarit.replace("{ISO3}", pays[0]) if pays else None
    if "{ISO2}" in gabarit:
        return gabarit.replace("{ISO2}", ISO2[pays[0]]) if pays and ISO2.get(pays[0]) else None
    return gabarit


def couvrir(carte: Carte, titre: str) -> list[dict]:
    comps, pays = carte.rattacher(titre)
    noeuds = {n["id"]: n for n in carte.s["noeuds"]}
    out = []
    for c in sorted(comps):
        for e in noeuds[c].get("evenements") or []:
            if not any(re.search(r"(?<![\w-])" + re.escape(t) + r"(?![\w-])", titre, re.I) for t in e["termes"]):
                continue
            serie = remplir(e["serie"], pays)
            if serie:
                out.append({"compartiment": c, "type": e["type"], "serie": serie, "seuil": e["seuil"], "pas": e["pas"]})
    return out


def principal() -> int:
    carte = Carte()
    cache, vus, cpt, ex = {}, set(), Counter(), []
    for l in (ICI / "registre/jugement-questions.jsonl").read_text(encoding="utf-8").splitlines():
        q = json.loads(l)
        if q["titre"] in vus or str(q.get("issue")) not in ("0", "1") or not q.get("jeu"):
            continue
        vus.add(q["titre"])
        if sq.structure(q["titre"]).split(" (")[0] not in OCCURRENCE:
            continue
        cpt["occurrence"] += 1
        cs = couvrir(carte, q["titre"])
        if not cs:
            continue
        cpt["événement reconnu"] += 1
        ok = []
        for c in cs:
            if c["serie"] not in cache:
                try:
                    cache[c["serie"]] = adaptateurs.lire(c["serie"])
                except Exception:
                    cache[c["serie"]] = []
            s = cache[c["serie"]]
            avant = [j for j, _ in s if j < q["jeu"]]
            if avant and (date.fromisoformat(q["jeu"]) - date.fromisoformat(avant[0])).days >= 365:
                ok.append(c)
        if ok:
            cpt["couverte (série ≥ 12 mois avant)"] += 1
            cpt["couverte " + q["source"]] += 1
            for c in ok:
                cpt["type : " + c["type"]] += 1
            ex.append((q["source"], q["titre"][:95], ok[0]["serie"]))
    for k, v in cpt.most_common():
        print(f"{v:5}  {k}")
    for e in ex[:25]:
        print("  -", e)
    return 0


if __name__ == "__main__":
    sys.exit(principal())
