"""Avertissements de navigation : exercices et tirs militaires chinois (bot 0.10.206, module Chine, couche 3, en ombre).

Décision d'auteur du 2026-11-16 (21 h 51). Les administrations maritimes chinoises (msa.gov.cn) ferment des zones de
tir quelques jours avant les exercices, mais leurs sites refusent les connexions étrangères (constaté par l'auteur,
manuellement). Relais : l'agence américaine NGA (Maritime Safety Information) republie les avertissements de
navigation du Pacifique (HYDROPAC) ; données du gouvernement fédéral américain, domaine public, JSON, sans clé.

L'API ne rend que les avertissements EN COURS : l'historique se construit au fil des passages (date d'émission gardée).

Filtre fixé d'avance, sans modèle :
- zone chinoise : le texte nomme la Chine, une mer ou une province côtière chinoise (ZONES) ;
- activité militaire : exercices, tirs, missiles, roquettes, opérations navales (MILITAIRE) ;
- pays riverains concernés : selon les zones nommées (Chine toujours, plus Taïwan, Japon, Philippines, Viêt Nam,
  Corée du Sud selon la mer).

Registres : registre/avis-navigation-chine.csv ; registre/avis-navigation-jours.txt (jours de collecte).
Usage : python collecte_avis_navigation.py [--sonde]
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import httpx

URLS = ["https://msi.nga.mil/api/publications/broadcast-warn?output=json&status=active",
        "https://msi.om.east.paas.nga.mil/api/publications/broadcast-warn?output=json&status=active"]
UA = {"User-Agent": "alphabet-situationnel-bot/1.0 (recherche ; GitHub Othman-Benbrahim)"}
REGISTRE = Path("registre") / "avis-navigation-chine.csv"
JOURS = Path("registre") / "avis-navigation-jours.txt"
CHAMPS = ["id", "navarea", "emission", "premier_vu", "annule", "zones", "pays", "militaire", "extrait"]

# zone nommée dans le texte → pays riverains concernés (la Chine est toujours ajoutée)
ZONES = {
    "TAIWAN": ["TW"], "TAIWAN STRAIT": ["TW"], "FUJIAN": ["TW"], "PINGTAN": ["TW"], "XIAMEN": ["TW"],
    "ZHEJIANG": ["TW", "JP"], "EAST CHINA SEA": ["TW", "JP"], "DIAOYU": ["JP"], "SENKAKU": ["JP"],
    "SOUTH CHINA SEA": ["PH", "VN"], "HAINAN": ["VN", "PH"], "PARACEL": ["VN"], "XISHA": ["VN"],
    "SPRATLY": ["PH", "VN"], "NANSHA": ["PH", "VN"], "SCARBOROUGH": ["PH"], "HUANGYAN": ["PH"],
    "GULF OF TONKIN": ["VN"], "BEIBU": ["VN"], "YELLOW SEA": ["KR"], "SHANDONG": ["KR"], "JIANGSU": ["KR"],
    "LIAONING": ["KR"], "BOHAI": [], "GUANGDONG": [], "CHINA": [], "CHINESE": [],
}
_ZONES = sorted(ZONES, key=len, reverse=True)
MILITAIRE = re.compile(r"\b(MILITARY|EXERCISES?|GUNNERY|FIRING|LIVE[- ]FIRE|MISSILES?|ROCKETS?|NAVAL|WEAPONS?|"
                       r"TORPEDO|AERIAL TARGET|HAZARDOUS OPERATIONS)\b")
_MOIS = {m: i for i, m in enumerate(["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], 1)}
_DATE = re.compile(r"(\d{2})\d{4}Z\s+([A-Z]{3})\s+(\d{4})")


def date_iso(texte: str | None) -> str | None:
    """« 161200Z NOV 2026 » → « 2026-11-16 » ; une date ISO est rendue telle quelle."""
    t = str(texte or "").upper()
    m = _DATE.search(t)
    if m and m.group(2) in _MOIS:
        return f"{m.group(3)}-{_MOIS[m.group(2)]:02d}-{int(m.group(1)):02d}"
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", t)
    return m.group(0) if m else None


def zones(texte: str) -> list[str]:
    t, out = str(texte or "").upper(), []
    for z in _ZONES:
        if re.search(r"\b" + re.escape(z) + r"\b", t):
            out.append(z)
            t = re.sub(r"\b" + re.escape(z) + r"\b", " ", t)      # « EAST CHINA SEA » ne compte pas « CHINA »
    return out


def classer(w: dict) -> dict | None:
    """Fiche d'un avertissement s'il concerne une zone chinoise, sinon None."""
    texte = str(w.get("text") or "")
    zs = zones(texte)
    if not zs:
        return None
    pays = ["CN"] + sorted({p for z in zs for p in ZONES[z]})
    ident = f"{w.get('navArea')}-{w.get('msgYear')}-{w.get('msgNumber')}"
    return {"id": ident, "navarea": w.get("navArea") or "", "emission": date_iso(w.get("issueDate")) or "",
            "annule": date_iso(w.get("cancelDate")) or "", "zones": ";".join(zs), "pays": ";".join(pays),
            "militaire": int(bool(MILITAIRE.search(texte.upper()))), "extrait": re.sub(r"\s+", " ", texte)[:300]}


def lire_api(c: httpx.Client) -> list[dict]:
    derniere = None
    for u in URLS:
        try:
            r = c.get(u)
            r.raise_for_status()
            j = r.json()
            return j.get("broadcast-warn") or j.get("broadcastWarn") or (j if isinstance(j, list) else [])
        except Exception as e:
            derniere = e
            print(f"  {u.split('/api')[0]} : {type(e).__name__}: {str(e)[:100]}")
    raise RuntimeError(f"API NGA inaccessible ({type(derniere).__name__})")


def lire() -> dict[str, dict]:
    if not REGISTRE.exists():
        return {}
    return {x["id"]: x for x in csv.DictReader(REGISTRE.open(encoding="utf-8"))}


def ecrire(reg: dict[str, dict]) -> None:
    REGISTRE.parent.mkdir(exist_ok=True)
    with REGISTRE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CHAMPS)
        w.writeheader()
        for x in sorted(reg.values(), key=lambda x: (x.get("emission") or "", x["id"])):
            w.writerow({k: x.get(k, "") for k in CHAMPS})


def _sommaire(texte: str) -> None:
    print(texte)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(texte + "\n")


def principal() -> int:
    a_ = argparse.ArgumentParser()
    a_.add_argument("--sonde", action="store_true", help="vérifier l'accès et le contenu, sans rien écrire")
    a = a_.parse_args()
    with httpx.Client(headers=UA, timeout=90, follow_redirects=True) as c:
        try:
            tous = lire_api(c)
        except RuntimeError as e:                          # 0.10.245 : panne de la NGA (maintenance depuis plusieurs jours)
            print(f"::warning::{e} : rien d'écrit ce passage (jour non compté) ; relais : force_chinoise (GDELT).")
            _sommaire(f"## Avertissements de navigation (NGA)\n\n{e} : panne de la source, rien d'écrit ce passage.")
            return 0
    fiches = [f for f in (classer(w) for w in tous) if f]
    mil = [f for f in fiches if f["militaire"]]
    l = [f"## Avertissements de navigation (NGA) : {len(tous)} en cours",
         "", "Par zone NAVAREA : " + ", ".join(f"{k} {v}" for k, v in Counter(w.get("navArea") for w in tous).most_common()),
         f"Zone chinoise : {len(fiches)} ; dont activité militaire : {len(mil)}.",
         "Par pays concerné (militaires) : " + ", ".join(f"{k} {v}" for k, v in Counter(
             p for f in mil for p in f["pays"].split(";")).most_common())]
    if a.sonde:
        l += ["", "Exemples (militaires, zone chinoise) :"] + [f"- {f['id']} ({f['emission']}) [{f['zones']}] : {f['extrait'][:200]}"
                                                            for f in mil[:8]]
        l += ["", "Aucune écriture (sonde)."]
        _sommaire("\n".join(l))
        return 0
    reg = lire()
    aujourdhui = datetime.now(timezone.utc).date().isoformat()
    nouveaux = 0
    for f in fiches:
        if f["id"] in reg:
            reg[f["id"]].update({k: f[k] for k in ("annule", "zones", "pays", "militaire") if f[k] != ""})
        else:
            reg[f["id"]] = {**f, "premier_vu": aujourdhui}
            nouveaux += 1
    ecrire(reg)
    jours = set(JOURS.read_text(encoding="utf-8").split()) if JOURS.exists() else set()
    jours.add(aujourdhui)
    JOURS.write_text("\n".join(sorted(jours)) + "\n", encoding="utf-8")
    _sommaire("\n".join(l + [f"{nouveaux} nouvel(s) avertissement(s) ; {len(reg)} au registre. Source : NGA, domaine public."]))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
