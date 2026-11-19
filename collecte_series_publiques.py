"""Séries publiques du monde physique et des savoirs (bot 0.10.358, ombre).

Décision de l'auteur du 2026-11-19 (16 h 41) : sources officielles, gratuites, sans clé, qui remplissent des compartiments
vides des fiches (registre/priorites-traces.md). Rien n'entre dans le bot. Chaque source est indépendante : une panne
n'empêche pas les autres ; robots.txt vérifié pour chacune.

- banquise_arctique, banquise_antarctique : étendue quotidienne, millions de km² (NSIDC, Sea Ice Index G02135) ;
- geomag_ap, taches_solaires, flux_f107 : indice géomagnétique Ap, nombre de taches, flux radio à 10,7 cm, quotidiens
  (GFZ Potsdam, CC BY 4.0) ;
- nino34_anomalie : anomalie hebdomadaire de surface de la mer, région Niño 3.4, °C (NOAA CPC, base 1991-2020) ;
- rhin_kaub_cm : niveau du Rhin à Kaub, moyenne du jour, cm (PEGELONLINE, administration fédérale allemande des voies
  navigables ; 30 jours d'historique, la série s'accumule) ;
- mississippi_saint_louis, mississippi_memphis : débit moyen du jour, m³/s (USGS) ;
- secheresse_us_d2plus : part du territoire américain en sécheresse sévère ou pire, % hebdomadaire (US Drought Monitor) ;
- psd_<culture>_production, psd_<culture>_stocks : production et stocks de fin de campagne MONDIAUX prévus par l'USDA
  pour la dernière campagne (PSD Online, mêmes chiffres que le rapport WASDE), datés du jour de la collecte : la
  série montre les révisions mensuelles ; millions de tonnes ;
- arxiv_cs_ai, arxiv_cs_lg : prépublications soumises par jour (API arXiv, 3 s entre deux requêtes).

Registre : registre/series-publiques.csv (serie, jour, valeur), fusionné à chaque passage (les séries à historique court
s'accumulent ; une valeur relue remplace l'ancienne).
"""
from __future__ import annotations

import csv
import io
import os
import re
import sys
import time
import zipfile
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import httpx

import politesse

REG = Path(os.environ.get("ALPHABET_REGISTRE", "registre"))
SORTIE = REG / "series-publiques.csv"
DEBUT = "2000-01-01"
NSIDC = ["https://noaadata.apps.nsidc.org/NOAA/G02135/{h}/daily/data/{H}_seaice_extent_daily_v4.0.csv",
         "https://noaadata.apps.nsidc.org/NOAA/G02135/{h}/daily/data/{H}_seaice_extent_daily_v3.0.csv"]
GFZ = "https://kp.gfz-potsdam.de/app/files/Kp_ap_Ap_SN_F107_since_1932.txt"
CPC = "https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for"
KAUB = "https://www.pegelonline.wsv.de/webservices/rest-api/v2/stations/KAUB/W/measurements.json?start=P30D"
USGS_SITES = {"mississippi_saint_louis": "07010000", "mississippi_memphis": "07032000"}
USGS_ANCIEN = "https://waterservices.usgs.gov/nwis/dv/"
USGS_NOUVEAU = "https://api.waterdata.usgs.gov/ogcapi/v0/collections/daily/items"
USDM = "https://usdmdataservices.unl.edu/api/USStatistics/GetDroughtSeverityStatisticsByAreaPercent"
PSD = {"grains": "https://apps.fas.usda.gov/psdonline/downloads/psd_grains_pulses_csv.zip",
       "oleagineux": "https://apps.fas.usda.gov/psdonline/downloads/psd_oilseeds_csv.zip"}
CULTURES = {"Wheat": "ble", "Corn": "mais", "Rice, Milled": "riz", "Oilseed, Soybean": "soja"}
ARXIV = "http://export.arxiv.org/api/query"
ARXIV_CATS = {"arxiv_cs_ai": "cs.AI", "arxiv_cs_lg": "cs.LG"}
ARXIV_JOURS = 45
ARXIV_MAX = 60
PAUSE = 2.0
PIED3 = 0.0283168


# ---------- lecteurs (purs, testés) ----------

def lire_nsidc(texte: str) -> list[tuple[str, float]]:
    out = []
    for r in csv.reader(io.StringIO(texte)):
        try:
            a, m, j, e = int(r[0]), int(r[1]), int(r[2]), float(r[3])
        except (ValueError, IndexError):
            continue
        if e > 0:
            out.append((date(a, m, j).isoformat(), round(e, 3)))
    return out


