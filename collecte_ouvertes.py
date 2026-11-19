"""Collecte de sources ouvertes pour les compartiments vides des niveaux rares (bot 0.10.337, ombre).

Décision d'auteur du 2026-11-19, 11 h 43 : couvrir d'abord les compartiments VIDES des niveaux peu mesurés (ordre
calculé par priorites_traces.py, d'après la fiche sur Gallagher, Hasko et Webb). Trois sources publiques, sans clé,
robots.txt vérifié pour chacune ; rien n'entre dans le bot.

- polarisation (niveau idéologie, humain:polarisation) : Voteview, fichier public des élus du Congrès (scores
  DW-NOMINATE) ; par Congrès, écart entre la médiane républicaine et la médiane démocrate sur la première dimension,
  Chambre des représentants. Agrégat seulement : aucun nom n'est lu ni écrit.
- co2 (niveau chimique, cycles-biogeochimiques:carbone) : NOAA GML, moyenne mensuelle du CO2 à Mauna Loa.
- attention (niveau psychologique, humain:disponibilite) : Wikimedia, pages vues quotidiennes (utilisateurs, toutes
  plateformes) d'une liste FIXE d'articles de concepts de crise ; la série est leur somme.

Registre : registre/ouvertes.csv (serie, jour, valeur), réécrit à chaque passage (une série absente garde ses lignes
précédentes).
"""
from __future__ import annotations

import csv
import io
import statistics
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import httpx

import politesse

REG = Path("registre")
SORTIE = REG / "ouvertes.csv"
VOTEVIEW = "https://voteview.com/static/data/out/members/HSall_members.csv"
CO2 = "https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.csv"
WIKI = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/"
        "{article}/daily/{debut}/{fin}")
ARTICLES = ["War", "Protest", "Riot", "Terrorism", "Coup_d'état", "Recession", "Inflation", "Pandemic"]  # liste fixe
DEBUT = "2016-01-01"
PAUSE = 2.0


def polarisation(texte: str, chambre: str = "House") -> list[tuple[str, float]]:
    """Par Congrès : médiane DW-NOMINATE (dim. 1) des républicains (200) moins celle des démocrates (100)."""
    par: dict[int, dict[str, list[float]]] = {}
    for r in csv.DictReader(io.StringIO(texte)):
        if r.get("chamber") != chambre or not r.get("nominate_dim1"):
            continue
        try:
            c, v = int(r["congress"]), float(r["nominate_dim1"])
        except ValueError:
            continue
        parti = {"100": "D", "200": "R"}.get(str(r.get("party_code")).split(".")[0])
        if parti:
            par.setdefault(c, {}).setdefault(parti, []).append(v)
    out = []
    for c, d in sorted(par.items()):
        if len(d.get("D", [])) >= 10 and len(d.get("R", [])) >= 10:
            debut = 1789 + 2 * (c - 1)                      # le Ne Congrès commence en janvier de l'année 1789 + 2(N−1)
            out.append((f"{debut}-01-03", round(statistics.median(d["R"]) - statistics.median(d["D"]), 4)))
    return out


def co2(texte: str) -> list[tuple[str, float]]:
    """co2_mm_mlo.csv : lignes « # » de commentaire, puis year,month,decimal date,average,… ; −99.99 = manquant."""
    lignes = [l for l in texte.splitlines() if l.strip() and not l.startswith("#")]
    out = []
    for r in csv.DictReader(lignes):
        try:
            v = float(r["average"])
            if v > 0:
                out.append((f"{int(r['year']):04d}-{int(r['month']):02d}-15", v))
        except (KeyError, ValueError):
            continue
    return out


def vues(corps: dict) -> dict[str, float]:
    out = {}
    for it in corps.get("items") or []:
        t = str(it.get("timestamp", ""))
        if len(t) >= 8:
            out[f"{t[:4]}-{t[4:6]}-{t[6:8]}"] = float(it.get("views") or 0)
    return out


def lire_existant() -> dict[str, list[tuple[str, float]]]:
    if not SORTIE.exists():
        return {}
    out: dict[str, list] = {}
    for r in csv.DictReader(SORTIE.open(encoding="utf-8")):
        out.setdefault(r["serie"], []).append((r["jour"], float(r["valeur"])))
    return out


def principal() -> int:
    series = lire_existant()
    fin = (date.today() - timedelta(days=1)).strftime("%Y%m%d")
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=120, follow_redirects=True) as c:
        for nom, url, lire in (("polarisation_chambre", VOTEVIEW, polarisation), ("co2_mauna_loa", CO2, co2)):
            if not politesse.autorise(c, url):
                print(f"::warning::{nom} : refusé par robots.txt ; rien collecté.")
                continue
            try:
                v = lire(c.get(url).raise_for_status().text)
            except Exception as e:
                v = []
                print(f"::warning::{nom} : {type(e).__name__}")
            if v:
                series[nom] = v
            print(f"{nom} : {len(v)} valeurs" + (f", dernière {v[-1]}" if v else ""), flush=True)
            time.sleep(PAUSE)
        exemple = WIKI.format(article=ARTICLES[0], debut=DEBUT.replace("-", ""), fin=fin)
        if politesse.autorise(c, exemple):
            total: dict[str, float] = {}
            complets = 0
            for a in ARTICLES:
                try:
                    v = vues(c.get(WIKI.format(article=a, debut=DEBUT.replace("-", ""), fin=fin)).raise_for_status().json())
                except Exception as e:
                    v = {}
                    print(f"::warning::attention {a} : {type(e).__name__}")
                if v:
                    complets += 1
                    for j, x in v.items():
                        total[j] = total.get(j, 0.0) + x
                time.sleep(PAUSE)
            if complets == len(ARTICLES):                 # somme faussée si un article manque : on garde l'ancienne
                series["attention_crise"] = sorted(total.items())
            print(f"attention_crise : {complets}/{len(ARTICLES)} articles, {len(total)} jours", flush=True)
        else:
            print("::warning::Wikimedia : refusé par robots.txt ; rien collecté.")
    if not series:
        return 0
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with SORTIE.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["serie", "jour", "valeur"])
        for s, v in sorted(series.items()):
            w.writerows((s, j, x) for j, x in v)
    print(f"ouvertes : {', '.join(f'{s} {len(v)}' for s, v in sorted(series.items()))}.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
