"""Puits de données (0.7.0) : des bases ouvertes interrogées directement, pour trois usages.

  1. Bras B : une SÉRIE datée que le code compte lui-même (combien de fenêtres de la durée de la question ont vu le
     seuil franchi). Le modèle choisit la série et le seuil dans un catalogue fermé ; il ne fournit aucun nombre.
  2. État présent : des faits datés et sourcés, donnés au lecteur à côté des résultats de recherche.
  3. Tests rétrospectifs : chaque connecteur est borné à la date d'information (`avant`). Wikipedia rend l'article
     tel qu'il était, la Wayback Machine la page telle qu'elle était, FRED la série telle qu'elle était publiée
     (millésimes ALFRED) ; les autres écartent tout point postérieur.

Chaque connecteur rend un relevé : {"source", "titre", "url", "debut", "points": [{"date", "valeur", "titre", "url",
"extrait"}]}. Un connecteur sans sa clé lève `SansCle` : il est sauté, jamais bloquant.

Clés (secrets GitHub) : FRED_API_KEY, FIRMS_MAP_KEY, UCDP_TOKEN (reçue le 2026-11-13 ; 5 000 requêtes par jour), BLS_API_KEY (facultative).
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


SECRETS_URL = re.compile(r"((?:api_?key|apikey|key|token|access_?token|appid|app_key|secret)=)[^&\s'\"]+", re.I)


def masquer(texte: str) -> str:
    """0.10.17 : retire les clés d'API des URL avant tout message d'erreur (le registre est public)."""
    return SECRETS_URL.sub(r"\1***", str(texte))


class ErreurSource(RuntimeError):
    """Erreur HTTP d'une source, message sans clé."""


def _verifier(r) -> None:
    try:
        r.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise ErreurSource(masquer(e)) from None


async def _get(url: str, params: dict | None = None, headers: dict | None = None, json_: bool = True):
    async with httpx.AsyncClient(timeout=DELAI, follow_redirects=True,
                                 headers={"User-Agent": AGENT, **(headers or {})}) as c:
        r = await c.get(url, params=params)
        _verifier(r)
        return r.json() if json_ else r.text


async def _get_octets(url: str) -> bytes:
    """0.10.10 : un fichier binaire (archive ZIP)."""
    async with httpx.AsyncClient(timeout=DELAI, follow_redirects=True, headers={"User-Agent": AGENT}) as c:
        r = await c.get(url)
        _verifier(r)
        return r.content


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


def _publie_le(p: dict, retard: int) -> str:
    """0.8.0 (audit M-05) : la date à laquelle un point était CONNU. La date d'un point est celle de sa période (un mois,
    une année) ; la valeur n'est publiée qu'après. Un point peut porter sa propre date de publication (`publie_le`)."""
    if p.get("publie_le"):
        return p["publie_le"]
    return (date.fromisoformat(p["date"]) + timedelta(days=retard)).isoformat() if retard else p["date"]


def _borne(points: list[dict], avant: date | None, retard: int = 0) -> list[dict]:
    garde = [p for p in points if p.get("date") and (avant is None or _publie_le(p, retard) <= avant.isoformat())]
    return sorted(garde, key=lambda p: p["date"])[-MAX_POINTS:]


def _releve(source: str, titre: str, url: str, points: list[dict], avant: date | None, debut: str | None = None,
            retard: int = 0, **extra) -> dict:
    pts = _borne(points, avant, retard)
    if retard:
        extra.setdefault("retard_publication_jours", retard)
    return {"source": source, "titre": titre, "url": url, "debut": debut or (pts[0]["date"] if pts else None),
            "date_limite": avant.isoformat() if avant else None, "points": pts, **extra}


# --------------------------------------------------------------------------- séries (comptables)

async def fred(serie: str, avant: date | None = None, debut: str | None = None) -> dict:
    """FRED ; avec `avant`, les millésimes ALFRED : la série telle qu'elle était publiée ce jour-là."""
    p = {"series_id": serie, "api_key": _cle("FRED_API_KEY"), "file_type": "json"}
    if debut:
        p["observation_start"] = debut
    if avant:
        # 0.10.17 : FRED compte les jours à l'heure de Saint-Louis ; un millésime daté d'« aujourd'hui » en UTC peut être
        # dans son futur (erreur 400). On lit donc au plus le millésime de la veille : jamais d'information postérieure.
        rt = min(avant, datetime.now(timezone.utc).date() - timedelta(days=1))
        p.update(realtime_start=rt.isoformat(), realtime_end=rt.isoformat(), observation_end=avant.isoformat())
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
    # Indicateurs du Développement dans le monde : l'année N paraît vers juillet de N+1 (≈ 200 jours après le 31/12).
    return _releve("Banque mondiale", f"{titre} — {pays}",
                   f"https://data.worldbank.org/indicator/{indicateur}?locations={pays}", pts, avant, retard=200,
                   revisions="valeurs actuelles, sans millésime : révisions possibles")


