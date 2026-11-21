"""Collecte agroclimatique pour l'écosystème « alimentation mondiale » (décision de l'auteur du 2026-11-21, 18 h 10-18 h 17).

Deux sources, collectées automatiquement, aucun modèle de langue :

1. ERA5-Land (Copernicus, réanalyse au sol, maille 0,1°, toutes les terres du globe, 1950 à aujourd'hui, environ
   5 jours de retard ; licence CC BY) par le jeu « reanalysis-era5-land-timeseries » du Climate Data Store : séries
   horaires en un point. Clé personnelle gratuite (secret CDS_API_KEY) ; API documentée, donc régie par ses conditions
   d'utilisation (règle de l'auteur du 2026-11-20). Par point et par jour : température maximale à 2 m, humidité du
   sol 0-7 cm et 7-28 cm (moyennes du jour), pluie du jour.
   Décision de l'auteur (18 h 17) : instrument de mesure objectif, pas besoin d'une seconde source indépendante. Les
   biais propres au modèle (irrigation non représentée, par exemple au Pendjab) se neutralisent en lisant l'ANOMALIE
   du point par rapport à ses propres années passées, jamais la valeur brute.
2. US Drought Monitor (université du Nebraska, USDA, NOAA ; domaine public, sans clé) : part de la surface de chaque
   État concerné dans chaque classe de sécheresse (D0 à D4), chaque semaine.

Registres : registre/era5land-points.csv (point, jour, tmax, sol_0_7, sol_7_28, pluie_mm) et
registre/secheresse-usdm.csv (etat, semaine, aucune, d0, d1, d2, d3, d4). Rien n'entre dans le bot.

    python collecte_agro.py
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
import time
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path

REG = Path("registre")
ERA5 = REG / "era5land-points.csv"
USDM = REG / "secheresse-usdm.csv"
CDS = "https://cds.climate.copernicus.eu/api/retrieve/v1"
JEU_ERA5 = "reanalysis-era5-land-timeseries"
DEBUT = date(2005, 1, 1)                       # vingt ans de référence pour les anomalies saisonnières
VARIABLES = {"2m_temperature": "t2m", "volumetric_soil_water_layer_1": "swvl1",
             "volumetric_soil_water_layer_2": "swvl2", "total_precipitation": "tp"}

# Grands bassins de production (culture principale) ; coordonnées d'une zone de culture, pas d'une ville.
POINTS = {
    "iowa": (42.03, -93.62, "maïs, soja (Corn Belt)"),
    "kansas": (38.50, -98.50, "blé d'hiver (Grandes Plaines)"),
    "vallee_centrale_californie": (36.70, -119.80, "fruits, légumes, riz ; sécheresse"),
    "ukraine_centre": (48.50, 32.30, "blé, maïs, tournesol"),
    "russie_krasnodar": (45.00, 39.00, "blé (sud de la Russie)"),
    "pendjab": (30.90, 75.85, "blé, riz (Inde)"),
    "plaine_chine_nord": (35.00, 115.00, "blé, maïs (Henan, Shandong)"),
    "mato_grosso": (-12.55, -55.71, "soja (Brésil)"),
    "pampa": (-33.90, -60.57, "soja, maïs, blé (Argentine)"),
    "beauce": (48.30, 1.60, "blé (France)"),
    "nouvelle_galles_du_sud": (-33.40, 147.50, "blé (Australie)"),
}
ETATS_USDM = {"CA": "Californie", "IA": "Iowa", "KS": "Kansas", "TX": "Texas", "NE": "Nebraska", "IL": "Illinois"}


# ------------------------------------------------------------------------------------------------------- ERA5-Land
def journalier(lignes_horaires: list[dict]) -> dict[str, dict]:
    """Séries horaires (temps, variable courte → valeur) → valeurs du jour. Température en kelvins → °C ; humidité en
    m³/m³ ; pluie : ERA5-Land cumule depuis 0 h UTC, la pluie du jour est le cumul de 24 h (lu à 0 h du lendemain), ou le
    maximum du jour à défaut."""
    par: dict[str, dict[str, list]] = {}
    for l in lignes_horaires:
        j = l["temps"][:10]
        for k, v in l.items():
            if k != "temps" and v is not None:
                par.setdefault(j, {}).setdefault(k, []).append((l["temps"], v))
    out = {}
    jours = sorted(par)
    for i, j in enumerate(jours):
        d = par[j]
        r = {}
        if d.get("t2m"):
            r["tmax"] = round(max(v for _, v in d["t2m"]) - 273.15, 2)
        for k, nom in (("swvl1", "sol_0_7"), ("swvl2", "sol_7_28")):
            if d.get(k):
                r[nom] = round(sum(v for _, v in d[k]) / len(d[k]), 4)
        lendemain = par.get(jours[i + 1]) if i + 1 < len(jours) else None
        minuit = [v for t, v in (lendemain or {}).get("tp", []) if t[11:13] == "00"]
        if minuit:
            r["pluie_mm"] = round(minuit[0] * 1000, 2)
        elif d.get("tp"):
            r["pluie_mm"] = round(max(v for _, v in d["tp"]) * 1000, 2)
        if r:
            out[j] = r
    return out


def lire_sortie_cds(contenu: bytes) -> list[dict]:
    """La sortie CSV du CDS (zip d'un ou plusieurs CSV, ou CSV nu) → lignes horaires {temps, t2m, swvl1, …}."""
    fichiers = []
    if contenu[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(contenu)) as z:
            fichiers = [z.read(n).decode("utf-8") for n in z.namelist() if n.endswith(".csv")]
    else:
        fichiers = [contenu.decode("utf-8")]
    par_temps: dict[str, dict] = {}
    for f in fichiers:
        for r in csv.DictReader(io.StringIO(f)):
            t = r.get("valid_time") or r.get("time") or r.get("date")
            if not t:
                continue
            t = t.replace("T", " ")
            ligne = par_temps.setdefault(t, {"temps": t})
            for court in VARIABLES.values():
                if r.get(court) not in (None, ""):
                    try:
                        ligne[court] = float(r[court])
                    except ValueError:
                        pass
    return [par_temps[t] for t in sorted(par_temps)]


def demander_cds(c, cle: str, lat: float, lon: float, debut: date, fin: date) -> bytes:
    """Une requête au Climate Data Store (API « retrieve v1 ») : soumission, attente, téléchargement."""
    h = {"PRIVATE-TOKEN": cle}
    corps = {"inputs": {"variable": list(VARIABLES), "location": {"longitude": lon, "latitude": lat},
                        "date": [f"{debut.isoformat()}/{fin.isoformat()}"], "data_format": "csv"}}
    r = c.post(f"{CDS}/processes/{JEU_ERA5}/execution", headers=h, json=corps)
    r.raise_for_status()
    job = r.json()["jobID"]
    for _ in range(180):                                       # au plus 30 minutes par point
        s = c.get(f"{CDS}/jobs/{job}", headers=h).json()
        if s.get("status") == "successful":
            res = c.get(f"{CDS}/jobs/{job}/results", headers=h).json()
            url = res["asset"]["value"]["href"]
            return c.get(url, headers=h).content
        if s.get("status") in ("failed", "rejected", "dismissed"):
            raise RuntimeError(f"requête CDS {s.get('status')} : {json.dumps(s)[:300]}")
        time.sleep(10)
    raise TimeoutError("requête CDS trop longue")


def lire_registre(chemin: Path) -> list[dict]:
    if not chemin.exists():
        return []
    with chemin.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def collecter_era5(c, cle: str) -> int:
    anciennes = lire_registre(ERA5)
    par_point: dict[str, dict[str, dict]] = {}
    for l in anciennes:
        par_point.setdefault(l["point"], {})[l["jour"]] = {k: l[k] for k in ("tmax", "sol_0_7", "sol_7_28", "pluie_mm")}
    fin = date.today() - timedelta(days=5)                    # ERA5-Land-T : environ 5 jours de retard
    nouveaux = 0
    for nom, (lat, lon, _) in POINTS.items():
        connus = par_point.get(nom, {})
        debut = (date.fromisoformat(max(connus)) - timedelta(days=10)) if connus else DEBUT
        try:
            j = journalier(lire_sortie_cds(demander_cds(c, cle, lat, lon, debut, fin)))
        except Exception as e:                                 # un point en panne n'arrête pas les autres
            print(f"ERA5-Land {nom} : {type(e).__name__}: {e}"[:400], flush=True)
            continue
        for jour, r in j.items():
            connus[jour] = {k: r.get(k, "") for k in ("tmax", "sol_0_7", "sol_7_28", "pluie_mm")}
            nouveaux += 1
        par_point[nom] = connus
        print(f"ERA5-Land {nom} : {len(j)} jours lus, {len(connus)} au registre", flush=True)
    with ERA5.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["point", "jour", "tmax", "sol_0_7", "sol_7_28", "pluie_mm"])
        for p in sorted(par_point):
            for j in sorted(par_point[p]):
                r = par_point[p][j]
                w.writerow([p, j, r["tmax"], r["sol_0_7"], r["sol_7_28"], r["pluie_mm"]])
    return nouveaux


