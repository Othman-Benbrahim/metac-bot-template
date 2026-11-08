"""Puits de données (0.7.0) : des bases ouvertes interrogées directement, pour trois usages.

  1. Bras B : une SÉRIE datée que le code compte lui-même (combien de fenêtres de la durée de la question ont vu le
     seuil franchi). Le modèle choisit la série et le seuil dans un catalogue fermé ; il ne fournit aucun nombre.
  2. État présent : des faits datés et sourcés, donnés au lecteur à côté des résultats de recherche.
  3. Tests rétrospectifs : chaque connecteur est borné à la date d'information (`avant`). Wikipedia rend l'article
     tel qu'il était, la Wayback Machine la page telle qu'elle était, FRED la série telle qu'elle était publiée
     (millésimes ALFRED) ; les autres écartent tout point postérieur.

Chaque connecteur rend un relevé : {"source", "titre", "url", "debut", "points": [{"date", "valeur", "titre", "url",
"extrait"}]}. Un connecteur sans sa clé lève `SansCle` : il est sauté, jamais bloquant.

Clés (secrets GitHub) : FRED_API_KEY, FIRMS_MAP_KEY, UCDP_TOKEN (en attente), BLS_API_KEY (facultative).
Toutes les autres sources sont sans clé.
"""
from __future__ import annotations

import csv
import io
import json
import math
import os
import re
from datetime import date, datetime, timedelta, timezone
from typing import Awaitable, Callable

import httpx

DELAI = 40
MAX_POINTS = 5000
# Politique de Wikimedia : « nom/version (contact) bibliothèque/version », contact = une URL.
AGENT = (f"AlphabetForecastBot/0.7 (https://github.com/Othman-Benbrahim/metac-bot-template; open-source forecasting "
         f"research) httpx/{httpx.__version__}")


class SansCle(RuntimeError):
    """La clé du connecteur manque : il est sauté."""


def _cle(var: str) -> str:
    v = os.environ.get(var)
    if not v:
        raise SansCle(f"{var} absente")
    return v


async def _get(url: str, params: dict | None = None, headers: dict | None = None, json_: bool = True):
    async with httpx.AsyncClient(timeout=DELAI, follow_redirects=True,
                                 headers={"User-Agent": AGENT, **(headers or {})}) as c:
        r = await c.get(url, params=params)
        r.raise_for_status()
        return r.json() if json_ else r.text


def _jour(v) -> str | None:
    """Une date lisible en AAAA-MM-JJ (années et mois complétés au premier jour), ou None."""
    s = str(v or "").strip()
    m = re.match(r"(\d{4})(?:-?(\d{2}))?(?:-?(\d{2}))?", s)
    if not m:
        return None
    a, mo, j = m.group(1), m.group(2) or "01", m.group(3) or "01"
    if not ("01" <= mo <= "12" and "01" <= j <= "31"):
        return None
    return f"{a}-{mo}-{j}"


def _num(v) -> float | None:
    try:
        x = float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def _borne(points: list[dict], avant: date | None) -> list[dict]:
    garde = [p for p in points if p.get("date") and (avant is None or p["date"] <= avant.isoformat())]
    return sorted(garde, key=lambda p: p["date"])[-MAX_POINTS:]


def _releve(source: str, titre: str, url: str, points: list[dict], avant: date | None, debut: str | None = None,
            **extra) -> dict:
    pts = _borne(points, avant)
    return {"source": source, "titre": titre, "url": url, "debut": debut or (pts[0]["date"] if pts else None),
            "date_limite": avant.isoformat() if avant else None, "points": pts, **extra}


# --------------------------------------------------------------------------- séries (comptables)

async def fred(serie: str, avant: date | None = None, debut: str | None = None) -> dict:
    """FRED ; avec `avant`, les millésimes ALFRED : la série telle qu'elle était publiée ce jour-là."""
    p = {"series_id": serie, "api_key": _cle("FRED_API_KEY"), "file_type": "json"}
    if debut:
        p["observation_start"] = debut
    if avant:
        p.update(realtime_start=avant.isoformat(), realtime_end=avant.isoformat(), observation_end=avant.isoformat())
    d = await _get("https://api.stlouisfed.org/fred/series/observations", p)
    pts = [{"date": o["date"], "valeur": _num(o.get("value"))} for o in d.get("observations", [])]
    return _releve("FRED" + (" (ALFRED, millésime)" if avant else ""), serie,
                   f"https://fred.stlouisfed.org/series/{serie}", [x for x in pts if x["valeur"] is not None], avant,
                   debut)


