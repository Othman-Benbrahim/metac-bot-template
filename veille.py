"""Veille de la carte : liens « Ressources » et flux RSS des fiches et des compartiments — bot 0.10.480, hors cadre.

Décision de l'auteur, 2026-11-23, 19 h 08 - 20 h 10 (voir veille/catalogue.yaml). Deux usages :
- la RÉSOLUTION (sans réseau) : quels flux pour une fiche, quels flux pour un compartiment — d'abord ceux que le
  catalogue donne au compartiment, sinon un flux du thème (organisation du compartiment) et un flux de la région (déduite
  de ses pays, sinon de la fiche) ; trois au plus ;
- la COLLECTE (python veille.py) : chaque flux du catalogue est lu une fois (robots.txt respecté, une requête par flux,
  pause entre deux), et l'on ne garde que titre, lien et date des derniers articles (jamais le texte). Un flux qui ne
  répond pas ou ne se lit pas est noté « muet » et n'apparaît pas sur la carte. Registre : registre/veille-flux.json.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import yaml

ICI = Path(__file__).resolve().parent
CATALOGUE = ICI / "veille" / "catalogue.yaml"
REG = Path(os.environ.get("ALPHABET_REGISTRE", "registre"))
SORTIE = REG / "veille-flux.json"
PAR_FLUX = 8
PAUSE = 1.0
MOYEN_ORIENT = {"ISR", "PSE", "LBN", "SYR", "IRQ", "IRN", "JOR", "SAU", "ARE", "QAT", "KWT", "BHR", "OMN", "YEM", "TUR", "EGY"}
AMERIQUE_DU_NORD = {"USA", "CAN"}
REGIONS_ONU = {"Afrique": "afrique", "Amériques": "ameriques", "Asie": "asie", "Europe": "europe", "Océanie": "oceanie"}


def catalogue(f: Path = CATALOGUE) -> dict:
    return yaml.safe_load(f.read_text(encoding="utf-8"))


def regions_pays() -> dict[str, str]:
    f = ICI / "ecosystemes" / "codes-pays-fips.csv"
    out = {}
    for r in csv.DictReader(l for l in f.read_text(encoding="utf-8").splitlines() if l and not l.startswith("#")):
        reg = REGIONS_ONU.get(r.get("region", ""))
        if reg:
            out[r["iso3"]] = reg
    out.update({x: "moyen_orient" for x in MOYEN_ORIENT})
    out.update({x: "amerique_du_nord" for x in AMERIQUE_DU_NORD})
    return out


def region_de(pays: list[str], defaut: str, table: dict[str, str]) -> str:
    regs = [table[p] for p in pays if p in table]
    if not regs:
        return defaut
    return max(set(regs), key=regs.count)


def flux_compartiment(cat: dict, theme: str, comp: dict, table: dict[str, str] | None = None, n: int = 3) -> list[str]:
    """Flux d'un compartiment : ceux que le catalogue lui donne ; sinon un du thème, un de la région, puis la suite."""
    fi = (cat.get("fiches") or {}).get(theme) or {}
    propres = (fi.get("compartiments") or {}).get(comp.get("id"), [])
    if propres:
        return list(dict.fromkeys(propres))[:n]
    table = table if table is not None else regions_pays()
    org = (cat.get("organisations") or {}).get(comp.get("organisation") or "", [])
    reg_nom = region_de(list((comp.get("geopolitique") or {}).get("pays") or []), fi.get("region", "monde"), table)
    reg = (cat.get("regions") or {}).get(reg_nom, [])
    out = []
    for groupe in (org[:1], reg[:1], org[1:2], reg[1:2]):
        for x in groupe:
            if x not in out:
                out.append(x)
    return out[:n]


def flux_fiche(cat: dict, theme: str) -> list[str]:
    return list(((cat.get("fiches") or {}).get(theme) or {}).get("flux") or [])


def liens_fiche(cat: dict, theme: str) -> list[dict]:
    return list(((cat.get("fiches") or {}).get(theme) or {}).get("liens") or [])


# ---- collecte
def _texte(e, *noms) -> str:
    for nom in noms:
        x = e.find(nom)
        if x is not None:
            if x.text and x.text.strip():
                return x.text.strip()
            if x.get("href"):
                return x.get("href")
    return ""


def _date(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    try:
        return parsedate_to_datetime(s).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    except (TypeError, ValueError):
        pass
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    except ValueError:
        return s[:16]


def lire_flux(contenu: bytes, n: int = PAR_FLUX) -> list[dict]:
    """RSS 2.0, RSS 1.0 (RDF) ou Atom : titre, lien, date des n derniers articles (rien d'autre)."""
    racine = ET.fromstring(contenu)
    for el in racine.iter():                                    # on retire les espaces de noms
        if isinstance(el.tag, str) and "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
    items = racine.findall(".//item") or racine.findall(".//entry")
    out = []
    for it in items:
        titre = re.sub(r"\s+", " ", _texte(it, "title"))
        lien = _texte(it, "link", "guid")
        if it.find("link") is not None and it.find("link").get("href"):
            lien = it.find("link").get("href")
        date = _date(_texte(it, "pubDate", "published", "updated", "date"))
        if titre and lien.startswith("http"):
            out.append({"titre": titre[:220], "lien": lien, "date": date})
    out.sort(key=lambda x: x["date"], reverse=True)
    return out[:n]


def principal() -> int:
    import httpx
    import politesse
    cat = catalogue()
    res = {}
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=30, follow_redirects=True) as c:
        for fid, f in (cat.get("flux") or {}).items():
            url = f["url"]
            e = {"titre": f["titre"], "url": url, "lu_le": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")}
            try:
                if not politesse.autorise(c, url):
                    e.update(statut="refuse_robots", articles=[])
                else:
                    r = c.get(url)
                    e["http"] = r.status_code
                    if r.status_code != 200:
                        e.update(statut="muet", articles=[])
                    else:
                        a = lire_flux(r.content)
                        e.update(statut="ok" if a else "vide", articles=a)
            except Exception as ex:
                e.update(statut="muet", erreur=type(ex).__name__, articles=[])
            res[fid] = e
            print(f"{fid} : {e['statut']}" + (f" ({e.get('http')})" if e.get("http") not in (None, 200) else "")
                  + (f", {len(e['articles'])} articles" if e["articles"] else ""), flush=True)
            time.sleep(PAUSE)
    REG.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = sum(1 for v in res.values() if v["statut"] == "ok")
    print(f"veille : {ok} flux lisibles sur {len(res)} ; muets : {sorted(k for k, v in res.items() if v['statut'] != 'ok')}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
