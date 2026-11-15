"""Indicateurs de niche (0.10.138, décision d'auteur du 2026-11-15, 16 h 54 : « fais-le aussi pour les prix
alimentaires, ça ne coûte rien d'essayer »). AUCUN modèle de langue, aucun coût, rien de posté.

Pour chaque couple (pays, jeu) du banc des indicateurs pertinents (registre/banc-indicateurs-frais.jsonl), mesuré
STRICTEMENT avant la date du jeu :
- wikimodif : activité de MODIFICATION (pas de consultation) des pages politiques du pays sur Wikipedia anglais
  (« Politics of X », « Human rights in X », « Censorship in X », « Elections in X ») : log((modifications des 30
  derniers jours + 1) / (moyenne par 30 jours des 180 jours précédents + 1)). D'après Oswald (CISS Munich, 2026) :
  les modifications de pages politiquement sensibles aident à prévoir les manifestations.
- prix_alim : prix alimentaires de détail du Programme alimentaire mondial (HDX, « WFP food prices for X ») :
  médiane, sur les couples marché × produit, de log(dernier prix connu / prix douze mois plus tôt), en monnaie locale,
  derniers prix d'au plus 120 jours avant la date. D'après Bellemare (AJAE 2015) : la hausse des prix alimentaires
  précède les émeutes.
Les deux passent ensuite par l'observatoire inductif (`induction.py`), lot après lot, avant tout pré-enregistrement.
Registre : registre/indicateurs-niche.jsonl.

    python indicateurs_niche.py
"""
from __future__ import annotations

import asyncio
import csv
import io
import json
import math
import statistics
import sys
from datetime import date, timedelta
from pathlib import Path

import httpx

SOURCE = Path("registre") / "banc-indicateurs-frais.jsonl"
FICHIER = Path("registre") / "indicateurs-niche.jsonl"
UA = {"User-Agent": "alphabet-situationnel-bot/1.0 (recherche ; GitHub Othman-Benbrahim)"}
PAGES = ("Politics of {p}", "Human rights in {p}", "Censorship in {p}", "Elections in {p}")


async def obtenir(c: httpx.AsyncClient, url: str, **kw):
    await asyncio.sleep(0.2)
    try:
        r = await c.get(url, timeout=30, **kw)
        return r if r.status_code == 200 else None
    except Exception:
        return None


async def wikimodif(c: httpx.AsyncClient, pays: str, d0: date) -> dict:
    debut, fin = d0 - timedelta(days=210), d0 - timedelta(days=1)
    par_jour: dict[str, int] = {}
    trouvees = 0
    for modele in PAGES:
        titre = modele.format(p=pays).replace(" ", "_")
        r = await obtenir(c, f"https://wikimedia.org/api/rest_v1/metrics/edits/per-page/en.wikipedia.org/{titre}/"
                             f"all-editor-types/daily/{debut:%Y%m%d}/{fin:%Y%m%d}")
        if r is None:
            continue
        res = ((r.json().get("items") or [{}])[0].get("results") or [])
        trouvees += 1
        for e in res:
            par_jour[e["timestamp"][:10]] = par_jour.get(e["timestamp"][:10], 0) + int(e.get("edits") or 0)
    if not trouvees:
        return {"present": False}
    recent = sum(v for k, v in par_jour.items() if k >= (d0 - timedelta(days=30)).isoformat())
    avant = sum(v for k, v in par_jour.items() if k < (d0 - timedelta(days=30)).isoformat()) / 6
    return {"present": True, "valeur": round(math.log((recent + 1) / (avant + 1)), 4), "pages": trouvees,
            "modifs_30j": recent, "moyenne_30j_avant": round(avant, 2)}


async def ressource_wfp(c: httpx.AsyncClient, pays: str, cache: dict) -> str | None:
    if pays in cache:
        return cache[pays]
    url = None
    r = await obtenir(c, "https://data.humdata.org/api/3/action/package_search",
                      params={"q": f'title:"WFP food prices" {pays}', "rows": 10})
    if r is not None:
        for pk in r.json().get("result", {}).get("results", []):
            if pays.lower() in pk.get("title", "").lower() and "food prices" in pk.get("title", "").lower():
                for res in pk.get("resources", []):
                    if str(res.get("format", "")).lower() == "csv" and "url" in res:
                        url = res["url"]
                        break
            if url:
                break
    cache[pays] = url
    return url


async def prix_alim(c: httpx.AsyncClient, pays: str, d0: date, cache: dict, cache_csv: dict) -> dict:
    url = await ressource_wfp(c, pays, cache)
    if not url:
        return {"present": False, "raison": "pas de jeu WFP"}
    if url not in cache_csv:
        r = await obtenir(c, url, follow_redirects=True)
        cache_csv[url] = r.text if r is not None else None
    texte = cache_csv[url]
    if not texte:
        return {"present": False, "raison": "téléchargement impossible"}
    series: dict[tuple, list[tuple[date, float]]] = {}
    for ligne in csv.DictReader(io.StringIO(texte)):
        try:
            d = date.fromisoformat(str(ligne.get("date", ""))[:10])
            p = float(ligne.get("price") or "nan")
        except ValueError:
            continue                                  # ligne d'étiquettes HXL ou date illisible
        if d >= d0 or not p > 0 or str(ligne.get("pricetype", "")).lower() != "retail":
            continue
        series.setdefault((ligne.get("market"), ligne.get("commodity"), ligne.get("unit")), []).append((d, p))
    changes = []
    for pts in series.values():
        pts.sort()
        d_last, p_last = pts[-1]
        if (d0 - d_last).days > 120:
            continue
        cible = d_last - timedelta(days=365)
        anciens = [x for x in pts if abs((x[0] - cible).days) <= 45]
        if anciens:
            p_old = min(anciens, key=lambda x: abs((x[0] - cible).days))[1]
            changes.append(math.log(p_last / p_old))
    if len(changes) < 3:
        return {"present": False, "raison": f"{len(changes)} séries utilisables"}
    return {"present": True, "valeur": round(statistics.median(changes), 4), "series": len(changes)}


async def principal() -> int:
    if not SOURCE.exists():
        print("Pas de registre source.")
        return 1
    lignes = [json.loads(l) for l in SOURCE.read_text(encoding="utf-8").splitlines() if l.strip()]
    deja = set()
    if FICHIER.exists():
        deja = {(x["pays"], x["jeu"]) for x in map(json.loads, FICHIER.read_text(encoding="utf-8").splitlines()) if x}
    couples = sorted({(x["pays"], x["jeu"]) for x in lignes if x.get("pays")} - deja)
    print(f"{len(couples)} couples pays × jeu à mesurer.")
    cache, cache_csv = {}, {}
    async with httpx.AsyncClient(headers=UA, follow_redirects=True) as c:
        with FICHIER.open("a", encoding="utf-8") as f:
            for pays, jeu in couples:
                d0 = date.fromisoformat(jeu)
                w = await wikimodif(c, pays, d0)
                p = await prix_alim(c, pays, d0, cache, cache_csv)
                f.write(json.dumps({"pays": pays, "jeu": jeu, "wikimodif": w, "prix_alim": p}, ensure_ascii=False) + "\n")
                f.flush()
                print(f"{pays[:22]:22s} {jeu} : wikimodif {w.get('valeur')} · prix_alim {p.get('valeur')} ({p.get('raison', '')})")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(principal()))
