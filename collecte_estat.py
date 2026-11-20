"""Inflation de Tokyo (indice des prix à la consommation, arrondissements de Tokyo) via l'API e-Stat (0.10.405).

This service uses API functions from e-Stat, however its contents are not guaranteed by government.
(Mention exigée par e-Stat : https://www.e-stat.go.jp/api/en/api-info/credit)

Clé gratuite dans le secret ESTAT_APP_ID, jamais écrite. Premier passage = repérage : liste des tableaux de l'enquête sur
les prix (code 00200573) qui portent sur les arrondissements de Tokyo (registre/estat-tableaux-tokyo.json : identifiant,
titre, période). Le tableau retenu sera fixé dans TABLEAU après lecture de cette liste.

    python collecte_estat.py              # collecte (registre/estat-tokyo-cpi.csv)
    python collecte_estat.py --reperage   # liste des tableaux
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import httpx

import politesse

API = "https://api.e-stat.go.jp/rest/3.0/app/json"
TABLEAUX = Path("registre") / "estat-tableaux-tokyo.json"
TABLEAU = None   # (repérage seul) ; la collecte utilise TABLEAUX_RETENUS
# repérage du 2026-11-20 : indice des prix, arrondissements de Tokyo, une table par année de base
TABLEAUX_RETENUS = {"2015": "0003143513", "2020": "0003427113", "2025": "0004052037"}
SERIE = Path("registre") / "estat-tokyo-cpi.csv"
META = Path("registre") / "estat-meta-tokyo.json"
# ce qu'on veut dans chaque dimension (nom exact e-Stat) ; le temps est pris en entier
CIBLES = {"categorie": ["生鮮食品を除く総合"], "zone": ["東京都区部", "区部"],
          "mesure": ["前年同月比", "前年同月比（%）"]}


def reperage(c: httpx.Client, cle: str) -> int:
    out = []
    for mot in ("区部", "東京都区部"):
        r = c.get(f"{API}/getStatsList", params={"appId": cle, "statsCode": "00200573", "searchWord": mot, "limit": 200})
        d = r.json().get("GET_STATS_LIST", {})
        res = d.get("DATALIST_INF", {}).get("TABLE_INF") or []
        if isinstance(res, dict):
            res = [res]
        for t in res:
            titre = t.get("TITLE")
            titre = titre.get("$") if isinstance(titre, dict) else titre
            out.append({"id": t.get("@id"), "titre": titre, "enquete": (t.get("STATISTICS_NAME") or ""),
                        "periode": t.get("SURVEY_DATE"), "mise_a_jour": t.get("UPDATED_DATE")})
        time.sleep(1)
    vus = {x["id"]: x for x in out}
    TABLEAUX.write_text(json.dumps(list(vus.values()), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"e-Stat : {len(vus)} tableaux repérés pour les arrondissements de Tokyo")
    for x in list(vus.values())[:40]:
        print(x["id"], x["mise_a_jour"], x["titre"])
    return 0


def _liste(x):
    return x if isinstance(x, list) else ([x] if x else [])


def codes_voulus(meta: dict) -> tuple[dict, dict]:
    """Pour chaque dimension sauf le temps : le code dont le nom est une cible (ou l'unique code). Rend aussi les noms
    des mois (code de temps -> nom)."""
    choix, temps = {}, {}
    for o in _liste(meta["GET_META_INFO"]["METADATA_INF"]["CLASS_INF"]["CLASS_OBJ"]):
        cl = _liste(o.get("CLASS"))
        if o["@id"] == "time":
            temps = {c["@code"]: c["@name"] for c in cl}
            continue
        trouve = None
        for noms in CIBLES.values():
            for n in noms:
                trouve = trouve or next((c["@code"] for c in cl if c["@name"] == n), None)
        if trouve is None and len(cl) == 1:
            trouve = cl[0]["@code"]
        if trouve is None:
            raise ValueError(f"dimension {o['@id']} ({o.get('@name')}) : aucune cible parmi "
                             f"{[c['@name'] for c in cl][:30]}")
        choix[o["@id"]] = trouve
    return choix, temps


def mois(nom: str) -> str | None:
    import re
    m = re.match(r"(\d{4})年(\d{1,2})月", nom or "")
    return f"{m.group(1)}-{int(m.group(2)):02d}" if m else None


def collecte(c: httpx.Client, cle: str) -> int:
    lignes, metas = [], {}
    for base, tid in TABLEAUX_RETENUS.items():
        meta = c.get(f"{API}/getMetaInfo", params={"appId": cle, "statsDataId": tid}).json()
        time.sleep(1)
        metas[base] = {o["@id"]: {"nom": o.get("@name"), "codes": [(x["@code"], x["@name"]) for x in _liste(o.get("CLASS"))][:80]}
                       for o in _liste(meta["GET_META_INFO"]["METADATA_INF"]["CLASS_INF"]["CLASS_OBJ"])}
        try:
            choix, temps = codes_voulus(meta)
        except ValueError as e:
            print(f"::warning::base {base} : {e}")
            continue
        params = {"appId": cle, "statsDataId": tid, "limit": 100000}
        for dim, code in choix.items():
            params["cd" + dim[0].upper() + dim[1:]] = code
        d = c.get(f"{API}/getStatsData", params=params).json()
        time.sleep(1)
        vals = _liste(d["GET_STATS_DATA"].get("STATISTICAL_DATA", {}).get("DATA_INF", {}).get("VALUE"))
        n = 0
        for v in vals:
            m = mois(temps.get(v.get("@time")))
            try:
                x = float(v["$"])
            except (KeyError, ValueError):
                continue
            if m:
                lignes.append((m, base, x))
                n += 1
        print(f"base {base} ({tid}) : {n} mois ; codes {choix}")
    META.write_text(json.dumps(metas, ensure_ascii=False, indent=1), encoding="utf-8")
    if not lignes:
        print("::warning::aucune valeur ; voir registre/estat-meta-tokyo.json")
        return 0
    import csv
    with SERIE.open("w", encoding="utf-8", newline="") as fo:
        w = csv.writer(fo)
        w.writerow(["mois", "base", "inflation_hors_frais_sur_un_an"])
        w.writerows(sorted(set(lignes)))
    print(f"e-Stat : {len(set(lignes))} valeurs -> {SERIE}")
    print("This service uses API functions from e-Stat, however its contents are not guaranteed by government.")
    return 0


def principal() -> int:
    cle = os.environ.get("ESTAT_APP_ID")
    if not cle:
        print("::warning::ESTAT_APP_ID absente : rien collecté.")
        return 0
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=60) as c:
        if "--reperage" in sys.argv:
            return reperage(c, cle)
        return collecte(c, cle)


if __name__ == "__main__":
    sys.exit(principal())
