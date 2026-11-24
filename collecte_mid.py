"""Correlates of War, Militarized Interstate Disputes v5.0 (1816-2014 ; Palmer et al. 2022) — bot 0.10.503.

Décision de l'auteur du 2026-11-24 (16 h 46) : seconde couche « entre États » depuis 1946 (affrontements armés, au-delà
des guerres), pour la tenue des trêves entre États. On garde les fichiers MIDA (niveau dispute) et MIDB (niveau
participant) tels que publiés (données codées). robots.txt respecté.
Sorties : registre/mid-a.csv, registre/mid-b.csv.
"""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import httpx

import politesse

URL = "https://correlatesofwar.org/wp-content/uploads/MID-5-Data-and-Supporting-Materials.zip"
SORTIES = {"MIDA": Path("registre") / "mid-a.csv", "MIDB": Path("registre") / "mid-b.csv"}


def principal() -> int:
    with httpx.Client(follow_redirects=True, timeout=180, headers={"User-Agent": politesse.UA}) as c:
        if not politesse.autorise(c, URL):
            print("MID : refusé par robots.txt, rien collecté")
            return 0
        r = c.get(URL)
        r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    noms = z.namelist()
    print("archive :", noms)
    for cle, sortie in SORTIES.items():
        n = [x for x in noms if x.split("/")[-1].upper().startswith(cle) and x.lower().endswith(".csv")]
        if not n:
            print(f"{cle} : absent de l'archive")
            continue
        texte = z.read(n[0]).decode("utf-8-sig", errors="replace")
        sortie.parent.mkdir(exist_ok=True)
        sortie.write_text(texte.replace("\r\n", "\n").replace("\r", "\n"), encoding="utf-8", newline="\n")
        L = texte.splitlines()
        print(f"{sortie} : {len(L) - 1} lignes ; en-têtes : {L[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
