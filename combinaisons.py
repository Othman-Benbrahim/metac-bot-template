"""Combinaisons de mécanismes : le bon sens d'abord, le calcul en appoint (bot 0.10.225, en ombre).

Décision d'auteur du 2026-11-17 (11 h 55, grille validée à 12 h 00) : une situation complexe est un agrégat de
situations simples, chacune avec sa causalité (théorie de l'auteur, « la matriochka ») ; il faut trouver la bonne
combinaison. Une combinaison trouvée sur des données ne vaut que si elle se vérifie sur d'autres situations aux mêmes
variables. Pré-enregistrement : preenregistrements/combinaisons-bon-sens.md (grille de 15 paires, datée avant toute
mesure). AUCUN modèle de langue : gratuit.

Questions : ACLED de ForecastBench, forme « une fois », tous les jeux depuis le 2024-07-21 ; B corrigé (code, valeur
au gel). Date d'information : la date du jeu. Pays : table d'OurAirports (comme les indicateurs de niche).

Six mécanismes, état « présent » fixé d'avance (mêmes seuils que l'observatoire, induction.py) :
  M4  la question porte sur des émeutes (et non des manifestations)        familles : mobilisation
  M10 élection nationale dans les 30 jours avant la date                    mobilisation
  M11 voisins en hausse (manifestations, 14 j contre 14 j, log > 0,4)       mobilisation
  M14 date de mémoire dans les 14 jours (pays sans calendrier : absente)    mobilisation, violence
  M17 alignement_rival ≥ 2                                                  stratégique, violence
  FC  force_chinoise ≥ 1                                                    stratégique, violence
Un indicateur non mesurable à la date (couverture insuffisante) exclut la question de la paire.

Pour chaque paire de la grille et chaque famille de la paire (union des familles de ses deux mécanismes ; M4 :
mobilisation seulement) :
1. EXPLORATION, jeux avant le 2026-01-01 : quatre cases (00, 10, 01, 11) ; OUI observés O, OUI attendus E = Σ B.
   Ajustement de la case « les deux » : δ = ln((O + 0,5) / (E + 0,5)), appliqué en logit à B. Interaction :
   I = r11 − r10 − r01 + r00, avec r = ln((O + 0,5) / (E + 0,5)) (renforcement : I > 0 ; redondance ou annulation :
   I < 0 ; additif : I proche de 0).
2. CONFIRMATION, jeux à partir du 2026-01-01, jamais utilisés pour fixer δ : sur les questions de la case « les deux »,
   perte log de B ajusté par δ contre B. Jugée seulement si au moins 10 questions dans la case aux deux étapes.
   Intervalle par bootstrap par blocs (jeu), 2 000 tirages, graine 0, au risque de la règle d'adoption commune
   (5 % / nombre d'essais ouverts, essais.py) divisé encore par k, k = nombre de paires × familles jugées (plausibles
   ET témoins). « Confirmée » : borne haute de l'intervalle corrigé sous 0.
3. VALEUR DU BON SENS : part des confirmées parmi les paires plausibles contre parmi les témoins (descriptif).
4. Explication : hors de ce programme, seulement pour les confirmées.

Registre : registre/combinaisons.jsonl (une ligne par question) ; résumé : registre/combinaisons.json.

    python combinaisons.py [--depuis 2024-07-21]
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import io
import json
import math
import random
import sys
from datetime import date
from pathlib import Path

import httpx

import banc_forecastbench as fb
import banc_indicateurs as bi
import indicateurs_niche as ni

REGISTRE = Path("registre")
FICHIER = REGISTRE / "combinaisons.jsonl"
RESUME = REGISTRE / "combinaisons.json"
COUPURE = "2026-01-01"          # exploration avant, confirmation à partir de
N_MIN = 10
MECANISMES = ("M4", "M10", "M11", "M14", "M17", "FC")
FAMILLES_M = {"M4": {"mobilisation"}, "M10": {"mobilisation"}, "M11": {"mobilisation"},
              "M14": {"mobilisation", "violence"}, "M17": {"strategique", "violence"},
              "FC": {"strategique", "violence"}}
# grille validée par l'auteur le 2026-11-17 (12 h 00) ; « faible » : candidat jugé mauvais par l'auteur, gardé
GRILLE = {
    ("M4", "M10"): "additif", ("M4", "M11"): "additif", ("M4", "M14"): "additif",
    ("M4", "M17"): "temoin", ("M4", "FC"): "temoin",
    ("M10", "M11"): "renforcement", ("M10", "M14"): "additif (faible selon l'auteur)",
    ("M10", "M17"): "renforcement", ("M10", "FC"): "renforcement",
    ("M11", "M14"): "additif (faible selon l'auteur)", ("M11", "M17"): "temoin", ("M11", "FC"): "temoin",
    ("M14", "M17"): "renforcement faible", ("M14", "FC"): "temoin", ("M17", "FC"): "redondant",
}


def familles_paire(a: str, b: str) -> set[str]:
    if "M4" in (a, b):
        return {"mobilisation"}
    return FAMILLES_M[a] | FAMILLES_M[b]


def etats(cca2: str | None, titre: str, d0: date, debut_elections: str | None) -> dict:
    """État (1, 0, ou None si non mesurable) de chaque mécanisme pour une question."""
    import re
    m = re.search(r"'([^']+)'", titre)
    ev = m.group(1) if m else "fatalities"
    out = {"M4": 1 if ev == "Riots" else (0 if ev == "Protests" else None)}
    if not cca2:
        return dict(out, **{k: None for k in MECANISMES[1:]})
    el = ni.elections(cca2, d0)
    ok_el = debut_elections is not None and el.get("present") and \
        date.fromordinal(d0.toordinal() - 30).isoformat() >= debut_elections
    out["M10"] = (1 if el["valeur"] >= 1 else 0) if ok_el else None
    vg = ni.voisins_gdelt(cca2, d0)
    out["M11"] = (1 if vg["valeur"] > 0.4 else 0) if vg.get("present") else None
    dm = ni.dates_memoire(cca2, d0)
    out["M14"] = (1 if dm.get("valeur", 0) >= 1 else 0) if dm.get("present") or "aucune date" in dm.get("raison", "") else None
    ar = ni.alignement_rival(cca2, d0)
    out["M17"] = (1 if ar["valeur"] >= 2 else 0) if ar.get("present") else None
    fc = ni.force_chinoise(cca2, d0)
    out["FC"] = (1 if fc["valeur"] >= 1 else 0) if fc.get("present") else None
    return out


def pl(p: float, y: int) -> float:
    p = min(max(p, 1e-3), 1 - 1e-3)
    return -math.log(p if y else 1 - p)


def logit(p: float) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def sig(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def cases(ls: list[dict], a: str, b: str, fam: str) -> dict[str, list[dict]]:
    out = {"00": [], "10": [], "01": [], "11": []}
    for x in ls:
        e = x["etats"]
        if x["famille"] != fam or e.get(a) is None or e.get(b) is None:
            continue
        out[f"{e[a]}{e[b]}"].append(x)
    return out


def ratio(xs: list[dict]) -> float:
    return math.log((sum(x["issue"] for x in xs) + 0.5) / (sum(x["p_B"] for x in xs) + 0.5))


def bootstrap(ecarts: list[tuple[str, float]], risque: float, tirages: int = 2000) -> tuple[float, float]:
    blocs: dict[str, list[float]] = {}
    for j, e in ecarts:
        blocs.setdefault(j, []).append(e)
    rnd, cles = random.Random(0), sorted(blocs)
    bs = []
    for _ in range(tirages):
        t = [e for _ in cles for e in blocs[rnd.choice(cles)]]
        bs.append(sum(t) / len(t))
    bs.sort()
    i, j = max(0, int(risque * tirages)), min(tirages - 1, int((1 - risque) * tirages) - 1)
    return bs[i], bs[j]


def resumer(ls: list[dict]) -> dict:
    explo = [x for x in ls if x["jeu"] < COUPURE]
    conf = [x for x in ls if x["jeu"] >= COUPURE]
    res, jugeables = [], []
    for (a, b), verdict in GRILLE.items():
        for fam in sorted(familles_paire(a, b)):
            ce, cc = cases(explo, a, b, fam), cases(conf, a, b, fam)
            ligne = {"paire": f"{a} × {b}", "famille": fam, "bon_sens": verdict,
                     "exploration": {k: len(v) for k, v in ce.items()},
                     "confirmation": {k: len(v) for k, v in cc.items()}}
            if all(len(v) >= 1 for v in ce.values()):
                r = {k: ratio(v) for k, v in ce.items()}
                ligne["interaction_exploration"] = round(r["11"] - r["10"] - r["01"] + r["00"], 3)
            if all(len(v) >= 1 for v in cc.values()):
                r = {k: ratio(v) for k, v in cc.items()}
                ligne["interaction_confirmation"] = round(r["11"] - r["10"] - r["01"] + r["00"], 3)
            if len(ce["11"]) >= N_MIN:
                ligne["delta"] = round(ratio(ce["11"]), 4)
            if "delta" in ligne and len(cc["11"]) >= N_MIN:
                jugeables.append(ligne)
            res.append(ligne)
    k = max(1, len(jugeables))
    import essais as es
    risque = es.risque_corrige(1) / k
    for ligne in jugeables:
        a, b = ligne["paire"].split(" × ")
        cc = cases(conf, a, b, ligne["famille"])["11"]
        d = ligne["delta"]
        ec = [(x["jeu"], pl(sig(logit(x["p_B"]) + d), x["issue"]) - pl(x["p_B"], x["issue"])) for x in cc]
        bas, haut = bootstrap(ec, risque)
        ligne.update({"n_confirmation": len(cc),
                      "perte_B": round(sum(pl(x["p_B"], x["issue"]) for x in cc) / len(cc), 4),
                      "perte_ajustee": round(sum(pl(sig(logit(x["p_B"]) + d), x["issue"]) for x in cc) / len(cc), 4),
                      "ecart_moyen": round(sum(e for _, e in ec) / len(ec), 4),
                      "intervalle_corrige": [round(bas, 4), round(haut, 4)],
                      "verdict": "confirmée" if haut < 0 else "non confirmée"})
    plaus = [x for x in jugeables if x["bon_sens"] != "temoin"]
    tem = [x for x in jugeables if x["bon_sens"] == "temoin"]
    part = lambda xs: (round(sum(x["verdict"] == "confirmée" for x in xs) / len(xs), 3) if xs else None)
    return {"note": "perte log, plus bas = mieux ; aucun modèle de langue ; δ fixé sur l'exploration, jugé sur la "
                    "confirmation", "coupure": COUPURE, "questions": len(ls), "exploration": len(explo),
            "confirmation": len(conf), "k_juges": len(jugeables), "risque_corrige": round(risque, 6),
            "valeur_du_bon_sens": {"plausibles_jugees": len(plaus), "part_confirmees": part(plaus),
                                   "temoins_juges": len(tem), "part_confirmes": part(tem)},
            "paires": res}


def lignes() -> list[dict]:
    if not FICHIER.exists():
        return []
    return [json.loads(l) for l in FICHIER.read_text(encoding="utf-8").splitlines() if l.strip()]


def table_pays() -> dict[str, str]:
    r = httpx.get(ni.OURAIRPORTS_PAYS, timeout=60, follow_redirects=True)
    r.raise_for_status()
    t = {}
    for x in csv.DictReader(io.StringIO(r.text)):
        t[x["name"].lower()] = x["code"]
        for k in (x.get("keywords") or "").split(","):
            if k.strip():
                t.setdefault(k.strip().lower(), x["code"])
    alias = {"ivory coast": "côte d'ivoire", "democratic republic of congo": "congo (kinshasa)",
             "republic of congo": "congo (brazzaville)", "czech republic": "czechia", "curacao": "curaçao"}
    for a, n in alias.items():
        if n in t:
            t[a] = t[n]
    return t


async def principal(depuis: str) -> int:
    # rivalités : une fois par mois (le calcul relit le registre mensuel)
    cache_riv: dict = {}
    brut = ni.rivalites
    ni.rivalites = lambda d0: cache_riv.setdefault((d0.year, d0.month), brut(d0))
    deja = {x["question_id"] for x in lignes()}
    pays = table_pays()
    debut_el = None
    if ni.ELECTIONS.exists():
        ds = [x["date"] for x in csv.DictReader(ni.ELECTIONS.open(encoding="utf-8"))]
        debut_el = min(ds) if ds else None
    jeux = sorted(fb.jeux_candidats(date.today(), date.fromisoformat(depuis) - __import__("datetime").timedelta(days=1),
                                    n_max=200))
    print(f"{len(jeux)} jeux ForecastBench de {jeux[0] if jeux else '?'} à {jeux[-1] if jeux else '?'} ; "
          f"calendrier électoral depuis {debut_el}")
    REGISTRE.mkdir(exist_ok=True)
    cache_etats: dict = {}
    n_ecrites = 0
    with FICHIER.open("a", encoding="utf-8") as fo:
        for j in jeux:
            try:
                qs = await fb._json(f"{fb.DEPOT}/question_sets/{j}-llm.json")
                rs = await fb._json(f"{fb.DEPOT}/resolution_sets/{j}_resolution_set.json")
            except Exception as e:
                print(f"Jeu {j} indisponible : {type(e).__name__}")
                continue
            items = [fb.construire(i, j) for i in fb.apparier(qs, rs, ("acled",))]
            items = [x for x in items if fb.facteur_acled(x["titre"]) == 1.0 and x["qid"] not in deja]
            for x in items:
                try:
                    m = float(x["_q"].get("freeze_datetime_value"))
                except (TypeError, ValueError):
                    continue
                nom = bi.pays_de(x["titre"])
                cca2 = pays.get((nom or "").lower())
                fam = __import__("banc_indicateurs_frais").famille(x["titre"])
                cle = (cca2, j, x["titre"].split("'")[1] if "'" in x["titre"] else "")
                if cle not in cache_etats:
                    cache_etats[cle] = etats(cca2, x["titre"], date.fromisoformat(j), debut_el)
                fo.write(json.dumps({"jeu": j, "question_id": x["qid"], "pays": nom, "cca2": cca2, "famille": fam,
                                     "issue": x["issue"], "p_B": fb.b_acled(m), "etats": cache_etats[cle],
                                     "licence": "ForecastBench, Forecasting Research Institute, CC BY-SA 4.0"},
                                    ensure_ascii=False) + "\n")
                n_ecrites += 1
            fo.flush()
            print(f"{j} : {len(items)} questions")
    r = resumer(lignes())
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{n_ecrites} questions écrites")
    print(json.dumps({k: v for k, v in r.items() if k != "paires"}, ensure_ascii=False, indent=1))
    for p in r["paires"]:
        if "verdict" in p:
            print(f"{p['paire']:10s} {p['famille']:12s} {p['bon_sens']:30s} n={p['n_confirmation']:4d} "
                  f"B {p['perte_B']:.3f} → {p['perte_ajustee']:.3f} {p['intervalle_corrige']} {p['verdict']}")
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--depuis", default="2024-07-21")
    o = a.parse_args()
    sys.exit(asyncio.run(principal(o.depuis)))
