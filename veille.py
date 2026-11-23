"""Veille de la carte : liens « Ressources » et flux RSS des fiches et des compartiments — bot 0.10.480 (secours des flux : 0.10.481), hors cadre.

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


def flux_compartiment(cat: dict, theme: str, comp: dict, table: dict[str, str] | None = None, n: int = 3,
                      sauf: set[str] | frozenset = frozenset()) -> list[str]:
    """Flux d'un compartiment : ceux que le catalogue lui donne ; sinon un du thème, un de la région, puis la suite.
    `sauf` (0.10.482) : flux muets au dernier passage, passés au profit du suivant de la liste."""
    fi = (cat.get("fiches") or {}).get(theme) or {}
    propres = [x for x in (fi.get("compartiments") or {}).get(comp.get("id"), []) if x not in sauf]
    if propres:
        return list(dict.fromkeys(propres))[:n]
    table = table if table is not None else regions_pays()
    org = [x for x in (cat.get("organisations") or {}).get(comp.get("organisation") or "", []) if x not in sauf]
    reg_nom = region_de(list((comp.get("geopolitique") or {}).get("pays") or []), fi.get("region", "monde"), table)
    reg = [x for x in (cat.get("regions") or {}).get(reg_nom, []) if x not in sauf]
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


def _reparer(contenu: bytes) -> bytes:
    """Flux presque bien formés : BOM et blancs avant <?xml, entités HTML (&nbsp;, &eacute;…) que XML ne connaît pas,
    esperluettes nues. Une page HTML (défi anti-robots) reste illisible, et c'est voulu."""
    import html.entities
    t = contenu.decode("utf-8", errors="replace").lstrip("﻿ \t\r\n")
    xml_ok = {"amp", "lt", "gt", "quot", "apos"}
    t = re.sub(r"&([A-Za-z][A-Za-z0-9]*);",
               lambda m: m.group(0) if m.group(1) in xml_ok
               else (f"&#{html.entities.name2codepoint[m.group(1)]};" if m.group(1) in html.entities.name2codepoint else ""), t)
    t = re.sub(r"&(?!#\d+;|#x[0-9A-Fa-f]+;|[A-Za-z][A-Za-z0-9]*;)", "&amp;", t)
    t = re.sub(r"^<\?xml[^>]*\?>", "", t)
    return t.encode("utf-8")


def muets(lus: dict) -> set[str]:
    """Flux muets au dernier passage (registre/veille-flux.json) : la résolution les passe pour un compartiment."""
    return {k for k, v in (lus or {}).items() if v.get("statut") != "ok"}


def lire_flux(contenu: bytes, n: int = PAR_FLUX) -> list[dict]:
    """RSS 2.0, RSS 1.0 (RDF) ou Atom : titre, lien, date des n derniers articles (rien d'autre)."""
    try:
        racine = ET.fromstring(contenu)
    except ET.ParseError:
        racine = ET.fromstring(_reparer(contenu))               # 0.10.482 : BOM, blancs en tête, entités HTML
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


def candidats(f: dict) -> list[dict]:
    """L'adresse principale du flux, puis ses adresses de secours (0.10.481) dans l'ordre du catalogue.

    Un secours est soit une autre adresse du même site (flux déplacé), soit une autre source du même rôle quand le site
    a refusé la lecture (robots.txt, 403) : on ne contourne jamais un refus, on change de source."""
    out = [{"url": f["url"], "titre": f["titre"]}]
    for s in f.get("secours") or []:
        out.append({"url": s, "titre": f["titre"]} if isinstance(s, str) else {"url": s["url"], "titre": s.get("titre", f["titre"])})
    return out


def lire_un(c, url: str) -> dict:
    import politesse
    try:
        if not politesse.autorise(c, url):
            return {"statut": "refuse_robots", "articles": []}
        r = c.get(url)
        e = {"http": r.status_code}
        if str(r.url) != url:
            e["url_finale"] = str(r.url)
        if r.status_code != 200:
            return {**e, "statut": "muet", "articles": []}
        a = lire_flux(r.content)
        return {**e, "statut": "ok" if a else "vide", "articles": a}
    except Exception as ex:
        return {"statut": "muet", "erreur": type(ex).__name__, "articles": []}


def principal() -> int:
    import httpx
    import politesse
    cat = catalogue()
    res, deja = {}, {}                                          # 0.10.484 : une adresse lue une seule fois par passage
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=30, follow_redirects=True) as c:
        for fid, f in (cat.get("flux") or {}).items():
            essais = []
            for cand in candidats(f):
                nouveau = cand["url"] not in deja
                if nouveau:
                    deja[cand["url"]] = lire_un(c, cand["url"])
                e = {"titre": cand["titre"], "url": cand["url"], "lu_le": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
                     **deja[cand["url"]]}
                essais.append({k: e.get(k) for k in ("url", "statut", "http", "erreur", "url_finale") if e.get(k) is not None})
                if nouveau:
                    time.sleep(PAUSE)
                if e["statut"] == "ok":
                    break
            if len(essais) > 1:
                e["essais"] = essais
            res[fid] = e
            print(f"{fid} : {e['statut']}" + (f" ({e.get('http')})" if e.get("http") not in (None, 200) else "")
                  + (f" [{e['erreur']}]" if e.get("erreur") else "")
                  + (f", {len(e['articles'])} articles" if e["articles"] else "")
                  + (f" — par le secours {e['url']}" if len(essais) > 1 and e["statut"] == "ok" else "")
                  + (f" — {len(essais)} adresses essayées" if len(essais) > 1 and e["statut"] != "ok" else ""), flush=True)
            for x in essais if e["statut"] != "ok" else []:
                print(f"    {x}", flush=True)
    REG.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = sum(1 for v in res.values() if v["statut"] == "ok")
    print(f"veille : {ok} flux lisibles sur {len(res)} ; muets : {sorted(k for k, v in res.items() if v['statut'] != 'ok')}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
