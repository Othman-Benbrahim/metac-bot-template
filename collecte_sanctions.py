"""Nouvelles sanctions par pays visé : OFAC (États-Unis) et liste britannique (bot 0.10.178, en ombre).

Décision d'auteur du 2026-11-16 (13 h 25) : « Oui, fais les deux ».

1. OFAC (Trésor américain, domaine public) : une page par jour d'action, https://ofac.treasury.gov/recent-actions/AAAAMMJJ
   (pas de flux RSS depuis 2024). On lit le titre et l'on compte, dans le corps, les étiquettes de programme des
   entrées ajoutées ([IRAN], [RUSSIA-EO14024]…). Le programme donne le pays visé par une table fixe (PROGRAMMES) ;
   les programmes sans pays (terrorisme, stupéfiants, cyber…) sont comptés sous « -- ».
2. Royaume-Uni (GOV.UK, Open Government Licence) : historique des modifications de « The UK Sanctions List »
   (API de contenu de GOV.UK, champ details.change_history). Chaque note (« Added 5 entries under the Russia
   sanctions regime ») donne un nombre et un régime ; le régime donne le pays visé.

3. Union européenne (0.10.207, décision d'auteur du 2026-11-16, 22 h 05) : liste consolidée des sanctions financières
   de l'UE (« Financial Sanctions Files », Commission européenne, CSV public). Une ligne par alias ou adresse : on
   regroupe par identifiant d'entité. Date d'inscription : Entity_DesignationDate, sinon la première date de
   publication de règlement de l'entité. Le programme (code à trois lettres : RUS, IRN, BLR…) donne le pays visé.
   La liste ne contient que les inscriptions EN VIGUEUR : l'historique se reconstruit d'un coup à partir des dates
   d'inscription, mais sans les personnes radiées depuis (biais du survivant, déclaré). Les lignes « ue » sont
   recalculées en entier à chaque passage.

On garde des comptes : source, jour, pays, designations (nombre d'entrées), actions (nombre d'actions ce jour-là).
Registres : registre/sanctions.csv ; registre/sanctions-couverture.txt (premier jour couvert).

Usage : python collecte_sanctions.py [--depuis AAAA-MM-JJ]   (par défaut : les 10 derniers jours)
"""
from __future__ import annotations

import argparse
import csv
import html
import io
import os
import re
import sys
import time
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx

OFAC = "https://ofac.treasury.gov/recent-actions/{j}"
GOVUK = "https://www.gov.uk/api/content/government/publications/the-uk-sanctions-list"
UE = "https://webgate.ec.europa.eu/fsd/fsf/public/files/csvFullSanctionsList_1_1/content?token=dG9rZW4tMjAxNw"
TABLE_CODES = "https://raw.githubusercontent.com/datasets/country-codes/main/data/country-codes.csv"
# programmes de l'UE sans pays (terrorisme, cyber, droits de l'homme, armes chimiques…) ou dont le code n'est pas
# celui du pays visé
PROGRAMMES_UE = {"UKR": "RU", "TERR": "--", "TAQA": "--", "CYB": "--", "HR": "--", "EUAQ": "--", "CHEM": "--",
                 "ISIL": "--", "HRGS": "--", "HYBRID": "--", "RUS_HYBRID": "RU", "MDA": "MD"}
SORTIE = Path("registre") / "sanctions.csv"
COUVERTURE = Path("registre") / "sanctions-couverture.txt"
UA = {"User-Agent": "alphabet-situationnel-bot/1.0 (recherche ; GitHub Othman-Benbrahim)"}

