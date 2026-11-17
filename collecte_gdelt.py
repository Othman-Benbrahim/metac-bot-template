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

0.10.202 (M13, en ombre, décision d'auteur du 2026-11-16, 18 h 56) : dans les mêmes fichiers, actes hostiles d'un
acteur russe (Actor1CountryCode = RUS) dans un autre pays : racines CAMEO 18 (agression), 19 (combat), 20 (violence de
masse), par pays du lieu de l'action et par jour. Sert à compter les transgressions répétées d'une même catégorie
(mécanisme « la réponse s'use à la répétition »). Registres : registre/gdelt-hostilites-ru.csv (pays, jour, agressions,
combats, violence_masse) ; registre/gdelt-hostilites-jours.txt.

0.10.205 (module Chine, couche 2, en ombre ; décision d'auteur du 2026-11-16, 21 h 45 : pas de saisie à la main) :
dans les mêmes fichiers, sanctions, embargos et boycotts imposés par un acteur chinois (Actor1CountryCode = CHN, code
CAMEO 163), par pays VISÉ (Actor2CountryCode, code à trois lettres converti en ISO à deux lettres) et par jour.
Registres : registre/gdelt-chine-sanctions.csv (pays, jour, evenements) ; registre/gdelt-chine-jours.txt.

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
C_PAYS_ACTEUR1 = 7                       # Actor1CountryCode (code CAMEO à trois lettres, « RUS »)
HOSTILES = Path("registre") / "gdelt-hostilites-ru.csv"
JOURS_H = Path("registre") / "gdelt-hostilites-jours.txt"
RACINES_HOSTILES = ("18", "19", "20")
C_CODE, C_PAYS_ACTEUR2 = 26, 17         # EventCode ; Actor2CountryCode
CHINE = Path("registre") / "gdelt-chine-sanctions.csv"
JOURS_C = Path("registre") / "gdelt-chine-jours.txt"
# 0.10.222 (M17, en ombre) : paires de pays. Coopération militaire (CAMEO 062 « coopérer militairement », 0312 « exprimer
# l'intention de coopérer militairement ») et démonstrations de force (racine 15) par jour et par paire orientée ; volume
# total et volume conflictuel (QuadClass 3 et 4) par mois et par paire non orientée, pour calculer les rivalités.
C_QUAD = 29
CODES_COOP = ("062", "0312")
PAIRES_J = Path("registre") / "gdelt-paires-jour.csv"
PAIRES_M = Path("registre") / "gdelt-paires-mois.csv"
JOURS_P = Path("registre") / "gdelt-paires-jours.txt"


def table_iso3(c: httpx.Client) -> dict[str, str]:
    """Code à trois lettres (CAMEO suit l'ISO pour les pays) → ISO à deux lettres."""
    try:
        r = c.get(TABLE_CODES, timeout=60)
        r.raise_for_status()
        return {x["ISO3166-1-Alpha-3"].strip(): x["ISO3166-1-Alpha-2"].strip() for x in csv.DictReader(io.StringIO(r.text))
                if len((x.get("ISO3166-1-Alpha-3") or "").strip()) == 3 and len((x.get("ISO3166-1-Alpha-2") or "").strip()) == 2}
    except Exception:
        return {}


def sanctions_chine(texte_csv: str, iso3: dict[str, str]) -> dict[str, int]:
    """Événements CAMEO 163 (sanctions, embargo, boycott) d'un acteur chinois, par pays visé (hors Chine)."""
    out: dict[str, int] = {}
    for col in csv.reader(io.StringIO(texte_csv), delimiter="\t"):
        if len(col) <= C_PAYS_ACTION or col[C_PAYS_ACTEUR1] != "CHN" or not col[C_CODE].startswith("163"):
            continue
        p = iso3.get(col[C_PAYS_ACTEUR2])
        if p and p != "CN":
            out[p] = out.get(p, 0) + 1
    return out


def paires(texte_csv: str, iso3: dict[str, str]) -> tuple[dict[tuple, list[int]], dict[tuple, list[int]]]:
    """0.10.222 : (jour : {(acteur1, acteur2) : [coopération militaire, démonstrations de force]},
    mois : {(a, b) triés : [événements, événements conflictuels]}), entre deux pays différents."""
    jour: dict[tuple, list[int]] = {}
    mois: dict[tuple, list[int]] = {}
    for col in csv.reader(io.StringIO(texte_csv), delimiter="\t"):
        if len(col) <= C_PAYS_ACTION:
            continue
        a, b = iso3.get(col[C_PAYS_ACTEUR1]), iso3.get(col[C_PAYS_ACTEUR2])
        if not a or not b or a == b:
            continue
        m = mois.setdefault(tuple(sorted((a, b))), [0, 0])
        m[0] += 1
        if col[C_QUAD] in ("3", "4"):
            m[1] += 1
        coop, force = col[C_CODE] in CODES_COOP, col[C_RACINE] == "15"
        if coop or force:
            v = jour.setdefault((a, b), [0, 0])
            v[0] += coop
            v[1] += force
    return jour, mois


def lire_p() -> tuple[dict[tuple, list[int]], dict[tuple, list[int]], set[str]]:
    pj, pm = {}, {}
    if PAIRES_J.exists():
        for x in csv.DictReader(PAIRES_J.open(encoding="utf-8")):
            pj[(x["jour"], x["a"], x["b"])] = [int(x["coop_mil"]), int(x["force"])]
    if PAIRES_M.exists():
        for x in csv.DictReader(PAIRES_M.open(encoding="utf-8")):
            pm[(x["mois"], x["a"], x["b"])] = [int(x["evenements"]), int(x["conflit"])]
    return pj, pm, (set(JOURS_P.read_text(encoding="utf-8").split()) if JOURS_P.exists() else set())


def ecrire_p(pj: dict, pm: dict, jours_p: set[str]) -> None:
    PAIRES_J.parent.mkdir(exist_ok=True)
    with PAIRES_J.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["jour", "a", "b", "coop_mil", "force"])
        for k in sorted(pj):
            w.writerow([*k, *pj[k]])
    with PAIRES_M.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["mois", "a", "b", "evenements", "conflit"])
        for k in sorted(pm):
            if pm[k][0] >= 3:                     # paires presque muettes écartées (taille du registre)
                w.writerow([*k, *pm[k]])
    JOURS_P.write_text("\n".join(sorted(jours_p)) + "\n", encoding="utf-8")


