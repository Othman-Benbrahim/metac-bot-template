"""Collecte des réunions des eurodéputés avec les représentants d'intérêts (2026-11-25, source validée par l'auteur à
16 h 32 : « le 3 est la ressource la plus pertinente »).

Source : Integrity Watch EU (Transparency International EU), licence ODbL 1.0, qui republie les réunions déclarées sur
les pages des députés du Parlement européen. Le site du Parlement répond 403 (CloudFront) aux machines de GitHub : non
forcé. Adresse lue dans le script de la page (static/mepmeetings.js, sonde du 2026-11-25) :
autoupdate_data_eu/mepmeetings/latest/. robots.txt vérifié avant chaque requête.

Écrit dans registre/lobbying/ :
- reunions.json.gz              le fichier brut (réutilisation permise par l'ODbL, attribution à Integrity Watch EU) ;
- registre-transparence.json.gz correspondance représentant → numéro au registre de transparence ;
- mensuel.csv                   par mois : réunions, députés déclarants, part liée à un dossier, part inscrite au
                                registre ; et par commission (format long : mois, mesure, cle, valeur) ;
- dossiers.csv                  par dossier législatif : réunions, députés, représentants distincts, première et
                                dernière date ;
- etat.json                     colonnes vues, nombre de lignes, date de mise à jour annoncée, dernière réunion.
Le mois de la dernière réunion est incomplet : il est marqué « partiel » et l'adaptateur ne le rend pas.
"""
from __future__ import annotations

import csv
import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

import httpx

import politesse

BASE = "https://integritywatch.eu/autoupdate_data_eu/mepmeetings/"
DOSSIER = Path("registre") / "lobbying"


def date_iso(d: str) -> str | None:
    """« 23-01-2024 » (parfois suivi de « Cancelled ») → « 2024-01-23 »."""
    p = (d or "").split(" ")[0].split("-")
    if len(p) != 3 or not all(x.isdigit() for x in p):
        return None
    return f"{p[2]}-{p[1]}-{p[0]}"


def agreger(reunions: list[dict], registre: dict[str, str]) -> tuple[list[tuple], list[dict], str | None]:
    mois: dict = defaultdict(lambda: {"n": 0, "deputes": set(), "dossier": 0, "inscrits": 0, "representants": 0})
    comm: dict = defaultdict(int)
    dossiers: dict = defaultdict(lambda: {"n": 0, "deputes": set(), "repr": set(), "debut": None, "fin": None})
    derniere = None
    for r in reunions:
        if "cancel" in (r.get("date") or "").lower():
            continue
        d = date_iso(r.get("date"))
        if not d:
            continue
        derniere = max(derniere or d, d)
        m = d[:7]
        x = mois[m]
        x["n"] += 1
        x["deputes"].add(r.get("epid"))
        if (r.get("dossier") or "").strip():
            x["dossier"] += 1
        for nom in r.get("lobbyistsArray") or []:
            x["representants"] += 1
            if registre.get(nom):
                x["inscrits"] += 1
        for c in r.get("committees") or []:
            comm[(m, c)] += 1
        for dos in [s.strip() for s in (r.get("dossier") or "").split(",") if s.strip()]:
            y = dossiers[dos]
            y["n"] += 1
            y["deputes"].add(r.get("epid"))
            y["repr"].update(r.get("lobbyistsArray") or [])
            y["debut"] = min(y["debut"] or d, d)
            y["fin"] = max(y["fin"] or d, d)
    lignes = []
    for m, x in sorted(mois.items()):
        lignes += [(m, "reunions", "", x["n"]), (m, "deputes", "", len(x["deputes"])),
                   (m, "part_dossier", "", round(100 * x["dossier"] / x["n"], 1)),
                   (m, "part_registre", "", round(100 * x["inscrits"] / x["representants"], 1) if x["representants"] else "")]
    lignes += [(m, "commission", c, n) for (m, c), n in sorted(comm.items())]
    dos = [{"dossier": k, "reunions": v["n"], "deputes": len(v["deputes"]), "representants": len(v["repr"]),
            "debut": v["debut"], "fin": v["fin"]} for k, v in sorted(dossiers.items(), key=lambda kv: -kv[1]["n"])]
    return lignes, dos, derniere


def principal() -> int:
    DOSSIER.mkdir(parents=True, exist_ok=True)
    etat: dict = {"source": "Integrity Watch EU (Transparency International EU), ODbL 1.0", "base": BASE}
    with httpx.Client(headers={"User-Agent": politesse.UA}, follow_redirects=True, timeout=300) as c:
        brut = {}
        for nom, url in (("sauvegardes", BASE + "backups.json"), ("reunions", BASE + "latest/mepmeetings.json"),
                         ("registre", BASE + "latest/mepmeetings_lobbysts_tr_match.json")):
            if not politesse.autorise(c, url):
                etat[nom] = "refuse_robots"
                continue
            r = c.get(url)
            etat[nom] = {"statut": r.status_code, "taille": len(r.content)}
            if r.status_code == 200:
                brut[nom] = r.json()
    if "reunions" not in brut:
        (DOSSIER / "etat.json").write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps(etat, ensure_ascii=False, indent=1))
        return 1
    reunions, registre = brut["reunions"], brut.get("registre") or {}
    for nom, obj in (("reunions", reunions), ("registre-transparence", registre)):
        with gzip.open(DOSSIER / f"{nom}.json.gz", "wt", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False)
    lignes, dos, derniere = agreger(reunions, registre)
    partiel = (derniere or "")[:7]
    with (DOSSIER / "mensuel.csv").open("w", encoding="utf-8", newline="") as f:
        f.write("# Réunions des eurodéputés avec des représentants d'intérêts, par mois (Integrity Watch EU, ODbL 1.0) ; "
                "collecte_lobbying.py\n")
        w = csv.writer(f)
        w.writerow(["mois", "mesure", "cle", "valeur", "partiel"])
        for l in lignes:
            w.writerow([*l, "1" if l[0] == partiel else ""])
    with (DOSSIER / "dossiers.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["dossier", "reunions", "deputes", "representants", "debut", "fin"])
        w.writeheader()
        w.writerows(dos)
    actives = [s for s in (brut.get("sauvegardes") or []) if s.get("active")]
    etat.update({"lignes": len(reunions), "colonnes": sorted({k for r in reunions[:500] for k in r}),
                 "mise_a_jour_annoncee": actives[0]["timestamp"] if actives else None, "derniere_reunion": derniere,
                 "premiere_reunion": min((date_iso(r.get("date")) for r in reunions if date_iso(r.get("date"))), default=None),
                 "dossiers": len(dos), "representants_au_registre": sum(1 for v in registre.values() if v)})
    (DOSSIER / "etat.json").write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(etat, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
