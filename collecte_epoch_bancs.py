"""Epoch AI, résultats des tests de référence (Benchmarking Hub, données CC BY, téléchargement public) — décision de
l'auteur du 2026-11-24, 14 h 35 (« classements Epoch AI et METR » validés). Le hub d'Epoch republie aussi les horizons
de tâche de METR : une seule source pour les deux.

Télécharge l'archive publique, garde chaque fichier CSV (chiffres seulement : colonnes de texte libre écartées) dans
registre/epoch-bancs/, et imprime l'inventaire (fichiers, colonnes, lignes, dernière date) pour choisir ensuite, par
procédure, ce qui servira. robots.txt respecté.
    python collecte_epoch_bancs.py
"""
from __future__ import annotations

import csv
import io
import sys
import zipfile
from pathlib import Path

import httpx

import politesse

URLS = ["https://epoch.ai/data/benchmark_data.zip", "https://epoch.ai/data/benchmarks.zip"]
SORTIE = Path("registre") / "epoch-bancs"
TEXTE = ("abstract", "note", "citation", "description", "comment", "notes")


def principal() -> int:
    with httpx.Client(follow_redirects=True, timeout=180, headers={"User-Agent": politesse.UA}) as c:
        contenu = None
        for u in URLS:
            if not politesse.autorise(c, u):
                print(f"Epoch (bancs) : refusé par robots.txt : {u}")
                continue
            r = c.get(u)
            print(f"essai {u} : HTTP {r.status_code}, {len(r.content)} octets, type {r.headers.get('content-type')}")
            if r.status_code == 200 and r.content[:2] == b"PK":
                contenu = r.content
                break
    if contenu is None:
        print("Epoch (bancs) : aucune archive lisible")
        return 0
    SORTIE.mkdir(parents=True, exist_ok=True)
    z = zipfile.ZipFile(io.BytesIO(contenu))
    for nom in z.namelist():
        if not nom.lower().endswith(".csv"):
            continue
        txt = z.read(nom).decode("utf-8-sig", errors="replace")
        lec = csv.DictReader(io.StringIO(txt))
        ent = lec.fieldnames or []
        garde = [x for x in ent if not any(t == x.lower().strip() or x.lower().startswith(t) for t in TEXTE)]
        L = list(lec)
        dates = [v for x in L for k, v in x.items() if k and "date" in k.lower() and v]
        dest = SORTIE / Path(nom).name
        with dest.open("w", encoding="utf-8", newline="\n") as f:
            w = csv.DictWriter(f, fieldnames=garde, extrasaction="ignore")
            w.writeheader()
            w.writerows(L)
        print(f"{Path(nom).name} : {len(L)} lignes ; dernière date {max(dates) if dates else '?'} ; colonnes {garde[:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
