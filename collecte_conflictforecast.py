"""Prévisions de ConflictForecast (Mueller et Rauh), toutes les versions mensuelles (bot 0.10.230, en ombre).

Décision d'auteur du 2026-11-17 (15 h 42) : un modèle CONCURRENT, comme ViEWS (claude/hypotheses-concurrentes.md).
ConflictForecast publie chaque mois des prévisions de conflit pour plus de 185 pays, à 3 et 12 mois (« armed
conflict », « any violence », « violence intensity »), et GARDE chaque version mensuelle telle qu'elle a été publiée :
on peut donc comparer, pour chaque question, la prévision disponible AVANT sa date, sans fuite.

Source : API ouverte et gratuite de conflictforecast.org (Backendless) : liste des répertoires mensuels, puis fichiers
CSV de chaque mois. Conditions (page Terms of Service) : usage et partage libres, sauf à but lucratif ; citation
obligatoire :
  Mueller, Hannes, Christopher Rauh (2022). The Hard Problem of Prediction for Conflict Prevention. Journal of the
  European Economic Association 20(6), 2440-2467, https://doi.org/10.1093/jeea/jvac025 ;
  Mueller, Hannes, Christopher Rauh, Ben Seimon (2024). Introducing a global dataset on conflict forecasts and news
  topics. Data & Policy 6, https://doi.org/10.1017/dap.2024.10.

Registre : registre/conflictforecast/<répertoire>/<fichier>.csv — fichiers NATIONAUX seulement (le fichier par
carreaux, « Grid Risk », est laissé de côté : trop lourd et hors de notre échelle) et le livre des codes.
Une seconde de pause entre deux téléchargements ; un répertoire déjà présent n'est pas relu.

    python collecte_conflictforecast.py [--max 200]
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

import httpx

API = ("https://api.backendless.com/C177D0DC-B3D5-818C-FF1E-1CC11BC69600/C5F2917E-C2F6-4F7D-9063-69555274134E/"
       "services/fileService")
DOSSIER = Path("registre") / "conflictforecast"
UA = {"User-Agent": "alphabet-situationnel-bot/1.0 (recherche non commerciale ; GitHub Othman-Benbrahim)",
      "accept": "application/json"}


def garder(nom: str) -> bool:
    n = nom.lower()
    return n.endswith(".csv") and "grid" not in n


def propre(nom: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", nom)


def principal(maximum: int) -> int:
    DOSSIER.mkdir(parents=True, exist_ok=True)
    with httpx.Client(headers=UA, timeout=120, follow_redirects=True) as c:
        try:
            r = c.get(f"{API}/get-all-directories")
            r.raise_for_status()
            reps = r.json()
        except Exception as e:
            print(f"API indisponible : {type(e).__name__}: {str(e)[:200]}")
            return 1
        noms = sorted({str(d.get("name", "")).strip("/") for d in reps if d.get("name")})
        print(f"{len(noms)} répertoires : {noms[:5]} … {noms[-5:]}")
        lus, fichiers = 0, 0
        for nom in noms:
            cible = DOSSIER / propre(nom)
            if cible.exists() and any(cible.iterdir()):
                continue
            if lus >= maximum:
                break
            time.sleep(1)
            try:
                rl = c.get(f"{API}/get-file-listing", params={"date": nom})
                rl.raise_for_status()
                liste = rl.json()
            except Exception as e:
                print(f"  {nom} : liste indisponible ({type(e).__name__})")
                continue
            cible.mkdir(parents=True, exist_ok=True)
            for f in liste:
                fn = str(f.get("name", ""))
                if not garder(fn) or not f.get("publicUrl"):
                    continue
                time.sleep(1)
                try:
                    rf = c.get(f["publicUrl"])
                    rf.raise_for_status()
                except Exception as e:
                    print(f"  {nom}/{fn} : {type(e).__name__}")
                    continue
                (cible / propre(fn)).write_bytes(rf.content)
                fichiers += 1
            lus += 1
            print(f"  {nom} : {sorted(p.name for p in cible.iterdir())}")
    # aperçu du plus récent répertoire lu, pour écrire ensuite la comparaison sur les bons noms de colonnes
    reps_locaux = sorted(p for p in DOSSIER.iterdir() if p.is_dir() and any(p.iterdir()))
    if reps_locaux:
        dernier = reps_locaux[-1]
        for p in sorted(dernier.iterdir()):
            lignes = p.read_text(encoding="utf-8", errors="replace").splitlines()
            print(f"\n--- {dernier.name}/{p.name} ({len(lignes)} lignes) ---")
            print("\n".join(l[:300] for l in lignes[:4]))
    bilan = (f"ConflictForecast : {lus} répertoires mensuels lus, {fichiers} fichiers ; "
             f"{len(reps_locaux)} répertoires en registre. Données : Mueller et Rauh (2022), Mueller, Rauh et Seimon "
             f"(2024), conflictforecast.org.")
    print("\n" + bilan)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fo:
            fo.write(f"## ConflictForecast\n\n{bilan}\n")
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--max", type=int, default=200)
    o = a.parse_args()
    sys.exit(principal(o.max))