async def bce(cle: str, avant: date | None = None) -> dict:
    """Portail de données de la BCE (SDMX), ex. « EXR/D.USD.EUR.SP00.A » (flux/clé)."""
    flux, _, k = cle.partition("/")
    p = {"format": "csvdata"}
    if avant:
        p["endPeriod"] = avant.isoformat()
    t = await _get(f"https://data-api.ecb.europa.eu/service/data/{flux}/{k}", p, json_=False)
    pts = []
    for r in csv.DictReader(io.StringIO(t)):
        per, j = str(r.get("TIME_PERIOD") or ""), None
        m = re.fullmatch(r"(\d{4})-?Q([1-4])", per)
        if m:                                        # trimestre : connu ≈ 60 jours après sa fin
            fin_t = date(int(m.group(1)), 3 * int(m.group(2)), 1) + timedelta(days=31)
            j, pub = date(int(m.group(1)), 3 * int(m.group(2)) - 2, 1).isoformat(), (fin_t + timedelta(days=60)).isoformat()
        else:
            j = _jour(per)
            if j is None:
                continue
            jours_ = {10: 1, 7: 35, 4: 400}.get(len(per), 1)   # jour : le lendemain ; mois : +35 j ; année : +400 j
            pub = (date.fromisoformat(j) + timedelta(days=jours_)).isoformat()
        pts.append({"date": j, "valeur": _num(r.get("OBS_VALUE")), "publie_le": pub})
    return _releve("BCE", cle, f"https://data.ecb.europa.eu/data/datasets/{flux}/{cle.replace('/', '.')}",
                   [x for x in pts if x["date"] and x["valeur"] is not None], avant,
                   revisions="publication estimée selon la fréquence (jour +1, mois +35, trimestre +60 après la fin)")


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
            # 0.8.0 (audit M-05) : connu ≈ 60 j après le début du mois (mois, ou dernier mois du trimestre), ≈ 450 j
            # après le début d'une année.
            retard_ = 450 if re.fullmatch(r"\d{4}", periode) else 60
            pts.append({"date": j, "valeur": _num(v),
                        "publie_le": (date.fromisoformat(j) + timedelta(days=retard_)).isoformat()})
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
                   "https://fiscaldata.treasury.gov/datasets/", [x for x in pts if x["valeur"] is not None], avant,
                   retard=15, revisions="valeurs actuelles, sans millésime : révisions possibles")


async def bls(serie: str, avant: date | None = None) -> dict:
    corps = {"seriesid": [serie]}
    if os.environ.get("BLS_API_KEY"):
        corps["registrationkey"] = os.environ["BLS_API_KEY"]
        corps.update(startyear=str((avant or date.today()).year - 19), endyear=str((avant or date.today()).year))
    async with httpx.AsyncClient(timeout=DELAI, headers={"User-Agent": AGENT}) as c:
        r = await c.post("https://api.bls.gov/publicAPI/v2/timeseries/data/", json=corps)
        r.raise_for_status()
        # 0.10.1 : la réponse du BLS contient parfois des caractères de contrôle dans ses messages (sonde du 10/11).
        d = json.loads(r.text, strict=False)
    series = (d.get("Results") or {}).get("series") or []
    pts = []
    for x in (series[0].get("data") if series else []) or []:
        per = x.get("period", "")
        if per.startswith("M") and per != "M13":
            pts.append({"date": f"{x['year']}-{per[1:]}-01", "valeur": _num(x.get("value"))})
    # Le mois M paraît vers le milieu de M+1 : ≈ 45 jours après le 1er du mois.
    return _releve("U.S. Bureau of Labor Statistics", serie, f"https://data.bls.gov/timeseries/{serie}",
                   [x for x in pts if x["valeur"] is not None], avant, retard=45,
                   revisions="valeurs actuelles, sans millésime : révisions possibles (FRED/ALFRED les a)")


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
    # Global Trends : l'année N paraît vers la mi-juin de N+1 (≈ 170 jours).
    return _releve("UNHCR Refugee Data Finder", f"{champ} · origine {pays_origine or 'toutes'} · asile {pays_asile or 'tous'}",
                   "https://www.unhcr.org/refugee-statistics/", [x for x in pts if x["valeur"] is not None], avant,
                   retard=170)


async def fts(pays: str, annees: list[int] | None = None, avant: date | None = None) -> dict:
    """OCHA Financial Tracking Service : financement humanitaire reçu par année (pays ISO3). Totaux VIVANTS, sans
    millésime : inutilisable pour une date d'information passée (0.8.0, audit M-05)."""
    if avant is not None and avant < date.today() - timedelta(days=7):
        raise RuntimeError("FTS : totaux vivants sans millésime, refusés pour une date d'information passée")
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
    """UCDP GED (événements de violence, morts estimés). Exige UCDP_TOKEN (en-tête x-ucdp-access-token ; 5 000 requêtes
    par jour, chaque page compte, erreurs comprises) ; sauté sans lui."""
    jeton = _cle("UCDP_TOKEN")
    v = version or os.environ.get("UCDP_VERSION") or "26.1"   # 0.10.65 : version donnée par UCDP avec la clé
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
    # 0.10.1 : les produits « temps réel » (NRT) ne couvrent que les derniers mois ; au-delà, le produit standard (SP)
    # (sonde du 10/11 : 400 pour une date de juin en NRT).
    if avant and (date.today() - avant).days > 60 and capteur.endswith("_NRT"):
        capteur = capteur[:-4] + "_SP"
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
        if fin and avant is not None and fin > avant.isoformat():
            fin = None                                    # 0.8.0 (audit M-06) : une fin de mandat future ne se voit pas
        pts.append({"date": _jour(b["debut"]["value"]), "valeur": None,
                    "titre": f"{b['pLabel']['value']} entre en fonction" + (f" (fin : {fin})" if fin else ""),
                    "url": b["p"]["value"]})
    return _releve("Wikidata", f"titulaires du poste {qid} ({poste})", f"https://www.wikidata.org/wiki/{qid}", pts, avant)


# --------------------------------------------------------------------------- textes à une date

def _texte_wiki(w: str) -> str:
    for _ in range(12):                                   # modèles imbriqués (infobox) : du plus intérieur au plus extérieur
        w, n = re.subn(r"\{\{[^{}]*\}\}", "", w)
        if not n:
            break
    w = re.sub(r"\{\|.*?\|\}", "", w, flags=re.S)         # tableaux
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


# --------------------------------------------------------------------------- 0.10.0 : quatre sources de plus

async def gaza(champ: str = "killed_cum", zone: str = "gaza", avant: date | None = None) -> dict:
    """Tech for Palestine : séries quotidiennes reprises des rapports officiels (Gaza : ministère de la Santé de Gaza ;
    Cisjordanie : OCHA). Valeurs actuelles, sans millésime : un rapport peut être corrigé après coup."""
    fichier = "west_bank_daily.json" if zone == "cisjordanie" else "casualties_daily.json"
    d = await _get(f"https://data.techforpalestine.org/api/v2/{fichier}")
    lignes = d if isinstance(d, list) else []
    pts = []
    for x in lignes:
        if not isinstance(x, dict):
            continue
        j = _jour(x.get("report_date"))
        v = _num(x.get(champ))
        if j and v is not None:
            pts.append({"date": j, "valeur": v})
    primaire = "OCHA (Cisjordanie)" if zone == "cisjordanie" else "ministère de la Santé de Gaza"
    return _releve(f"Tech for Palestine, d'après {primaire}", f"{champ} — {zone}",
                   f"https://data.techforpalestine.org/api/v2/{fichier}", pts, avant, retard=1,
                   revisions="valeurs actuelles, sans millésime : corrections possibles")


