"""Collecte des chiffres des matières stratégiques, sources gratuites et ouvertes (bot 0.10.389, ombre).

Décision de l'auteur du 2026-11-20, 14 h 48. Aucun modèle de langue ; rien n'entre dans le bot. Fichier robots vérifié
avant chaque source (politesse.autorise) ; une source indisponible n'arrête pas les autres.

1. Banque mondiale, « Pink Sheet » (mensuel) : CMO-Historical-Data-Monthly.xlsx, feuille des prix mensuels → séries
   (mois, série, unité, valeur) dans registre/matieres/banque-mondiale-mensuel.csv.
2. USGS, Mineral Commodity Summaries 2026 (annuel, domaine public CC0) : la publication des données (DOI
   10.5066/P1WKQ63T) est suivie jusqu'à sa page ScienceBase ; ses fichiers CSV sont copiés tels quels dans
   registre/matieres/usgs-mcs2026/.
3. UN Comtrade, aperçu public sans clé (500 lignes par appel) : exportations mensuelles de graphite de la Chine vers le
   monde (SH 250410 naturel en poudre ou paillettes, 250490 autre naturel, 380110 artificiel) → registre/matieres/
   comtrade-graphite.csv (période, produit, flux, valeur en dollars, poids net en kg).

    python collecte_matieres.py
"""
from __future__ import annotations

import csv
import io
import re
import sys
import time
from pathlib import Path

import httpx

import politesse

DOSSIER = Path("registre") / "matieres"
# 0.10.392 : le dossier 2025 s'arrête en décembre 2025 (run 44749409258) ; on essaie d'abord le dossier 2026
BM_XLSX_LISTE = ["https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx",
                 "https://thedocs.worldbank.org/en/doc/18675f1d1639c7a34d463f59263ba0a2-0050012025/related/CMO-Historical-Data-Monthly.xlsx"]
BM_XLSX = BM_XLSX_LISTE[-1]
USGS_DOI = "https://doi.org/10.5066/P1WKQ63T"
COMTRADE = "https://comtradeapi.un.org/public/v1/preview/C/M/HS"
CHINE = 156
PRODUITS = {"250410": "graphite naturel en poudre ou en paillettes", "250490": "autre graphite naturel",
            "380110": "graphite artificiel"}
MOIS = re.compile(r"^(\d{4})M(\d{2})$")


def banque_mondiale(c: httpx.Client) -> int:
    from openpyxl import load_workbook
    if not politesse.autorise(c, BM_XLSX):
        print("::warning::Banque mondiale : refusé par robots.txt")
        return 0
    r = None
    for url in BM_XLSX_LISTE:
        r = c.get(url)
        if r.status_code == 200 and r.content[:2] == b"PK":
            print(f"Banque mondiale : fichier {url.split('/doc/')[1][:40]}…")
            break
    r.raise_for_status()
    wb = load_workbook(io.BytesIO(r.content), read_only=True, data_only=True)
    ws = next((w for w in wb.worksheets if "monthly" in w.title.lower() and "price" in w.title.lower()), wb.worksheets[0])
    lignes = [list(x) for x in ws.iter_rows(values_only=True)]
    debut = next(i for i, l in enumerate(lignes) if l and isinstance(l[0], str) and MOIS.match(l[0].strip()))
    # en-tête = dernière ligne avant les données qui porte au moins 10 libellés ; unités = la ligne suivante si elle
    # commence par des parenthèses ou des $ (forme du fichier de la Banque mondiale)
    texte = lambda l: sum(1 for v in l[1:] if isinstance(v, str) and v.strip())
    cand = [i for i in range(debut) if texte(lignes[i]) >= 10]
    h = cand[0] if cand else debut - 2
    noms = [str(v or "").strip() for v in lignes[h]]
    unites = [str(v or "").strip() for v in lignes[h + 1]] if h + 1 < debut else [""] * len(noms)
    out = DOSSIER / "banque-mondiale-mensuel.csv"
    n = 0
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["mois", "serie", "unite", "valeur"])
        for l in lignes[debut:]:
            m = MOIS.match(str(l[0] or "").strip())
            if not m:
                continue
            for j in range(1, len(l)):
                if j < len(noms) and noms[j] and isinstance(l[j], (int, float)):
                    w.writerow([f"{m.group(1)}-{m.group(2)}", noms[j], unites[j] if j < len(unites) else "", l[j]])
                    n += 1
    print(f"Banque mondiale : {n} valeurs, {len([x for x in noms if x])} séries, feuille « {ws.title} »")
    return n


