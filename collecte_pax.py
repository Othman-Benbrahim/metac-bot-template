"""PA-X, base des accords de paix (Université d'Édimbourg, PeaceRep), v10 du 20 juillet 2026 — bot 0.10.500.

Décision de l'auteur du 2026-11-24 (16 h 16) : « Je valide les trois points » (PA-X comme source pour les accords).
Licence CC BY-NC-SA 4.0 ; citation : Bell, C. & Badanjak, S. (2019), « Introducing PA-X: A new peace agreement database
and dataset », Journal of Peace Research 56(3) ; PA-X, www.peaceagreements.org.
On ne garde AUCUN texte d'accord : seulement, par accord, le processus de paix, la nature du conflit, le niveau
(inter-États ou non), le stade (Cea = cessez-le-feu, SubComp, SubPar, Pre, Imp, Ren, Other) et la date de signature.
robots.txt respecté (politesse.autorise) ; un refus n'est jamais contourné.
Sortie : registre/pax-accords.csv. Usage : python collecte_pax.py
"""
from __future__ import annotations

import csv
import io
import re
import sys
from pathlib import Path

import httpx

import politesse

# 2026-11-24, 16 h 22 : le site peaceagreements.org refuse la collecte (robots.txt) ; décision de l'auteur (16 h 25) :
# le refus vaut pour ce site seulement → copie v10 publiée par PeaceRep elle-même sur GitHub (dépôt de sa carte).
URL = "https://raw.githubusercontent.com/peacerep/pax-map/HEAD/data/pax_data_v10.csv"
SORTIE = Path("registre") / "pax-accords.csv"
# en-têtes possibles (données courtes ou intitulés du livre de codes)
COLS = {"processus": ("PPName", "Peace Process Name", "PP"), "nature": ("Contp", "Conflict Nature"),
        "niveau": ("Agtp", "Agreement/Conflict Level"), "stade": ("Stage",), "date": ("Dat", "Signed Date", "Date Signed"),
        "pays": ("Con", "Country")}


def _col(entetes, noms):
    for n in noms:
        if n in entetes:
            return n
    return None


def _date(v: str) -> str:
    v = (v or "").strip()
    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", v):                 # JJ/MM/AAAA dans la copie de PeaceRep
        j, m, a = v.split("/")
        return f"{a}-{m}-{j}"
    return v[:10]


def principal() -> int:
    if len(sys.argv) > 1:                                      # fichier local (même contenu), pour les essais
        return _ecrire(Path(sys.argv[1]).read_bytes().decode("utf-8-sig", errors="replace"))
    with httpx.Client(follow_redirects=True, timeout=120, headers={"User-Agent": politesse.UA}) as c:
        if not politesse.autorise(c, URL):
            print("PA-X : refusé par robots.txt, rien collecté")
            return 0
        r = c.get(URL)
        r.raise_for_status()
    return _ecrire(r.content.decode("utf-8-sig", errors="replace"))


def _ecrire(texte: str) -> int:
    lec = csv.DictReader(io.StringIO(texte))
    ent = lec.fieldnames or []
    choix = {k: _col(ent, v) for k, v in COLS.items()}
    print("en-têtes reconnus :", choix)
    manque = [k for k, v in choix.items() if v is None and k in ("processus", "stade", "date")]
    if manque:
        print("en-têtes absents :", manque, "; en-têtes du fichier :", ent[:60])
        return 1
    lignes = []
    for x in lec:
        d = _date(x.get(choix["date"]) or "")
        if len(d) != 10:
            continue
        lignes.append({k: (x.get(v) or "").strip() if v else "" for k, v in choix.items() if k != "date"} | {"date": d})
    lignes.sort(key=lambda z: (z["date"], z["processus"]))
    SORTIE.parent.mkdir(exist_ok=True)
    with SORTIE.open("w", encoding="utf-8", newline="\n") as f:
        w = csv.DictWriter(f, fieldnames=["date", "processus", "pays", "nature", "niveau", "stade"])
        w.writeheader()
        w.writerows(lignes)
    print(f"PA-X : {len(lignes)} accords datés → {SORTIE}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
