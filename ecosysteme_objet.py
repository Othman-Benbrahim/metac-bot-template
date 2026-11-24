"""Échelle « objet » de la couche écosystème (décision de l'auteur, 2026-11-24, 20 h 48 : carte blanche pour compléter la
carte ; échelle proposée après le premier passage de la couche). Une série ne compte pour une question que si le titre
nomme ce qu'elle mesure. Table écrite à la main (OBJETS, par préfixe d'adaptateur) ; pour les séries par pays ou par
lieu, l'objet est le pays (noms de codes-pays-fips.csv + gentilés usuels) ou le lieu. Série sans objet = ne compte pas.
"""
from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path

ICI = Path(__file__).resolve().parent
OBJETS = {
    "fred:DCOILBRENTEU": r"oil|crude|brent|wti|opec|petrol|gasoline|barrel",
    "fred:DCOILWTICO": r"oil|crude|brent|wti|opec|petrol|gasoline|barrel",
    "eia:": r"oil|crude|brent|wti|opec|petrol|gasoline|barrel|refiner",
    "fred:DHHNGSP": r"natural gas|gas price|henry hub|lng|fertili[sz]er",
    "fred:CPIAUCSL": r"inflation|cpi|consumer prices?|fed\b|federal reserve|fomc|interest rates?|rate (cut|hike)",
    "fred:CPILFESL": r"inflation|cpi|core|fed\b|federal reserve|fomc|interest rates?|rate (cut|hike)",
    "fred:T10YIE": r"inflation|breakeven|fed\b|federal reserve|fomc|interest rates?",
    "fred:CES0500000003": r"wages?|earnings|inflation|fed\b|federal reserve",
    "fred:DFF": r"fed\b|federal reserve|fomc|interest rates?|rate (cut|hike)|federal funds",
    "fred:DGS10": r"treasur|yield|bond|mortgage|interest rates?|fed\b|federal reserve",
    "fred:ECBDFR": r"\becb\b|european central bank|euro\b|eurozone",
    "fred:UNRATE": r"unemployment|jobless|jobs report|payrolls?|recession|fed\b|federal reserve",
    "fred:DTWEXBGS": r"dollar|usd|currenc|exchange rate|yuan|renminbi|euro\b|yen",
    "fred:SP500": r"s&p|sp500|stock|equit|wall street|market crash|nasdaq|dow",
    "fred:NASDAQCOM": r"nasdaq|tech stocks|stock|equit",
    "fred:DJIA": r"\bdow\b|dow jones|stock|equit",
    "fred:VIXCLS": r"\bvix\b|volatil|market crash|stock|s&p",
    "fred:CBBTCUSD": r"bitcoin|\bbtc\b|crypto",
    "fred:CBETHUSD": r"ethereum|\beth\b|crypto",
    "fred:PFOODINDEXM": r"food|famine|hunger|wheat|corn|maize|rice|grain",
    "fred:PWHEAMTUSDM": r"wheat|grain|bread|food",
    "fred:PMAIZMTUSDM": r"corn|maize|grain|food",
    "fred:UMCSENT": r"consumer (sentiment|confidence)|michigan",
    "fred:DPSACBW027SBOG": r"bank|deposit|banking",
    "fred:PCOPPUSDM": r"copper", "fred:PALUMUSDM": r"alumin", "fred:PNICKUSDM": r"nickel", "fred:PZINCUSDM": r"zinc",
    "fred:PURANUSDM": r"uranium|nuclear power", "fred:PIORECRUSDM": r"iron ore|steel",
    "seismes:": r"earthquake|quake|seismic|magnitude",
    "tribunaux:scotus": r"supreme court|scotus",
    "federal_register:": r"executive order|federal register|tariff|proclamation",
    "elections:US": r"election|vote|midterm|primary",
    "pub:nino34": r"el ni[nñ]o|la ni[nñ]a|enso",
    "pub:banquise": r"arctic|sea ice",
    "pub:psd_ble": r"wheat|grain",
    "pub:arxiv": r"\bai\b|artificial intelligence|machine learning|model",
    "certificats": r"\bai\b|openai|anthropic|google|model|gpt|claude|gemini",
    "ouvert:co2": r"\bco2\b|carbon|emission|climate",
    "ouvert:polarisation": r"congress|house|senate|partisan|bipartisan",
    "pub:secheresse": r"drought",
    "pub:rhin": r"rhine",
    "pub:geomag": r"geomagnetic|solar storm",
    "urgences:": r"aviation|aircraft|flight|airline|hijack",
}
DETROITS = {"ormuz": r"hormuz", "taiwan": r"taiwan", "malacca": r"malacca", "bab_el_mandeb": r"bab|red sea|houthi",
            "suez": r"suez|red sea", "bosphore": r"bosphorus|turkish straits|black sea", "panama": r"panama",
            "bonne_esperance": r"cape of good hope", "rotterdam": r"rotterdam"}
