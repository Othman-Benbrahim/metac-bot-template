"""Comptes quotidiens de manifestations et d'émeutes par pays, tirés de GDELT (bot 0.10.173, en ombre).

Décision d'auteur du 2026-11-16 (12 h 32) : « Oui » (compte GDELT direct plutôt que l'API geoprotests, qui le
reformate). GDELT code automatiquement les événements de la presse mondiale (classification CAMEO) et publie un fichier
par jour, gratuit, sans clé : http://data.gdeltproject.org/events/AAAAMMJJ.export.CSV.zip.

On ne garde que des COMPTES, par pays (lieu de l'action) et par jour de publication du fichier :
  manifestations : événements de code racine 14 (« Protest ») ;
  emeutes        : événements de code de base 145 (« Protest violently, riot ») ;
  articles       : somme du nombre d'articles de ces événements (code racine 14).
Ce que cela mesure : l'ATTENTION de la presse aux manifestations, pas leur nombre réel (doublons, lieux mal codés).
Les questions ACLED se résolvent sur ACLED : GDELT n'est qu'un indicateur extérieur, jugé par l'observatoire.

Codes pays : GDELT emploie les codes FIPS 10-4 ; conversion en ISO à deux lettres par la table publique
datasets/country-codes (colonnes FIPS et ISO3166-1-Alpha-2).

Registres : registre/gdelt-manifestations.csv (pays, jour, manifestations, emeutes, articles) ;
registre/gdelt-jours.txt (jours lus, y compris ceux sans aucune manifestation pour un pays).

Usage : python collecte_gdelt.py [--depuis AAAA-MM-JJ]   (par défaut : les jours manquants des 7 derniers jours)
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import sys
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx

URL_JOUR = "http://data.gdeltproject.org/events/{j}.export.CSV.zip"
TABLE_CODES = "https://raw.githubusercontent.com/datasets/country-codes/main/data/country-codes.csv"
COMPTES = Path("registre") / "gdelt-manifestations.csv"
JOURS = Path("registre") / "gdelt-jours.txt"
UA = {"User-Agent": "alphabet-situationnel-bot/1.0 (recherche ; GitHub Othman-Benbrahim)"}

# colonnes du format des événements GDELT 1.0 (58 colonnes depuis avril 2013)
C_BASE, C_RACINE, C_ARTICLES, C_PAYS_ACTION = 27, 28, 33, 51

# quelques codes FIPS courants, si la table publique est inaccessible (diffèrent souvent de l'ISO)
FIPS_SECOURS = {"US": "US", "UK": "GB", "FR": "FR", "GM": "DE", "RS": "RU", "UP": "UA", "CH": "CN", "IN": "IN",
                "PK": "PK", "IS": "IL", "IZ": "IQ", "IR": "IR", "SY": "SY", "TU": "TR", "EG": "EG", "SF": "ZA",
                "NI": "NG", "KE": "KE", "ET": "ET", "SU": "SD", "OD": "SS", "CG": "CD", "CF": "CG", "ML": "ML",
                "UV": "BF", "NG": "NE", "BG": "BD", "BM": "MM", "RP": "PH", "ID": "ID", "MX": "MX", "BR": "BR",
                "AR": "AR", "CI": "CL", "CO": "CO", "VE": "VE", "PE": "PE", "SP": "ES", "IT": "IT", "PO": "PT",
                "PL": "PL", "AS": "AU", "JA": "JP", "KS": "KR", "KN": "KP", "SA": "SA", "YM": "YE", "LE": "LB",
                "AF": "AF", "SO": "SO", "LY": "LY", "TS": "TN", "AG": "DZ", "MO": "MA", "GG": "GE", "AM": "AM",
                "AJ": "AZ", "BO": "BY", "EI": "IE", "HA": "HT", "CS": "CR", "GT": "GT", "HO": "HN", "NU": "NI",
                "CE": "LK", "NP": "NP", "TH": "TH", "VM": "VN", "MY": "MY", "SN": "SG", "TW": "TW", "IV": "CI",
                "SG": "SN", "GH": "GH", "CM": "CM", "CD": "TD", "MZ": "MZ", "ZI": "ZW", "ZA": "ZM", "UG": "UG",
                "TZ": "TZ", "RW": "RW", "BY": "BI", "GV": "GN", "MR": "MR", "SL": "SL", "LI": "LR", "SW": "SE",
                "NO": "NO", "DA": "DK", "FI": "FI", "NL": "NL", "BE": "BE", "SZ": "CH", "AU": "AT", "EZ": "CZ",
                "LO": "SK", "HU": "HU", "RO": "RO", "BU": "BG", "GR": "GR", "RI": "RS", "HR": "HR", "BK": "BA",
                "MK": "MK", "AL": "AL", "MD": "MD", "LH": "LT", "LG": "LV", "EN": "EE", "KZ": "KZ", "UZ": "UZ",
                "TI": "TJ", "KG": "KG", "TX": "TM", "MG": "MN", "CA": "CA", "CU": "CU", "DR": "DO", "BL": "BO",
                "EC": "EC", "PA": "PY", "UY": "UY", "QA": "QA", "AE": "AE", "KU": "KW", "BA": "BH", "MU": "OM",
                "JO": "JO", "WE": "PS", "GZ": "PS", "NZ": "NZ", "KV": "XK"}


def table_fips(c: httpx.Client) -> dict[str, str]:
    try:
        r = c.get(TABLE_CODES, timeout=60)
        r.raise_for_status()
        t = {}
        for x in csv.DictReader(io.StringIO(r.text)):
            f, i = (x.get("FIPS") or "").strip(), (x.get("ISO3166-1-Alpha-2") or "").strip()
            if len(f) == 2 and len(i) == 2:
                t.setdefault(f, i)
        if len(t) > 150:
            t.update({"WE": "PS", "GZ": "PS", "KV": "XK"})
            return t
    except Exception as e:
        print(f"table FIPS → ISO indisponible ({type(e).__name__}) : table de secours ({len(FIPS_SECOURS)} pays).")
    return dict(FIPS_SECOURS)


def compter(texte_csv: str, fips: dict[str, str]) -> dict[str, list[int]]:
    """Par pays ISO : [manifestations, émeutes, articles]."""
    out: dict[str, list[int]] = {}
    for col in csv.reader(io.StringIO(texte_csv), delimiter="\t"):
        if len(col) <= C_PAYS_ACTION or col[C_RACINE] != "14":
            continue
        pays = fips.get(col[C_PAYS_ACTION])
        if not pays:
            continue
        v = out.setdefault(pays, [0, 0, 0])
        v[0] += 1
        if col[C_BASE] == "145":
            v[1] += 1
        try:
            v[2] += int(col[C_ARTICLES] or 0)
        except ValueError:
            pass
    return out


def lire() -> tuple[dict[tuple, list[int]], set[str]]:
    comptes = {}
    if COMPTES.exists():
        for x in csv.DictReader(COMPTES.open(encoding="utf-8")):
            comptes[(x["pays"], x["jour"])] = [int(x["manifestations"]), int(x["emeutes"]), int(x["articles"])]
    jours = set(JOURS.read_text(encoding="utf-8").split()) if JOURS.exists() else set()
    return comptes, jours


def ecrire(comptes: dict[tuple, list[int]], jours: set[str]) -> None:
    COMPTES.parent.mkdir(exist_ok=True)
    with COMPTES.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pays", "jour", "manifestations", "emeutes", "articles"])
        for (p, j), v in sorted(comptes.items(), key=lambda t: (t[0][1], t[0][0])):
            w.writerow([p, j, *v])
    JOURS.write_text("\n".join(sorted(jours)) + "\n", encoding="utf-8")


def principal() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--depuis", default="")
    a = ap.parse_args()
    hier = datetime.now(timezone.utc).date() - timedelta(days=1)
    debut = date.fromisoformat(a.depuis) if a.depuis else hier - timedelta(days=6)
    comptes, jours = lire()
    lus = absents = 0
    with httpx.Client(headers=UA, follow_redirects=True, timeout=120) as c:
        fips = table_fips(c)
        print(f"{len(fips)} codes FIPS convertis en ISO.")
        d = debut
        while d <= hier:
            j = d.isoformat()
            if j in jours:
                d += timedelta(days=1)
                continue
            try:
                r = c.get(URL_JOUR.format(j=d.strftime("%Y%m%d")))
                if r.status_code == 404:
                    absents += 1
                    print(f"  {j} : fichier absent (404)")
                    d += timedelta(days=1)
                    continue
                r.raise_for_status()
                with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                    texte = z.read(z.namelist()[0]).decode("utf-8", errors="replace")
            except Exception as e:
                print(f"  {j} : échec ({type(e).__name__}: {str(e)[:80]})")
                d += timedelta(days=1)
                continue
            par_pays = compter(texte, fips)
            for p, v in par_pays.items():
                comptes[(p, j)] = v
            jours.add(j)
            lus += 1
            tot = [sum(v[i] for v in par_pays.values()) for i in range(3)]
            print(f"  {j} : {tot[0]} manifestations, {tot[1]} émeutes, {len(par_pays)} pays")
            if lus % 20 == 0:
                ecrire(comptes, jours)          # sauvegarde régulière pendant un long rattrapage
            d += timedelta(days=1)
    ecrire(comptes, jours)
    bilan = f"{lus} jour(s) lus, {absents} absent(s) ; {len(jours)} jours couverts au total."
    print(bilan)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(f"## GDELT manifestations\n\n{bilan}\n")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
