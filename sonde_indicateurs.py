"""Sonde des indicateurs indirects (0.10.116, décision d'auteur du 2026-11-15 : les signaux faibles d'Ansoff passent par
des indicateurs qui précèdent les événements sans en parler). Teste, depuis GitHub Actions, l'accès gratuit à chaque
source candidate, pour un pays d'essai, et imprime ce qui répond. Rien n'est écrit au registre.

Sources candidates (accès gratuit, sans clé) :
- change : taux de change national contre le dollar, FMI (IFS) via DBnomics ;
- inflation : indice des prix à la consommation, FMI (IFS) via DBnomics ;
- prix alimentaires : jeux « WFP food prices » de l'Humanitarian Data Exchange (HDX) ;
- attention médiatique : volume et ton des articles par pays, GDELT DOC 2.0 ;
- choc climatique : précipitations et températures journalières, archive Open-Meteo.

    python sonde_indicateurs.py
"""
from __future__ import annotations

import asyncio
import json
import sys

import httpx

PAYS = {"nom": "Armenia", "iso2": "AM", "iso3": "ARM", "lat": 40.18, "lon": 44.51}

ESSAIS = {
    "change_fmi_dbnomics": f"https://api.db.nomics.world/v22/series/IMF/IFS/M.{PAYS['iso2']}.ENDA_XDC_USD_RATE?observations=1",
    "inflation_fmi_dbnomics": f"https://api.db.nomics.world/v22/series/IMF/IFS/M.{PAYS['iso2']}.PCPI_IX?observations=1",
    "prix_alimentaires_hdx": f"https://data.humdata.org/api/3/action/package_search?q=wfp+food+prices+{PAYS['nom'].lower()}&rows=3",
    "attention_gdelt": f"https://api.gdeltproject.org/api/v2/doc/doc?query={PAYS['nom']}%20protest&mode=timelinevolraw&format=json&timespan=6months",
    "climat_open_meteo": (f"https://archive-api.open-meteo.com/v1/archive?latitude={PAYS['lat']}&longitude={PAYS['lon']}"
                          "&start_date=2026-06-01&end_date=2026-08-31&daily=precipitation_sum,temperature_2m_max"),
    # 0.10.117 : indicateurs plus « niches » (demande de l'auteur du 2026-11-15)
    "attention_wikipedia": ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/"
                            f"{PAYS['nom']}/daily/20260601/20260831"),
    "coupures_internet_ioda": (f"https://api.ioda.inetintel.cc.gatech.edu/v2/outages/alerts?entityType=country&entityCode={PAYS['iso2']}"
                               "&from=1751328000&until=1756684800"),
    "conseils_voyage_royaume_uni": f"https://www.gov.uk/api/content/foreign-travel-advice/{PAYS['nom'].lower()}",
    "catastrophes_gdacs": ("https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH?fromDate=2026-06-01&toDate=2026-08-31"
                           f"&country={PAYS['nom']}"),
    "seismes_usgs": ("https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime=2026-06-01&endtime=2026-08-31"
                     f"&latitude={PAYS['lat']}&longitude={PAYS['lon']}&maxradiuskm=500&minmagnitude=4"),
    "vols_opensky": "https://opensky-network.org/api/states/all?lamin=38.8&lomin=43.4&lamax=41.3&lomax=46.6",
}


def resumer(nom: str, j) -> str:
    try:
        if nom.endswith("dbnomics"):
            s = j["series"]["docs"][0]
            per, val = s.get("period") or [], s.get("value") or []
            return f"{len(per)} points, dernier {per[-1] if per else '?'} = {val[-1] if val else '?'}"
        if nom == "prix_alimentaires_hdx":
            r = j["result"]["results"]
            return f"{j['result']['count']} jeux ; premier : {r[0]['title'] if r else '—'} ; ressources : {len(r[0].get('resources', [])) if r else 0}"
        if nom == "attention_gdelt":
            tl = j.get("timeline") or []
            d = tl[0]["data"] if tl else []
            return f"{len(d)} points ; dernier : {d[-1] if d else '—'}"
        if nom == "attention_wikipedia":
            it = j.get("items") or []
            return f"{len(it)} jours ; vues du dernier jour : {it[-1]['views'] if it else '—'}"
        if nom == "coupures_internet_ioda":
            d = j.get("data") or []
            return f"{len(d)} alertes de coupure sur la période"
        if nom == "conseils_voyage_royaume_uni":
            ch = (j.get("details") or {}).get("change_history") or []
            return f"{len(ch)} changements datés ; dernier : {ch[0] if ch else '—'}"
        if nom == "catastrophes_gdacs":
            return f"{len(j.get('features') or [])} événements"
        if nom == "seismes_usgs":
            return f"{len(j.get('features') or [])} séismes M ≥ 4"
        if nom == "vols_opensky":
            return f"{len(j.get('states') or [])} avions en vol au-dessus de la zone (instantané)"
        if nom == "climat_open_meteo":
            d = j.get("daily") or {}
            return f"{len(d.get('time') or [])} jours ; précipitations totales {sum(x or 0 for x in d.get('precipitation_sum') or []):.1f} mm"
    except Exception as e:
        return f"réponse inattendue : {type(e).__name__} {str(j)[:200]}"
    return str(j)[:200]


async def principal() -> int:
    ok = 0
    async with httpx.AsyncClient(timeout=60, follow_redirects=True,
                                 headers={"User-Agent": "alphabet-situationnel-bot/1.0 (recherche ; GitHub Othman-Benbrahim)"}) as c:
        for nom, url in ESSAIS.items():
            await asyncio.sleep(6)            # GDELT refuse plus d'une requête toutes les 5 secondes
            try:
                r = await c.get(url)
                if r.status_code != 200:
                    print(f"❌ {nom} : HTTP {r.status_code} {r.text[:200]}")
                    continue
                j = r.json()
                print(f"✅ {nom} : {resumer(nom, j)}")
                ok += 1
            except Exception as e:
                print(f"❌ {nom} : {type(e).__name__} {str(e)[:200]}")
    print(f"{ok}/{len(ESSAIS)} sources accessibles.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(principal()))