# préfixe d'étiquette OFAC → pays visé (table fixée le 2026-11-16) ; absent de la table : sans pays (« -- »)
PROGRAMMES = {
    "IRAN": "IR", "IRGC": "IR", "IFSR": "IR", "HRIT": "IR", "RUSSIA": "RU", "UKRAINE": "RU", "CAATSA": "RU",
    "VENEZUELA": "VE", "DPRK": "KP", "NKSPEA": "KP", "CUBA": "CU", "SYRIA": "SY", "BURMA": "MM", "SUDAN": "SD",
    "DARFUR": "SD", "SOUTH": "SS", "LIBYA": "LY", "YEMEN": "YE", "IRAQ": "IQ", "LEBANON": "LB", "CAR": "CF",
    "DRCONGO": "CD", "MALI": "ML", "SOMALIA": "SO", "BELARUS": "BY", "NICARAGUA": "NI", "HK": "HK", "CHINA": "CN",
    "ETHIOPIA": "ET", "WEST": "BA", "BALKANS": "BA", "ZIMBABWE": "ZW", "HAITI": "HT", "AFGHANISTAN": "AF",
}
ETIQUETTE = re.compile(r"\[([A-Z][A-Z0-9]*(?:[-_ ][A-Z0-9]+)*)\]")

# régime britannique (mot du nom) → pays visé
REGIMES_UK = {
    "russia": "RU", "belarus": "BY", "iran": "IR", "syria": "SY", "democratic people's republic of korea": "KP",
    "dprk": "KP", "myanmar": "MM", "burma": "MM", "libya": "LY", "sudan": "SD", "south sudan": "SS", "yemen": "YE",
    "iraq": "IQ", "lebanon": "LB", "mali": "ML", "somalia": "SO", "zimbabwe": "ZW", "venezuela": "VE",
    "nicaragua": "NI", "guinea-bissau": "GW", "republic of guinea": "GN", "guinea": "GN", "bosnia": "BA",
    "haiti": "HT", "afghanistan": "AF", "central african republic": "CF", "democratic republic of the congo": "CD",
}
NOTE_UK = re.compile(r"(?:added|designated|made)\s+(\d+)\s+(?:new\s+)?(entr(?:y|ies)|designations?|amendments?)"
                     r"[^.;]*?\bunder the ([A-Za-z' -]+?) (?:sanctions )?regime", re.I)


def pays_programme(etiquette: str) -> str:
    tete = re.sub(r"\d+$", "", re.split(r"[-_ ]", etiquette.upper())[0])   # DPRK3, LIBYA2, IRAQ3 → DPRK, LIBYA, IRAQ
    if etiquette.upper().startswith("SOUTH SUDAN") or etiquette.upper().startswith("SOUTH-SUDAN"):
        return "SS"
    if tete == "SOUTH":
        return "--"
    return PROGRAMMES.get(tete, "--")


def lire_ofac(page: str) -> tuple[str, Counter]:
    """(titre, comptes par pays des étiquettes de programme dans le corps)."""
    m = re.search(r"<title>(.*?)</title>", page, re.S | re.I)
    titre = html.unescape(m.group(1)).split("|")[0].strip() if m else ""
    corps = re.sub(r"<script.*?</script>|<style.*?</style>", " ", page, flags=re.S | re.I)
    corps = html.unescape(re.sub(r"<[^>]+>", " ", corps))
    comptes = Counter(pays_programme(e) for e in ETIQUETTE.findall(corps))
    return titre, comptes


def pays_regime(nom: str) -> str:
    n = nom.lower().strip()
    for k in sorted(REGIMES_UK, key=len, reverse=True):
        if k in n:
            return REGIMES_UK[k]
    return "--"


def lire_notes_uk(historique: list[dict], depuis: str) -> list[tuple[str, str, int]]:
    """(jour, pays, nombre) pour les ajouts (entrées, désignations) ; les « amendments » ne comptent pas."""
    out = []
    for h in historique:
        j = str(h.get("public_timestamp") or "")[:10]
        if not j or j < depuis:
            continue
        for nombre, quoi, regime in NOTE_UK.findall(str(h.get("note") or "")):
            if quoi.lower().startswith("amendment"):
                continue
            out.append((j, pays_regime(regime), int(nombre)))
    return out


