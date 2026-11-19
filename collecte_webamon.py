"""Collecte Webamon (offre gratuite, sans clé) : comptes quotidiens pour information-cyber:cyber (bot 0.10.350, ombre).

L'auteur confirme le 2026-11-19 (15 h 01) que la collecte automatique est permise par Webamon. La sonde du même jour
(run 44535877566) a montré que l'offre gratuite rend un total « total_hits » par requête. On ne garde que des COMPTES
par jour (aucun domaine, aucune adresse, rien de l'index des données volées) :
- new_domains : nouveaux domaines enregistrés ce jour-là ;
- scans : analyses d'URL soumises ce jour-là (hameçonnage et menaces confondus).

Petite dose : à chaque passage, au plus MAX_REQUETES requêtes, pour les jours manquants des JOURS derniers jours (le
plus récent d'abord), une pause entre deux. La syntaxe de date de l'index n'étant pas documentée, on essaie quelques
formes sur un jour connu et l'on garde la première qui rend un compte strictement entre 0 et le total ; si aucune ne
convient, on n'écrit rien.

Registre : registre/webamon.csv (index, jour, total).
"""
from __future__ import annotations

import csv
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import httpx

import politesse

BASE = "https://search.webamon.com"
SORTIE = Path("registre") / "webamon.csv"
INDEX = ("new_domains", "scans")
JOURS = 90
MAX_REQUETES = 30
PAUSE = 5.0
FORMES = ('date:[{j} TO {j}]', 'date:"{j}"', 'date:{j}*', 'date:[{j} TO {k}}}')


def total(c: httpx.Client, index: str, requete: str) -> int | None:
    try:
        r = c.get(BASE + "/search", params={"lucene_query": requete, "index": index, "size": 1})
        if r.status_code == 429:
            return -1
        r.raise_for_status()
        return int(r.json().get("total_hits"))
    except Exception:
        return None


def lire() -> dict[tuple[str, str], int]:
    if not SORTIE.exists():
        return {}
    return {(r["index"], r["jour"]): int(r["total"]) for r in csv.DictReader(SORTIE.open(encoding="utf-8"))}


def principal() -> int:
    deja = lire()
    hier = date.today() - timedelta(days=1)
    with httpx.Client(headers={"User-Agent": politesse.UA, "Accept": "application/json"}, timeout=60) as c:
        if not politesse.autorise(c, BASE + "/search"):
            print("::warning::Webamon : refusé par robots.txt ; rien collecté.")
            return 0
        n_req = 0
        tout = {i: total(c, i, "*") for i in INDEX}
        n_req += len(INDEX)
        test = (hier - timedelta(days=1)).isoformat()
        forme = None
        for f in FORMES:
            t = total(c, "new_domains", f.format(j=test, k=(hier).isoformat()))
            n_req += 1
            time.sleep(PAUSE)
            if t is not None and t > 0 and (tout["new_domains"] is None or t < tout["new_domains"]):
                forme = f
                break
        if not forme:
            print("::warning::Webamon : aucune syntaxe de date ne rend un compte plausible ; rien écrit.")
            return 0
        print(f"syntaxe retenue : {forme}", flush=True)
        for d in range(1, JOURS + 1):
            j = (date.today() - timedelta(days=d)).isoformat()
            k = (date.today() - timedelta(days=d - 1)).isoformat()
            for idx in INDEX:
                if (idx, j) in deja or n_req >= MAX_REQUETES:
                    continue
                t = total(c, idx, forme.format(j=j, k=k))
                n_req += 1
                if t == -1:
                    print("::warning::Webamon : quota du jour atteint ; on s'arrête.")
                    n_req = MAX_REQUETES
                    break
                if t is not None and t >= 0:
                    deja[(idx, j)] = t
                time.sleep(PAUSE)
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with SORTIE.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["index", "jour", "total"])
        for (i, j), t in sorted(deja.items(), key=lambda x: (x[0][1], x[0][0])):
            w.writerow([i, j, t])
    print(f"Webamon : {len(deja)} comptes (index × jour) ; {n_req} requêtes ce passage.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