async def banque_mondiale(pays: str, indicateur: str, avant: date | None = None) -> dict:
    d = await _get(f"https://api.worldbank.org/v2/country/{pays}/indicator/{indicateur}",
                   {"format": "json", "per_page": 500})
    lignes = d[1] if isinstance(d, list) and len(d) > 1 and d[1] else []
    # Une valeur annuelle n'est publiée qu'après l'année : bornée, on ne garde que les années closes avant `avant`.
    pts = [{"date": f"{x['date']}-12-31", "valeur": _num(x.get("value"))} for x in lignes if _num(x.get("value")) is not None]
    titre = (lignes[0].get("indicator") or {}).get("value", indicateur) if lignes else indicateur
    return _releve("Banque mondiale", f"{titre} — {pays}",
                   f"https://data.worldbank.org/indicator/{indicateur}?locations={pays}", pts, avant)


async def bce(cle: str, avant: date | None = None) -> dict:
    """Portail de données de la BCE (SDMX), ex. « EXR/D.USD.EUR.SP00.A » (flux/clé)."""
    flux, _, k = cle.partition("/")
    p = {"format": "csvdata"}
    if avant:
        p["endPeriod"] = avant.isoformat()
    t = await _get(f"https://data-api.ecb.europa.eu/service/data/{flux}/{k}", p, json_=False)
    pts = [{"date": _jour(r.get("TIME_PERIOD")), "valeur": _num(r.get("OBS_VALUE"))} for r in csv.DictReader(io.StringIO(t))]
    return _releve("BCE", cle, f"https://data.ecb.europa.eu/data/datasets/{flux}/{cle.replace('/', '.')}",
                   [x for x in pts if x["date"] and x["valeur"] is not None], avant)


