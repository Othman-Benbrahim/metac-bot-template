"""Inflation de Tokyo (indice des prix à la consommation, arrondissements de Tokyo) via l'API e-Stat (0.10.405).

This service uses API functions from e-Stat, however its contents are not guaranteed by government.
(Mention exigée par e-Stat : https://www.e-stat.go.jp/api/en/api-info/credit)

Clé gratuite dans le secret ESTAT_APP_ID, jamais écrite. Premier passage = repérage : liste des tableaux de l'enquête sur
les prix (code 00200573) qui portent sur les arrondissements de Tokyo (registre/estat-tableaux-tokyo.json : identifiant,
titre, période). Le tableau retenu sera fixé dans TABLEAU après lecture de cette liste.

    python collecte_estat.py
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
TABLEAU = None   # identifiant statsDataId, fixé après le repérage


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


def principal() -> int:
    cle = os.environ.get("ESTAT_APP_ID")
    if not cle:
        print("::warning::ESTAT_APP_ID absente : rien collecté.")
        return 0
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=60) as c:
        if TABLEAU is None:
            return reperage(c, cle)
    return 0


if __name__ == "__main__":
    sys.exit(principal())