async def sanctions_ue(terme: str | None = None, programme: str | None = None, avant: date | None = None) -> dict:
    """Liste consolidée des sanctions financières de l'UE (fichier ouvert de la Commission) : une entrée par personne ou
    entité, datée de sa désignation. La liste ne garde que les désignations EN VIGUEUR : une radiation disparaît,
    d'où un biais de survie en rétrospectif (signalé dans le relevé)."""
    t = await _get("https://webgate.ec.europa.eu/fsd/fsf/public/files/csvFullSanctionsList_1_1/content",
                   {"token": "dG9rZW4tMjAxNw"}, json_=False)
    lecteur = csv.DictReader(io.StringIO(t.lstrip("\ufeff")), delimiter=";")
    champs = {k.lower(): k for k in (lecteur.fieldnames or [])}

    def col(*mots: str) -> str | None:
        return next((v for k, v in champs.items() if all(m in k for m in mots)), None)
    c_id, c_nom = col("logical", "id"), col("wholename")
    c_date, c_pub = col("designation", "date"), col("publication", "date")
    c_prog, c_type = col("programme"), col("subjecttype")
    vus: dict[str, dict] = {}
    for r in lecteur:
        ident = (r.get(c_id) if c_id else None) or r.get(c_nom or "", "")
        nom, prog = (r.get(c_nom) or "").strip() if c_nom else "", (r.get(c_prog) or "").strip() if c_prog else ""
        if programme and programme.upper() not in prog.upper():
            continue
        if terme and terme.lower() not in nom.lower() and ident not in vus:
            continue
        # 0.10.1 : la date de désignation manque souvent (sonde : 158 entrées seulement) ; repli sur la date de
        # publication du règlement qui l'inscrit.
        j = (_jour(r.get(c_date)) if c_date else None) or (_jour(r.get(c_pub)) if c_pub else None)
        e = vus.setdefault(ident, {"date": j, "valeur": None, "noms": set(), "programme": prog,
                                   "type": (r.get(c_type) or "") if c_type else ""})
        if j and (not e["date"] or j < e["date"]):
            e["date"] = j
        if nom:
            e["noms"].add(nom)
    pts = [{"date": e["date"], "valeur": None,
            "titre": f"{' / '.join(sorted(e['noms'])[:2])} [{e['programme']}{(' · ' + e['type']) if e['type'] else ''}]"}
           for e in vus.values() if e["date"]]
    return _releve("Commission européenne, liste consolidée des sanctions financières",
                   "désignations en vigueur" + (f" · programme {programme}" if programme else "")
                   + (f" · « {terme} »" if terme else ""),
                   "https://data.europa.eu/data/datasets/consolidated-list-of-persons-groups-and-entities-subject-to-eu-financial-sanctions",
                   pts, avant, biais="radiations absentes (liste des désignations en vigueur)")


async def oms(indicateur: str, pays: str, dimension: str | None = None, avant: date | None = None) -> dict:
    """OMS, Global Health Observatory (OData) : indicateurs annuels par pays (ex. WHOSIS_000001, espérance de vie)."""
    filtre = f"SpatialDim eq '{pays}'" + (f" and Dim1 eq '{dimension}'" if dimension else "")
    d = await _get(f"https://ghoapi.azureedge.net/api/{indicateur}", {"$filter": filtre})
    pts = []
    for x in (d.get("value") or []) if isinstance(d, dict) else []:
        v, a = _num(x.get("NumericValue")), x.get("TimeDim")
        if v is None or not a:
            continue
        pts.append({"date": f"{int(a)}-12-31", "valeur": v,
                    "titre": " · ".join(str(x.get(k)) for k in ("Dim1", "Dim2") if x.get(k)) or None})
    # Les estimations de l'OMS paraissent avec un an de retard au moins.
    return _releve("OMS, Global Health Observatory", f"{indicateur} — {pays}" + (f" ({dimension})" if dimension else ""),
                   f"https://www.who.int/data/gho/data/indicators/indicator-details/GHO/{indicateur}", pts, avant,
                   retard=365, revisions="estimations actuelles, révisées d'une édition à l'autre")


async def ecosystemes(registre: str, paquet: str, avant: date | None = None) -> dict:
    """ecosyste.ms : versions publiées d'un paquet open source (registre, ex. npmjs.org, pypi.org, crates.io), datées."""
    from urllib.parse import quote
    base = f"https://packages.ecosyste.ms/api/v1/registries/{quote(registre, safe='')}/packages/{quote(paquet, safe='')}"
    d = await _get(base + "/versions", {"per_page": 1000, "sort": "published_at", "order": "asc"})
    pts = [{"date": _jour(x.get("published_at")), "valeur": None, "titre": f"version {x.get('number')}",
            "publie_le": _jour(x.get("published_at"))}
           for x in (d if isinstance(d, list) else []) if isinstance(x, dict) and _jour(x.get("published_at"))]
    return _releve("ecosyste.ms", f"versions de {paquet} ({registre})", base, pts, avant)


EPOCH_LICENCE = "CC BY 4.0 — Epoch AI (epoch.ai), citer la source"


def _vrai(v) -> bool:
    return str(v or "").strip().lower() not in ("", "0", "false", "no", "non", "none", "nan")


