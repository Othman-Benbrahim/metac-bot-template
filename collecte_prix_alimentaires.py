"""Prix alimentaires en temps réel, par pays (Banque mondiale, RTFP ; bot 0.10.214, en ombre).

Décision d'auteur du 2026-11-17 (0 h 21), à la place des blogs de la Banque mondiale (analyses publiées après coup,
sans flux RSS officiel). Source : « Monthly estimates of food prices and inflation by country »
(WLD_2021_RTFP-CTRY_v02_M, Microdata Library de la Banque mondiale, catalogue 4509, données ouvertes ; auteur
B. P. J. Andrée ; DOI 10.48529/2ZH0-JF55). 37 pays, surtout fragiles (Afghanistan, Soudan, Somalie, Yémen…),
mensuel depuis 2008 ; variables : Open, High, Low, Close (indice des prix alimentaires), Inflation, ISO3, price_date.

IMPORTANT, MILLÉSIMES : ce sont des ESTIMATIONS de modèle, recalculées à chaque version (le nom du fichier porte la
date de version, ex. WLD_RTFP_country_2026-11-02.csv). Une version récente réécrit le passé. On garde donc chaque
version comme un instantané daté, et l'indicateur ne lit que la dernière version publiée AVANT la date d'une question
(jamais une version postérieure : ce serait une fuite). Le passé antérieur à notre première collecte n'a pas de
millésime : indicateur absent.

Accès : la page de téléchargement est dynamique ; la sonde essaie l'API du catalogue (NADA) pour trouver le fichier.
Registres : registre/prix-alimentaires.csv (version, pays, mois, close, inflation).
Usage : python collecte_prix_alimentaires.py [--sonde]
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import httpx

BASE = "https://microdata.worldbank.org/index.php"
CATALOGUE = 4509
RESSOURCES = f"{BASE}/api/catalog/{CATALOGUE}/resources"
TELECHARGER = f"{BASE}/catalog/{CATALOGUE}/download/{{rid}}"
CODES = "https://raw.githubusercontent.com/datasets/country-codes/main/data/country-codes.csv"
REGISTRE = Path("registre") / "prix-alimentaires.csv"
CHAMPS = ["version", "pays", "mois", "close", "inflation"]
UA = {"User-Agent": "alphabet-situationnel-bot/1.0 (recherche ; GitHub Othman-Benbrahim)"}
_FICHIER = re.compile(r"WLD_RTFP_country_(\d{4}-\d{2}-\d{2})", re.I)


def ressources(c: httpx.Client) -> list[dict]:
    r = c.get(RESSOURCES)
    r.raise_for_status()
    j = r.json()
    if isinstance(j, dict):
        for k in ("resources", "result", "rows", "data"):
            if isinstance(j.get(k), list):
                return j[k]
    return j if isinstance(j, list) else []


def choisir(res: list[dict]) -> tuple[str | None, str | None]:
    """(identifiant de ressource, date de version) du fichier pays, d'après son nom."""
    for x in res:
        nom = " ".join(str(x.get(k) or "") for k in ("filename", "title", "name", "_links"))
        m = _FICHIER.search(nom)
        if m:
            return str(x.get("resource_id") or x.get("id") or ""), m.group(1)
    return None, None


def texte_csv(contenu: bytes) -> str:
    """CSV, éventuellement dans une archive zip."""
    if contenu[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(contenu)) as z:
            nom = next((n for n in z.namelist() if n.lower().endswith(".csv")), None)
            if not nom:
                raise ValueError("archive sans CSV")
            return z.read(nom).decode("utf-8-sig", "replace")
    return contenu.decode("utf-8-sig", "replace")


def mois_iso(valeur: str) -> str | None:
    v = str(valeur or "").strip()
    for f in ("%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y", "%Y-%m"):
        try:
            return datetime.strptime(v[:10], f).strftime("%Y-%m")
        except ValueError:
            continue
    return None