async def eurostat(jeu: str, filtres: dict | None = None, avant: date | None = None) -> dict:
    """Eurostat (JSON-stat). Les filtres doivent réduire toutes les dimensions sauf le temps à une seule valeur."""
    p = {"format": "JSON", "lang": "en", **{k: v for k, v in (filtres or {}).items()}}
    d = await _get(f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{jeu}", p)
    ids, tailles = d.get("id") or [], d.get("size") or []
    if not ids or "time" not in ids:
        raise RuntimeError("Eurostat : réponse sans dimension temporelle")
    trop = [i for i, n in zip(ids, tailles) if i != "time" and n > 1]
    if trop:
        raise RuntimeError(f"Eurostat : filtres insuffisants, dimensions à plusieurs valeurs : {', '.join(trop)}")
    temps = d["dimension"]["time"]["category"]["index"]
    valeurs = d.get("value") or {}
    pts = []
    for periode, i in temps.items():
        v = valeurs.get(str(i)) if isinstance(valeurs, dict) else (valeurs[i] if i < len(valeurs) else None)
        j = _jour(periode.replace("-Q", "Q").replace("M", "-").replace("Q1", "-03").replace("Q2", "-06").replace("Q3", "-09")
                  .replace("Q4", "-12"))
        if j and _num(v) is not None:
            pts.append({"date": j, "valeur": _num(v)})
    return _releve("Eurostat", f"{d.get('label', jeu)} {json.dumps(filtres or {}, ensure_ascii=False)}",
                   f"https://ec.europa.eu/eurostat/databrowser/view/{jeu}/default/table", pts, avant)


async def tresor(jeu: str, champ: str, filtre: str | None = None, avant: date | None = None) -> dict:
    """Treasury FiscalData, ex. jeu « v2/accounting/od/avg_interest_rates », champ « avg_interest_rate_amt »."""
    f = [x for x in [filtre, f"record_date:lte:{avant.isoformat()}" if avant else None] if x]
    p = {"fields": f"record_date,{champ}", "sort": "-record_date", "page[size]": 5000}
    if f:
        p["filter"] = ",".join(f)
    d = await _get(f"https://api.fiscaldata.treasury.gov/services/api/fiscal_service/{jeu.strip('/')}", p)
    pts = [{"date": x.get("record_date"), "valeur": _num(x.get(champ))} for x in d.get("data", [])]
    return _releve("U.S. Treasury FiscalData", f"{jeu} · {champ}" + (f" · {filtre}" if filtre else ""),
                   "https://fiscaldata.treasury.gov/datasets/", [x for x in pts if x["valeur"] is not None], avant)


async def bls(serie: str, avant: date | None = None) -> dict:
    corps = {"seriesid": [serie]}
    if os.environ.get("BLS_API_KEY"):
        corps["registrationkey"] = os.environ["BLS_API_KEY"]
        corps.update(startyear=str((avant or date.today()).year - 19), endyear=str((avant or date.today()).year))
    async with httpx.AsyncClient(timeout=DELAI, headers={"User-Agent": AGENT}) as c:
        r = await c.post("https://api.bls.gov/publicAPI/v2/timeseries/data/", json=corps)
        r.raise_for_status()
        d = r.json()
    series = (d.get("Results") or {}).get("series") or []
    pts = []
    for x in (series[0].get("data") if series else []) or []:
        per = x.get("period", "")
        if per.startswith("M") and per != "M13":
            pts.append({"date": f"{x['year']}-{per[1:]}-01", "valeur": _num(x.get("value"))})
    return _releve("U.S. Bureau of Labor Statistics", serie, f"https://data.bls.gov/timeseries/{serie}",
                   [x for x in pts if x["valeur"] is not None], avant)


async def unhcr(pays_origine: str | None = None, pays_asile: str | None = None, champ: str = "refugees",
                avant: date | None = None) -> dict:
    fin = (avant or date.today()).year
    p = {"limit": 100, "yearFrom": 1990, "yearTo": fin, "cf_type": "ISO"}
    if pays_origine:
        p["coo"] = pays_origine
    if pays_asile:
        p["coa"] = pays_asile
    d = await _get("https://api.unhcr.org/population/v1/population/", p)
    pts = [{"date": f"{x.get('year')}-12-31", "valeur": _num(x.get(champ))} for x in d.get("items", [])]
    return _releve("UNHCR Refugee Data Finder", f"{champ} · origine {pays_origine or 'toutes'} · asile {pays_asile or 'tous'}",
                   "https://www.unhcr.org/refugee-statistics/", [x for x in pts if x["valeur"] is not None], avant)


async def fts(pays: str, annees: list[int] | None = None, avant: date | None = None) -> dict:
    """OCHA Financial Tracking Service : financement humanitaire reçu par année (pays ISO3)."""
    fin = (avant or date.today()).year
    pts = []
    for a in sorted(set(annees or range(fin - 5, fin + 1)))[-8:]:
        d = await _get("https://api.hpc.tools/v1/public/fts/flow", {"countryISO3": pays, "year": a})
        tot = ((d.get("data") or {}).get("incoming") or {}).get("fundingTotal")
        if _num(tot) is not None:
            pts.append({"date": f"{a}-12-31" if a < fin else (avant or date.today()).isoformat(), "valeur": _num(tot)})
    return _releve("OCHA FTS", f"financement humanitaire reçu (USD) · {pays}", "https://fts.unocha.org/", pts, avant)


async def ucdp(pays: str | None = None, debut: str = "2015-01-01", version: str | None = None,
               avant: date | None = None) -> dict:
    """UCDP GED (événements de violence, morts estimés). Exige UCDP_TOKEN : en attente, sauté sans lui."""
    jeton = _cle("UCDP_TOKEN")
    v = version or os.environ.get("UCDP_VERSION") or "25.1"
    p = {"pagesize": 1000, "StartDate": debut, "EndDate": (avant or date.today()).isoformat()}
    if pays:
        p["Country"] = pays
    pts, page, url = [], 0, f"https://ucdpapi.pcr.uu.se/api/gedevents/{v}"
    while url and page < 5:
        d = await _get(url, p if page == 0 else None, {"x-ucdp-access-token": jeton})
        for x in d.get("Result", []):
            pts.append({"date": _jour(x.get("date_start")), "valeur": _num(x.get("best")),
                        "titre": f"{x.get('conflict_name', '')} — {x.get('where_coordinates', '')}"})
        url, page = d.get("NextPageUrl") or None, page + 1
    return _releve("UCDP GED", f"événements de violence organisée · {pays or 'tous pays'}", "https://ucdp.uu.se/",
                   pts, avant, debut)


# --------------------------------------------------------------------------- événements datés (comptables aussi)

async def usgs_seismes(magnitude_min: float = 6.0, debut: str = "1990-01-01", latitude: float | None = None,
                       longitude: float | None = None, rayon_km: float | None = None, avant: date | None = None) -> dict:
    p = {"format": "geojson", "starttime": debut, "endtime": (avant or date.today()).isoformat(),
         "minmagnitude": magnitude_min, "limit": 20000, "orderby": "time-asc"}
    if latitude is not None and longitude is not None and rayon_km:
        p.update(latitude=latitude, longitude=longitude, maxradiuskm=rayon_km)
    d = await _get("https://earthquake.usgs.gov/fdsnws/event/1/query", p)
    pts = []
    for f in d.get("features", []):
        pr = f.get("properties") or {}
        t = datetime.fromtimestamp((pr.get("time") or 0) / 1000, tz=timezone.utc).date().isoformat()
        pts.append({"date": t, "valeur": _num(pr.get("mag")), "titre": pr.get("place"), "url": pr.get("url")})
    return _releve("USGS", f"séismes de magnitude ≥ {magnitude_min}", "https://earthquake.usgs.gov/", pts, avant, debut)


async def gdacs(types: str = "EQ;TC;FL;VO;DR;WF;TS", debut: str | None = None, alerte: str = "Orange;Red",
                avant: date | None = None) -> dict:
    fin = avant or date.today()
    p = {"eventlist": types.replace(",", ";"), "fromDate": debut or (fin - timedelta(days=365)).isoformat(),
         "toDate": fin.isoformat(), "alertlevel": alerte.replace(",", ";")}
    d = await _get("https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH", p)
    pts = []
    for f in d.get("features", []):
        pr = f.get("properties") or {}
        pts.append({"date": _jour(pr.get("fromdate")), "valeur": None,
                    "titre": f"{pr.get('eventtype')} {pr.get('alertlevel')} — {pr.get('name') or pr.get('description')}"
                             f" ({pr.get('country') or ''})",
                    "url": (pr.get("url") or {}).get("report") if isinstance(pr.get("url"), dict) else pr.get("url")})
    return _releve("GDACS (ONU / Commission européenne, JRC)", f"alertes {alerte} · {types}", "https://www.gdacs.org/",
                   pts, avant, p["fromDate"])


async def eonet(categorie: str | None = None, jours: int = 60, avant: date | None = None) -> dict:
    p = {"status": "all", "days": jours}
    if avant:
        p = {"status": "all", "start": (avant - timedelta(days=jours)).isoformat(), "end": avant.isoformat()}
    if categorie:
        p["category"] = categorie
    d = await _get("https://eonet.gsfc.nasa.gov/api/v3/events", p)
    pts = []
    for e in d.get("events", []):
        g = e.get("geometry") or [{}]
        src = e.get("sources") or [{}]
        pts.append({"date": _jour(g[0].get("date")), "valeur": None, "titre": e.get("title"), "url": src[0].get("url")})
    return _releve("NASA EONET", f"événements naturels · {categorie or 'toutes catégories'}",
                   "https://eonet.gsfc.nasa.gov/", pts, avant)


async def federal_register(terme: str, type_doc: str | None = None, avant: date | None = None) -> dict:
    p = {"conditions[term]": terme, "order": "newest", "per_page": 100,
         "fields[]": ["title", "publication_date", "html_url", "abstract", "type"]}
    if type_doc:
        p["conditions[type][]"] = type_doc
    if avant:
        p["conditions[publication_date][lte]"] = avant.isoformat()
    d = await _get("https://www.federalregister.gov/api/v1/documents.json", p)
    pts = [{"date": x.get("publication_date"), "valeur": None, "titre": f"[{x.get('type')}] {x.get('title')}",
            "url": x.get("html_url"), "extrait": (x.get("abstract") or "")[:300]} for x in d.get("results", [])]
    return _releve("Federal Register (États-Unis)", f"documents « {terme} »", "https://www.federalregister.gov/", pts, avant)


async def firms(pays: str, jours: int = 10, capteur: str = "VIIRS_SNPP_NRT", avant: date | None = None) -> dict:
    """NASA FIRMS : nombre de détections de feux actifs par jour (pays ISO3, 1 à 10 jours)."""
    cle = _cle("FIRMS_MAP_KEY")
    jours = max(1, min(10, int(jours)))
    url = f"https://firms.modaps.eosdis.nasa.gov/api/country/csv/{cle}/{capteur}/{pays}/{jours}"
    if avant:
        url += f"/{(avant - timedelta(days=jours - 1)).isoformat()}"
    t = await _get(url, json_=False)
    compte: dict[str, int] = {}
    for r in csv.DictReader(io.StringIO(t)):
        j = _jour(r.get("acq_date"))
        if j:
            compte[j] = compte.get(j, 0) + 1
    pts = [{"date": j, "valeur": float(n)} for j, n in compte.items()]
    return _releve("NASA FIRMS", f"détections de feux actifs par jour · {pays} · {capteur}",
                   "https://firms.modaps.eosdis.nasa.gov/", pts, avant)


async def wikidata_poste(poste: str, avant: date | None = None) -> dict:
    """Titulaires successifs d'un poste (P39), avec dates de début et de fin : les changements de titulaire."""
    qid = poste if re.fullmatch(r"Q\d+", poste) else None
    if qid is None:
        s = await _get("https://www.wikidata.org/w/api.php", {"action": "wbsearchentities", "search": poste,
                                                              "language": "en", "format": "json", "limit": 1})
        if not s.get("search"):
            raise RuntimeError(f"Wikidata : poste introuvable « {poste} »")
        qid = s["search"][0]["id"]
    req = f"""SELECT ?p ?pLabel ?debut ?fin WHERE {{ ?p p:P39 ?st . ?st ps:P39 wd:{qid} ; pq:P580 ?debut .
              OPTIONAL {{ ?st pq:P582 ?fin }} SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }}"""
    d = await _get("https://query.wikidata.org/sparql", {"query": req, "format": "json"},
                   {"Accept": "application/sparql-results+json"})
    pts = []
    for b in d.get("results", {}).get("bindings", []):
        fin = _jour((b.get("fin") or {}).get("value"))
        pts.append({"date": _jour(b["debut"]["value"]), "valeur": None,
                    "titre": f"{b['pLabel']['value']} entre en fonction" + (f" (fin : {fin})" if fin else ""),
                    "url": b["p"]["value"]})
    return _releve("Wikidata", f"titulaires du poste {qid} ({poste})", f"https://www.wikidata.org/wiki/{qid}", pts, avant)


# --------------------------------------------------------------------------- textes à une date

def _texte_wiki(w: str) -> str:
    w = re.sub(r"\{\{[^{}]*\}\}", "", w)
    w = re.sub(r"\{\{[^{}]*\}\}", "", w)
    w = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", w, flags=re.S)
    w = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", w)
    w = re.sub(r"<[^>]+>|'''?|\[https?://\S+ ([^\]]*)\]", lambda m: m.group(1) or "", w)
    return re.sub(r"\n{3,}", "\n\n", w).strip()


async def wikipedia(titre: str, langue: str = "en", avant: date | None = None) -> dict:
    """L'article tel qu'il était à la date `avant` (dernière révision antérieure), sinon tel qu'il est."""
    p = {"action": "query", "prop": "revisions", "titles": titre, "rvlimit": 1, "rvprop": "timestamp|ids|content",
         "rvslots": "main", "format": "json", "formatversion": 2, "redirects": 1}
    if avant:
        p.update(rvdir="older", rvstart=f"{avant.isoformat()}T23:59:59Z")
    d = await _get(f"https://{langue}.wikipedia.org/w/api.php", p)
    pages = (d.get("query") or {}).get("pages") or []
    revs = pages[0].get("revisions") if pages else None
    if not revs:
        raise RuntimeError(f"Wikipedia : aucune révision de « {titre} » avant {avant}")
    r = revs[0]
    texte = _texte_wiki(((r.get("slots") or {}).get("main") or {}).get("content", ""))
    url = f"https://{langue}.wikipedia.org/w/index.php?oldid={r['revid']}"
    return _releve("Wikipedia", f"{pages[0].get('title', titre)} (révision du {r['timestamp'][:10]})", url,
                   [{"date": r["timestamp"][:10], "valeur": None, "titre": pages[0].get("title", titre), "url": url,
                     "extrait": texte[:6000]}], avant)


async def wayback(url: str, avant: date | None = None) -> dict:
    """La dernière capture de la page ANTÉRIEURE à `avant` (Wayback Machine), en texte."""
    fin = (avant or date.today()).strftime("%Y%m%d") + "235959"
    lignes = await _get("https://web.archive.org/cdx/search/cdx",
                        {"url": url, "to": fin, "output": "json", "limit": -1, "filter": "statuscode:200",
                         "fl": "timestamp,original"})
    if not isinstance(lignes, list) or len(lignes) < 2:
        raise RuntimeError(f"Wayback : aucune capture de {url} avant {fin[:8]}")
    ts, orig = lignes[-1][0], lignes[-1][1]
    page = await _get(f"https://web.archive.org/web/{ts}id_/{orig}", json_=False)
    page = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", page, flags=re.S | re.I)
    texte = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page)).strip()
    j = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"
    lien = f"https://web.archive.org/web/{ts}/{orig}"
    return _releve("Wayback Machine (Internet Archive)", f"{orig} (capture du {j})", lien,
                   [{"date": j, "valeur": None, "titre": orig, "url": lien, "extrait": texte[:6000]}], avant)