async def epoch_modeles(organisation: str | None = None, domaine: str | None = None, pays: str | None = None,
                        frontiere: bool = False, calcul_min: float | None = None, mesure: str = "sorties",
                        avant: date | None = None) -> dict:
    """0.10.10 : base des modèles d'IA d'Epoch AI (plus de 3 200 notables, 1950 à aujourd'hui), CC BY 4.0. Une ligne par
    modèle, datée de sa publication. `mesure` : « sorties » (événements : compter les sorties) ou « calcul » (calcul
    d'entraînement en FLOP, pour suivre la croissance). Instantané du jour, sans millésime : une ligne peut être ajoutée
    ou corrigée après la date d'information (colonne « Last modified ») ; le relevé compte ces lignes et le signale."""
    t = await _get("https://epoch.ai/data/all_ai_models.csv", json_=False)
    pts, modifiees_apres = [], 0
    for r in csv.DictReader(io.StringIO(t.lstrip("\ufeff"))):
        j = _jour(r.get("Publication date"))
        if not j:
            continue
        if organisation and organisation.lower() not in str(r.get("Organization") or "").lower():
            continue
        if domaine and domaine.lower() not in str(r.get("Domain") or "").lower():
            continue
        if pays and pays.lower() not in str(r.get("Country (of organization)") or "").lower():
            continue
        if frontiere and not _vrai(r.get("Frontier model")):
            continue
        flop = _num(r.get("Training compute (FLOP)"))
        if calcul_min is not None and (flop is None or flop < calcul_min):
            continue
        if mesure == "calcul" and flop is None:
            continue
        if avant and j <= avant.isoformat() and (_jour(r.get("Last modified")) or "") > avant.isoformat():
            modifiees_apres += 1
        pts.append({"date": j, "valeur": flop if mesure == "calcul" else None, "publie_le": j,
                    "titre": f"{r.get('Model')} ({r.get('Organization')})"})
    filtres = " · ".join(x for x in (organisation, domaine, pays, "frontière" if frontiere else None,
                                     f"≥ {calcul_min:g} FLOP" if calcul_min else None) if x)
    return _releve("Epoch AI, base des modèles d'IA", ("calcul d'entraînement (FLOP)" if mesure == "calcul"
                                                       else "sorties de modèles") + (f" — {filtres}" if filtres else ""),
                   "https://epoch.ai/data/ai-models", pts, avant, licence=EPOCH_LICENCE,
                   revisions=f"instantané du jour ; {modifiees_apres} ligne(s) antérieure(s) modifiée(s) après la date "
                             "d'information" if avant else "instantané du jour, sans millésime")


def _colonne(champs: list[str], *mots: str) -> str | None:
    bas = {c.lower(): c for c in champs}
    return next((v for k, v in bas.items() if all(m in k for m in mots)), None)


async def epoch_benchmarks(benchmark: str, modele: str | None = None, avant: date | None = None) -> dict:
    """0.10.10 : résultats de benchmarks d'Epoch AI (archive ZIP de CSV, CC BY 4.0). Une ligne par résultat : date de
    sortie du modèle, score, modèle. Les colonnes sont repérées par leur nom (modèle, score, date), le fichier par le nom
    du benchmark : la sonde vérifie qu'elles existent. Le score d'un modèle peut être mesuré bien après sa sortie : la
    date retenue est celle de la sortie (le relevé le signale)."""
    import zipfile
    z = zipfile.ZipFile(io.BytesIO(await _get_octets("https://epoch.ai/data/benchmark_data.zip")))
    cible = benchmark.lower().replace(" ", "_")
    noms = [n for n in z.namelist() if n.lower().endswith(".csv")]
    fichier = next((n for n in noms if cible in n.lower().replace(" ", "_").replace("-", "_")), None)
    pts = []
    for n in ([fichier] if fichier else noms):
        lecteur = csv.DictReader(io.StringIO(z.read(n).decode("utf-8", "replace").lstrip("\ufeff")))
        ch = lecteur.fieldnames or []
        c_mod = _colonne(ch, "model")
        c_score = _colonne(ch, "best", "score") or _colonne(ch, "score")
        c_date = _colonne(ch, "release", "date") or _colonne(ch, "date")
        c_bench = None if fichier else _colonne(ch, "benchmark")
        if not (c_mod and c_score and c_date) or (not fichier and not c_bench):
            continue
        for r in lecteur:
            if c_bench and cible not in str(r.get(c_bench) or "").lower().replace(" ", "_").replace("-", "_"):
                continue
            if modele and modele.lower() not in str(r.get(c_mod) or "").lower():
                continue
            brut = str(r.get(c_score) or "").strip()
            j, v = _jour(r.get(c_date)), _num(brut.rstrip("%"))
            if v is not None and brut.endswith("%"):
                v /= 100                                    # même échelle que les scores écrits en fraction
            if j and v is not None:
                pts.append({"date": j, "valeur": v, "titre": str(r.get(c_mod))})
    return _releve("Epoch AI, résultats de benchmarks", f"{benchmark}" + (f" — {modele}" if modele else ""),
                   "https://epoch.ai/benchmarks", pts, avant, licence=EPOCH_LICENCE, fichier=fichier,
                   revisions="date = sortie du modèle ; le score peut avoir été mesuré plus tard")


# --------------------------------------------------------------------------- 0.10.27 (d'après ShadowBroker)

R_TERRE_KM = 6371.0088
URL_FRONT_ARCHIVE = "https://codeload.github.com/cyterat/deepstate-map-data/tar.gz/refs/heads/main"
URL_FRONT = "https://raw.githubusercontent.com/cyterat/deepstate-map-data/main/deepstate-map-data.geojson.gz"
_FRONT: dict = {}


