"""Centres urbains du monde, GHS-UCDB R2024A (Commission européenne, JRC ; CC BY 4.0), source validée par l'auteur le
2026-11-25 à 14 h 36. Pour chaque thème retenu, télécharge la dernière version du fichier (zip de quelques Mo), en extrait
la table des attributs (sans la géométrie) et l'écrit dans registre/ucdb/<thème>.csv.gz ; registre/ucdb/etat.json
décrit ce qui a été trouvé (fichiers, tables, colonnes). L'agrégation par pays se fait ensuite (mise_au_point/ucdb_pays.py),
sur les tables enregistrées. robots.txt vérifié avant toute requête.
    uv run python collecte_ucdb.py
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import re
import sqlite3
import sys
import tempfile
import zipfile
from pathlib import Path

import httpx

import politesse

BASE = "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_UCDB_GLOBE_R2024A/GHS_UCDB_THEME_GLOBE_R2024A/"
THEMES = ("GENERAL_CHARACTERISTICS", "HAZARD_RISK", "CLIMATE", "HEALTH", "EMISSIONS", "WATER", "SOCIOECONOMIC",
          "GREENNESS", "EXPOSURE")
DOSSIER = Path("registre") / "ucdb"
GEOM = re.compile(r"geom|shape|wkb|wkt", re.I)


def _derniere_version(c: httpx.Client, url: str) -> str | None:
    r = c.get(url)
    r.raise_for_status()
    vs = sorted(set(re.findall(r'href="(V\d+-\d+)/"', r.text)), key=lambda v: [int(x) for x in v[1:].split("-")])
    return vs[-1] if vs else None


def _table(z: zipfile.ZipFile) -> tuple[list[str], list[list], dict]:
    """Table des attributs : un CSV s'il y en a un, sinon la plus grande table d'un GeoPackage (SQLite), sans géométrie."""
    noms = z.namelist()
    info = {"fichiers": noms}
    for n in noms:
        if n.lower().endswith(".csv"):
            t = z.read(n).decode("utf-8-sig", "replace")
            rows = list(csv.reader(io.StringIO(t)))
            info["lu"] = n
            return rows[0], rows[1:], info
    for n in noms:
        if n.lower().endswith(".gpkg"):
            with tempfile.NamedTemporaryFile(suffix=".gpkg") as tmp:
                tmp.write(z.read(n))
                tmp.flush()
                con = sqlite3.connect(tmp.name)
                tables = [r[0] for r in con.execute("SELECT table_name FROM gpkg_contents")]
                info["tables"] = tables
                best = max(tables, key=lambda t: con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0])
                cols = [r[1] for r in con.execute(f'PRAGMA table_info("{best}")') if not GEOM.search(r[1])]
                rows = [list(r) for r in con.execute(f'SELECT {", ".join(chr(34) + c + chr(34) for c in cols)} FROM "{best}"')]
                info["lu"] = f"{n}:{best}"
                return cols, rows, info
    return [], [], info


def principal() -> int:
    DOSSIER.mkdir(parents=True, exist_ok=True)
    etat = {}
    with httpx.Client(headers={"User-Agent": politesse.UA}, follow_redirects=True, timeout=300) as c:
        for th in THEMES:
            dossier = f"{BASE}GHS_UCDB_THEME_{th}_GLOBE_R2024A/"
            try:
                if not politesse.autorise(c, dossier):
                    etat[th] = "refuse_robots"
                    continue
                v = _derniere_version(c, dossier)
                if not v:
                    etat[th] = "aucune version"
                    continue
                url = f"{dossier}{v}/GHS_UCDB_THEME_{th}_GLOBE_R2024A_{v.replace('-', '_')}.zip"
                r = c.get(url)
                r.raise_for_status()
                cols, rows, info = _table(zipfile.ZipFile(io.BytesIO(r.content)))
                with gzip.open(DOSSIER / f"{th.lower()}.csv.gz", "wt", encoding="utf-8", newline="") as f:
                    w = csv.writer(f)
                    w.writerow(cols)
                    w.writerows(rows)
                etat[th] = {"version": v, "lignes": len(rows), "colonnes": cols, **info}
            except Exception as ex:
                etat[th] = f"erreur {type(ex).__name__}: {str(ex)[:160]}"
    (DOSSIER / "etat.json").write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: (v if isinstance(v, str) else {"lignes": v["lignes"], "colonnes": len(v["colonnes"]), "lu": v.get("lu")})
                      for k, v in etat.items()}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
