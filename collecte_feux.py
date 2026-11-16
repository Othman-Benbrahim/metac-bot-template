"""Feux et anomalies thermiques par pays, vus par satellite (NASA FIRMS ; bot 0.10.208, en ombre).

Décision d'auteur du 2026-11-16 (22 h 07), après la revue de la boîte à outils de Bellingcat. En zone de conflit, une
hausse brutale des points chauds signale frappes, incendies de villages ou de dépôts, combats ; ailleurs, elle suit
surtout les brûlis agricoles (saisonniers) : d'où le rapport à la quinzaine précédente et le jugement par
l'observatoire, jamais une lecture directe.

Source : API « area » de FIRMS (NASA, données publiques, clé gratuite FIRMS_MAP_KEY), zone « world » :
https://firms.modaps.eosdis.nasa.gov/api/area/csv/{clé}/{source}/world/{jours}/{date}
0.10.211 : l'API « country » répond « 400 Invalid API call » à tout appel, même à la liste des pays (sonde du
2026-11-16) ; on lit donc les détections MONDIALES par fenêtre de JOURS jours (une requête au lieu d'une par pays)
et l'on rattache chaque point à un pays par les frontières de Natural Earth (1:50 m, domaine public ; points en mer :
sans pays). Calcul géométrique : shapely (le workflow le charge avec « uv run --with shapely »).
Capteur : VIIRS ; pour chaque fenêtre, le premier produit qui la couvre selon les dates publiées par FIRMS
(data_availability), archive standard (SP) avant temps quasi réel (NRT) ; aucun produit : fenêtre ignorée. Fenêtres de JOURS jours, une requête mondiale par fenêtre.

On garde des COMPTES : pays, jour, detections, forte_confiance (confiance « h »).
Registres : registre/feux.csv ; registre/feux-jours.txt (jours lus pour TOUS les pays).
Usage : python collecte_feux.py [--depuis AAAA-MM-JJ] [--sonde]   (par défaut : les 10 derniers jours)
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import sys
import time
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx

API = "https://firms.modaps.eosdis.nasa.gov/api/area/csv/{cle}/{source}/world/{jours}/{date}"
FRONTIERES = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson"
SANS_CODE = {"Somaliland": "SO", "Northern Cyprus": "CY"}     # pays de fait sans code ISO : rattachés au pays de droit
REGISTRE = Path("registre") / "feux.csv"
JOURS_LUS = Path("registre") / "feux-jours.txt"
JOURS = 5
UA = {"User-Agent": "alphabet-situationnel-bot/1.0 (recherche ; GitHub Othman-Benbrahim)"}


def compter(texte: str) -> dict[str, list[int]]:
    """CSV FIRMS → jour (acq_date) : [détections, confiance forte] (tous pays confondus)."""
    out: dict[str, list[int]] = {}
    for x in csv.DictReader(io.StringIO(texte)):
        j = (x.get("acq_date") or "")[:10]
        if len(j) != 10:
            continue
        v = out.setdefault(j, [0, 0])
        v[0] += 1
        v[1] += str(x.get("confidence") or "").strip().lower() in ("h", "high")
    return out


def frontieres(geojson: dict) -> tuple[list, list[str]]:
    """Géométries shapely et codes ISO à deux lettres (ISO_A2_EH, puis ISO_A2) des pays de Natural Earth."""
    from shapely.geometry import shape
    geoms, codes = [], []
    for f in geojson.get("features") or []:
        p = f.get("properties") or {}
        code = SANS_CODE.get(p.get("ADMIN")) or next((p.get(k) for k in ("ISO_A2_EH", "ISO_A2")
                                                       if len(str(p.get(k) or "")) == 2), None)
        if code and f.get("geometry"):
            geoms.append(shape(f["geometry"]))
            codes.append(code)
    return geoms, codes


def compter_par_pays(texte: str, geoms: list, codes: list[str]) -> dict[tuple, list[int]]:
    """CSV mondial FIRMS → (pays, jour) : [détections, confiance forte] ; points hors de tout pays ignorés."""
    import shapely
    xs = [x for x in csv.DictReader(io.StringIO(texte)) if len((x.get("acq_date") or "")[:10]) == 10]
    if not xs:
        return {}
    pts = shapely.points([float(x["longitude"]) for x in xs], [float(x["latitude"]) for x in xs])
    arbre = shapely.STRtree(geoms)
    i_pts, i_geo = arbre.query(pts, predicate="within")
    pays_de = {}
    for i, g in zip(i_pts.tolist(), i_geo.tolist()):
        pays_de.setdefault(i, codes[g])
    out: dict[tuple, list[int]] = {}
    for i, x in enumerate(xs):
        p = pays_de.get(i)
        if not p:
            continue
        v = out.setdefault((p, x["acq_date"][:10]), [0, 0])
        v[0] += 1
        v[1] += str(x.get("confidence") or "").strip().lower() in ("h", "high")
    return out


DISPO = "https://firms.modaps.eosdis.nasa.gov/api/data_availability/csv/{cle}/ALL"
# ordre de préférence (0.10.212) : un SEUL capteur tant que possible, pour qu'une quinzaine ne soit pas comparée à
# une quinzaine vue par un autre satellite. NOAA-20 d'abord : il couvre toute la période en archive standard puis en
# temps quasi réel, alors que le temps quasi réel de Suomi NPP s'arrête au 2 novembre 2026 (sonde du 2026-11-16) ;
# archive standard avant temps quasi réel
ORDRE = ("VIIRS_NOAA20_SP", "VIIRS_NOAA20_NRT", "VIIRS_SNPP_SP", "VIIRS_SNPP_NRT", "VIIRS_NOAA21_NRT")


def plages(texte: str) -> dict[str, tuple[str, str]]:
    return {r.get("data_id"): (r.get("min_date") or "", r.get("max_date") or "")
            for r in csv.DictReader(io.StringIO(texte)) if r.get("data_id")}


def source_pour(debut: str, fin: str, dispo: dict[str, tuple[str, str]]) -> str | None:
    """Premier produit qui couvre toute la fenêtre ; None si aucun (données pas encore publiées)."""
    for c in ORDRE:
        lo, hi = dispo.get(c) or ("", "")
        if lo and hi and lo <= debut and fin <= hi:
            return c
    return None


def lire() -> dict[tuple, list[int]]:
    if not REGISTRE.exists():
        return {}
    return {(x["pays"], x["jour"]): [int(x["detections"]), int(x["forte_confiance"])]
            for x in csv.DictReader(REGISTRE.open(encoding="utf-8"))}


def ecrire(reg: dict[tuple, list[int]], jours: set[str]) -> None:
    REGISTRE.parent.mkdir(exist_ok=True)
    with REGISTRE.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pays", "jour", "detections", "forte_confiance"])
        for (p, j), v in sorted(reg.items(), key=lambda t: (t[0][1], t[0][0])):
            w.writerow([p, j, *v])
    JOURS_LUS.write_text("\n".join(sorted(jours)) + "\n", encoding="utf-8")


def sonde(c: httpx.Client, cle: str) -> int:
    """0.10.211 : premier passage = 2 340 refus « 400 Invalid API call » sur l'API « country ». Essais variés, réponses
    affichées (sans la clé), rien d'écrit."""
    hier = (datetime.now(timezone.utc).date() - timedelta(days=2)).isoformat()
    base = "https://firms.modaps.eosdis.nasa.gov/api"
    essais = [("pays, 1 jour, sans date", f"{base}/country/csv/{cle}/VIIRS_NOAA20_NRT/FRA/1"),
              ("pays, 1 jour, avec date", f"{base}/country/csv/{cle}/VIIRS_NOAA20_NRT/FRA/1/{hier}"),
              ("pays UKR, 3 jours", f"{base}/country/csv/{cle}/VIIRS_NOAA20_NRT/UKR/3/{hier}"),
              ("liste des pays", f"{base}/countries/?format=csv"),
              ("zone monde, 1 jour", f"{base}/area/csv/{cle}/VIIRS_NOAA20_NRT/world/1/{hier}"),
              ("zone Ukraine (rectangle), 1 jour", f"{base}/area/csv/{cle}/VIIRS_NOAA20_NRT/22,44,41,53/1/{hier}"),
              ("compteur de transactions", f"https://firms.modaps.eosdis.nasa.gov/mapserver/mapkey_status/?MAP_KEY={cle}")]
    l = ["## Sonde FIRMS", ""]
    for nom, url in essais:
        try:
            r = c.get(url, timeout=180)
            t = r.text
            lignes = t.count("\n")
            l.append(f"- {nom} : HTTP {r.status_code}, {len(t)} caractères, {lignes} lignes ; début : "
                     f"{t[:160].replace(cle, '«clé»')!r}")
        except Exception as e:
            l.append(f"- {nom} : {type(e).__name__}: {str(e)[:120].replace(cle, '«clé»')}")
        time.sleep(1)
    texte = "\n".join(l)
    print(texte)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(texte + "\n")
    return 0