async def _geometries_front() -> list[tuple[str, dict]]:
    """(date, géométrie) pour chaque jour. Source sûre : les fichiers quotidiens du dossier data/, datés par leur nom
    (archive du dépôt, un seul téléchargement). Le fichier unifié du même dépôt a des dates vides pour ses 502 premières
    lignes (constat du 2026-11-11) : il ne sert qu'en repli, pour les seuls jours datés. Gardé en mémoire du processus."""
    if "g" in _FRONT:
        return _FRONT["g"]
    import gzip
    import tarfile
    out: list[tuple[str, dict]] = []
    try:
        tf = tarfile.open(fileobj=io.BytesIO(await _get_octets(URL_FRONT_ARCHIVE)), mode="r:gz")
        for m in tf:
            k = re.search(r"/data/deepstatemap_data_(\d{4})(\d{2})(\d{2})\.geojson$", m.name)
            if not k:
                continue
            d = json.load(tf.extractfile(m))
            feats = d.get("features") if d.get("type") == "FeatureCollection" else [d]
            geoms = [f.get("geometry") or f for f in feats or []]
            polys = [c for g in geoms for c in ([g["coordinates"]] if g.get("type") == "Polygon"
                                                 else g.get("coordinates") or [])]
            out.append((f"{k.group(1)}-{k.group(2)}-{k.group(3)}", {"type": "MultiPolygon", "coordinates": polys}))
    except Exception:
        out = []
    if not out:
        d = json.loads(gzip.decompress(await _get_octets(URL_FRONT)).decode("utf-8"))
        out = [(j, f.get("geometry") or {}) for f in d.get("features") or []
               if (j := _jour((f.get("properties") or {}).get("date")))]
    out.sort(key=lambda x: x[0])
    _FRONT["g"] = out
    return out


def _anneaux(geom: dict) -> list[list]:
    g = geom or {}
    if g.get("type") == "Polygon":
        return list(g.get("coordinates") or [])
    if g.get("type") == "MultiPolygon":
        return [r for poly in g.get("coordinates") or [] for r in poly]
    return []


def _surface_km2(geom: dict) -> float:
    """Surface d'un (multi)polygone en lon/lat sur la sphère : somme signée des anneaux (trous comptés en négatif par
    leur orientation, contrôlée ici par la règle : l'anneau extérieur de chaque polygone est positif)."""
    tot = 0.0
    polys = [geom.get("coordinates")] if geom.get("type") == "Polygon" else (geom.get("coordinates") or [])
    for poly in polys:
        for i, r in enumerate(poly or []):
            s = 0.0
            for (x1, y1), (x2, y2) in zip(r, r[1:] + r[:1]):
                s += math.radians(x2 - x1) * (2 + math.sin(math.radians(y1)) + math.sin(math.radians(y2)))
            a = abs(s) * R_TERRE_KM ** 2 / 2
            tot += a if i == 0 else -a
    return tot


def _dans(lon: float, lat: float, geom: dict) -> bool:
    """Point dans le (multi)polygone (règle pair-impair sur tous les anneaux : les trous sont exclus)."""
    dedans = False
    for r in _anneaux(geom):
        for (x1, y1), (x2, y2) in zip(r, r[1:] + r[:1]):
            if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / ((y2 - y1) or 1e-12) + x1:
                dedans = not dedans
    return dedans


def _distance_bord_km(lon: float, lat: float, geom: dict) -> float:
    """Distance du point au bord le plus proche (projection équirectangulaire locale, précise à l'échelle d'un front)."""
    kx = math.cos(math.radians(lat)) * math.pi / 180 * R_TERRE_KM
    ky = math.pi / 180 * R_TERRE_KM
    best = float("inf")
    for r in _anneaux(geom):
        for (x1, y1), (x2, y2) in zip(r, r[1:] + r[:1]):
            ax, ay = (x1 - lon) * kx, (y1 - lat) * ky
            bx, by = (x2 - lon) * kx, (y2 - lat) * ky
            dx, dy = bx - ax, by - ay
            L = dx * dx + dy * dy
            t = 0.0 if L == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / L))
            best = min(best, math.hypot(ax + t * dx, ay + t * dy))
    return best


async def front_ukraine(localite: str | None = None, latitude: float | None = None, longitude: float | None = None,
                        avant: date | None = None) -> dict:
    """Ligne de front en Ukraine, jour par jour depuis le 2024-07-08 : territoire occupé selon DeepState, archivé chaque
    jour par le miroir GitHub cyterat/deepstate-map-data (code GPL-3.0 ; données soumises aux conditions de DeepState :
    seuls des chiffres calculés entrent au registre). Sans coordonnées : surface occupée (km²) par jour. Avec latitude et
    longitude d'une localité : DISTANCE en km de la localité à la zone occupée (0 si elle y est), série de niveaux qui
    se compte avec seuil 0 et sens « <= » (« la localité sera-t-elle occupée ? »). Publication : le lendemain."""
    pts = []
    for j, g in await _geometries_front():
        if not g.get("coordinates"):
            continue
        if latitude is not None and longitude is not None:
            lat, lon = float(latitude), float(longitude)
            v = 0.0 if _dans(lon, lat, g) else round(_distance_bord_km(lon, lat, g), 2)
        else:
            v = round(_surface_km2(g), 1)
        pts.append({"date": j, "valeur": v})
    pts.sort(key=lambda p: p["date"])
    titre = (f"distance (km) de {localite or 'la localité'} ({latitude}, {longitude}) à la zone occupée ; 0 = occupée"
             if latitude is not None and longitude is not None else "surface du territoire ukrainien occupé (km²)")
    return _releve("DeepState, via le miroir cyterat/deepstate-map-data", titre,
                   "https://github.com/cyterat/deepstate-map-data", pts, avant, retard=1,
                   biais="carte d'un projet ukrainien (DeepState) ; aucun autre producteur indépendant")