def lire_gfz(texte: str) -> dict[str, list[tuple[str, float]]]:
    out = {"geomag_ap": [], "taches_solaires": [], "flux_f107": []}
    for l in texte.splitlines():
        if l.startswith("#") or not l.strip():
            continue
        c = l.split()
        if len(c) < 27:
            continue
        try:
            j = date(int(c[0]), int(c[1]), int(c[2])).isoformat()
            ap, sn, f = float(c[23]), float(c[24]), float(c[25])
        except ValueError:
            continue
        if j < DEBUT:
            continue
        for nom, v in (("geomag_ap", ap), ("taches_solaires", sn), ("flux_f107", f)):
            if v >= 0:
                out[nom].append((j, v))
    return out


MOIS = {m: i + 1 for i, m in enumerate(["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"])}


def lire_cpc(texte: str) -> list[tuple[str, float]]:
    out = []
    for l in texte.splitlines():
        m = re.match(r"\s*(\d{2})([A-Z]{3})(\d{4})(.*)", l)
        if not m or m.group(2) not in MOIS:
            continue
        v = re.findall(r"-?\d+\.\d", m.group(4))
        if len(v) >= 8:
            out.append((date(int(m.group(3)), MOIS[m.group(2)], int(m.group(1))).isoformat(), float(v[5])))
    return out


def moyenne_par_jour(points: list[tuple[str, float]]) -> list[tuple[str, float]]:
    d = defaultdict(list)
    for t, v in points:
        d[t[:10]].append(v)
    return sorted((j, round(sum(v) / len(v), 1)) for j, v in d.items())


def lire_kaub(corps: list) -> list[tuple[str, float]]:
    return moyenne_par_jour([(x["timestamp"], float(x["value"])) for x in corps if x.get("value") is not None])


def lire_usgs_ancien(corps: dict) -> list[tuple[str, float]]:
    out = []
    for ts in (corps.get("value") or {}).get("timeSeries") or []:
        for bloc in ts.get("values") or []:
            for x in bloc.get("value") or []:
                try:
                    v = float(x["value"])
                except (KeyError, ValueError, TypeError):
                    continue
                if v >= 0:
                    out.append((x["dateTime"][:10], round(v * PIED3, 1)))
    return sorted(out)


def lire_usgs_nouveau(corps: dict) -> list[tuple[str, float]]:
    out = []
    for f in corps.get("features") or []:
        p = f.get("properties") or {}
        try:
            v = float(p["value"])
        except (KeyError, ValueError, TypeError):
            continue
        if v >= 0:
            out.append((str(p["time"])[:10], round(v * PIED3, 1)))
    return sorted(out)


def _jour_usdm(x: str) -> str | None:
    x = str(x)
    for f, n in (("%Y-%m-%d", 10), ("%Y%m%d", 8), ("%m/%d/%Y", 10)):
        try:
            return datetime.strptime(x[:n], f).date().isoformat()
        except ValueError:
            continue
    return None


def lire_usdm(texte: str) -> list[tuple[str, float]]:
    try:
        import json
        lignes = json.loads(texte)
    except ValueError:
        lignes = list(csv.DictReader(io.StringIO(texte)))
    out = []
    for r in lignes:
        j = _jour_usdm(r.get("MapDate") or r.get("mapDate") or "")
        try:
            v = float(r.get("D2") if r.get("D2") is not None else r.get("d2"))
        except (TypeError, ValueError):
            continue
        if j:
            out.append((j, v))
    return sorted(set(out))


def lire_psd(contenu_zip: bytes) -> dict[str, float]:
    """Dernière campagne de chaque culture : production et stocks de fin mondiaux (somme des pays), millions de t."""
    with zipfile.ZipFile(io.BytesIO(contenu_zip)) as z:
        texte = z.read(next(n for n in z.namelist() if n.lower().endswith(".csv"))).decode("utf-8", "replace")
    tot = defaultdict(float)
    for r in csv.DictReader(io.StringIO(texte)):
        cul = CULTURES.get(r.get("Commodity_Description", ""))
        att = {"Production": "production", "Ending Stocks": "stocks"}.get(r.get("Attribute_Description", ""))
        if not cul or not att or r.get("Country_Name") == "World":
            continue
        try:
            tot[(cul, att, int(r["Market_Year"]))] += float(r["Value"])
        except (KeyError, ValueError):
            continue
    out = {}
    for cul in set(CULTURES.values()):
        ans = [a for (c, _, a), v in tot.items() if c == cul and v]
        if ans:
            a = max(ans)
            for att in ("production", "stocks"):
                if (cul, att, a) in tot:
                    out[f"psd_{cul}_{att}"] = round(tot[(cul, att, a)] / 1000, 2)   # milliers de t → millions de t
    return out


def total_arxiv(xml: str) -> int | None:
    m = re.search(r"<opensearch:totalResults[^>]*>(\d+)<", xml)
    return int(m.group(1)) if m else None


# ---------- collecte ----------

