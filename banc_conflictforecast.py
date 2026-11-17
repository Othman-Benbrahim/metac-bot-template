"""ConflictForecast comme INDICATEUR contre B, sur les questions ACLED de ForecastBench (bot 0.10.231, en ombre).

Décision d'auteur du 2026-11-17 (« D'accord », vers 16 h 50) : comparer ConflictForecast (Mueller et Rauh) à nos
prévisions, sans fuite. Préenregistrement : preenregistrements/conflictforecast.md.

Les cibles de ConflictForecast (conflit armé, toute violence, intensité à 3 mois) ne sont pas celles des questions
ACLED (« plus d'événements que la moyenne ? ») : il ne peut pas concourir tel quel. On le lit donc comme un
indicateur, à états FIXÉS D'AVANCE :
  ESC = escalade prévue : prévision d'intensité à 3 mois (int_lnbest_03, modèle « best ») − niveau actuel > 0,5
        (1) ; sinon (0) ;
  AV  = toute violence probable : p(anyviolence, 3 mois) ≥ 0,5 (1) ; sinon (0).
Règle contre la fuite : une version dont les dernières données sont du mois M ne sert qu'à partir du 25 du mois M+1 ;
pour une question posée le jour d, on prend la version la plus récente utilisable à d.

Test : comme le banc des combinaisons. Pour chaque indicateur, chaque état et chaque famille, δ = ln((O+0,5)/(E+0,5))
sur l'exploration (jeux avant 2026-01-01), appliqué en logit à B sur la confirmation (2026) ; bootstrap par jeu au
risque es.risque_corrige(1) / k (k = cases jugeables, au moins 10 questions de chaque côté). Famille attendue :
violence ; mobilisation = témoin.

    python banc_conflictforecast.py
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
from datetime import date
from pathlib import Path

import combinaisons as cb

CF = Path("registre") / "conflictforecast.csv"
SORTIE = Path("registre") / "banc-conflictforecast.json"
CODES = "https://raw.githubusercontent.com/datasets/country-codes/main/data/country-codes.csv"
COUPURE = "2026-01-01"
SEUIL_ESC = 0.5
SEUIL_AV = 0.5
INDICATEURS = ("ESC", "AV")
ATTENDU = {"ESC": "violence", "AV": "violence"}


def utilisable_le(periode: int) -> str:
    """Dernier mois de données AAAAMM → date ISO à partir de laquelle la version sert (25 du mois suivant)."""
    a, m = divmod(int(periode), 100)
    a, m = (a + 1, 1) if m == 12 else (a, m + 1)
    return f"{a:04d}-{m:02d}-25"


def proba(x: str) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v / 100 if v > 1 else v                      # anciennes versions (2021-2024) en pourcentage


def charger_cf(texte: str, iso3_iso2: dict[str, str]) -> dict[str, list[tuple[str, dict]]]:
    """{ISO2 : [(utilisable_le, {"ESC": 0/1/None, "AV": 0/1/None}), …] trié}."""
    brut: dict[tuple[str, str], dict] = {}
    for x in csv.DictReader(io.StringIO(texte)):
        if x.get("horizon") != "3":
            continue
        cle = (x["isocode"], x["periode"])
        d = brut.setdefault(cle, {})
        if x["cible"] == "lnbest" and x.get("p_all") and x.get("actuel") not in (None, ""):
            try:
                d["ESC"] = 1 if float(x["p_all"]) - float(x["actuel"]) > SEUIL_ESC else 0
            except ValueError:
                pass
        elif x["cible"] == "anyviolence":
            p = proba(x.get("p_all"))
            if p is not None:
                d["AV"] = 1 if p >= SEUIL_AV else 0
    out: dict[str, list[tuple[str, dict]]] = {}
    for (iso3, periode), d in brut.items():
        iso2 = iso3_iso2.get(iso3)
        if iso2:
            out.setdefault(iso2, []).append((utilisable_le(int(periode)), d))
    for v in out.values():
        v.sort(key=lambda t: t[0])
    return out


def etat_au(serie: list[tuple[str, dict]], jour: str) -> dict:
    dispo = [d for u, d in serie if u <= jour]
    return dispo[-1] if dispo else {}


def resumer(ls: list[dict], coupure: str = COUPURE) -> dict:
    import essais as es
    explo = [x for x in ls if x["jeu"] < coupure]
    conf = [x for x in ls if x["jeu"] >= coupure]
    cellules, jugeables = [], []
    for ind in INDICATEURS:
        for fam in sorted({x["famille"] for x in ls}):
            for etat in (1, 0):
                ce = [x for x in explo if x["famille"] == fam and x["cf"].get(ind) == etat]
                cc = [x for x in conf if x["famille"] == fam and x["cf"].get(ind) == etat]
                c = {"indicateur": ind, "famille": fam, "etat": etat, "attendue": fam == ATTENDU[ind],
                     "n_exploration": len(ce), "n_confirmation": len(cc)}
                if len(ce) >= cb.N_MIN:
                    c["delta"] = round(cb.ratio(ce), 4)
                    if len(cc) >= cb.N_MIN:
                        jugeables.append((c, cc))
                cellules.append(c)
    k = max(1, len(jugeables))
    risque = es.risque_corrige(1) / k
    for c, cc in jugeables:
        d = c["delta"]
        ec = [(x["jeu"], cb.pl(cb.sig(cb.logit(x["p_B"]) + d), x["issue"]) - cb.pl(x["p_B"], x["issue"])) for x in cc]
        bas, haut = cb.bootstrap(ec, risque)
        c.update({"perte_B": round(sum(cb.pl(x["p_B"], x["issue"]) for x in cc) / len(cc), 4),
                  "perte_ajustee": round(sum(cb.pl(cb.sig(cb.logit(x["p_B"]) + d), x["issue"]) for x in cc) / len(cc), 4),
                  "ecart_moyen": round(sum(e for _, e in ec) / len(ec), 4),
                  "intervalle_corrige": [round(bas, 4), round(haut, 4)],
                  "verdict": "confirmé" if haut < 0 else "non confirmé"})
    return {"note": "perte log, plus bas = mieux ; δ fixé sur l'exploration, jugé sur la confirmation ; aucun modèle "
                    "de langue ; données ConflictForecast : Mueller et Rauh (2022), Mueller, Rauh et Seimon (2024)",
            "coupure": coupure, "questions": len(ls), "avec_conflictforecast": sum(bool(x["cf"]) for x in ls),
            "k_juges": len(jugeables), "risque_corrige": round(risque, 6), "cellules": cellules}


def table_iso() -> dict[str, str]:
    import httpx
    t = httpx.get(CODES, timeout=60, follow_redirects=True)
    t.raise_for_status()
    table = {x["ISO3166-1-Alpha-3"].strip(): x["ISO3166-1-Alpha-2"].strip() for x in csv.DictReader(io.StringIO(t.text))
             if len((x.get("ISO3166-1-Alpha-3") or "").strip()) == 3 and len((x.get("ISO3166-1-Alpha-2") or "").strip()) == 2}
    table.setdefault("XKX", "XK")
    return table


def principal() -> int:
    if not CF.exists():
        print("registre/conflictforecast.csv absent : lancer d'abord la collecte.")
        return 1
    texte = CF.read_text(encoding="utf-8")
    if "actuel" not in texte.splitlines()[0]:
        print("Registre sans colonne « actuel » : relancer la collecte ConflictForecast (relecture complète).")
        return 1
    cf = charger_cf(texte, table_iso())
    ls = []
    for x in cb.lignes():
        if not x.get("cca2"):
            continue
        ls.append({**x, "cf": etat_au(cf.get(x["cca2"], []), x["jeu"])})
    res = resumer(ls)
    SORTIE.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    lignes = [f"{c['indicateur']}={c['etat']} {c['famille']} : n {c['n_exploration']}/{c['n_confirmation']}"
              + (f", δ {c['delta']}" if "delta" in c else "")
              + (f", écart {c['ecart_moyen']} {c['intervalle_corrige']} → {c['verdict']}" if "verdict" in c else "")
              for c in res["cellules"]]
    bilan = (f"{res['questions']} questions, {res['avec_conflictforecast']} avec une version utilisable ; "
             f"{res['k_juges']} cases jugées (risque {res['risque_corrige']}).\n\n" + "\n".join(f"- {l}" for l in lignes))
    print(bilan)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fo:
            fo.write(f"## ConflictForecast contre B\n\n{bilan}\n")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