def lire_c() -> tuple[dict[tuple, int], set[str]]:
    h = {}
    if CHINE.exists():
        for x in csv.DictReader(CHINE.open(encoding="utf-8")):
            h[(x["pays"], x["jour"])] = int(x["evenements"])
    return h, (set(JOURS_C.read_text(encoding="utf-8").split()) if JOURS_C.exists() else set())


def ecrire_c(h: dict[tuple, int], jours_c: set[str]) -> None:
    CHINE.parent.mkdir(exist_ok=True)
    with CHINE.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pays", "jour", "evenements"])
        for (p, j), v in sorted(h.items(), key=lambda t: (t[0][1], t[0][0])):
            w.writerow([p, j, v])
    JOURS_C.write_text("\n".join(sorted(jours_c)) + "\n", encoding="utf-8")

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


def hostilites(texte_csv: str, fips: dict[str, str], acteur: str = "RUS") -> dict[str, list[int]]:
    """0.10.202 : par pays ISO du lieu de l'action (hors Russie) : [agressions (18), combats (19), violence de masse (20)]."""
    out: dict[str, list[int]] = {}
    for col in csv.reader(io.StringIO(texte_csv), delimiter="\t"):
        if len(col) <= C_PAYS_ACTION or col[C_PAYS_ACTEUR1] != acteur or col[C_RACINE] not in RACINES_HOSTILES:
            continue
        pays = fips.get(col[C_PAYS_ACTION])
        if not pays or pays == "RU":
            continue
        out.setdefault(pays, [0, 0, 0])[RACINES_HOSTILES.index(col[C_RACINE])] += 1
    return out


def lire_h() -> tuple[dict[tuple, list[int]], set[str]]:
    h = {}
    if HOSTILES.exists():
        for x in csv.DictReader(HOSTILES.open(encoding="utf-8")):
            h[(x["pays"], x["jour"])] = [int(x["agressions"]), int(x["combats"]), int(x["violence_masse"])]
    return h, (set(JOURS_H.read_text(encoding="utf-8").split()) if JOURS_H.exists() else set())


def ecrire_h(h: dict[tuple, list[int]], jours_h: set[str]) -> None:
    HOSTILES.parent.mkdir(exist_ok=True)
    with HOSTILES.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pays", "jour", "agressions", "combats", "violence_masse"])
        for (p, j), v in sorted(h.items(), key=lambda t: (t[0][1], t[0][0])):
            w.writerow([p, j, *v])
    JOURS_H.write_text("\n".join(sorted(jours_h)) + "\n", encoding="utf-8")


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
    hostiles, jours_h = lire_h()
    chine, jours_c = lire_c()
    pj, pm, jours_p = lire_p()
    lus = absents = 0
    with httpx.Client(headers=UA, follow_redirects=True, timeout=120) as c:
        fips = table_fips(c)
        iso3 = table_iso3(c)
        print(f"{len(fips)} codes FIPS convertis en ISO.")
        d = debut
        while d <= hier:
            j = d.isoformat()
            if j in jours and j in jours_h and j in jours_c and j in jours_p:
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
            for p, v in hostilites(texte, fips).items():
                hostiles[(p, j)] = v
            jours_h.add(j)
            if iso3:
                for p, v in sanctions_chine(texte, iso3).items():
                    chine[(p, j)] = v
                jours_c.add(j)
                if j not in jours_p:                 # les totaux mensuels ne sont ajoutés qu'une fois par jour
                    jr, mo = paires(texte, iso3)
                    for k, v in jr.items():
                        pj[(j, *k)] = v
                    for k, v in mo.items():
                        t = pm.setdefault((j[:7], *k), [0, 0])
                        t[0] += v[0]
                        t[1] += v[1]
                    jours_p.add(j)
            lus += 1
            tot = [sum(v[i] for v in par_pays.values()) for i in range(3)]
            print(f"  {j} : {tot[0]} manifestations, {tot[1]} émeutes, {len(par_pays)} pays")
            if lus % 20 == 0:
                ecrire(comptes, jours)          # sauvegarde régulière pendant un long rattrapage
                ecrire_h(hostiles, jours_h)
                ecrire_c(chine, jours_c)
                ecrire_p(pj, pm, jours_p)
            d += timedelta(days=1)
    ecrire(comptes, jours)
    ecrire_h(hostiles, jours_h)
    ecrire_c(chine, jours_c)
    ecrire_p(pj, pm, jours_p)
    bilan = f"{lus} jour(s) lus, {absents} absent(s) ; {len(jours)} jours couverts au total."
    print(bilan)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(f"## GDELT manifestations\n\n{bilan}\n")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
