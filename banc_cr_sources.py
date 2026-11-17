"""Classe de référence pondérée sur les SOURCES D'ÉVÉNEMENTS du bot (bot 0.10.235, en ombre).

Décision d'auteur du 2026-11-17 (19 h 13) : « Oui, plus on testera, mieux ce sera ». La classe de référence pondérée
(banc_classe_reference.py) bat le compte sur GDELT à 7, 30 et 90 jours (adoptée comme B de ce banc), mais pas sur les
séries FRED et DBnomics (essai b_noyau clos). Avant toute entrée dans le bot en direct : la tester sur les sources
d'événements que le bot interroge (puits, alphabet_puits.py), qui varient elles aussi par rafales.
Préenregistrement : preenregistrements/classe-reference.md, partie « sources d'événements du bot ». Aucun modèle de
langue ; tout est gratuit (UCDP : jeton déjà en secret).

Groupes FIXÉS ICI, avant tout passage (la classe pondérée mêle les groupes d'une même source, comme les pays sur GDELT) :
  ucdp               événements de violence organisée par pays (25 pays en conflit), depuis 2024-01-01 ;
  coupures_internet  jours d'alerte critique IODA par pays (20 pays), depuis 2023-06-01 ;
  usgs_seismes       séismes mondiaux de magnitude ≥ 4,5 et ≥ 5,5, depuis 2023-06-01 ;
  gdacs              alertes (vertes, orange, rouges) par type d'aléa, depuis 2023-06-01 ;
  lancements         lancements spatiaux par propriétaire (US, PRC, CIS, IND, JPN, ESA, FR), toute l'histoire ;
  sanctions_us       nouvelles cibles OFAC par programme (8 programmes).
Questions : comme le banc GDELT (cas_echelle) : « plus d'événements dans les F jours après d0 que dans les F jours
avant ? », posée si au moins 1 événement avant ; tous les jours entre le début de la source et la date de relevé sont
tenus pour couverts. B = part lissée des fenêtres passées « oui » du même groupe ; B_noyau = classe pondérée (z, m ;
largeurs 1 ; 1).

Critère : pour chaque source, à 30 jours, questions de confirmation (d0 à partir du 2025-11-01), au moins 30 : écart de
perte log B_noyau − B, bootstrap par mois, risque es.risque_corrige(1) / k (k = sources jugées). 7 et 90 jours : rapportés,
non jugés. Une source « meilleure que B » devient CANDIDATE à l'entrée dans le bot (décision d'auteur datée à part).

    python banc_cr_sources.py
"""
from __future__ import annotations

import asyncio
import json
import math
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import banc_classe_reference as bcr
import combinaisons as cb
import combinaisons_gdelt as cg

SORTIE = Path("registre") / "banc-cr-sources.json"
COUPURE = cg.COUPURE
N_MIN = 30
PAYS_UCDP = ("Sudan", "Ukraine", "Myanmar", "Syria", "Somalia", "DR Congo", "Nigeria", "Burkina Faso", "Mali", "Niger",
             "Ethiopia", "Yemen", "Afghanistan", "Pakistan", "India", "Colombia", "Mexico", "Cameroon", "Mozambique",
             "Israel", "Iraq", "Haiti", "Philippines", "Kenya", "South Sudan")
PAYS_IODA = ("IR", "IQ", "SY", "SD", "ET", "MM", "PK", "IN", "RU", "UA", "VE", "CU", "SN", "KE", "NG", "LY", "YE", "AF",
             "BD", "TR")
ALEAS = ("EQ", "TC", "FL", "VO", "DR", "WF")
PROPRIETAIRES = ("US", "PRC", "CIS", "IND", "JPN", "ESA", "FR")
PROGRAMMES = ("RUSSIA-EO14024", "IRAN", "SDGT", "CYBER2", "GLOMAG", "DPRK", "VENEZUELA", "SDNTK")


def groupes() -> list[tuple[str, str, dict, str]]:
    """[(source, groupe, paramètres, début)]."""
    g = [("ucdp", p, {"pays": p, "debut": "2024-01-01"}, "2024-01-01") for p in PAYS_UCDP]
    g += [("coupures_internet", p, {"pays": p, "debut": "2023-06-01"}, "2023-06-01") for p in PAYS_IODA]
    g += [("usgs_seismes", f"M{m}", {"magnitude_min": m, "debut": "2023-06-01"}, "2023-06-01") for m in (4.5, 5.5)]
    g += [("gdacs", a, {"types": a, "debut": "2023-06-01", "alerte": "Green;Orange;Red"}, "2023-06-01") for a in ALEAS]
    g += [("lancements", o, {"proprietaire": o}, "2023-06-01") for o in PROPRIETAIRES]
    g += [("sanctions_us", p, {"programme": p}, "2023-06-01") for p in PROGRAMMES]
    return g


