"""Comptes quotidiens d'événements par pays, tirés de GDELT 1.0 (fichiers quotidiens publics, sans clé) (0.10.120,
décision d'auteur du 2026-11-15 : la croyance des acteurs et les seuils de mobilisation demandent la suite DATÉE des
événements par pays, que l'accès ACLED du banc ne donne pas).

Pour chaque jour de la période : téléchargement de http://data.gdeltproject.org/events/AAAAMMJJ.export.CSV.zip, puis
comptes par pays (dernier élément du nom de lieu de l'action, ActionGeo_FullName) et par famille CAMEO :
  manif (code racine 14 : protestations), violence (18 assaut, 19 combat, 20 violence de masse), menace (13).
Les fichiers bruts ne sont pas gardés ; seul le tableau agrégé l'est : registre/gdelt-comptes.csv (jour, pays, famille,
nombre). Limite connue : GDELT compte des ARTICLES codés automatiquement, pas des événements vérifiés ; un même fait
rapporté par beaucoup de médias compte plusieurs fois (mesure d'attention autant que d'événements).

    python gdelt_comptes.py --debut 2026-03-01 --fin 2026-10-31
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import io
import sys
import zipfile
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

import httpx

SORTIE = Path("registre/gdelt-comptes.csv")
FAMILLES = {"14": "manif", "18": "violence", "19": "violence", "20": "violence", "13": "menace"}
COL_RACINE, COL_LIEU = 28, 52          # EventRootCode, ActionGeo_FullName (format GDELT 1.0, 58 colonnes)


def deja_faits() -> set[str]:
    if not SORTIE.exists():
        return set()
    with SORTIE.open(encoding="utf-8") as f:
        return {r["jour"] for r in csv.DictReader(f)}


def agreger(contenu: bytes) -> Counter:
    c: Counter = Counter()
    with zipfile.ZipFile(io.BytesIO(contenu)) as z:
        with z.open(z.namelist()[0]) as f:
            for ligne in io.TextIOWrapper(f, encoding="utf-8", errors="replace"):
                cols = ligne.rstrip("\n").split("\t")
                if len(cols) <= COL_LIEU:
                    continue
                fam = FAMILLES.get(cols[COL_RACINE])
                lieu = cols[COL_LIEU]
                if fam and lieu:
                    c[(lieu.split(",")[-1].strip(), fam)] += 1
    return c


async def principal(debut: date, fin: date) -> int:
    faits = deja_faits()
    SORTIE.parent.mkdir(exist_ok=True)
    nouveau = not SORTIE.exists()
    ok = ko = 0
    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as cl:
        with SORTIE.open("a", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            if nouveau:
                w.writerow(["jour", "pays", "famille", "nombre"])
            d = debut
            while d <= fin:
                j = d.isoformat()
                if j not in faits:
                    url = f"http://data.gdeltproject.org/events/{d.strftime('%Y%m%d')}.export.CSV.zip"
                    try:
                        r = await cl.get(url)
                        if r.status_code == 200:
                            for (pays, fam), n in sorted(agreger(r.content).items()):
                                w.writerow([j, pays, fam, n])
                            f.flush()
                            ok += 1
                        else:
                            ko += 1
                            print(f"{j} : HTTP {r.status_code}")
                    except Exception as e:
                        ko += 1
                        print(f"{j} : {type(e).__name__} {str(e)[:120]}")
                d += timedelta(days=1)
    print(f"{ok} jour(s) ajouté(s), {ko} en échec.")
    return 0 if ok or not ko else 1


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--debut", default="2026-03-01")
    a.add_argument("--fin", default="2026-10-31")
    o = a.parse_args()
    sys.exit(asyncio.run(principal(date.fromisoformat(o.debut), date.fromisoformat(o.fin))))