def table_iso3(c: httpx.Client) -> dict[str, str]:
    try:
        r = c.get(TABLE_CODES, timeout=60)
        r.raise_for_status()
        return {x["ISO3166-1-Alpha-3"].strip(): x["ISO3166-1-Alpha-2"].strip() for x in csv.DictReader(io.StringIO(r.text))
                if len((x.get("ISO3166-1-Alpha-3") or "").strip()) == 3 and len((x.get("ISO3166-1-Alpha-2") or "").strip()) == 2}
    except Exception:
        return {}


def pays_programme_ue(code: str, iso3: dict[str, str]) -> str:
    code = (code or "").strip().upper()
    if code in PROGRAMMES_UE:
        return PROGRAMMES_UE[code]
    return iso3.get(code[:3], "--")


def _colonne(entete: list[str], *motifs: str) -> int | None:
    for m in motifs:
        for i, nom in enumerate(entete):
            if nom.strip().lower() == m.lower():
                return i
    for m in motifs:
        for i, nom in enumerate(entete):
            if m.lower() in nom.lower():
                return i
    return None


def lire_ue(texte: str, iso3: dict[str, str]) -> tuple[Counter, int]:
    """(jour, pays) → nombre d'inscriptions en vigueur ; et nombre d'entités lues."""
    lignes = list(csv.reader(io.StringIO(texte.lstrip("\ufeff")), delimiter=";"))
    if not lignes:
        return Counter(), 0
    e = lignes[0]
    i_id = _colonne(e, "Entity_LogicalId")
    i_des = _colonne(e, "Entity_DesignationDate")
    i_pub = _colonne(e, "Entity_Regulation_PublicationDate")
    i_prog = _colonne(e, "Entity_Regulation_Programme")
    if i_id is None or i_prog is None or (i_des is None and i_pub is None):
        raise ValueError(f"colonnes attendues absentes : {e[:12]}")
    ent: dict[str, dict] = {}
    for l in lignes[1:]:
        if len(l) <= max(x for x in (i_id, i_des, i_pub, i_prog) if x is not None):
            continue
        x = ent.setdefault(l[i_id], {"des": "", "pubs": []})
        if i_des is not None and l[i_des][:10] and not x["des"]:
            x["des"] = l[i_des][:10]
        if i_pub is not None and l[i_pub][:10]:
            x["pubs"].append((l[i_pub][:10], l[i_prog]))
        elif l[i_prog]:
            x["pubs"].append(("9999-12-31", l[i_prog]))
    out = Counter()
    for x in ent.values():
        if not x["pubs"]:
            continue
        premiere = min(x["pubs"])
        jour = x["des"] or premiere[0]
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", jour):
            out[(jour, pays_programme_ue(premiere[1], iso3))] += 1
    return out, len(ent)


def lire() -> dict[tuple, list[int]]:
    if not SORTIE.exists():
        return {}
    return {(x["source"], x["jour"], x["pays"]): [int(x["designations"]), int(x["actions"])]
            for x in csv.DictReader(SORTIE.open(encoding="utf-8"))}