async def hdx(terme: str, avant: date | None = None) -> dict:
    """Catalogue HDX (OCHA) : jeux de données humanitaires publics, avec leur date de mise à jour."""
    d = await _get("https://data.humdata.org/api/3/action/package_search", {"q": terme, "rows": 10, "sort": "metadata_modified desc"})
    pts = [{"date": _jour(x.get("last_modified") or x.get("metadata_modified")), "valeur": None,
            "titre": f"{x.get('title')} ({(x.get('organization') or {}).get('title', '')})",
            "url": f"https://data.humdata.org/dataset/{x.get('name')}", "extrait": (x.get("notes") or "")[:300]}
           for x in (d.get("result") or {}).get("results", [])]
    return _releve("HDX (OCHA)", f"jeux de données « {terme} »", "https://data.humdata.org/", pts, avant)


# --------------------------------------------------------------------------- catalogue

CATALOGUE: dict[str, dict] = {
    "fred": {"fn": fred, "cle": "FRED_API_KEY", "comptable": True,
             "params": '{"serie": "identifiant FRED, ex. UNRATE, CPIAUCSL, DGS10, FEDFUNDS", "debut": "AAAA-MM-JJ facultatif"}',
             "pour": "séries économiques et financières américaines (taux, chômage, prix, dette, marchés)"},
    "banque_mondiale": {"fn": banque_mondiale, "comptable": True,
                        "params": '{"pays": "ISO3 ou WLD", "indicateur": "code, ex. NY.GDP.MKTP.KD.ZG"}',
                        "pour": "indicateurs annuels par pays (PIB, inflation, population, dette)"},
    "bce": {"fn": bce, "comptable": True, "params": '{"cle": "flux/clé SDMX, ex. EXR/D.USD.EUR.SP00.A"}',
            "pour": "taux de change, taux directeurs et monnaie de la zone euro"},
    "eurostat": {"fn": eurostat, "comptable": True,
                 "params": '{"jeu": "code, ex. une_rt_m", "filtres": {"geo": "FR", "...": "une valeur par dimension"}}',
                 "pour": "statistiques européennes (chômage, inflation HICP, PIB) par pays"},
    "tresor": {"fn": tresor, "comptable": True,
               "params": '{"jeu": "ex. v2/accounting/od/avg_interest_rates", "champ": "ex. avg_interest_rate_amt", '
                         '"filtre": "facultatif, ex. security_desc:eq:Total Marketable"}',
               "pour": "finances fédérales américaines (dette, taux moyens, dépenses)"},
    "bls": {"fn": bls, "comptable": True, "params": '{"serie": "identifiant BLS, ex. CUUR0000SA0, LNS14000000"}',
            "pour": "emploi et prix américains"},
    "unhcr": {"fn": unhcr, "comptable": True,
              "params": '{"pays_origine": "ISO3 facultatif", "pays_asile": "ISO3 facultatif", "champ": "refugees|asylum_seekers|idps"}',
              "pour": "réfugiés et déplacés par année"},
    "fts": {"fn": fts, "comptable": True, "params": '{"pays": "ISO3", "annees": [2021, 2022, "..."]}',
            "pour": "financement humanitaire reçu par année"},
    "ucdp": {"fn": ucdp, "cle": "UCDP_TOKEN", "comptable": True,
             "params": '{"pays": "nom ou code UCDP facultatif", "debut": "AAAA-MM-JJ"}',
             "pour": "événements de violence organisée et morts estimés (à agréger par mois ou par an)"},
    "usgs_seismes": {"fn": usgs_seismes, "comptable": True,
                     "params": '{"magnitude_min": 6.0, "debut": "AAAA-MM-JJ", "latitude": "…", "longitude": "…", "rayon_km": "…"}',
                     "pour": "séismes (dates et magnitudes)"},
    "gdacs": {"fn": gdacs, "comptable": True,
              "params": '{"types": "EQ;TC;FL;VO;DR;WF;TS", "debut": "AAAA-MM-JJ", "alerte": "Orange;Red"}',
              "pour": "alertes de catastrophes (séismes, cyclones, inondations, volcans, sécheresses, feux, tsunamis)"},
    "eonet": {"fn": eonet, "comptable": True,
              "params": '{"categorie": "wildfires|severeStorms|volcanoes|floods|… facultatif", "jours": 60}',
              "pour": "événements naturels en cours (état présent)"},
    "federal_register": {"fn": federal_register, "comptable": True,
                         "params": '{"terme": "mots-clés", "type_doc": "PRESDOCU|RULE|PRORULE|NOTICE facultatif"}',
                         "pour": "décrets, règles et documents présidentiels américains"},
    "firms": {"fn": firms, "cle": "FIRMS_MAP_KEY", "comptable": True,
              "params": '{"pays": "ISO3", "jours": "1 à 10"}', "pour": "feux actifs détectés par satellite (10 derniers jours)"},
    "wikidata_poste": {"fn": wikidata_poste, "comptable": True,
                       "params": '{"poste": "intitulé en anglais ou QID, ex. President of France"}',
                       "pour": "titulaires successifs d'un poste (durées en fonction, changements)"},
    "wikipedia": {"fn": wikipedia, "comptable": False, "params": '{"titre": "titre exact de l\'article", "langue": "en"}',
                  "pour": "l'article tel qu'il était à la date d'information"},
    "wayback": {"fn": wayback, "comptable": False, "params": '{"url": "adresse exacte d\'une page"}',
                "pour": "une page officielle telle qu'elle était à la date d'information"},
    "hdx": {"fn": hdx, "comptable": False, "params": '{"terme": "mots-clés"}', "pour": "jeux de données humanitaires (HDX)"},
}