def usgs(c: httpx.Client) -> int:
    r = c.get(USGS_DOI)
    item = re.search(r"sciencebase\.gov/catalog/item/([0-9a-f]{24})", str(r.url) + " " + r.text)
    if not item:
        print(f"::warning::USGS : page ScienceBase introuvable (arrivée sur {r.url})")
        return 0
    api = f"https://www.sciencebase.gov/catalog/item/{item.group(1)}?format=json"
    if not politesse.autorise(c, api):
        print("::warning::ScienceBase : refusé par robots.txt")
        return 0
    d = c.get(api).json()
    fichiers = [(x.get("name"), x.get("url")) for x in (d.get("files") or []) + (d.get("attachments") or []) if x.get("url")]
    dest = DOSSIER / "usgs-mcs2026"
    dest.mkdir(parents=True, exist_ok=True)
    n = 0
    for nom, url in fichiers:
        if not nom or not re.search(r"\.(csv|zip)$", nom, re.I):
            continue
        b = c.get(url)
        if b.status_code != 200:
            continue
        if nom.lower().endswith(".zip"):
            import zipfile
            with zipfile.ZipFile(io.BytesIO(b.content)) as z:
                for zi in z.namelist():
                    if zi.lower().endswith(".csv"):
                        (dest / Path(zi).name).write_bytes(z.read(zi))
                        n += 1
        else:
            (dest / nom).write_bytes(b.content)
            n += 1
        time.sleep(0.5)
    print(f"USGS : {n} fichiers CSV ({len(fichiers)} fichiers listés sur ScienceBase {item.group(1)})")
    return n


def _comtrade_get(c: httpx.Client, params: dict) -> list[dict]:
    """Un appel à l'aperçu public, avec attente croissante sur 429 (limite de débit) ; le corps d'une erreur 400 est
    affiché pour le diagnostic."""
    for essai in range(5):
        r = c.get(COMTRADE.replace("/M/", f"/{params.pop('_freq', 'M')}/") if "_freq" in params else COMTRADE, params=params)
        if r.status_code == 429:
            time.sleep(15 * (essai + 1))
            continue
        if r.status_code != 200:
            print(f"  Comtrade {params.get('period')} {params.get('cmdCode')} : HTTP {r.status_code} {r.text[:200]!r}")
            return []
        return (r.json() or {}).get("data") or []
    print(f"  Comtrade {params.get('period')} {params.get('cmdCode')} : limite de débit, abandon")
    return []


def comtrade(c: httpx.Client, annees=range(2022, 2027)) -> int:
    """0.10.392 (run 44749409258 : HTTP 400 et 429 alternés) : un mois par appel, pause de 6 s, attente croissante."""
    if not politesse.autorise(c, COMTRADE):
        print("::warning::Comtrade : refusé par robots.txt")
        return 0
    from datetime import date
    fin = date.today().strftime("%Y%m")
    lignes = []
    for a in annees:
        for m in range(1, 13):
            periode = f"{a}{m:02d}"
            if periode > fin:
                break
            for code in PRODUITS:
                for x in _comtrade_get(c, {"reporterCode": CHINE, "period": periode, "cmdCode": code, "flowCode": "X",
                                           "partnerCode": 0}):
                    lignes.append([x.get("period"), code, x.get("flowCode"), x.get("primaryValue"), x.get("netWgt")])
                time.sleep(6)
    out = DOSSIER / "comtrade-graphite.csv"
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["periode", "produit_sh", "flux", "valeur_usd", "poids_net_kg"])
        for l in sorted(lignes, key=lambda l: (str(l[0]), l[1])):
            w.writerow(l)
    print(f"Comtrade : {len(lignes)} lignes (exportations chinoises de graphite vers le monde)")
    return len(lignes)


def principal() -> int:
    DOSSIER.mkdir(parents=True, exist_ok=True)
    ok = 0
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=120, follow_redirects=True) as c:
        for nom, f in (("Banque mondiale", banque_mondiale), ("USGS", usgs), ("Comtrade", comtrade)):
            try:
                ok += bool(f(c))
            except Exception as e:
                print(f"::warning::{nom} : {type(e).__name__}: {str(e)[:200]}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(principal())