def principal() -> int:
    a_ = argparse.ArgumentParser()
    a_.add_argument("--depuis", default="")
    a_.add_argument("--sonde", action="store_true")
    a = a_.parse_args()
    cle = os.environ.get("FIRMS_MAP_KEY", "").strip()
    if not cle:
        print("Clé FIRMS absente (secret FIRMS_MAP_KEY) : rien à faire.")
        return 1
    if a.sonde:
        with httpx.Client(headers=UA, timeout=120, follow_redirects=True) as c:
            return sonde(c, cle)
    aujourdhui = datetime.now(timezone.utc).date()
    hier = aujourdhui - timedelta(days=1)
    debut = date.fromisoformat(a.depuis) if a.depuis else aujourdhui - timedelta(days=10)
    reg = lire()
    jours = set(JOURS_LUS.read_text(encoding="utf-8").split()) if JOURS_LUS.exists() else set()
    requetes = echecs = 0
    with httpx.Client(headers=UA, timeout=300, follow_redirects=True) as c:
        geoms, codes = frontieres(c.get(FRONTIERES, timeout=120).json())
        tous = sorted(set(codes))
        print(f"{len(tous)} pays et territoires (Natural Earth 1:50 m).")
        dispo = plages(c.get(DISPO.format(cle=cle)).text)
        print("Produits FIRMS :", ", ".join(f"{k} {v[0]}→{v[1]}" for k, v in dispo.items() if k in ORDRE))
        d = debut
        while d <= hier:
            fin = min(d + timedelta(days=JOURS - 1), hier)
            fenetre = [(d + timedelta(days=k)).isoformat() for k in range((fin - d).days + 1)]
            if all(j in jours for j in fenetre):
                d = fin + timedelta(days=1)
                continue
            produit = source_pour(fenetre[0], fenetre[-1], dispo)
            if not produit:
                print(f"  fenêtre {fenetre[0]} → {fenetre[-1]} : aucun produit FIRMS ne la couvre ; ignorée")
                d = fin + timedelta(days=1)
                continue
            try:
                r = c.get(API.format(cle=cle, source=produit, jours=len(fenetre), date=d.isoformat()))
                requetes += 1
                if r.status_code != 200 or r.text.lower().startswith(("invalid", "error")):
                    raise RuntimeError(f"HTTP {r.status_code} {r.text[:80]}")
                par_pays = compter_par_pays(r.text, geoms, codes)
            except Exception as e:
                echecs += 1
                print(f"  fenêtre {fenetre[0]} → {fenetre[-1]} : {type(e).__name__}: {str(e)[:100]}")
                d = fin + timedelta(days=1)
                time.sleep(2)
                continue
            # garde : une fenêtre sans AUCUN point chaud dans le monde veut dire « données pas encore publiées »,
            # jamais « zéro feu » : rien n'est gardé, la fenêtre sera relue
            if not par_pays:
                print(f"  fenêtre {fenetre[0]} → {fenetre[-1]} : aucune détection dans le monde, données non publiées ; ignorée")
            else:
                for p in tous:
                    for j in fenetre:
                        reg[(p, j)] = par_pays.get((p, j), [0, 0])
                jours.update(fenetre)
                print(f"  fenêtre {fenetre[0]} → {fenetre[-1]} ({produit}) : "
                      f"{sum(v[0] for v in par_pays.values())} détections rattachées à un pays")
            ecrire(reg, jours)
            d = fin + timedelta(days=1)
            time.sleep(2)
    ecrire(reg, jours)
    recents = Counter()
    for (p, j), v in reg.items():
        if j >= (hier - timedelta(days=13)).isoformat():
            recents[p] += v[0]
    bilan = (f"{requetes} requête(s), {echecs} échec(s) ; {len(jours)} jours complets au registre. "
             f"Pays les plus touchés sur 14 jours : {dict(recents.most_common(8))}. Source : NASA FIRMS (VIIRS).")
    print(bilan)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(f"## Feux par pays (NASA FIRMS)\n\n{bilan}\n")
    return 0 if requetes and echecs < requetes else 1


if __name__ == "__main__":
    sys.exit(principal())
