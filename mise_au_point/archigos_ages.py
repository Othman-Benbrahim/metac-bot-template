"""Âge des dirigeants en poste au 1er juillet de chaque année, par région, 1946-2015 (Archigos 4.1, peacesciencer 1.1.0)
→ ecosystemes/dirigeants-ages.csv. Demande de l'auteur, 2026-11-25 (l'âge des dirigeants comme indicateur) ; source déjà
validée le 2026-11-24. Une ligne par année et région : nombre de dirigeants, âge moyen, part des 70 ans et plus.
    uv run --with pyreadr python -I mise_au_point/archigos_ages.py chemin/vers/archigos.rda
Régions par code Gleditsch-Ward (découpage usuel) : ameriques 2-165, europe 200-399, afrique 400-626,
moyen_orient 630-698, asie_oceanie 700-990."""
import sys
from pathlib import Path

import pandas as pd
import pyreadr

REG = {"ameriques": (2, 165), "europe": (200, 399), "afrique": (400, 626), "moyen_orient": (630, 698), "asie_oceanie": (700, 990)}
df = list(pyreadr.read_r(sys.argv[1]).values())[0].dropna(subset=["yrborn"])
df["s"], df["e"] = pd.to_datetime(df.startdate), pd.to_datetime(df.enddate)
lignes = []
for an in range(1946, 2016):
    j = pd.Timestamp(f"{an}-07-01")
    x = df[(df.s <= j) & (df.e > j)].drop_duplicates("gwcode")
    for nom, (lo, hi) in [("monde", (0, 999)), *REG.items()]:
        y = x[(x.gwcode >= lo) & (x.gwcode <= hi)]
        if len(y):
            age = an - y.yrborn
            lignes.append((an, nom, len(y), round(age.mean(), 2), round(100 * (age >= 70).mean(), 2)))
out = Path(__file__).resolve().parent.parent / "ecosystemes" / "dirigeants-ages.csv"
with out.open("w", encoding="utf-8") as h:
    h.write("# Âge des dirigeants en poste au 1er juillet (Archigos 4.1 via peacesciencer 1.1.0, 1946-2015) ; mise_au_point/archigos_ages.py\n")
    h.write("annee,region,n,age_moyen,part70\n")
    for l in lignes:
        h.write(",".join(map(str, l)) + "\n")
print(len(lignes), "lignes ->", out)
