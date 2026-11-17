"""Événements UCDP GED localisés par carreau PRIO-GRID, historique long (bot 0.10.239, en ombre).

Décision d'auteur du 2026-11-17 (20 h 00, « Oui, c'est parti ») : adapter les théories géographiques à la bonne
échelle (claude/resultat-geo-math-2026-11-17.md). La diffusion d'Hägerstrand est locale : on la mesure entre carreaux
de 0,5° (PRIO-GRID, environ 55 km), pas entre pays. UCDP GED donne pour chaque événement son carreau (priogrid_gid).

Source : API UCDP GED (jeton UCDP_TOKEN, déjà en secret ; 5 000 requêtes par jour, chaque page compte), version
annuelle (jusqu'à fin 2025) puis versions candidates mensuelles de 2026 (alphabet_puits.versions_candidates). Données
UCDP sous licence CC BY 4.0 ; citation : Sundberg et Melander (2013), Journal of Peace Research 50(4) ; Davies,
Pettersson et Öberg (2025).
Le plafond de 5 pages du puits du bot est contourné proprement : une requête par pays et par ANNÉE, pages suivies
jusqu'au bout (au plus 60 pages par année).

Registre : registre/ucdp-cellules.csv.gz (pays, jour, cellule, evenements, morts, max_morts), comptes par pays, jour et
carreau ; max_morts (0.10.240) = morts du plus grand événement du carreau ce jour-là (loi de Richardson, par événement) ;
relu en entier à chaque passage (les versions annuelles révisent le passé).

    python collecte_ucdp_grille.py [--debut 2015]
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import gzip
import os
import sys
from datetime import date
from pathlib import Path

SORTIE = Path("registre") / "ucdp-cellules.csv.gz"
PAGES_MAX = 60


async def lire(src: str, pays: str, debut: str, fin: str, version: str, jeton: str) -> tuple[list[dict], int]:
    import alphabet_puits as apz
    p = {"pagesize": 1000, "StartDate": debut, "EndDate": fin, "Country": apz.code_gw(pays)}
    url, page, out = f"https://ucdpapi.pcr.uu.se/api/gedevents/{version}", 0, []
    while url and page < PAGES_MAX:
        d = await apz._get(url, p if page == 0 else None, {"x-ucdp-access-token": jeton})
        for x in d.get("Result", []):
            out.append({"jour": str(x.get("date_start") or "")[:10], "cellule": x.get("priogrid_gid"),
                        "morts": x.get("best")})
        url, page = d.get("NextPageUrl") or None, page + 1
    return out, page


async def principal(debut: int) -> int:
    import alphabet_puits as apz
    import banc_cr_sources as bs
    jeton = os.environ.get("UCDP_TOKEN")
    if not jeton:
        print("UCDP_TOKEN absent.")
        return 1
    annuelle = os.environ.get("UCDP_VERSION") or "26.1"
    an_annuelle = 2000 + int(annuelle.split(".")[0]) - 1          # 26.1 couvre jusqu'à fin 2025
    aujourdhui = date.today()
    comptes: dict[tuple, list] = {}
    requetes, journal = 0, []
    for pays in bs.PAYS_UCDP:
        n_pays = 0
        for an in range(debut, an_annuelle + 1):
            try:
                ev, pages = await lire("ged", pays, f"{an}-01-01", f"{an}-12-31", annuelle, jeton)
            except Exception as e:
                journal.append(f"{pays} {an} : {type(e).__name__}: {apz.masquer(str(e))[:100]}")
                continue
            requetes += max(1, pages)
            if pages >= PAGES_MAX:
                journal.append(f"{pays} {an} : {PAGES_MAX} pages atteintes (tronqué)")
            for x in ev:
                if not x["jour"] or x["cellule"] in (None, ""):
                    continue
                k = (pays, x["jour"], int(x["cellule"]))
                v = comptes.setdefault(k, [0, 0.0, 0.0])
                v[0] += 1
                v[1] += float(x["morts"] or 0)
                v[2] = max(v[2], float(x["morts"] or 0))
                n_pays += 1
        for vc in apz.versions_candidates(f"{an_annuelle + 1}-01-01", aujourdhui, annuelle):
            m = int(vc.split(".")[-1])
            fin = date(an_annuelle + 1 + (m == 12), m % 12 + 1, 1)
            try:
                ev, pages = await lire("ged", pays, f"{an_annuelle + 1}-{m:02d}-01", fin.isoformat(), vc, jeton)
            except Exception:
                break
            requetes += max(1, pages)
            for x in ev:
                if not x["jour"] or x["cellule"] in (None, "") or not x["jour"].startswith(f"{an_annuelle + 1}-{m:02d}"):
                    continue
                k = (pays, x["jour"], int(x["cellule"]))
                v = comptes.setdefault(k, [0, 0.0, 0.0])
                v[0] += 1
                v[1] += float(x["morts"] or 0)
                v[2] = max(v[2], float(x["morts"] or 0))
                n_pays += 1
        journal.append(f"{pays} : {n_pays} événements")
        print(journal[-1], flush=True)
    SORTIE.parent.mkdir(exist_ok=True)
    with gzip.open(SORTIE, "wt", encoding="utf-8", newline="") as fo:
        w = csv.writer(fo)
        w.writerow(["pays", "jour", "cellule", "evenements", "morts", "max_morts"])
        for (p, j, c), (n, m, mx) in sorted(comptes.items()):
            w.writerow([p, j, c, n, round(m), round(mx)])
    bilan = (f"UCDP par carreau : {len(comptes)} lignes, {requetes} requêtes ; " + " ; ".join(x for x in journal if "tronqué" in x or "Error" in x))
    print(bilan)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fo:
            fo.write(f"## UCDP par carreau PRIO-GRID\n\n{bilan}\n\n" + "\n".join(f"- {x}" for x in journal) + "\n")
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--debut", type=int, default=2015)
    sys.exit(asyncio.run(principal(a.parse_args().debut)))