async def coupures_internet(pays: str, debut: str = "2022-01-01", avant: date | None = None) -> dict:
    """Alertes de coupure d'Internet par pays (IODA, Georgia Tech ; usage de recherche) : une alerte « critical » est
    un événement daté. Les jours de plusieurs alertes comptent une fois."""
    fin = avant or datetime.now(timezone.utc).date()
    t0 = int(datetime.fromisoformat(f"{_jour(debut) or '2022-01-01'}T00:00:00+00:00").timestamp())
    t1 = int(datetime.fromisoformat(f"{fin.isoformat()}T23:59:59+00:00").timestamp())
    d = await _get("https://api.ioda.inetintel.cc.gatech.edu/v2/outages/alerts",
                   {"entityType": "country", "entityCode": pays.upper()[:2], "from": t0, "until": t1, "limit": 5000})
    lignes = d.get("data") if isinstance(d, dict) else d
    if isinstance(lignes, dict):
        lignes = lignes.get("alerts") or lignes.get("data") or []
    jours: dict[str, set] = {}
    for a in lignes or []:
        if not isinstance(a, dict) or str(a.get("level") or "").lower() != "critical":
            continue
        t = a.get("time") or a.get("from")
        try:
            j = datetime.fromtimestamp(int(t), timezone.utc).date().isoformat()
        except (TypeError, ValueError, OSError):
            j = _jour(t)
        if j:
            jours.setdefault(j, set()).add(str(a.get("datasource") or "?"))
    pts = [{"date": j, "valeur": None, "titre": "alerte critique : " + ", ".join(sorted(s))} for j, s in sorted(jours.items())]
    return _releve("IODA (Georgia Tech)", f"jours d'alerte critique de coupure d'Internet · {pays.upper()[:2]}",
                   f"https://ioda.inetintel.cc.gatech.edu/country/{pays.upper()[:2]}", pts, avant, debut=_jour(debut))


async def lancements(proprietaire: str | None = None, nom: str | None = None, site: str | None = None,
                     avant: date | None = None) -> dict:
    """Lancements spatiaux d'après le catalogue des satellites de CelesTrak (domaine public) : un lancement = un
    indicatif international « AAAA-NNN » ; filtres : propriétaire (code SATCAT : US, PRC, CIS, FR, IND, ESA…), nom
    d'objet (ex. STARLINK) et site de lancement (ex. AFETR, AFWTR, TSC, JSC, BOWIE…)."""
    t = await _get("https://celestrak.org/pub/satcat.csv", json_=False)
    vus: dict[str, dict] = {}
    for r in csv.DictReader(io.StringIO(t.lstrip("\ufeff"))):
        ident = (r.get("OBJECT_ID") or "")[:8]
        j = _jour(r.get("LAUNCH_DATE"))
        if not j or len(ident) < 8:
            continue
        if proprietaire and (r.get("OWNER") or "").upper() != proprietaire.upper():
            continue
        if nom and nom.upper() not in (r.get("OBJECT_NAME") or "").upper():
            continue
        if site and (r.get("LAUNCH_SITE") or "").upper() != site.upper():
            continue
        e = vus.setdefault(ident, {"date": j, "valeur": None, "objets": 0, "site": r.get("LAUNCH_SITE") or ""})
        e["objets"] += 1
    pts = [{"date": e["date"], "valeur": None, "titre": f"{i} · {e['objets']} objet(s) catalogué(s) · site {e['site']}"}
           for i, e in sorted(vus.items(), key=lambda x: x[1]["date"])]
    filtres = " · ".join(x for x in (proprietaire and f"propriétaire {proprietaire}", nom and f"objets « {nom} »",
                                     site and f"site {site}") if x)
    return _releve("CelesTrak, catalogue des satellites (SATCAT)", "lancements" + (f" · {filtres}" if filtres else ""),
                   "https://celestrak.org/satcat/search.php", pts, avant,
                   biais="un lancement sans objet catalogué (échec au décollage) peut manquer")


async def sanctions_us(terme: str | None = None, programme: str | None = None, avant: date | None = None) -> dict:
    """Liste SDN de l'OFAC (sanctions américaines), via OpenSanctions (CC BY-NC 4.0, usage non commercial) : une cible
    par ligne, datée de sa première apparition dans les relevés d'OpenSanctions. Les cibles déjà présentes au premier
    relevé (stock initial, toutes à la même date) sont retirées : leur date ne dit pas quand elles ont été désignées."""
    t = await _get("https://data.opensanctions.org/datasets/latest/us_ofac_sdn/targets.simple.csv", json_=False)
    lignes = list(csv.DictReader(io.StringIO(t.lstrip("\ufeff"))))
    dates = [_jour(r.get("first_seen")) for r in lignes]
    stock = min((x for x in dates if x), default=None)
    pts = []
    for r, j in zip(lignes, dates):
        if not j or j == stock:
            continue
        if programme and programme.upper() not in (r.get("sanctions") or "").upper():
            continue
        if terme and terme.lower() not in ((r.get("name") or "") + " " + (r.get("aliases") or "")).lower():
            continue
        pts.append({"date": j, "valeur": None,
                    "titre": f"{(r.get('name') or '')[:80]} [{(r.get('schema') or '')}] {(r.get('countries') or '')[:30]}"})
    pts.sort(key=lambda p: p["date"])
    return _releve("OFAC, liste SDN, via OpenSanctions", "nouvelles cibles des sanctions américaines"
                   + (f" · programme {programme}" if programme else "") + (f" · « {terme} »" if terme else ""),
                   "https://www.opensanctions.org/datasets/us_ofac_sdn/", pts, avant,
                   biais=f"dates = première apparition chez OpenSanctions ; stock initial du {stock} retiré ; radiations absentes")


# --------------------------------------------------------------------------- catalogue


# --------------------------------------------------------------------------- 0.10.40 : DBnomics

DBNOMICS = "https://api.db.nomics.world/v22"
RETARD_DBNOMICS = {"annual": 450, "quarterly": 75, "monthly": 45, "weekly": 10, "daily": 2}


def _periode_dbnomics(periode: str, debut_jour: str | None) -> str | None:
    """« 2024 », « 2024-03 », « 2024-Q1 », « 2024-S1 », « 2024-W05 », « 2024-03-15 » → jour ISO. DBnomics donne aussi
    `period_start_day` : la date de DÉBUT de période ; on garde la convention du module (date de la période)."""
    return _jour(debut_jour) if debut_jour else _jour(periode)


def parser_dbnomics(d: dict) -> tuple[dict, list[dict]]:
    docs = ((d.get("series") or {}).get("docs") or [])
    if not docs:
        raise RuntimeError("DBnomics : série introuvable (vérifier fournisseur/jeu/code, ex. IMF/WEO:latest/FRA.NGDP_RPCH)")
    x = docs[0]
    freq = str(x.get("@frequency") or "").lower()
    retard = RETARD_DBNOMICS.get(freq, 60)
    pts = []
    debuts = x.get("period_start_day") or [None] * len(x.get("period") or [])
    for per, deb, v in zip(x.get("period") or [], debuts, x.get("value") or []):
        j, val = _periode_dbnomics(str(per), deb), _num(v)
        # les jeux du FMI (WEO) contiennent des PROJECTIONS : jamais une période postérieure à aujourd'hui
        if j and val is not None and j <= date.today().isoformat():
            pts.append({"date": j, "valeur": val, "publie_le": (date.fromisoformat(j) + timedelta(days=retard)).isoformat()})
    return x, pts


