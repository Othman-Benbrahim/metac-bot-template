"""COLT — Country and Organizational Leader Travel (Pardee Institute, Université de Denver ; Harvard Dataverse,
doi:10.7910/DVN/HJK7DN), voyages à l'étranger des chefs d'État et de gouvernement depuis 1990 — bot 0.10.504.

Décision de l'auteur du 2026-11-24 (16 h 52 : « On commence », rencontres) : mesure extérieure des rencontres en
personne entre dirigeants (visite de l'un chez l'autre, ou présence des deux au même endroit les mêmes jours).
Personnalités publiques dans leur rôle public seulement. Fichiers tabulaires téléchargés par l'API publique de
Dataverse (format d'origine), tels que publiés ; un fichier soumis à restriction n'est pas demandé.
Sorties : registre/colt/<nom>.csv (et .tab tels quels) ; registre/colt/fichiers.json (liste des fichiers du jeu).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

import politesse

BASE = "https://dataverse.harvard.edu"
DOI = "doi:10.7910/DVN/HJK7DN"
SORTIE = Path("registre") / "colt"


def principal() -> int:
    SORTIE.mkdir(parents=True, exist_ok=True)
    with httpx.Client(follow_redirects=True, timeout=300, headers={"User-Agent": politesse.UA}) as c:
        url = f"{BASE}/api/datasets/:persistentId/?persistentId={DOI}"
        if not politesse.autorise(c, url):
            print("COLT : refusé par robots.txt, rien collecté")
            return 0
        r = c.get(url)
        r.raise_for_status()
        v = r.json()["data"]["latestVersion"]
        fichiers = [{"id": f["dataFile"]["id"], "nom": f["dataFile"].get("filename"),
                     "restreint": f.get("restricted", False), "taille": f["dataFile"].get("filesize"),
                     "type": f["dataFile"].get("contentType")} for f in v.get("files", [])]
        (SORTIE / "fichiers.json").write_text(json.dumps({"version": v.get("versionNumber"), "licence":
                                              v.get("license"), "fichiers": fichiers}, ensure_ascii=False, indent=1),
                                              encoding="utf-8")
        print("version", v.get("versionNumber"), "licence", v.get("license"))
        for f in fichiers:
            print("fichier :", f)
            nom = f["nom"] or str(f["id"])
            if f["restreint"] or not nom.lower().endswith((".csv", ".tab", ".txt", ".xlsx")):
                continue
            d = c.get(f"{BASE}/api/access/datafile/{f['id']}", params={"format": "original"})
            if d.status_code != 200:
                print(f"  {nom} : HTTP {d.status_code}")
                continue
            if nom.lower().endswith(".xlsx"):                    # tableur → une feuille CSV par onglet
                import csv
                import io
                import openpyxl
                wb = openpyxl.load_workbook(io.BytesIO(d.content), read_only=True, data_only=True)
                for ws in wb.worksheets:
                    cible = SORTIE / f"{Path(nom).stem}-{ws.title}.csv.gz".replace(" ", "_")
                    import gzip                          # compressé : le CSV brut dépasse 100 Mo (limite de GitHub)
                    with gzip.open(cible, "wt", encoding="utf-8", newline="\n") as fh:
                        w, n = csv.writer(fh), 0
                        for L in ws.iter_rows(values_only=True):
                            w.writerow(["" if v is None else v for v in L])
                            n += 1
                    print(f"  {cible.name} : {n} lignes, {cible.stat().st_size} octets compressés")
                continue
            (SORTIE / nom.replace("/", "_")).write_bytes(d.content)
            premiere = d.content[:400].decode("utf-8", errors="replace").splitlines()[0] if d.content else ""
            print(f"  {nom} : {len(d.content)} octets ; en-têtes : {premiere}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
