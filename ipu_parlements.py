"""Parlements du monde, relevé IPU Parline (bot 0.10.373, ombre).

Lit registre/ipu/parlements-*.csv et systemes-electoraux-*.csv (export fourni à la main par l'auteur ; l'API est fermée aux programmes, on ne la lit
pas). Trois usages :
- statut : chambre « Suspendu » → règle d'inertie des régimes fermés (regimes_fermes_inertie) pour les questions
  « tiendra-t-il des élections » ;
- designation : chambre élue au scrutin indirect ou nommée → les sondages ne s'appliquent pas, la brique s'abstient ;
- calendrier : date prévue de la prochaine élection, croisée avec Wikidata (registre/elections.csv). Deux sources de
  propriétaires différents (règle des deux sources indépendantes) ; l'écart est publié, jamais tranché d'office.
`python ipu_parlements.py` écrit registre/ipu/croisement-wikidata.md.
"""
from __future__ import annotations

import csv
import re
import sys
from datetime import date
from functools import lru_cache
from pathlib import Path

DOSSIER = Path("registre") / "ipu"
WIKIDATA = Path("registre") / "elections.csv"
SORTIE = DOSSIER / "croisement-wikidata.md"
FENETRE = 60          # jours de tolérance entre la date prévue (IPU) et une élection datée (Wikidata)
LEGISLATIVE = re.compile(r"parliament|legislative|general election|national assembly|duma|congress|house|chamber|"
                         r"senate|majlis|knesset|sejm|bundestag|storting|riksdag|cortes|diet", re.I)


@lru_cache(maxsize=1)
def chambres() -> list[dict]:
    fs = sorted(DOSSIER.glob("parlements-*.csv"))
    return list(csv.DictReader(fs[-1].open(encoding="utf-8"))) if fs else []


def de(iso: str) -> list[dict]:
    return [c for c in chambres() if c["iso"] == iso.upper()]


def suspendu(iso: str) -> bool:
    return any(c["statut"] == "Suspendu" for c in de(iso))


def basse(iso: str) -> dict | None:
    cs = de(iso)
    return next((c for c in cs if c["type_chambre"] in ("Chambre basse", "")), cs[0] if cs else None)


def elue_directement(iso: str) -> bool | None:
    c = basse(iso)
    return None if c is None else c["designation"] == "Scrutin direct"


@lru_cache(maxsize=1)
def systemes() -> dict[str, dict]:
    fs = sorted(DOSSIER.glob("systemes-electoraux-*.csv"))
    return {r["chambre_code"]: r for r in csv.DictReader(fs[-1].open(encoding="utf-8"))} if fs else {}


def systeme(iso: str) -> str | None:
    """Sous-catégorie du système électoral de la chambre basse (ou unique) : « Scrutin proportionnel de liste (List PR) »…"""
    c = basse(iso)
    return ((systemes().get(c["chambre_code"]) or {}).get("sous_systeme") or None) if c else None


def vote_obligatoire(iso: str) -> str | None:
    c = basse(iso)
    return ((systemes().get(c["chambre_code"]) or {}).get("vote_obligatoire") or None) if c else None


def _date(s: str) -> date | None:
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def croiser(aujourdhui: date | None = None) -> list[dict]:
    aujourdhui = aujourdhui or date.today()
    wd = list(csv.DictReader(WIKIDATA.open(encoding="utf-8"))) if WIKIDATA.exists() else []
    out = []
    for c in chambres():
        d = _date(c["prochaine_election"])
        if c["designation"] != "Scrutin direct" or not d or d < aujourdhui:
            continue
        proches = [w for w in wd if w["pays"] == c["iso"] and w["type"] == "election" and _date(w["date"])
                   and abs((_date(w["date"]) - d).days) <= FENETRE and LEGISLATIVE.search(w["nom"] or "")]
        out.append({"iso": c["iso"], "pays": c["pays"], "chambre": c["chambre"], "ipu": d.isoformat(),
                    "wikidata": sorted({w["date"] for w in proches}), "statut": c["statut"]})
    return out


def principal() -> int:
    if not chambres():
        print("aucun relevé IPU")
        return 1
    cr = croiser()
    acc = [x for x in cr if x["wikidata"]]
    L = ["# Prochaines élections : IPU (Parline) croisé avec Wikidata", "",
         f"{len(chambres())} chambres au relevé ; {len(cr)} chambres élues au suffrage direct avec une élection prévue à venir ; "
         f"{len(acc)} retrouvées dans Wikidata à ± {FENETRE} jours (nom législatif). Une seule source = date à confirmer.", "",
         "Chambres suspendues (règle d'inertie des régimes fermés) : "
         + ", ".join(sorted({f"{c['pays']} ({c['chambre']})" for c in chambres() if c["statut"] == "Suspendu"})) + ".", "",
         "| Pays | Chambre | IPU | Wikidata |", "|---|---|---|---|"]
    L += [f"| {x['pays']} | {x['chambre']} | {x['ipu']} | {', '.join(x['wikidata']) or '— (une seule source)'} |"
          for x in sorted(cr, key=lambda x: x["ipu"])]
    SORTIE.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"{len(cr)} à venir, {len(acc)} recoupées par Wikidata")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
