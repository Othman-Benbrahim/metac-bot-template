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
import time
import zipfile
from datetime import datetime
from pathlib import Path

import httpx

BASE = "https://microdata.worldbank.org/index.php"
CATALOGUE = 4509
IDNO = "WLD_2021_RTFP-CTRY_v02_M"
# 0.10.217 : l'API NADA attend l'identifiant texte de l'étude (« idno ») ; l'adresse numérique répond 400
RESSOURCES = [f"{BASE}/api/catalog/resources/{IDNO}", f"{BASE}/api/catalog/{IDNO}/resources",
              f"{BASE}/api/catalog/{CATALOGUE}/resources"]
TELECHARGER = f"{BASE}/catalog/{CATALOGUE}/download/{{rid}}"
CODES = "https://raw.githubusercontent.com/datasets/country-codes/main/data/country-codes.csv"
REGISTRE = Path("registre") / "prix-alimentaires.csv"
CHAMPS = ["version", "pays", "mois", "close", "inflation"]
GARDER_MOIS = 18
UA = {"User-Agent": "alphabet-situationnel-bot/1.0 (recherche ; GitHub Othman-Benbrahim)"}
_FICHIER = re.compile(r"WLD_RTFP_country_(\d{4}-\d{2}-\d{2})", re.I)


def ressources(c: httpx.Client) -> list[dict]:
    """Liste des ressources de l'étude ; essaie les adresses de RESSOURCES dans l'ordre."""
    erreurs = []
    for u in RESSOURCES:
        try:
            r = c.get(u)
            r.raise_for_status()
            j = r.json()
        except Exception as e:
            erreurs.append(f"{u.split('/api/')[1]} : {type(e).__name__} {str(e)[:60]}")
            continue
        if isinstance(j, dict):
            for k in ("resources", "result", "rows", "data", "files"):
                v = j.get(k)
                if isinstance(v, dict):
                    v = v.get("rows") or v.get("resources") or list(v.values())
                if isinstance(v, list):
                    return v
        if isinstance(j, list):
            return j
        erreurs.append(f"{u.split('/api/')[1]} : forme inattendue {str(j)[:80]}")
    raise RuntimeError(" | ".join(erreurs))


def versions(res: list[dict]) -> dict[str, str]:
    """0.10.218 : toutes les versions du fichier pays au catalogue : {date de version : identifiant de ressource}.
    Le catalogue garde chaque version hebdomadaire depuis juin 2023 : des millésimes réels, publiés à leur date."""
    out = {}
    for x in res:
        nom = " ".join(str(x.get(k) or "") for k in ("filename", "title", "name", "_links"))
        m = _FICHIER.search(nom)
        if m and (x.get("resource_id") or x.get("id")):
            out[m.group(1)] = str(x.get("resource_id") or x.get("id"))
    return out


def choisir(res: list[dict]) -> tuple[str | None, str | None]:
    """(identifiant de ressource, date de version) de la version la PLUS RÉCENTE du fichier pays."""
    v = versions(res)
    if not v:
        return None, None
    d = max(v)
    return v[d], d


def recentes(lignes: list[dict], mois: int = GARDER_MOIS) -> list[dict]:
    """Ne garde, pour chaque pays, que les `mois` derniers mois de la version (assez pour le glissement sur un an et
    son accélération sur trois mois) : la base complète remonte à 2007 et chaque version la recopie."""
    dernier: dict[str, str] = {}
    for x in lignes:
        dernier[x["pays"]] = max(dernier.get(x["pays"], ""), x["mois"])
    out = []
    for x in lignes:
        a, m = int(dernier[x["pays"]][:4]), int(dernier[x["pays"]][5:7])
        k = (a - int(x["mois"][:4])) * 12 + m - int(x["mois"][5:7])
        if k < mois:
            out.append(x)
    return out


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
            _sommaire(f"## Prix alimentaires (RTFP)\n\nAPI du catalogue inaccessible : {type(e).__name__}: {str(e)[:500]}")
            return 1
        tout = versions(res)
        rid, version = choisir(res)
        if a.sonde:
            l = ["## Sonde des prix alimentaires (RTFP)", "", f"{len(res)} ressource(s) au catalogue ; "
                 f"{len(tout)} version(s) du fichier pays, de {min(tout, default='—')} à {max(tout, default='—')}."]
            l.append(f"Version la plus récente : {version} (ressource {rid}).")
            if rid:
                r = c.get(TELECHARGER.format(rid=rid))
                l.append(f"Téléchargement : HTTP {r.status_code}, {len(r.content)} octets.")
                if r.status_code == 200:
                    xs = lire_rtfp(texte_csv(r.content), table_iso3(c), version)
                    l.append(f"Lu : {len(xs)} lignes, {len({x['pays'] for x in xs})} pays, dernier mois "
                             f"{max((x['mois'] for x in xs), default='—')} ; gardées : {len(recentes(xs))}.")
            _sommaire("\n".join(l + ["", "Rien d'écrit (sonde)."]))
            return 0
        if not tout:
            _sommaire("## Prix alimentaires (RTFP)\n\nFichier pays introuvable parmi les ressources du catalogue.")
            return 1
        anciens = list(csv.DictReader(REGISTRE.open(encoding="utf-8"))) if REGISTRE.exists() else []
        connues = {x["version"] for x in anciens}
        a_lire = sorted(v for v in tout if v not in connues)
        if not a_lire:
            _sommaire(f"## Prix alimentaires (RTFP)\n\nToutes les versions ({len(tout)}) sont déjà au registre.")
            return 0
        iso3 = table_iso3(c)
        nouvelles, echecs = [], []
        for v in a_lire:
            try:
                r = c.get(TELECHARGER.format(rid=tout[v]))
                r.raise_for_status()
                xs = recentes(lire_rtfp(texte_csv(r.content), iso3, v))
                if len(xs) < 100:
                    raise ValueError(f"trop court ({len(xs)} lignes)")
                nouvelles += xs
            except Exception as e:
                echecs.append(f"{v} ({type(e).__name__})")
            time.sleep(1)
    if not nouvelles:
        _sommaire("## Prix alimentaires (RTFP)\n\nAucune version lue : " + ", ".join(echecs[:10]))
        return 1
    REGISTRE.parent.mkdir(exist_ok=True)
    with REGISTRE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CHAMPS)
        w.writeheader()
        for x in sorted(anciens + nouvelles, key=lambda x: (x["version"], x["pays"], x["mois"])):
            w.writerow({k: x.get(k, "") for k in CHAMPS})
    lues = sorted({x["version"] for x in nouvelles})
    _sommaire(f"## Prix alimentaires (RTFP)\n\n{len(lues)} version(s) ajoutée(s) ({lues[0]} → {lues[-1]}), "
              f"{len(nouvelles)} lignes ; {len(echecs)} échec(s){' : ' + ', '.join(echecs[:10]) if echecs else ''}. "
              f"Source : Banque mondiale, Microdata Library ({IDNO}).")
    return 0

if __name__ == "__main__":
    sys.exit(principal())