async def dbnomics(serie: str, avant: date | None = None) -> dict:
    """DBnomics (Banque de France, Cepremap) : une seule API, sans clé, pour les séries de près de 80 fournisseurs
    (FMI, OCDE, BCE, Eurostat, BIS, OIT, instituts nationaux). `serie` = « fournisseur/jeu/code ». Valeurs actuelles,
    sans millésime : révisions possibles (pour l'économie américaine en rétrospectif, préférer ALFRED)."""
    serie = serie.strip().strip("/")
    d = await _get(f"{DBNOMICS}/series/{serie}", {"observations": 1, "format": "json"})
    x, pts = parser_dbnomics(d)
    titre = f"{x.get('provider_code', '')}/{x.get('dataset_code', '')}/{x.get('series_code', '')} · {x.get('series_name', '')}"
    return _releve("DBnomics", titre, f"https://db.nomics.world/{serie}", pts, avant,
                   frequence=x.get("@frequency"), revisions="valeurs actuelles, sans millésime : révisions possibles")


async def dbnomics_recherche(terme: str, avant: date | None = None) -> dict:
    """Trouver l'identifiant d'une série DBnomics : les séries dont le nom contient les mots-clés (en anglais)."""
    d = await _get(f"{DBNOMICS}/search", {"q": terme, "limit": 10})
    pts = []
    for x in ((d.get("results") or {}).get("docs") or []):
        code = f"{x.get('provider_code')}/{x.get('code')}"
        pts.append({"date": _jour(x.get("indexed_at") or x.get("converted_at")), "valeur": None,
                    "titre": f"jeu {code} — {x.get('name', '')} ({x.get('nb_series', '?')} séries)",
                    "url": f"https://db.nomics.world/{code}", "extrait": (x.get("description") or "")[:300]})
    return _releve("DBnomics (recherche)", f"jeux de données « {terme} »", "https://db.nomics.world/", pts, None)

