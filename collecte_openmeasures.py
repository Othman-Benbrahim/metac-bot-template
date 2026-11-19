"""Collecte Open Measures (API publique, sans clé) : comptes de récits de complot sur des plateformes marginales
(bot 0.10.351, ombre). Compartiment humain:croyance_complot, premier de l'ordre des collectes (priorites_traces.py).

Proposée par l'auteur le 2026-11-19 (15 h 12) ; documentation : docs.openmeasures.io (guide « public API »).
Limites de l'offre publique : 39 requêtes par jour, contenus d'au moins six mois. On ne garde que des COMPTES par jour
(aucun texte, aucun nom de compte) :
- complot : vocabulaire fixe du Nouvel Ordre mondial (Barkun) : « new world order », « deep state », « illuminati »,
  « great reset », « globalists » ;
- reference : termes très courants (« the OR and »), pour normaliser par le volume de la plateforme.
Plateforme : Telegram (la plus suivie par nos autres collectes). Une requête par (plateforme, série) et par passage,
sur une fenêtre de 180 jours qui finit six mois avant aujourd'hui ; l'histoire s'allonge de passage en passage.

Le point d'accès des séries temporelles (« /timeseries », intervalle quotidien) n'est pas documenté sur la page publique
consultée ; on l'essaie, et l'on lit la réponse de façon tolérante (seaux { clé ou date, nombre }). Si rien n'est
reconnu, on n'écrit rien et on le dit.

Registre : registre/openmeasures.csv (site, serie, jour, n).
"""
from __future__ import annotations

import csv
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx

import politesse

BASE = "https://api.openmeasures.io"
SORTIE = Path("registre") / "openmeasures.csv"
SITES = ("telegram",)
SERIES = {"complot": '"new world order" OR "deep state" OR illuminati OR "great reset" OR globalists',
          "reference": "the OR and"}
FENETRE = 180
RETARD = 183
PAUSE = 10.0


def seaux(obj) -> list[tuple[str, float]]:
    """Cherche dans une réponse JSON une liste de seaux datés : {key_as_string|key|date, doc_count|count|value}."""
    if isinstance(obj, dict):
        for v in obj.values():
            r = seaux(v)
            if r:
                return r
        return []
    if isinstance(obj, list) and obj and isinstance(obj[0], dict):
        out = []
        for b in obj:
            k = b.get("key_as_string") or b.get("date") or b.get("key")
            n = b.get("doc_count", b.get("count", b.get("value")))
            if k is None or n is None:
                return []
            if isinstance(k, (int, float)):
                k = datetime.fromtimestamp(k / 1000, tz=timezone.utc).date().isoformat()
            out.append((str(k)[:10], float(n)))
        return out
    return []


def lire() -> dict[tuple[str, str, str], float]:
    if not SORTIE.exists():
        return {}
    return {(r["site"], r["serie"], r["jour"]): float(r["n"]) for r in csv.DictReader(SORTIE.open(encoding="utf-8"))}


def principal() -> int:
    deja = lire()
    jusqu = date.today() - timedelta(days=RETARD)
    debut_connu = min((j for (_, _, j) in deja), default=None)
    # on remonte le temps : la fenêtre finit au plus ancien jour déjà connu, ou six mois avant aujourd'hui
    fin = date.fromisoformat(debut_connu) - timedelta(days=1) if debut_connu else jusqu
    debut = fin - timedelta(days=FENETRE)
    nouveaux = 0
    with httpx.Client(headers={"User-Agent": politesse.UA, "Accept": "application/json"}, timeout=120) as c:
        if not politesse.autorise(c, BASE + "/timeseries"):
            print("::warning::Open Measures : refusé par robots.txt ; rien collecté.")
            return 0
        for site in SITES:
            for nom, terme in SERIES.items():
                try:
                    r = c.get(BASE + "/timeseries", params={"site": site, "term": terme, "interval": "day",
                                                            "querytype": "boolean_content",
                                                            "since": f"{debut.isoformat()}T00:00:00Z",
                                                            "until": f"{fin.isoformat()}T23:59:59Z"})
                    if r.status_code == 429:
                        print("::warning::Open Measures : quota du jour atteint.")
                        break
                    r.raise_for_status()
                    s = seaux(r.json())
                except Exception as e:
                    s = []
                    print(f"::warning::Open Measures {site} {nom} : {type(e).__name__}")
                for j, n in s:
                    if debut.isoformat() <= j <= fin.isoformat():
                        deja[(site, nom, j)] = n
                        nouveaux += 1
                print(f"{site} {nom} : {len(s)} seaux reçus ({debut} → {fin})", flush=True)
                time.sleep(PAUSE)
    if not nouveaux:
        print("::warning::Open Measures : aucun seau reconnu ; rien écrit.")
        return 0
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with SORTIE.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["site", "serie", "jour", "n"])
        for (s, nom, j), n in sorted(deja.items(), key=lambda x: (x[0][2], x[0][0], x[0][1])):
            w.writerow([s, nom, j, n])
    print(f"Open Measures : {nouveaux} comptes nouveaux ; {len(deja)} au total.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
