"""Nouvelles sanctions par pays visé : OFAC (États-Unis) et liste britannique (bot 0.10.178, en ombre).

Décision d'auteur du 2026-11-16 (13 h 25) : « Oui, fais les deux ».

1. OFAC (Trésor américain, domaine public) : une page par jour d'action, https://ofac.treasury.gov/recent-actions/AAAAMMJJ
   (pas de flux RSS depuis 2024). On lit le titre et l'on compte, dans le corps, les étiquettes de programme des
   entrées ajoutées ([IRAN], [RUSSIA-EO14024]…). Le programme donne le pays visé par une table fixe (PROGRAMMES) ;
   les programmes sans pays (terrorisme, stupéfiants, cyber…) sont comptés sous « -- ».
2. Royaume-Uni (GOV.UK, Open Government Licence) : historique des modifications de « The UK Sanctions List »
   (API de contenu de GOV.UK, champ details.change_history). Chaque note (« Added 5 entries under the Russia
   sanctions regime ») donne un nombre et un régime ; le régime donne le pays visé.

On garde des comptes : source, jour, pays, designations (nombre d'entrées), actions (nombre d'actions ce jour-là).
Registres : registre/sanctions.csv ; registre/sanctions-couverture.txt (premier jour couvert).

Usage : python collecte_sanctions.py [--depuis AAAA-MM-JJ]   (par défaut : les 10 derniers jours)
"""
from __future__ import annotations

import argparse
import csv
import html
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
    ok_ofac = ok_uk = False
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
    bilan = f"OFAC {'lu' if ok_ofac else 'INDISPONIBLE'} ; Royaume-Uni {'lu' if ok_uk else 'INDISPONIBLE'} ; {len(comptes)} cases."
    print(bilan)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(f"## Sanctions\n\n{bilan}\n")
    return 0 if (ok_ofac or ok_uk) else 1


if __name__ == "__main__":
    sys.exit(principal())