CATALOGUE: dict[str, dict] = {
    "fred": {"fn": fred, "nature": "niveau", "cle": "FRED_API_KEY", "comptable": True,
             "params": '{"serie": "identifiant FRED, ex. UNRATE, CPIAUCSL, DGS10, FEDFUNDS", "debut": "AAAA-MM-JJ facultatif"}',
             "pour": "séries économiques et financières américaines (taux, chômage, prix, dette, marchés)"},
    "banque_mondiale": {"fn": banque_mondiale, "nature": "niveau", "comptable": True,
                        "params": '{"pays": "ISO3 ou WLD", "indicateur": "code, ex. NY.GDP.MKTP.KD.ZG"}',
                        "pour": "indicateurs annuels par pays (PIB, inflation, population, dette)"},
    "bce": {"fn": bce, "nature": "niveau", "comptable": True, "params": '{"cle": "flux/clé SDMX, ex. EXR/D.USD.EUR.SP00.A"}',
            "pour": "taux de change, taux directeurs et monnaie de la zone euro"},
    "eurostat": {"fn": eurostat, "nature": "niveau", "comptable": True,
                 "params": '{"jeu": "code, ex. une_rt_m", "filtres": {"geo": "FR", "...": "une valeur par dimension"}}',
                 "pour": "statistiques européennes (chômage, inflation HICP, PIB) par pays"},
    "tresor": {"fn": tresor, "nature": "niveau", "comptable": True,
               "params": '{"jeu": "ex. v2/accounting/od/avg_interest_rates", "champ": "ex. avg_interest_rate_amt", '
                         '"filtre": "facultatif, ex. security_desc:eq:Total Marketable"}',
               "pour": "finances fédérales américaines (dette, taux moyens, dépenses)"},
    "bls": {"fn": bls, "nature": "niveau", "comptable": True, "params": '{"serie": "identifiant BLS, ex. CUUR0000SA0, LNS14000000"}',
            "pour": "emploi et prix américains"},
    "unhcr": {"fn": unhcr, "nature": "niveau", "comptable": True,
              "params": '{"pays_origine": "ISO3 facultatif", "pays_asile": "ISO3 facultatif", "champ": "refugees|asylum_seekers|idps"}',
              "pour": "réfugiés et déplacés par année"},
    "fts": {"fn": fts, "nature": "flux", "comptable": True, "params": '{"pays": "ISO3", "annees": [2021, 2022, "..."]}',
            "pour": "financement humanitaire reçu par année"},
    "ucdp": {"fn": ucdp, "nature": "flux", "cle": "UCDP_TOKEN", "comptable": True,
             "params": '{"pays": "nom ou code UCDP facultatif", "debut": "AAAA-MM-JJ"}',
             "pour": "événements de violence organisée et morts estimés (à agréger par mois ou par an)"},
    "usgs_seismes": {"fn": usgs_seismes, "nature": "evenements", "comptable": True,
                     "params": '{"magnitude_min": 6.0, "debut": "AAAA-MM-JJ", "latitude": "…", "longitude": "…", "rayon_km": "…"}',
                     "pour": "séismes (dates et magnitudes)"},
    "gdacs": {"fn": gdacs, "nature": "evenements", "comptable": True,
              "params": '{"types": "EQ;TC;FL;VO;DR;WF;TS", "debut": "AAAA-MM-JJ", "alerte": "Orange;Red"}',
              "pour": "alertes de catastrophes (séismes, cyclones, inondations, volcans, sécheresses, feux, tsunamis)"},
    "eonet": {"fn": eonet, "nature": "evenements", "comptable": True,
              "params": '{"categorie": "wildfires|severeStorms|volcanoes|floods|… facultatif", "jours": 60}',
              "pour": "événements naturels en cours (état présent)"},
    "federal_register": {"fn": federal_register, "nature": "evenements", "comptable": True,
                         "params": '{"terme": "mots-clés", "type_doc": "PRESDOCU|RULE|PRORULE|NOTICE facultatif"}',
                         "pour": "décrets, règles et documents présidentiels américains"},
    "firms": {"fn": firms, "nature": "flux", "cle": "FIRMS_MAP_KEY", "comptable": True,
              "params": '{"pays": "ISO3", "jours": "1 à 10"}', "pour": "feux actifs détectés par satellite (10 derniers jours)"},
    "wikidata_poste": {"fn": wikidata_poste, "nature": "evenements", "comptable": True,
                       "params": '{"poste": "intitulé en anglais ou QID, ex. President of France"}',
                       "pour": "titulaires successifs d'un poste (durées en fonction, changements)"},
    "wikipedia": {"fn": wikipedia, "nature": "texte", "comptable": False, "params": '{"titre": "titre exact de l\'article", "langue": "en"}',
                  "pour": "l'article tel qu'il était à la date d'information"},
    "wayback": {"fn": wayback, "nature": "texte", "comptable": False, "params": '{"url": "adresse exacte d\'une page"}',
                "pour": "une page officielle telle qu'elle était à la date d'information"},
    "hdx": {"fn": hdx, "nature": "texte", "comptable": False, "params": '{"terme": "mots-clés"}', "pour": "jeux de données humanitaires (HDX)"},
    "gaza": {"fn": gaza, "nature": "niveau", "comptable": True,
             "params": '{"champ": "killed_cum|injured_cum|killed|killed_children_cum|…", "zone": "gaza|cisjordanie"}',
             "pour": "victimes à Gaza et en Cisjordanie, séries quotidiennes (cumuls et quotidiens)"},
    "sanctions_ue": {"fn": sanctions_ue, "nature": "evenements", "comptable": True,
                     "params": '{"terme": "nom facultatif", "programme": "code facultatif, ex. RUS, IRN, BLR"}',
                     "pour": "désignations aux sanctions financières de l'UE (qui, quand, quel programme)"},
    "oms": {"fn": oms, "nature": "niveau", "comptable": True,
            "params": '{"indicateur": "code GHO, ex. WHOSIS_000001", "pays": "ISO3", "dimension": "facultatif, ex. SEX_BTSX"}',
            "pour": "indicateurs de santé annuels par pays (OMS)"},
    "ecosystemes": {"fn": ecosystemes, "nature": "evenements", "comptable": True,
                    "params": '{"registre": "npmjs.org|pypi.org|crates.io|…", "paquet": "nom exact"}',
                    "pour": "versions publiées d'un logiciel open source (dates de sortie)"},
    "epoch_modeles": {"fn": epoch_modeles, "nature": "evenements", "comptable": True,
                      "params": '{"organisation": "facultatif, ex. OpenAI", "domaine": "facultatif, ex. Language", '
                                '"pays": "facultatif", "frontiere": true, "calcul_min": 1e25, "mesure": "sorties|calcul"}',
                      "pour": "sorties de modèles d'IA et calcul d'entraînement (Epoch AI, CC BY 4.0)"},
    "front_ukraine": {"fn": front_ukraine, "nature": "niveau", "comptable": True,
                      "params": '{"localite": "nom facultatif", "latitude": "facultatif, ex. 48.28", "longitude": "facultatif, ex. 37.18"}',
                      "pour": "ligne de front en Ukraine, quotidienne depuis 2024-07 : surface occupée (km²), ou, avec les "
                              "coordonnées d'une localité, sa distance (km) à la zone occupée (seuil 0, sens « <= » : "
                              "la localité sera-t-elle prise ?)"},
    "coupures_internet": {"fn": coupures_internet, "nature": "evenements", "comptable": True,
                          "params": '{"pays": "code ISO2, ex. IR", "debut": "AAAA-MM-JJ"}',
                          "pour": "jours d'alerte critique de coupure d'Internet dans un pays (IODA)"},
    "lancements": {"fn": lancements, "nature": "evenements", "comptable": True,
                   "params": '{"proprietaire": "code SATCAT facultatif, ex. US, PRC, CIS, IND", "nom": "facultatif, ex. STARLINK", '
                             '"site": "facultatif, ex. AFETR"}',
                   "pour": "lancements spatiaux datés (CelesTrak, domaine public)"},
    "sanctions_us": {"fn": sanctions_us, "nature": "evenements", "comptable": True,
                     "params": '{"terme": "nom facultatif", "programme": "facultatif, ex. RUSSIA-EO14024, IRAN, SDGT"}',
                     "pour": "nouvelles cibles des sanctions américaines (OFAC, via OpenSanctions)"},
    "dbnomics": {"fn": dbnomics, "nature": "niveau", "comptable": True,
                 "params": '{"serie": "fournisseur/jeu/code, ex. IMF/WEO:latest/FRA.NGDP_RPCH, OECD/MEI/FRA.LRHUTTTT.STSA.M"}',
                 "pour": "séries de près de 80 fournisseurs en une API (FMI, OCDE, BCE, Eurostat, BIS, OIT, instituts nationaux)"},
    "dbnomics_recherche": {"fn": dbnomics_recherche, "nature": "texte", "comptable": False,
                           "params": '{"terme": "mots-clés en anglais, ex. unemployment France"}',
                           "pour": "trouver le jeu DBnomics qui contient une série (avant d'appeler dbnomics)"},
    "epoch_benchmarks": {"fn": epoch_benchmarks, "nature": "niveau", "comptable": True,
                         "params": '{"benchmark": "nom, ex. GPQA Diamond, FrontierMath, SWE-bench", "modele": "facultatif"}',
                         "pour": "scores des modèles d'IA aux benchmarks, datés de la sortie du modèle (Epoch AI, CC BY 4.0)"},
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

from alphabet_compte import _agreger, _remplit, compter  # noqa: E402,F401  (0.9.5)


Llm = Callable[[str], Awaitable[str]]
