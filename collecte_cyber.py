"""Collecte des failles logicielles pour l'écosystème « information et cyber », compartiment « cyber » (décision de
l'auteur du 2026-11-21, 19 h 33 ; repérée par la veille systemshardening.com, qui cite ces sources sans en publier).

Deux sources primaires, publiques, sans clé, collectées automatiquement ; aucun modèle de langue ; rien n'entre dans le
bot :

1. Catalogue KEV de la CISA (Known Exploited Vulnerabilities : failles dont l'exploitation réelle est établie), fichier
   JSON public, domaine public américain. On garde l'identifiant, la date d'ajout, l'éditeur et l'usage connu par des
   rançongiciels (des identifiants et des dates, pas de texte).
2. NVD (NIST), API 2.0 : nombre de failles publiées par mois, et nombre de failles « critiques » (CVSS v3) par mois,
   depuis 2016. Une requête par mois et par gravité, en ne demandant qu'un résultat (seul le total sert) ; sans clé,
   l'API accepte 5 requêtes par 30 secondes : une requête toutes les 6,5 s. Les passages suivants ne refont que les
   trois derniers mois.

Registres : registre/cyber-kev.csv (cve, date_ajout, editeur, rancongiciel) et registre/cyber-nvd-mois.csv
(mois, publiees, critiques).

    python collecte_cyber.py
"""
from __future__ import annotations

import csv
import sys
import time
from datetime import date
from pathlib import Path

REG = Path("registre")
KEV_CSV = REG / "cyber-kev.csv"
NVD_CSV = REG / "cyber-nvd-mois.csv"
KEV = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
NVD = "https://services.nvd.nist.gov/rest/json/cves/2.0"
DEBUT_NVD = (2016, 1)
PAUSE_NVD = 6.5


def lire_kev(js: dict) -> list[list]:
    out = []
    for v in js.get("vulnerabilities", []):
        cve, d = v.get("cveID"), v.get("dateAdded")
        if cve and d:
            out.append([cve, d[:10], v.get("vendorProject", ""),
                        "oui" if str(v.get("knownRansomwareCampaignUse", "")).lower() == "known" else "non"])
    return sorted(out, key=lambda r: (r[1], r[0]))


def mois_entre(debut: tuple[int, int], fin: date) -> list[tuple[int, int]]:
    a, m = debut
    out = []
    while (a, m) <= (fin.year, fin.month):
        out.append((a, m))
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)
    return out


def bornes(a: int, m: int) -> tuple[str, str]:
    import calendar
    dernier = calendar.monthrange(a, m)[1]
    return f"{a:04d}-{m:02d}-01T00:00:00.000", f"{a:04d}-{m:02d}-{dernier:02d}T23:59:59.999"


def total_nvd(c, a: int, m: int, critique: bool) -> int | None:
    debut, fin = bornes(a, m)
    p = {"pubStartDate": debut, "pubEndDate": fin, "resultsPerPage": 1}
    if critique:
        p["cvssV3Severity"] = "CRITICAL"
    for essai in range(3):
        time.sleep(PAUSE_NVD)
        r = c.get(NVD, params=p)
        if r.status_code == 200:
            return int(r.json().get("totalResults", 0))
        if r.status_code in (403, 429, 503):                   # limite ou surcharge : on attend et on réessaie
            time.sleep(30 * (essai + 1))
            continue
        return None
    return None


def principal() -> int:
    import httpx
    import politesse
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=60, follow_redirects=True) as c:
        # 1. KEV
        if politesse.autorise(c, KEV):
            try:
                r = c.get(KEV)
                r.raise_for_status()
                lignes = lire_kev(r.json())
                with KEV_CSV.open("w", encoding="utf-8", newline="") as f:
                    w = csv.writer(f)
                    w.writerow(["cve", "date_ajout", "editeur", "rancongiciel"])
                    w.writerows(lignes)
                print(f"KEV : {len(lignes)} failles exploitées, dernière ajoutée le {lignes[-1][1] if lignes else '—'}")
            except Exception as e:
                print(f"KEV : {type(e).__name__}: {e}"[:300])
        else:
            print("KEV : robots.txt refuse, rien collecté")
        # 2. NVD, comptes mensuels
        connus = {}
        if NVD_CSV.exists():
            with NVD_CSV.open(encoding="utf-8") as f:
                connus = {r["mois"]: r for r in csv.DictReader(f)}
        tous = mois_entre(DEBUT_NVD, date.today())
        a_faire = [x for x in tous if f"{x[0]:04d}-{x[1]:02d}" not in connus] + \
            [x for x in tous[-3:] if f"{x[0]:04d}-{x[1]:02d}" in connus]   # les trois derniers mois bougent encore
        for a, m in a_faire:
            n, k = total_nvd(c, a, m, False), total_nvd(c, a, m, True)
            if n is None or k is None:
                print(f"NVD {a}-{m:02d} : échec, gardé pour le prochain passage")
                continue
            connus[f"{a:04d}-{m:02d}"] = {"mois": f"{a:04d}-{m:02d}", "publiees": n, "critiques": k}
        with NVD_CSV.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["mois", "publiees", "critiques"])
            w.writeheader()
            for k_ in sorted(connus):
                w.writerow(connus[k_])
        print(f"NVD : {len(connus)} mois au registre ({len(a_faire)} demandés à ce passage)")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
