"""Cadrage d'un acteur par une institution, dans le temps (EmoAtlas ; bot 0.10.368, ombre).

Décision d'auteur du 2026-11-19 (21 h 10, usage 1 d'EmoAtlas). Côté « dit » : comment chaque institution parle de
chaque acteur, semaine après semaine. Sources : les flux RSS OFFICIELS déjà lus par collecte_routines.py
(registre/routines-sources.csv : Kremlin, Maison Blanche, Département d'État, Pentagone, ONU, OTAN, Commission
européenne, Élysée, MAE chinois) et les communiqués du Conseil de l'UE. robots.txt respecté.

Pour chaque élément (titre + résumé du flux) : les phrases qui nomment un acteur suivi (ACTEURS) ; par institution ×
acteur × semaine, le texte réuni passe dans EmoAtlas (huit émotions de Plutchik, écarts au hasard z). AUCUN TEXTE n'est
gardé : seulement les scores, le nombre de phrases et les empreintes des éléments déjà vus.
Registre : registre/cadrage.csv (institution, acteur, semaine, phrases, 8 émotions) ; registre/cadrage-vus.txt.
Environnement : workflow dédié (Python 3.11, emoatlas, numpy < 2, spaCy 3.7 et en_core_web_sm 3.7.1).
"""
from __future__ import annotations

import csv
import os
import re
import sys
import time
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

REG = Path(os.environ.get("ALPHABET_REGISTRE", "registre"))
SORTIE = REG / "cadrage.csv"
VUS = REG / "cadrage-vus.txt"
EMOTIONS = ("anger", "fear", "sadness", "disgust", "surprise", "anticipation", "trust", "joy")
SUPPLEMENTS = {"conseil_ue": "https://www.consilium.europa.eu/en/rss/pressreleases.ashx"}
ACTEURS = {
    "russie": r"\b(russia|russian|moscow|kremlin|putin)\b",
    "ukraine": r"\b(ukraine|ukrainian|kyiv|kiev|zelensky)\b",
    "iran": r"\b(iran|iranian|tehran)\b",
    "israel": r"\b(israel|israeli|netanyahu)\b",
    "chine": r"\b(china|chinese|beijing|xi jinping)\b",
    "etats_unis": r"\b(united states|u\.s\.|american|washington)\b",
    "ue": r"\b(european union|\beu\b|brussels)\b",
    "venezuela": r"\b(venezuela|venezuelan|caracas)\b",
}


def phrases(texte: str) -> list[str]:
    return [p.strip() for p in re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", texte)) if len(p.strip()) > 20]


def par_acteur(texte: str) -> dict[str, list[str]]:
    out = defaultdict(list)
    for p in phrases(texte):
        for a, motif in ACTEURS.items():
            if re.search(motif, p, re.I):
                out[a].append(p)
    return out


def semaine(jour: str) -> str:
    d = date.fromisoformat(jour)
    return (d - timedelta(days=d.weekday())).isoformat()


def principal() -> int:
    import httpx
    from emoatlas import EmoScores

    import collecte_rss as cr
    import politesse
    sources = {r["source"]: r["url"] for r in csv.DictReader((REG / "routines-sources.csv").open(encoding="utf-8"))}
    sources.update(SUPPLEMENTS)
    vus = set(VUS.read_text(encoding="utf-8").split()) if VUS.exists() else set()
    lignes = {}
    if SORTIE.exists():
        for r in csv.DictReader(SORTIE.open(encoding="utf-8")):
            lignes[(r["institution"], r["acteur"], r["semaine"])] = r
    textes: dict[tuple, list[str]] = defaultdict(list)
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=60, follow_redirects=True) as c:
        for inst, url in sources.items():
            if not politesse.autorise(c, url):
                print(f"{inst} : refusé par robots.txt")
                continue
            try:
                r = c.get(url)
                r.raise_for_status()
                items = cr.articles(r.content)
            except Exception as e:
                print(f"::warning::{inst} : {type(e).__name__}")
                continue
            n = 0
            for it in items:
                cle = f"{inst}:{it['empreinte']}"
                if cle in vus:
                    continue
                vus.add(cle)
                for a, ps in par_acteur(it["texte"]).items():
                    textes[(inst, a, semaine(it["jour"]))] += ps
                    n += len(ps)
            print(f"{inst} : {len(items)} éléments, {n} phrases sur les acteurs suivis", flush=True)
            time.sleep(1.0)
    e = EmoScores(language="english", spacy_model="en_core_web_sm")
    for (inst, a, s), ps in textes.items():
        ancien = lignes.get((inst, a, s))
        # les scores d'une semaine sont recalculés sur les seules phrases nouvelles quand la semaine existe déjà :
        # on garde la moyenne pondérée par le nombre de phrases (aucun texte n'étant conservé)
        z = e.zscores(" ".join(ps))
        n_new = len(ps)
        if ancien:
            n_old = int(ancien["phrases"])
            z = {k: (float(ancien[k]) * n_old + float(z.get(k, 0)) * n_new) / (n_old + n_new) for k in EMOTIONS}
            n_new += n_old
        lignes[(inst, a, s)] = {"institution": inst, "acteur": a, "semaine": s, "phrases": n_new,
                                **{k: round(float(z.get(k, 0)), 3) for k in EMOTIONS}}
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with SORTIE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["institution", "acteur", "semaine", "phrases", *EMOTIONS])
        w.writeheader()
        w.writerows(sorted(lignes.values(), key=lambda r: (r["semaine"], r["institution"], r["acteur"])))
    VUS.write_text("\n".join(sorted(vus)) + "\n", encoding="utf-8")
    print(f"cadrage : {len(textes)} cases (institution × acteur × semaine) mises à jour ; {len(lignes)} au total.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