def catalogue_texte(env=os.environ) -> str:
    lignes = []
    for nom, c in CATALOGUE.items():
        if c.get("cle") and not env.get(c["cle"]):
            continue                                        # sans sa clé, la source n'est pas proposée
        lignes.append(f"- {nom}{' (comptable)' if c['comptable'] else ''} : {c['pour']}. Paramètres : {c['params']}")
    return "\n".join(lignes)


async def appeler(source: str, params: dict, avant: date | None) -> dict:
    c = CATALOGUE.get(source)
    if c is None:
        raise RuntimeError(f"source inconnue : {source}")
    import inspect
    admis = set(inspect.signature(c["fn"]).parameters) - {"avant"}
    return await c["fn"](**{k: v for k, v in (params or {}).items() if k in admis}, avant=avant)


def texte_releve(r: dict, n: int = 40) -> str:
    """Le relevé en clair pour le modèle : les n derniers points, datés et sourcés."""
    pts = r.get("points") or []
    tete = f"{r['source']} — {r['titre']} — {r['url']} ({len(pts)} points" + (
        f", du {pts[0]['date']} au {pts[-1]['date']}" if pts else "") + (
        f" ; borné au {r['date_limite']}" if r.get("date_limite") else "") + ")"
    corps = []
    for p in pts[-n:]:
        bits = [f"[{p['date']}]"]
        if p.get("valeur") is not None:
            bits.append(f"{p['valeur']:g}")
        if p.get("titre"):
            bits.append(str(p["titre"]))
        if p.get("url") and p.get("url") != r["url"]:
            bits.append(f"— {p['url']}")
        corps.append(" ".join(bits) + (f"\n{p['extrait']}" if p.get("extrait") else ""))
    return tete + "\n" + "\n".join(corps)