def lire_rtfp(texte: str, iso3: dict[str, str], version: str) -> list[dict]:
    out = []
    for x in csv.DictReader(io.StringIO(texte)):
        k = {str(a).strip().lower(): b for a, b in x.items()}
        p = iso3.get(str(k.get("iso3") or "").strip().upper())
        m = mois_iso(k.get("price_date") or k.get("date") or "")
        if not p or not m:
            continue
        out.append({"version": version, "pays": p, "mois": m, "close": (k.get("close") or "").strip(),
                    "inflation": (k.get("inflation") or "").strip()})
    return out


def table_iso3(c: httpx.Client) -> dict[str, str]:
    r = c.get(CODES, timeout=60)
    r.raise_for_status()
    return {x["ISO3166-1-Alpha-3"].strip(): x["ISO3166-1-Alpha-2"].strip() for x in csv.DictReader(io.StringIO(r.text))
            if len((x.get("ISO3166-1-Alpha-3") or "").strip()) == 3 and len((x.get("ISO3166-1-Alpha-2") or "").strip()) == 2}


def _sommaire(texte: str) -> None:
    print(texte)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(texte + "\n")


def principal() -> int:
    a_ = argparse.ArgumentParser()
    a_.add_argument("--sonde", action="store_true")
    a = a_.parse_args()
    with httpx.Client(headers=UA, timeout=180, follow_redirects=True) as c:
        try:
            res = ressources(c)
        except Exception as e:
            _sommaire(f"## Prix alimentaires (RTFP)\n\nAPI du catalogue inaccessible : {type(e).__name__}: {str(e)[:150]}")
            return 1
        rid, version = choisir(res)
        if a.sonde:
            l = ["## Sonde des prix alimentaires (RTFP)", "", f"{len(res)} ressource(s) au catalogue {CATALOGUE} :"]
            l += [f"- {str({k: x.get(k) for k in ('resource_id', 'id', 'title', 'filename', 'dctype')})[:220]}" for x in res[:10]]
            l.append(f"Fichier pays retenu : ressource {rid}, version {version}")
            if rid:
                r = c.get(TELECHARGER.format(rid=rid))
                l.append(f"Téléchargement : HTTP {r.status_code}, {len(r.content)} octets, type {r.headers.get('content-type')} ; "
                         f"début : {r.content[:160]!r}")
            _sommaire("\n".join(l + ["", "Rien d'écrit (sonde)."]))
            return 0
        if not rid:
            _sommaire("## Prix alimentaires (RTFP)\n\nFichier pays introuvable parmi les ressources du catalogue.")
            return 1
        anciens = list(csv.DictReader(REGISTRE.open(encoding="utf-8"))) if REGISTRE.exists() else []
        if any(x["version"] == version for x in anciens):
            _sommaire(f"## Prix alimentaires (RTFP)\n\nVersion {version} déjà au registre : rien à faire.")
            return 0
        r = c.get(TELECHARGER.format(rid=rid))
        r.raise_for_status()
        lignes = lire_rtfp(texte_csv(r.content), table_iso3(c), version)
    if len(lignes) < 1000:
        _sommaire(f"## Prix alimentaires (RTFP)\n\nFichier lu mais trop court ({len(lignes)} lignes) : rien d'écrit.")
        return 1
    REGISTRE.parent.mkdir(exist_ok=True)
    with REGISTRE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CHAMPS)
        w.writeheader()
        for x in anciens + lignes:
            w.writerow({k: x.get(k, "") for k in CHAMPS})
    _sommaire(f"## Prix alimentaires (RTFP)\n\nVersion {version} ajoutée : {len(lignes)} lignes, "
              f"{len({x['pays'] for x in lignes})} pays, dernier mois {max(x['mois'] for x in lignes)}. "
              f"Source : Banque mondiale, Microdata Library (WLD_2021_RTFP-CTRY_v02_M).")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