# ---------------------------------------------------------------------------------------------- US Drought Monitor
USDM_API = ("https://usdmdataservices.unl.edu/api/StateStatistics/GetDroughtSeverityStatisticsByAreaPercent"
            "?aoi={etat}&startdate={debut}&enddate={fin}&statisticsType=1")


def lire_usdm(js: list[dict], etat: str) -> list[list]:
    out = []
    for r in js:
        k = {x.lower(): v for x, v in r.items()}
        semaine = str(k.get("mapdate") or k.get("validstart") or "")[:10]
        if len(semaine) == 8 and semaine.isdigit():
            semaine = f"{semaine[:4]}-{semaine[4:6]}-{semaine[6:]}"
        try:
            out.append([etat, semaine] + [float(k.get(c, 0) or 0) for c in ("none", "d0", "d1", "d2", "d3", "d4")])
        except (TypeError, ValueError):
            continue
    return out


def collecter_usdm(c) -> int:
    import politesse
    if not politesse.autorise(c, USDM_API.format(etat="CA", debut="1/1/2026", fin="1/2/2026")):
        print("US Drought Monitor : robots.txt refuse, rien collecté")
        return 0
    lignes = []
    fin = date.today()
    for etat in ETATS_USDM:
        url = USDM_API.format(etat=etat, debut="1/1/2005", fin=f"{fin.month}/{fin.day}/{fin.year}")
        try:
            r = c.get(url, headers={"Accept": "application/json"})
            r.raise_for_status()
            lu = lire_usdm(r.json(), etat)
        except Exception as e:
            print(f"US Drought Monitor {etat} : {type(e).__name__}: {e}"[:300], flush=True)
            continue
        lignes += lu
        print(f"US Drought Monitor {etat} : {len(lu)} semaines", flush=True)
        time.sleep(2)
    if lignes:
        with USDM.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["etat", "semaine", "aucune", "d0", "d1", "d2", "d3", "d4"])
            w.writerows(sorted(lignes, key=lambda l: (l[0], l[1])))
    return len(lignes)


def principal() -> int:
    import httpx
    import politesse
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=120, follow_redirects=True) as c:
        n_usdm = collecter_usdm(c)
        cle = os.environ.get("CDS_API_KEY", "").strip()
        n_era5 = collecter_era5(c, cle) if cle else 0
        if not cle:
            print("ERA5-Land : secret CDS_API_KEY absent, rien collecté")
    print(f"bilan : ERA5-Land {n_era5} jours-points, US Drought Monitor {n_usdm} semaines-États")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
