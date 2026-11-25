"""Procès contre les actions de l'administration Trump, d'après le tracker public de Just Security (2026-11-25 ; source
validée par l'auteur à 22 h 38, collecte décidée à 22 h 45). robots.txt : permis, « Crawl-delay: 3 » (une seule page lue).

Page : https://www.justsecurity.org/107087/tracker-litigation-legal-challenges-trump-administration/ ; tableau
TablePress id="tablepress-42", colonnes lues par la sonde du 2026-11-25 : Case Name, Filings, Date Case Filed,
State A.G.'s, Case Status, Issue, Executive Action, Last Case Update, Case Summary, Case Updates.

On ne garde que les FAITS : nom de l'affaire, tribunal, numéro de dossier, lien CourtListener (source primaire), dates de
dépôt et de dernière mise à jour, présence des procureurs généraux des États, statut, thème, mesure attaquée. Les résumés
et l'historique rédigés par Just Security ne sont pas gardés (leur texte). Attribution : Just Security.

Le statut est pris dans une liste fermée (glossaire publié par Just Security, lu par la sonde) ; « famille » le range en
neuf classes pour compter : attente, bloque_temp, bloque, refuse_temp, refuse, debloque_appel, partiel, clos_plaignant,
clos_gouvernement, clos (« appel » = un appel est pendant ou a statué, gardé à part).

Écrit registre/justsecurity/proces.csv (photo courante), millesimes/proces-AAAA-MM-DD.csv.gz (une photo par passage,
pour suivre les changements de statut) et statuts.csv (passage, famille, appel, nombre).
"""
from __future__ import annotations

import csv
import datetime as dt
import gzip
import html
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

import httpx

import politesse

URL = "https://www.justsecurity.org/107087/tracker-litigation-legal-challenges-trump-administration/"
DOSSIER = Path("registre") / "justsecurity"
CHAMPS = ["affaire", "tribunal", "dossier", "courtlistener", "depot", "procureurs_etats", "statut", "famille", "appel",
          "theme", "mesure", "maj"]
ATTENDU = ["Case Name", "Filings", "Date Case Filed", "State A.G.'s", "Case Status", "Issue", "Executive Action",
           "Last Case Update"]


def _texte(x: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x))).strip()


def famille(statut: str) -> tuple[str, int]:
    """(famille, appel) d'après le glossaire de Just Security (2026-11-25). L'ordre des tests compte."""
    s = statut.lower()
    appel = int("appeal" in s or "appellate" in s)
    if not s:
        return "", 0
    if "in part" in s or "split outcome" in s:
        return "partiel", appel
    if "unblocked by appellate" in s:
        return "debloque_appel", 1
    if "closed" in s or "dismissed" in s:
        if "plaintiff" in s:
            return "clos_plaignant", appel
        if "government" in s:
            return "clos_gouvernement", appel
        return "clos", appel
    if "denied" in s:
        return ("refuse_temp" if "temporary" in s else "refuse"), appel
    if "blocked" in s:
        return ("bloque_temp" if "temporarily" in s else "bloque"), appel
    if "pending" in s:
        return "attente", appel
    return "autre", appel


def _affaire(cellule: str) -> dict:
    t = _texte(cellule)
    m = re.match(r"(.*?)\s*\(([^()]*)\)\s*(\S*)\s*$", t)
    lien = re.search(r'href="(https://www\.courtlistener\.com/[^"]+)"', cellule)
    return {"affaire": (m.group(1) if m else t)[:300], "tribunal": m.group(2) if m else "",
            "dossier": m.group(3) if m else "", "courtlistener": lien.group(1) if lien else ""}


def analyser(page: str) -> list[dict]:
    m = re.search(r'<table[^>]*id="tablepress-42".*?</table>', page, re.S | re.I)
    if not m:
        raise ValueError("tableau tablepress-42 introuvable")
    lignes = re.findall(r"<tr.*?</tr>", m.group(0), re.S | re.I)
    cel = lambda l: re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", l, re.S | re.I)
    entete = [_texte(c) for c in cel(lignes[0])]
    if entete[:len(ATTENDU)] != ATTENDU:
        raise ValueError(f"colonnes changées : {entete}")
    out = []
    for l in lignes[1:]:
        c = cel(l)
        if len(c) < len(ATTENDU):
            continue
        d = _affaire(c[0])
        statut = _texte(c[4])
        fam, appel = famille(statut)
        d.update({"depot": _texte(c[2])[:10], "procureurs_etats": _texte(c[3])[:80], "statut": statut, "famille": fam,
                  "appel": appel, "theme": _texte(c[5])[:120], "mesure": _texte(c[6])[:200], "maj": _texte(c[7])[:10]})
        out.append(d)
    return out


def ecrire(lignes: list[dict], jour: str) -> dict:
    DOSSIER.mkdir(parents=True, exist_ok=True)
    (DOSSIER / "millesimes").mkdir(exist_ok=True)
    with (DOSSIER / "proces.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=CHAMPS)
        w.writeheader()
        w.writerows(lignes)
    with (DOSSIER / "proces.csv").open("rb") as src, gzip.open(DOSSIER / "millesimes" / f"proces-{jour}.csv.gz", "wb") as dst:
        shutil.copyfileobj(src, dst)
    compte = Counter((l["famille"], l["appel"]) for l in lignes)
    chemin = DOSSIER / "statuts.csv"
    anciennes = []
    if chemin.exists():
        with chemin.open(encoding="utf-8") as h:
            anciennes = [r for r in csv.DictReader(h) if r["passage"] != jour]
    with chemin.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=["passage", "famille", "appel", "nombre"])
        w.writeheader()
        w.writerows(anciennes)
        for (f, a), n in sorted(compte.items()):
            w.writerow({"passage": jour, "famille": f, "appel": a, "nombre": n})
    etat = {"passage": jour, "affaires": len(lignes), "familles": {f"{f}|{a}": n for (f, a), n in sorted(compte.items())},
            "autres_statuts": sorted({l["statut"] for l in lignes if l["famille"] == "autre"}),
            "source": "Just Security, Litigation Tracker", "url": URL}
    (DOSSIER / "etat.json").write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")
    return etat


def principal() -> int:
    with httpx.Client(headers={"User-Agent": politesse.UA}, follow_redirects=True, timeout=120) as c:
        if not politesse.autorise(c, URL):
            print("refusé par robots.txt : rien n'est lu")
            return 0
        r = c.get(URL)
        r.raise_for_status()
    lignes = analyser(r.text)
    etat = ecrire(lignes, dt.date.today().isoformat())
    print(json.dumps(etat, ensure_ascii=False, indent=1))
    return 0 if lignes else 1


if __name__ == "__main__":
    sys.exit(principal())
