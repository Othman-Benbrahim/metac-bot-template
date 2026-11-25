"""Élections nationales à venir, d'après la liste publique d'IFES ElectionGuide (2026-11-25, validé par l'auteur à
18 h 29 ; adresse donnée par lui). robots.txt vérifié (sonde du 2026-11-25 : page accessible, 200).

Page : https://electionguide.org/elections/type/upcoming/ ; tableau principal aux colonnes « Country, Election for,
Start Date, End Date, Status, Is Snap?, Last Held*, Last Registered » (en-têtes lus par la sonde). Seuls ces champs
factuels sont gardés, avec l'attribution à IFES ElectionGuide. Les dates portent « (d) » (fixée) ou « (t) »
(provisoire, d'après les cas vus) : gardé tel quel dans « precision ».

Écrit registre/elections-ifes/avenir.csv et une copie datée par passage (millesimes/), pour suivre les reports et les
avancements de date d'un passage à l'autre (un report est un signal en soi).
"""
from __future__ import annotations

import csv
import datetime as dt
import html
import json
import re
import shutil
import sys
from pathlib import Path

import httpx

import politesse

URL = "https://electionguide.org/elections/type/upcoming/"
DOSSIER = Path("registre") / "elections-ifes"
CHAMPS = ["id", "pays", "scrutin", "debut", "debut_precision", "fin", "fin_precision", "statut", "anticipe",
          "derniere", "inscrits"]


def _texte(x: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x))).strip()


def _date(x: str) -> tuple[str, str]:
    m = re.search(r"(\d{4}-\d{2}-\d{2})\s*\((\w)\)", x)
    if m:
        return m.group(1), m.group(2)
    m = re.search(r"([A-Z][a-z]{2}) (\d{1,2}),? (\d{4})", x)
    if m:
        try:
            return dt.datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%b %d %Y").date().isoformat(), \
                (re.search(r"\((\w)\)", x) or [None, ""])[1]
        except ValueError:
            pass
    return "", ""


NOMS = ["Country", "Election for", "Start Date", "End Date", "Status", "Is Snap?", "Last Held*", "Last Registered"]


def analyser(page: str) -> list[dict]:
    """Lignes du tableau principal. 2026-11-25, premier passage : le HTML de la page n'est pas bien imbriqué (une
    recherche « <table>…</table> » coupe le tableau) ; on lit donc les lignes <tr> qui suivent l'en-tête « Is Snap? » et
    ont au moins 8 cellules, et on aligne les 8 DERNIÈRES cellules sur les 8 colonnes nommées (une cellule de drapeau
    peut précéder)."""
    k = page.find("Is Snap?")
    if k < 0:
        return []
    out = []
    for tr in re.findall(r"<tr.*?</tr>", page[k:], re.S):
        cel = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
        if len(cel) < len(NOMS):
            continue
        c = dict(zip(NOMS, cel[-len(NOMS):]))
        m = re.search(r"/elections/id/(\d+)/", c["Election for"])
        d1, p1 = _date(_texte(c["Start Date"]))
        d2, p2 = _date(_texte(c["End Date"]))
        out.append({"id": m.group(1) if m else "", "pays": _texte(c["Country"]), "scrutin": _texte(c["Election for"]),
                    "debut": d1, "debut_precision": p1, "fin": d2, "fin_precision": p2, "statut": _texte(c["Status"]),
                    "anticipe": _texte(c["Is Snap?"]), "derniere": _texte(c["Last Held*"]),
                    "inscrits": _texte(c["Last Registered"])})
    return out


def principal() -> int:
    DOSSIER.mkdir(parents=True, exist_ok=True)
    etat: dict = {"source": "IFES ElectionGuide (liste publique des élections à venir)", "url": URL}
    with httpx.Client(headers={"User-Agent": politesse.UA}, follow_redirects=True, timeout=120) as c:
        if not politesse.autorise(c, URL):
            etat["statut"] = "refuse_robots"
        else:
            r = c.get(URL)
            etat["http"] = r.status_code
            L = analyser(r.text) if r.status_code == 200 else []
            if L:
                with (DOSSIER / "avenir.csv").open("w", encoding="utf-8", newline="") as f:
                    f.write("# Élections à venir, IFES ElectionGuide (electionguide.org) ; collecte_elections_ifes.py\n")
                    w = csv.DictWriter(f, fieldnames=CHAMPS)
                    w.writeheader()
                    w.writerows(L)
                (DOSSIER / "millesimes").mkdir(exist_ok=True)
                shutil.copy(DOSSIER / "avenir.csv", DOSSIER / "millesimes" / f"avenir-{dt.date.today().isoformat()}.csv")
                etat.update({"statut": "ok", "scrutins": len(L), "pays": len({x["pays"] for x in L}),
                             "anticipes": sum(1 for x in L if x["anticipe"].lower() == "yes"),
                             "premier": min((x["debut"] for x in L if x["debut"]), default=None),
                             "dernier": max((x["debut"] for x in L if x["debut"]), default=None)})
            else:
                etat["statut"] = "tableau introuvable"
                k = r.text.find("Is Snap?")
                (DOSSIER / "page-extrait.txt").write_text(r.text[max(0, k - 1500): k + 4000] if k >= 0 else r.text[:5000],
                                                          encoding="utf-8")
    (DOSSIER / "etat.json").write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(etat, ensure_ascii=False, indent=1))
    return 0 if etat.get("statut") == "ok" else 1


if __name__ == "__main__":
    sys.exit(principal())