def principal() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--depuis", default="")
    a = ap.parse_args()
    aujourd_hui = datetime.now(timezone.utc).date()
    debut = date.fromisoformat(a.depuis) if a.depuis else aujourd_hui - timedelta(days=10)
    comptes = lire()
    ok_ofac = ok_uk = ok_ue = False
    with httpx.Client(headers=UA, timeout=60, follow_redirects=True) as c:
        # OFAC : une page par jour ouvré
        d, pages = debut, 0
        while d <= aujourd_hui:
            if d.weekday() < 5:
                j = d.isoformat()
                try:
                    r = c.get(OFAC.format(j=d.strftime("%Y%m%d")))
                    titre, par_pays = lire_ofac(r.text) if r.status_code == 200 else ("", Counter())
                    if r.status_code == 200 and "not found" in titre.lower():
                        ok_ofac = True                     # page « introuvable » servie en 200 : pas d'action
                    elif r.status_code == 200:
                        for k in [k for k in comptes if k[0] == "ofac" and k[1] == j]:
                            del comptes[k]
                        for p, n in par_pays.items():
                            comptes[("ofac", j, p)] = [n, 1]
                        if not par_pays:
                            comptes[("ofac", j, "--")] = [0, 1]
                        pages += 1
                        ok_ofac = True
                        print(f"  OFAC {j} : {titre[:90]} ; {dict(par_pays)}")
                    elif r.status_code != 404:
                        print(f"  OFAC {j} : HTTP {r.status_code}")
                    else:
                        ok_ofac = True                     # 404 : aucun action ce jour-là (réponse valable)
                except httpx.HTTPError as e:
                    print(f"  OFAC {j} : {type(e).__name__}")
                time.sleep(1.0)
            d += timedelta(days=1)
        print(f"OFAC : {pages} jour(s) d'action.")
        # Royaume-Uni : historique des modifications de la liste
        try:
            r = c.get(GOVUK)
            r.raise_for_status()
            hist = ((r.json().get("details") or {}).get("change_history")) or []
            notes = lire_notes_uk(hist, debut.isoformat())
            for k in [k for k in comptes if k[0] == "uk" and k[1] >= debut.isoformat()]:
                del comptes[k]
            for j, p, n in notes:
                v = comptes.setdefault(("uk", j, p), [0, 0])
                v[0] += n
                v[1] += 1
            ok_uk = True
            print(f"Royaume-Uni : {len(hist)} notes dans l'historique, {len(notes)} ajouts depuis le {debut}.")
            for h in hist[:3]:
                print(f"  exemple : {str(h.get('public_timestamp'))[:16]} {str(h.get('note'))[:140]}")
        except Exception as e:
            print(f"Royaume-Uni : indisponible ({type(e).__name__}: {str(e)[:80]})")
        # Union européenne : liste consolidée, recalculée en entier
        try:
            iso3 = table_iso3(c)
            r = c.get(UE, timeout=180)
            r.raise_for_status()
            par_jour, n_ent = lire_ue(r.text, iso3)
            if n_ent < 100:
                raise ValueError(f"liste trop courte ({n_ent} entités)")
            for k in [k for k in comptes if k[0] == "ue"]:
                del comptes[k]
            for (j, p), n in par_jour.items():
                comptes[("ue", j, p)] = [n, 1]
            ok_ue = True
            recents = sum(n for (j, _), n in par_jour.items() if j >= debut.isoformat())
            print(f"UE : {n_ent} entités en vigueur, {len(par_jour)} cases jour × pays ; {recents} inscriptions depuis le {debut}.")
            par_pays = Counter()
            for (_, p), n in par_jour.items():
                par_pays[p] += n
            print("  par pays (toutes dates) :", dict(par_pays.most_common(8)))
        except Exception as e:
            print(f"UE : indisponible ({type(e).__name__}: {str(e)[:100]})")
    SORTIE.parent.mkdir(exist_ok=True)
    with SORTIE.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source", "jour", "pays", "designations", "actions"])
        for (s, j, p), v in sorted(comptes.items(), key=lambda t: (t[0][1], t[0][0], t[0][2])):
            w.writerow([s, j, p, *v])
    if ok_ofac and ok_uk:
        ancien = COUVERTURE.read_text(encoding="utf-8").strip() if COUVERTURE.exists() else ""
        if not ancien or debut.isoformat() < ancien:
            COUVERTURE.write_text(debut.isoformat() + "\n", encoding="utf-8")
    bilan = (f"OFAC {'lu' if ok_ofac else 'INDISPONIBLE'} ; Royaume-Uni {'lu' if ok_uk else 'INDISPONIBLE'} ; "
             f"UE {'lue' if ok_ue else 'INDISPONIBLE'} ; {len(comptes)} cases.")
    print(bilan)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(f"## Sanctions\n\n{bilan}\n")
    return 0 if (ok_ofac or ok_uk) else 1


if __name__ == "__main__":
    sys.exit(principal())
