"""Collecteur quotidien de Violations Watch (0.10.147, décision d'auteur du 2026-11-15, 20 h 32 : « l'intégrer en
ombre et le tester ; peut-être est-elle fiable, et alors on raterait quelque chose »). Aucun modèle de langue.

violationswatch.org : journal ouvert, mis à jour chaque jour, d'incidents présumés (droit humanitaire, droits humains),
compilés depuis les médias et les réseaux sociaux ; éditeur anonyme, aucune licence affichée, données depuis le
2026-11-06, fenêtre glissante de 28 jours. Faute de licence, on ne garde que des COMPTES (pays, jour de premier
signalement, gravité), jamais les textes ni les identifiants des victimes. Recueillir chaque jour constitue
l'historique que le site ne garde pas.
Registre : registre/violationswatch-comptes.csv (pays, jour, gravite, incidents).

    python collecte_violationswatch.py
"""
from __future__ import annotations

import csv
import io
import re
import sys
from pathlib import Path

import httpx

SOURCE = "https://violationswatch.org/incidents.csv"
FICHIER = Path("registre") / "violationswatch-comptes.csv"
UA = {"User-Agent": "alphabet-situationnel-bot/1.0 (recherche ; GitHub Othman-Benbrahim)"}


def pays(location: str) -> str:
    """« Palestine (Gaza) » → « Palestine » : même nom que les questions ACLED."""
    return re.sub(r"\s*\(.*?\)\s*", "", location or "").strip()


def compter(texte: str) -> dict[tuple, set]:
    vus: dict[tuple, set] = {}
    for x in csv.DictReader(io.StringIO(texte.lstrip("﻿"))):
        jour = str(x.get("first_reported", ""))[:10]
        if not jour or not x.get("id"):
            continue
        vus.setdefault((pays(x.get("location", "")), jour, x.get("priority", "") or "?"), set()).add(x["id"])
    return vus


def fusionner(anciens: dict[tuple, int], nouveaux: dict[tuple, set]) -> dict[tuple, int]:
    """Le même incident revient chaque jour pendant 28 jours : on garde, par case, le plus grand compte vu."""
    out = dict(anciens)
    for k, ids in nouveaux.items():
        out[k] = max(out.get(k, 0), len(ids))
    return out


def lire() -> dict[tuple, int]:
    if not FICHIER.exists():
        return {}
    return {(x["pays"], x["jour"], x["gravite"]): int(x["incidents"])
            for x in csv.DictReader(FICHIER.open(encoding="utf-8"))}


def principal() -> int:
    try:
        r = httpx.get(SOURCE, headers=UA, timeout=60, follow_redirects=True)
        r.raise_for_status()
    except Exception as e:
        print(f"Violations Watch indisponible : {type(e).__name__}: {e}")
        return 0
    comptes = fusionner(lire(), compter(r.text))
    FICHIER.parent.mkdir(exist_ok=True)
    with FICHIER.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pays", "jour", "gravite", "incidents"])
        for (p, j, g), n in sorted(comptes.items(), key=lambda t: (t[0][1], t[0][0], t[0][2])):
            w.writerow([p, j, g, n])
    print(f"{len(comptes)} cases pays × jour × gravité ; {sum(comptes.values())} incidents comptés.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
