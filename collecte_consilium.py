"""Calendrier des réunions du Conseil européen et du Conseil de l'UE (consilium.europa.eu, pages publiques ; décision de
l'auteur du 2026-11-26, 16 h 59 : « let's go »). robots.txt respecté (politesse.autorise) ; seules des dates et des
intitulés de réunion sont gardés.

Écrit registre/calendrier-consilium.csv (date, reunion, page). Diagnostic imprimé au premier passage (structure de la
page encore inconnue : on lit les dates « 17 December 2026 » et l'intitulé voisin, et on montre ce qui a été trouvé).
    python collecte_consilium.py
"""
from __future__ import annotations

import csv
import re
import sys
from datetime import datetime
from html import unescape
from pathlib import Path

import httpx

import politesse

PAGES = ["https://www.consilium.europa.eu/en/meetings/future-euco-meetings/",
         "https://www.consilium.europa.eu/en/meetings/upcoming-summits/"] + \
        [f"https://www.consilium.europa.eu/en/meetings/calendar/?page={i}" for i in range(1, 9)]
SORTIE = Path("registre") / "calendrier-consilium.csv"
DATE = re.compile(r"\b(\d{1,2}) (January|February|March|April|May|June|July|August|September|October|November|December) (20\d\d)\b")
LIEN = re.compile(r'href="(/en/meetings/[a-z0-9-]+/20\d\d/\d\d/\d\d/?)"[^>]*>(.*?)</a>', re.S)


def texte(h: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", h))).strip()


def principal() -> int:
    lignes = {}
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=60, follow_redirects=True) as c:
        for u in PAGES:
            if not politesse.autorise(c, u):
                print(f"refusé par robots.txt : {u}")
                continue
            r = c.get(u)
            print(f"{u} : HTTP {r.status_code}, {len(r.text)} caractères")
            if r.status_code != 200:
                continue
            # 1) liens de réunion datés dans l'adresse (/en/meetings/<formation>/AAAA/MM/JJ/)
            n = 0
            for href, lib in LIEN.findall(r.text):
                a, m, j = href.rstrip("/").split("/")[-3:]
                cle = (f"{a}-{m}-{j}", href.split("/")[3])
                lignes[cle] = {"date": cle[0], "reunion": texte(lib)[:150] or cle[1], "page": "https://www.consilium.europa.eu" + href}
                n += 1
            # 2) repli : dates écrites en toutes lettres (page sans liens datés)
            if n == 0:
                for jj, mm, aa in DATE.findall(texte(r.text)):
                    d = datetime.strptime(f"{jj} {mm} {aa}", "%d %B %Y").date().isoformat()
                    reun = "European Council" if "euco" in u else "Conseil de l'UE (formation non lue)"
                    lignes.setdefault((d, reun), {"date": d, "reunion": reun, "page": u})
            print(f"   réunions lues : {n} par liens datés ; total cumulé {len(lignes)}")
    if not lignes:
        print("aucune réunion lue")
        return 0
    with SORTIE.open("w", encoding="utf-8", newline="\n") as f:
        w = csv.DictWriter(f, fieldnames=["date", "reunion", "page"])
        w.writeheader()
        for k in sorted(lignes):
            w.writerow(lignes[k])
    for k in sorted(lignes)[:15]:
        print("  ", lignes[k]["date"], lignes[k]["reunion"][:80])
    return 0


if __name__ == "__main__":
    sys.exit(principal())
