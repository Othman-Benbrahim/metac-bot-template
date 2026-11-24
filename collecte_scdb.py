"""Supreme Court Database (Penn State ; « Modern Database 2026 Release 01 », affaires 1946-2025) — bot 0.10.508.

Décision de l'auteur du 2026-11-24 (18 h 19 : « la suite ? » → justice) : mesure de l'issue au fond (part des affaires
gagnées par le demandeur) et du rythme des départs de juges. Fichiers « case centered » et « justice centered »
(organisés par citation), données codées. robots.txt respecté. Citation : Spaeth et al., Supreme Court Database.
Sorties : registre/scdb-affaires.csv, registre/scdb-juges.csv.
"""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import httpx

import politesse

FICHIERS = {
    "registre/scdb-affaires.csv": "https://scdb.la.psu.edu/?jet_download=69e2a3e7da8f9782e65de282ff4742e4116bae7e",
    "registre/scdb-juges.csv": "https://scdb.la.psu.edu/?jet_download=c99e5d5b7131dda1f6d1c06a5e7c4dda58c38c88",
}


def _texte(contenu: bytes) -> str:
    if contenu[:2] == b"PK":                               # archive zip : le premier .csv
        z = zipfile.ZipFile(io.BytesIO(contenu))
        nom = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        contenu = z.read(nom)
    for enc in ("utf-8-sig", "latin-1"):
        try:
            return contenu.decode(enc)
        except UnicodeDecodeError:
            continue
    return contenu.decode("utf-8", errors="replace")


def principal() -> int:
    code = 0
    with httpx.Client(follow_redirects=True, timeout=180, headers={"User-Agent": politesse.UA}) as c:
        for sortie, url in FICHIERS.items():
            if not politesse.autorise(c, url):
                print(f"{url} : refusé par robots.txt")
                continue
            r = c.get(url)
            if r.status_code != 200:
                print(f"{url} : HTTP {r.status_code}")
                code = 1
                continue
            t = _texte(r.content).replace("\r\n", "\n")
            Path(sortie).parent.mkdir(exist_ok=True)
            Path(sortie).write_text(t, encoding="utf-8", newline="\n")
            L = t.splitlines()
            print(f"{sortie} : {len(L) - 1} lignes ; en-têtes : {L[0][:600]}")
    return code


if __name__ == "__main__":
    sys.exit(principal())
