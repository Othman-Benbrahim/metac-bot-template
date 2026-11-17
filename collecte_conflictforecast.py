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

Chaque fichier mensuel contient TOUTE la série depuis 2010 (ajustements compris, environ 20 Mo) ; seule la DERNIÈRE
période de chaque version est la prévision réellement publiée ce mois-là. Correction du 2026-11-17 (16 h 25) : le
premier passage avait enregistré les fichiers bruts (4,2 Go) ; on ne garde plus que cette dernière période.

Registre : registre/conflictforecast.csv (version, isocode, periode, cible, horizon, p_all, p_text, p_hist) :
  version = répertoire mensuel (AAAA-MM) ; periode = dernier mois de données de cette version (AAAAMM) ;
  cible = armedconf | anyviolence (probabilités) | lnbest (intensité, log des morts par habitant) ;
  horizon = 3 ou 12 mois ; p_all = modèle « best » (texte + histoire), p_text = modèle texte, p_hist = histoire seule.
Fichiers nationaux seulement (le fichier par carreaux est laissé de côté). Une seconde de pause entre deux
téléchargements ; une version déjà extraite n'est pas relue ; le répertoire « latest » est ignoré (doublon du dernier
mois daté).

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
SORTIE = Path("registre") / "conflictforecast.csv"
COLONNES = ["version", "isocode", "periode", "cible", "horizon", "p_all", "p_text", "p_hist"]
UA = {"User-Agent": "alphabet-situationnel-bot/1.0 (recherche non commerciale ; GitHub Othman-Benbrahim)",
      "accept": "application/json"}


def garder(nom: str) -> bool:
    n = nom.lower()
    return n.endswith(".csv") and "grid" not in n


def propre(nom: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", nom)


def version_iso(nom: str) -> str | None:
    """« 10-2026 » → « 2026-10 » ; None pour « latest » ou un nom inattendu."""
    m = re.fullmatch(r"(\d{2})-(\d{4})", nom)
    return f"{m.group(2)}-{m.group(1)}" if m else None


def cible_horizon(fichier: str) -> tuple[str, int] | None:
    n = fichier.lower()
    m = re.search(r"(armedconf|anyviolence|lnbest)\D*?(\d+)\.csv$", n)
    return (m.group(1), int(m.group(2))) if m else None


def extraire(texte: str, version: str, fichier: str) -> list[dict]:
    """Lignes de la DERNIÈRE période du fichier : la prévision publiée dans cette version."""
    import csv as _csv
    import io as _io
    ch = cible_horizon(fichier)
    if not ch:
        return []
    cible, horizon = ch
    lignes = list(_csv.DictReader(_io.StringIO(texte)))
    if not lignes:
        return []
    def periode(x: dict) -> int | None:
        try:
            if x.get("period"):
                return int(float(x["period"]))
            return int(float(x["year"])) * 100 + int(float(x["month"]))
        except (TypeError, ValueError):
            return None
    derniere = max(p for p in (periode(x) for x in lignes) if p is not None)
    out = []
    for x in lignes:
        if periode(x) != derniere:
            continue
        pref = next((k[:-4] for k in x if k and k.endswith("_all")), None)
        if pref:
            p_all, p_text, p_hist = x.get(f"{pref}_all"), x.get(f"{pref}_text"), x.get(f"{pref}_hist")
        else:                                            # ancien format (2021-2024) : best_model, text_model
            p_all, p_text, p_hist = x.get("best_model"), x.get("text_model"), ""
        out.append({"version": version, "isocode": x.get("isocode", ""), "periode": derniere, "cible": cible,
                    "horizon": horizon, "p_all": p_all or "", "p_text": p_text or "", "p_hist": p_hist or ""})
    return out


def principal(maximum: int) -> int:
    import csv as _csv
    deja = set()
    if SORTIE.exists():
        deja = {x["version"] for x in _csv.DictReader(SORTIE.open(encoding="utf-8"))}
    SORTIE.parent.mkdir(exist_ok=True)
    neuf = not SORTIE.exists()
    lus, n_lignes = 0, 0
    with httpx.Client(headers=UA, timeout=180, follow_redirects=True) as c, \
            SORTIE.open("a", encoding="utf-8", newline="") as fo:
        w = _csv.DictWriter(fo, fieldnames=COLONNES)
        if neuf:
            w.writeheader()
        try:
            r = c.get(f"{API}/get-all-directories")
            r.raise_for_status()
            reps = r.json()
        except Exception as e:
            print(f"API indisponible : {type(e).__name__}: {str(e)[:200]}")
            return 1
        noms = sorted((version_iso(str(d.get("name", "")).strip("/")), str(d.get("name", "")).strip("/"))
                      for d in reps if d.get("name"))
        noms = [(v, n) for v, n in noms if v]
        print(f"{len(noms)} versions datées : {noms[0][0]} → {noms[-1][0]}")
        for v, nom in noms:
            if v in deja or lus >= maximum:
                continue
            time.sleep(1)
            try:
                rl = c.get(f"{API}/get-file-listing", params={"date": nom})
                rl.raise_for_status()
                liste = rl.json()
            except Exception as e:
                print(f"  {nom} : liste indisponible ({type(e).__name__})")
                continue
            n_v = 0
            for f in liste:
                fn = str(f.get("name", ""))
                if not garder(fn) or not f.get("publicUrl") or not cible_horizon(fn):
                    continue
                time.sleep(1)
                try:
                    rf = c.get(f["publicUrl"])
                    rf.raise_for_status()
                except Exception as e:
                    print(f"  {nom}/{fn} : {type(e).__name__}")
                    continue
                for ligne in extraire(rf.text, v, fn):
                    w.writerow(ligne)
                    n_v += 1
            fo.flush()
            lus += 1
            n_lignes += n_v
            print(f"  {v} : {n_v} lignes")
    bilan = (f"ConflictForecast : {lus} versions mensuelles extraites, {n_lignes} lignes ; données : Mueller et Rauh "
             f"(2022), Mueller, Rauh et Seimon (2024), conflictforecast.org.")
    print(bilan)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fo:
            fo.write(f"## ConflictForecast\n\n{bilan}\n")
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--max", type=int, default=200)
    o = a.parse_args()
    sys.exit(principal(o.max))