def lire_existant() -> dict[str, dict[str, float]]:
    out = defaultdict(dict)
    if SORTIE.exists():
        for r in csv.DictReader(SORTIE.open(encoding="utf-8")):
            out[r["serie"]][r["jour"]] = float(r["valeur"])
    return out


def principal() -> int:
    series = lire_existant()
    aujourdhui = date.today()

    def poser(nom: str, valeurs: list[tuple[str, float]], remplacer: bool = False) -> None:
        if remplacer:
            series[nom] = {}
        series[nom].update(dict(valeurs))
        print(f"{nom} : {len(valeurs)} valeurs lues" + (f", dernière {valeurs[-1]}" if valeurs else ""), flush=True)

    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=180, follow_redirects=True) as c:
        def get(url: str, **kw) -> httpx.Response | None:
            if not politesse.autorise(c, url):
                print(f"::warning::refusé par robots.txt : {url.split('?')[0]}")
                return None
            try:
                r = c.get(url, **kw)
                r.raise_for_status()
                return r
            except Exception as e:
                print(f"::warning::{url.split('?')[0]} : {type(e).__name__}", flush=True)
                return None
            finally:
                time.sleep(PAUSE)

        for h, H, nom in (("north", "N", "banquise_arctique"), ("south", "S", "banquise_antarctique")):
            for modele in NSIDC:
                r = get(modele.format(h=h, H=H))
                if r is not None and (v := lire_nsidc(r.text)):
                    poser(nom, v, remplacer=True)
                    break
        if (r := get(GFZ)) is not None:
            for nom, v in lire_gfz(r.text).items():
                if v:
                    poser(nom, v, remplacer=True)
        if (r := get(CPC)) is not None and (v := lire_cpc(r.text)):
            poser("nino34_anomalie", v, remplacer=True)
        if (r := get(KAUB)) is not None:
            try:
                poser("rhin_kaub_cm", lire_kaub(r.json())[:-1])        # le jour en cours est incomplet
            except Exception as e:
                print(f"::warning::Kaub : {type(e).__name__}")
        for nom, site in USGS_SITES.items():
            debut = "2016-01-01" if not series.get(nom) else (aujourdhui - timedelta(days=60)).isoformat()
            v = []
            r = get(USGS_ANCIEN, params={"format": "json", "sites": site, "parameterCd": "00060", "statCd": "00003",
                                         "startDT": debut})
            if r is not None:
                v = lire_usgs_ancien(r.json())
            if not v:
                r = get(USGS_NOUVEAU, params={"f": "json", "monitoring_location_id": f"USGS-{site}", "parameter_code": "00060",
                                              "statistic_id": "00003", "time": f"{debut}/..", "limit": 10000})
                if r is not None:
                    v = lire_usgs_nouveau(r.json())
            if v:
                poser(nom, v)
        r = get(USDM, params={"aoi": "us", "startdate": "1/1/2000", "enddate": aujourdhui.strftime("%m/%d/%Y"),
                              "statisticsType": 1}, headers={"Accept": "application/json"})
        if r is not None and (v := lire_usdm(r.text)):
            poser("secheresse_us_d2plus", v, remplacer=True)
        dernier_psd = max(series.get("psd_ble_stocks", {}) or {"": 0})
        if not dernier_psd or dernier_psd < (aujourdhui - timedelta(days=6)).isoformat():
            for _, url in PSD.items():
                if (r := get(url)) is not None:
                    try:
                        for nom, x in lire_psd(r.content).items():
                            poser(nom, [(aujourdhui.isoformat(), x)])
                    except Exception as e:
                        print(f"::warning::PSD : {type(e).__name__}")
        n = 0
        for d in range(1, ARXIV_JOURS + 1):
            j = aujourdhui - timedelta(days=d)
            for nom, cat in ARXIV_CATS.items():
                if j.isoformat() in series.get(nom, {}) and d > 3 or n >= ARXIV_MAX:   # les 3 derniers jours sont relus
                    continue
                q = f"cat:{cat} AND submittedDate:[{j:%Y%m%d}0000 TO {j:%Y%m%d}2359]"
                r = get(ARXIV, params={"search_query": q, "max_results": 0})
                n += 1
                if r is not None and (t := total_arxiv(r.text)) is not None:
                    series[nom][j.isoformat()] = float(t)
                time.sleep(1.0)                                      # 3 s au total entre deux requêtes arXiv
        print(f"arXiv : {n} requêtes", flush=True)
    if not any(series.values()):
        print("::warning::aucune série ; rien écrit.")
        return 0
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with SORTIE.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["serie", "jour", "valeur"])
        for s in sorted(series):
            w.writerows((s, j, v) for j, v in sorted(series[s].items()))
    print("séries publiques : " + ", ".join(f"{s} {len(v)}" for s, v in sorted(series.items())))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
