"""Mesures ParlGov : passage des voix aux sièges et durée de formation des gouvernements (bot 0.10.375, ombre).

Données : ParlGov (Döring et Manow, version du 12 août 2024), view_election.csv et view_cabinet.csv fournis par
l'auteur le 2026-11-20. Licence non vérifiée : les fichiers bruts restent hors du dépôt (PARLGOV_BRUTS) ; seuls les
comptes et fréquences dérivés sont publiés, avec la citation. Mesure, ne déduit pas : les fréquences observées deviennent les paramètres
des règles coutumières `voix_vers_sieges` et `formation_gouvernement_duree`. Système électoral : relevé IPU de la
chambre basse en 2026 (ipu_parlements.systeme), appliqué aux élections depuis PERIODE seulement, pour limiter l'écart
entre le système d'aujourd'hui et celui de l'élection.
`python mesures_parlgov.py` écrit registre/parlgov/mesures.json et mesures.md.
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import os

import ipu_parlements as ipu

DOSSIER = Path("registre") / "parlgov"
BRUTS = Path(os.environ.get("PARLGOV_BRUTS", "/tmp/claude-0/parlgov"))   # fichiers bruts hors dépôt (licence non vérifiée)
PERIODE = "2000-01-01"
ISO3 = {"AUS": "AU", "AUT": "AT", "BEL": "BE", "BGR": "BG", "CAN": "CA", "CHE": "CH", "CYP": "CY", "CZE": "CZ", "DEU": "DE",
        "DNK": "DK", "ESP": "ES", "EST": "EE", "FIN": "FI", "FRA": "FR", "GBR": "GB", "GRC": "GR", "HRV": "HR", "HUN": "HU",
        "IRL": "IE", "ISL": "IS", "ISR": "IL", "ITA": "IT", "JPN": "JP", "LTU": "LT", "LUX": "LU", "LVA": "LV", "MLT": "MT",
        "NLD": "NL", "NOR": "NO", "NZL": "NZ", "POL": "PL", "PRT": "PT", "ROU": "RO", "SVK": "SK", "SVN": "SI", "SWE": "SE",
        "TUR": "TR"}
EXCLUS = {"none", "other", "Others", "one-seat", "independent", "Ind"}
ECARTS = [(0, 3), (3, 100)]          # deux tranches : sous 3 points, chaque famille a moins de 30 cas par tranche fine


def famille(sy: str | None) -> str:
    if not sy:
        return "inconnu"
    for k, v in (("List PR", "proportionnelle de liste"), ("MMP", "mixte compensatoire"), ("Parallel", "parallèle"),
                 ("FPTP", "uninominal un tour"), ("TRS", "deux tours"), ("STV", "vote unique transférable"),
                 ("AV", "vote préférentiel")):
        if k in sy:
            return v
    return "autre"


def _f(x: str) -> float | None:
    try:
        return float(x)
    except ValueError:
        return None


def voix_sieges() -> dict:
    el = defaultdict(list)
    for r in csv.DictReader((BRUTS / "view_election.csv").open(encoding="utf-8")):
        if r["election_type"] == "parliament" and r["election_date"] >= PERIODE and r["party_name_short"] not in EXCLUS:
            v, s = _f(r["vote_share"]), _f(r["seats"])
            if v is not None and s is not None:
                el[(r["country_name_short"], r["election_date"])].append((v, s))
    res = defaultdict(lambda: {"n": 0, "premier_aussi_premier": 0, "deuxieme_aussi_deuxieme": 0, "ecarts_vers_deuxieme": 0,
                               "par_ecart": {f"{a}-{b}": [0, 0] for a, b in ECARTS}})
    for (c, d), ps in el.items():
        if len(ps) < 2:
            continue
        pv = sorted(ps, key=lambda x: -x[0])
        if pv[0][0] == pv[1][0] or len({s for _, s in ps}) < 2:
            continue
        ps_s = sorted(ps, key=lambda x: -x[1])
        if ps_s[0][1] == ps_s[1][1]:
            continue                                                  # égalité en sièges : exclue
        for cle in (famille(ipu.systeme(ISO3.get(c, ""))), "ensemble"):
            r = res[cle]
            r["n"] += 1
            r["premier_aussi_premier"] += ps_s[0] == pv[0]
            r["ecarts_vers_deuxieme"] += ps_s[0] != pv[0] and ps_s[0] == pv[1]
            r["deuxieme_aussi_deuxieme"] += len(ps_s) > 2 and ps_s[1] == pv[1] and ps_s[2][1] != ps_s[1][1]
            ecart = pv[0][0] - pv[1][0]
            for a, b in ECARTS:
                if a <= ecart < b:
                    r["par_ecart"][f"{a}-{b}"][0] += 1
                    r["par_ecart"][f"{a}-{b}"][1] += ps_s[0] == pv[0]
    return {k: {"n": v["n"], "premier_en_voix_premier_en_sieges": round(v["premier_aussi_premier"] / v["n"], 3),
                "deuxieme_en_voix_deuxieme_en_sieges": round(v["deuxieme_aussi_deuxieme"] / v["n"], 3),
                "desaccords": v["n"] - v["premier_aussi_premier"], "desaccords_au_profit_du_deuxieme": v["ecarts_vers_deuxieme"],
                "par_ecart_points": {e: {"n": n, "taux": round(k_ / n, 3) if n else None} for e, (n, k_) in v["par_ecart"].items()}}
            for k, v in sorted(res.items())}


def formation() -> dict:
    cab = {}
    for r in csv.DictReader((BRUTS / "view_cabinet.csv").open(encoding="utf-8")):
        cab.setdefault(r["cabinet_id"], r)
    par_election = defaultdict(list)
    for r in cab.values():
        if r["election_date"] >= PERIODE and r["caretaker"] == "0" and r["start_date"] >= r["election_date"]:
            par_election[(r["country_name_short"], r["election_date"])].append(r["start_date"])
    jours = defaultdict(list)
    for (c, d), ss in par_election.items():
        j = (date.fromisoformat(min(ss)) - date.fromisoformat(d)).days
        jours[c].append(j)
        jours["ensemble"].append(j)
    out = {}
    for c, js in sorted(jours.items()):
        js = sorted(js)
        out[c] = {"n": len(js), "mediane_jours": statistics.median(js), "p_plus_30": round(sum(j > 30 for j in js) / len(js), 3),
                  "p_plus_90": round(sum(j > 90 for j in js) / len(js), 3), "max": js[-1]}
    return out


def principal() -> int:
    vs, fo = voix_sieges(), formation()
    m = {"source": "ParlGov, Döring et Manow, version du 12 août 2024", "periode": f"élections depuis {PERIODE}",
         "voix_vers_sieges": vs, "formation_gouvernement": fo,
         "note": "fréquences observées ; gouvernement intérimaire exclu ; première équipe non intérimaire après l'élection"}
    (DOSSIER / "mesures.json").write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    L = ["# ParlGov : voix → sièges et durée de formation (élections depuis 2000)", "",
         "| Système (IPU, chambre basse) | Élections | 1er en voix = 1er en sièges | 2e = 2e | écart < 3 pts | ≥ 3 pts |",
         "|---|---|---|---|---|---|"]
    for k, v in vs.items():
        pe = v["par_ecart_points"]
        L.append(f"| {k} | {v['n']} | {v['premier_en_voix_premier_en_sieges']} | {v['deuxieme_en_voix_deuxieme_en_sieges']} | "
                 + " | ".join(f"{x['taux']} ({x['n']})" if x["n"] else "—" for x in pe.values()) + " |")
    L += ["", "| Pays | Élections | Médiane (jours) | > 30 j | > 90 j | Max |", "|---|---|---|---|---|---|"]
    L += [f"| {c} | {v['n']} | {v['mediane_jours']} | {v['p_plus_30']} | {v['p_plus_90']} | {v['max']} |" for c, v in fo.items()]
    (DOSSIER / "mesures.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