# --------------------------------------------------------------------------- le compte (bras B)

def _agreger(points: list[dict], agregation: str | None) -> list[dict]:
    if agregation not in ("mois", "annee"):
        return points
    cles: dict[str, float] = {}
    for p in points:
        k = p["date"][:7] + "-01" if agregation == "mois" else p["date"][:4] + "-01-01"
        cles[k] = cles.get(k, 0.0) + (p["valeur"] if p.get("valeur") is not None else 1.0)
    return [{"date": k, "valeur": v} for k, v in sorted(cles.items())]


def _remplit(v: float | None, seuil: float | None, sens: str) -> bool:
    if seuil is None:
        return True                                         # un événement suffit
    if v is None:
        return False
    return v >= seuil if sens == ">=" else v > seuil if sens == ">" else v <= seuil if sens == "<=" else v < seuil


def compter(releve: dict, fenetre_jours: int, mode: str = "atteint", seuil: float | None = None, sens: str = ">=",
            agregation: str | None = None, fin: date | None = None) -> dict:
    """Fenêtres DISJOINTES de la durée de la question, comptées à rebours depuis `fin` jusqu'au début du relevé.

    mode « evenement » : la fenêtre compte si au moins un point (filtré par le seuil s'il y en a un) y tombe ;
    mode « atteint »   : si au moins une valeur de la fenêtre remplit la condition ;
    mode « franchit »  : si la condition n'était PAS remplie au début de la fenêtre et l'est ensuite.
    Fréquence = k / n ; à 0 ou n, ramenée à 1/(2n) ou 1 - 1/(2n) (le moteur exige ]0, 1[). Moins de 5 fenêtres :
    pas de fréquence."""
    pts = _agreger([p for p in releve.get("points") or [] if p.get("date")], agregation)
    if mode not in ("evenement", "atteint", "franchit"):
        return {"frequence": None, "motif": f"mode inconnu : {mode}"}
    if not pts or fenetre_jours < 1:
        return {"frequence": None, "motif": "relevé vide"}
    fin = fin or date.fromisoformat(releve.get("date_limite") or pts[-1]["date"])
    debut = date.fromisoformat(_jour(releve.get("debut")) or pts[0]["date"])
    W = timedelta(days=int(fenetre_jours))
    k = n = 0
    b = fin
    while b - W >= debut:
        a = b - W
        dans = [p for p in pts if a.isoformat() < p["date"] <= b.isoformat()]
        if mode == "evenement":
            ok = any(_remplit(p.get("valeur"), seuil, sens) for p in dans)
        else:
            avant = [p for p in pts if p["date"] <= a.isoformat()]
            if mode == "franchit" and not avant:
                b = a
                continue                                    # pas d'état initial connu : fenêtre non comptée
            ok = any(_remplit(p.get("valeur"), seuil, sens) for p in dans)
            if mode == "franchit":
                ok = ok and not _remplit(avant[-1].get("valeur"), seuil, sens)
        n += 1
        k += 1 if ok else 0
        b = a
    if n < 5:
        return {"frequence": None, "k": k, "n": n,
                "motif": f"trop peu de fenêtres de {fenetre_jours} jours dans le relevé ({n} < 5)"}
    f = k / n
    if k == 0:
        f = 1 / (2 * n)
    elif k == n:
        f = 1 - 1 / (2 * n)
    return {"frequence": f, "k": k, "n": n, "fenetre_jours": int(fenetre_jours), "mode": mode, "seuil": seuil,
            "sens": sens, "agregation": agregation, "periode": f"{debut.isoformat()}/{fin.isoformat()}",
            "dernier_point": pts[-1]["date"]}


Llm = Callable[[str], Awaitable[str]]