VILLES = {"delhi": "india|delhi", "teheran": "iran|tehran", "houston": "texas|houston", "berlin": "germany|berlin",
          "shanghai": "china|shanghai", "kyiv": "ukraine|kyiv|kiev", "bandar_abbas": "iran|hormuz"}
PHENOMENES = r"heat|hot|temperature|cold|freez|frost|drought|rain|monsoon|flood|weather|snow|wildfire|heatwave"
GENTILES = {"USA": "united states|u\\.s\\.|\\bus\\b|america|american", "GBR": "united kingdom|\\buk\\b|britain|british",
            "RUS": "russia|russian|kremlin|putin", "UKR": "ukrain|zelensk", "CHN": "china|chinese|beijing|xi jinping",
            "IRN": "iran|iranian|tehran", "ISR": "israel|israeli|netanyahu|gaza", "PSE": "palestin|gaza|west bank|hamas",
            "LBN": "leban|hezbollah", "TWN": "taiwan", "PRK": "north korea", "IND": "india|indian|modi",
            "SDN": "sudan", "COD": "congo|drc", "MEX": "mexic", "HTI": "haiti", "MMR": "myanmar|burma",
            "EGY": "egypt", "ETH": "ethiopia", "ARE": "emirates|uae", "MDA": "moldova", "ZMB": "zambia"}


@lru_cache(1)
def _pays():
    P = {}
    for r in csv.DictReader(l for l in (ICI / "ecosystemes" / "codes-pays-fips.csv").read_text(encoding="utf-8").splitlines()
                            if l and not l.startswith("#")):
        for k in (r["iso2"], r["iso3"]):
            if k:
                P[k] = (GENTILES.get(r["iso3"]) or re.escape(r["nom"].lower()))
    return P


def motif(adaptateur: str) -> str | None:
    a = adaptateur or ""
    for k, v in OBJETS.items():
        if a == k or a.startswith(k if k.endswith(":") else k + ":") or (not k.endswith(":") and a.startswith(k)):
            return v
    parties = a.split(":")
    if parties[0] in ("portwatch", "portwatch_ref", "port") and len(parties) > 1:
        return DETROITS.get(parties[1])
    if parties[0] in ("meteo", "climat", "pluie", "meteo_prevue") and len(parties) > 1:
        # 2026-11-24 (sondes) : l'objet d'une série météo est le phénomène ET le lieu, pas le lieu seul
        lieu = VILLES.get(parties[1])
        return rf"^(?=.*(?:{PHENOMENES}))(?=.*(?:{lieu}))" if lieu else None
    P = _pays()
    codes = [x for x in parties[1:] if x in P]
    if parties[0] in ("gestes", "paire", "paire_mois", "dyade", "ucdp_dyade", "sanctions", "ooni", "feux", "ucdp_mois",
                      "manifestations", "violations", "acaps_risques", "prix_alimentaires", "recit_russe", "avions",
                      "memoire", "rss") and codes:
        return "|".join(P[c] for c in codes)
    return None                                       # série générale : pas d'objet, ne compte pas


def porte_sur(adaptateur: str, titre: str) -> bool:
    m = motif(adaptateur)
    return bool(m and re.search(m, titre or "", re.I | re.S))