def comptes_jour(points: list[dict], debut: str) -> dict[str, int]:
    c: dict[str, int] = {}
    for p in points:
        j = str(p.get("date") or "")[:10]
        if j and j >= debut:
            c[j] = c.get(j, 0) + 1
    return c


def jours(debut: str, fin: date) -> set[str]:
    d, out = date.fromisoformat(debut), set()
    while d < fin:
        out.add(d.isoformat())
        d += timedelta(days=1)
    return out


def cas_source(comptes: dict, couverts: dict[str, set[str]], dernier: date, fenetre: int) -> list[dict]:
    """Comme banc_classe_reference.cas_echelle, mais couverture par source et seuil de 1 événement avant."""
    sauve = (cg.MIN_AVANT, cg.MANQUE_MAX)
    try:
        cg.MIN_AVANT = {t: 1 for t in {t for t, _ in comptes}}
        out = []
        for typ in sorted({t for t, _ in comptes}):
            sous = {k: v for k, v in comptes.items() if k[0] == typ}
            out += bcr.cas_echelle(sous, couverts[typ], couverts[typ], dernier, fenetre)
        return out
    finally:
        cg.MIN_AVANT, cg.MANQUE_MAX = sauve


def juger(xs: list[dict], k: int) -> dict:
    import essais as es
    jug = [x for x in xs if "p_K" in x]
    conf = [x for x in jug if x["jeu"] >= COUPURE]
    r = {"questions": len(xs), "avec_noyau": len(jug), "n_confirmation": len(conf)}
    if conf:
        r["perte_B"] = round(bcr.perte(conf, "p_B"), 4)
        r["perte_noyau"] = round(bcr.perte(conf, "p_K"), 4)
        r["oui"] = round(sum(x["issue"] for x in conf) / len(conf), 3)
    if len(conf) >= N_MIN and k:
        ec = [(x["jeu"][:7], cb.pl(x["p_K"], x["issue"]) - cb.pl(x["p_B"], x["issue"])) for x in conf]
        bas, haut = cb.bootstrap(ec, es.risque_corrige(1) / k)
        r.update(ecart_moyen=round(sum(e for _, e in ec) / len(ec), 4), intervalle_corrige=[round(bas, 4), round(haut, 4)],
                 verdict="meilleur que B" if haut < 0 else ("moins bon que B" if bas > 0 else "non tranché"))
    return r


async def collecter(avant: date) -> tuple[dict, dict, list[str]]:
    import alphabet_puits as apz
    comptes, debuts, journal = {}, {}, []
    for src, grp, params, debut in groupes():
        try:
            r = await apz.appeler(src, params, avant)
        except Exception as e:
            journal.append(f"{src}/{grp} : {type(e).__name__}: {apz.masquer(str(e))[:120]}")
            continue
        c = comptes_jour(r.get("points") or [], debut)
        comptes[(src, grp)] = c
        debuts[src] = min(debuts.get(src, debut), debut)
        journal.append(f"{src}/{grp} : {sum(c.values())} événements")
        await asyncio.sleep(0.5)
    return comptes, debuts, journal


def principal() -> int:
    avant = date.today()
    comptes, debuts, journal = asyncio.run(collecter(avant))
    print("\n".join(journal))
    couverts = {s: jours(d, avant) for s, d in debuts.items()}
    dernier = avant - timedelta(days=1)
    res = {"note": "perte log, plus bas = mieux ; aucun modèle de langue ; critère : 30 jours, par source",
           "releve": avant.isoformat(), "journal": journal, "par_echelle": {}}
    for f in (30, 7, 90):
        xs = cas_source(comptes, couverts, dernier, f)
        bcr.noyau(xs)
        par = {s: [x for x in xs if x["type"] == s] for s in sorted({x["type"] for x in xs})}
        k = sum(1 for v in par.values() if sum(1 for x in v if "p_K" in x and x["jeu"] >= COUPURE) >= N_MIN) if f == 30 else 0
        res["par_echelle"][f"{f} jours"] = {"k_juges": k, "sources": {s: juger(v, k) for s, v in par.items()}}
    SORTIE.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    lignes = []
    for e, d in res["par_echelle"].items():
        for s, r in d["sources"].items():
            lignes.append(f"| {e} | {s} | {r['n_confirmation']} | {r.get('perte_B', '—')} | {r.get('perte_noyau', '—')} | "
                          f"{r.get('intervalle_corrige', '—')} | {r.get('verdict', 'non jugé')} |")
    texte = ("| Échelle | Source | Questions (conf.) | B | B_noyau | Intervalle corrigé | Verdict |\n|---|---|---|---|---|---|---|\n"
             + "\n".join(lignes))
    print(texte)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fo:
            fo.write("## Classe de référence pondérée, sources d'événements du bot\n\n" + texte + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
