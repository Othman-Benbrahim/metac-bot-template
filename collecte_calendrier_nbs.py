"""Silence statistique chinois : publications du Bureau national des statistiques (NBS) prévues et observées
(bot 0.10.209, M15, en ombre).

Décision d'auteur du 2026-11-16 (22 h 19). Quand un chiffre est mauvais, une administration fermée peut retarder
ou suspendre sa publication (chômage des jeunes, été 2023). L'absence d'une publication PRÉVUE est observable de
l'extérieur, sans accès aux données elles-mêmes.

1. Calendrier prévu : registre/calendrier-nbs.csv, recopié du calendrier officiel publié en début d'année
   (« Regular Press Release Calendar of NBS in 2026 », stats.gov.cn, 26 décembre 2025). À renouveler chaque année
   (le calendrier 2027 paraît fin décembre 2026).
2. Publications observées : liste des communiqués anglais du NBS (https://www.stats.gov.cn/english/PressRelease/),
   lue chaque jour ; la date est celle de l'adresse (t2026MMJJ), le titre donne la publication (motifs fixes).
   Le site anglais publie souvent un ou deux jours après le chinois : tolérance de 3 jours.

Registre : registre/publications-nbs.csv (jour, publication, titre, url) ; registre/publications-nbs-jours.txt.
Le jugement (à temps, en retard, absente) est fait par l'indicateur `silence_statistique`, pas ici.
Usage : python collecte_calendrier_nbs.py [--pages 1]
"""
from __future__ import annotations

import argparse
import csv
import html
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

LISTE = "https://www.stats.gov.cn/english/PressRelease/"
UA = {"User-Agent": "alphabet-situationnel-bot/1.0 (recherche ; GitHub Othman-Benbrahim)"}
OBSERVEES = Path("registre") / "publications-nbs.csv"
JOURS = Path("registre") / "publications-nbs-jours.txt"
CHAMPS = ["jour", "publication", "titre", "url"]

# titre anglais → publication du calendrier (motifs fixés d'avance)
MOTIFS = [
    ("economie_nationale", r"^\s*National Economy"),
    ("pib_trimestriel", r"Accounting Results of GDP|Value Added of Major Industries"),
    ("pmi", r"Purchasing Managers"),
    ("ipc", r"Consumer Price Index"),
    ("ipp", r"Producer Price Index"),
    ("production_industrielle", r"Industrial Production Operation"),
    ("investissement", r"Investment in Fixed Assets"),
    ("immobilier", r"Real Estate Development"),
    ("ventes_detail", r"Retail Sales"),
    ("revenus_menages", r"Income and Consumption Expenditure"),
    ("prix_logements", r"Sales Prices of Commercial Residential"),
    ("profits_industriels", r"Profits of Industrial Enterprises"),
]
_LIEN = re.compile(r'<a[^>]+href="([^"]*?/(\d{6})/t(\d{8})_\d+\.html)"[^>]*>(.*?)</a>', re.I | re.S)


def publication(titre: str) -> str | None:
    t = re.sub(r"^\s*\d+\.\s*", "", titre)          # « 4.Consumer Price Index… » → sans le numéro de rang
    for nom, m in MOTIFS:
        if re.search(m, t, re.I):
            return nom
    return None


def lire_page(page_html: str) -> list[dict]:
    out = []
    for url, _, jour, titre in _LIEN.findall(page_html):
        titre = html.unescape(re.sub(r"<[^>]+>|\s+", " ", titre)).strip()
        p = publication(titre)
        if p:
            out.append({"jour": f"{jour[:4]}-{jour[4:6]}-{jour[6:]}", "publication": p, "titre": titre[:150],
                        "url": url if url.startswith("http") else LISTE + url.lstrip("./")})
    return out


def principal() -> int:
    a_ = argparse.ArgumentParser()
    a_.add_argument("--pages", type=int, default=1, help="pages de la liste à lire (1 = environ trois semaines)")
    a = a_.parse_args()
    obs = {x["url"]: x for x in csv.DictReader(OBSERVEES.open(encoding="utf-8"))} if OBSERVEES.exists() else {}
    nouvelles = lues = 0
    with httpx.Client(headers=UA, timeout=60, follow_redirects=True) as c:
        for n in range(a.pages):
            url = LISTE if n == 0 else f"{LISTE}index_{n}.html"
            r = c.get(url)
            if r.status_code != 200:
                print(f"  page {n} : HTTP {r.status_code}")
                if n == 0:
                    return 1
                break
            items = lire_page(r.text)
            lues += 1
            for x in items:
                if x["url"] not in obs:
                    obs[x["url"]] = x
                    nouvelles += 1
            time.sleep(1)
    OBSERVEES.parent.mkdir(exist_ok=True)
    with OBSERVEES.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CHAMPS)
        w.writeheader()
        for x in sorted(obs.values(), key=lambda x: (x["jour"], x["publication"])):
            w.writerow({k: x.get(k, "") for k in CHAMPS})
    jours = set(JOURS.read_text(encoding="utf-8").split()) if JOURS.exists() else set()
    jours.add(datetime.now(timezone.utc).date().isoformat())
    JOURS.write_text("\n".join(sorted(jours)) + "\n", encoding="utf-8")
    bilan = (f"{lues} page(s) lue(s) ; {nouvelles} nouvelle(s) publication(s) ; {len(obs)} au registre "
             f"(depuis le {min((x['jour'] for x in obs.values()), default='—')}). Source : NBS (stats.gov.cn).")
    print(bilan)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(f"## Publications du NBS (M15)\n\n{bilan}\n")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
