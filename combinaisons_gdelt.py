"""Combinaisons de mécanismes, banc de questions fabriquées sur GDELT (bot 0.10.226, en ombre).

Décision d'auteur du 2026-11-17 (13 h 50) : les questions ACLED de ForecastBench sont trop peu nombreuses pour juger
la grille de bon sens (environ 400 questions d'exploration ; la case « les deux mécanismes » compterait souvent moins
de 10 questions). On fabrique donc nos propres questions à partir des comptes GDELT déjà collectés depuis juillet 2024,
avec la MÊME grille (preenregistrements/combinaisons-bon-sens.md) et le même jugement (combinaisons.resumer).
Aucun modèle de langue : gratuit.

Questions, pour chaque pays et chaque premier du mois d0 (de 2024-09-01 au dernier mois dont les 30 jours suivants
sont collectés) ; fenêtre « avant » = [d0 − 30 j, d0), fenêtre « après » = [d0, d0 + 30 j) :
  manifestations  (famille mobilisation, M4 = 0) : plus de manifestations après qu'avant ? posée si ≥ 10 avant
  émeutes         (famille mobilisation, M4 = 1) : plus d'émeutes après qu'avant ?           posée si ≥ 5 avant
  force           (famille stratégique)          : plus de démonstrations de force (racine CAMEO 15, tout acteur)
                                                   visant le pays après qu'avant ?           posée si ≥ 5 avant
Chaque fenêtre doit avoir au plus 3 jours GDELT manquants.

B (taux de base) : pour le même pays et le même type de question, part des mois antérieurs où la question a été
« oui » parmi les mois où la question se posait (même seuil), comptée seulement sur les mois dont la fenêtre « après »
se termine avant d0, lissée (k + 1) / (n + 2).
Aucune information postérieure à d0.

Mécanismes : calculés à d0 par combinaisons.etats (mêmes seuils), donc avec des données antérieures à d0.

Exploration : d0 avant le 2025-11-01 ; confirmation : à partir du 2025-11-01. Les deux bancs (ForecastBench et
celui-ci) jugent la même grille : le risque de chacun est divisé par deux en plus.

RÉSERVES déclarées avant tout passage :
- l'issue vient de GDELT (presse codée automatiquement), pas d'ACLED : plus bruitée ;
- pour M11, l'indicateur (voisins) et l'issue (le pays) viennent de la même presse : un regain d'attention médiatique
  pour une région gonfle les deux. Aucun volume de presse total par pays n'est collecté pour le contrôler ;
- les questions d'un même mois sont corrélées : le bootstrap tire des mois entiers.

Registre : registre/combinaisons-gdelt.jsonl (une ligne par question, réécrit à chaque passage) ;
résumé : registre/combinaisons-gdelt.json.

    python combinaisons_gdelt.py
"""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import combinaisons as cb
import indicateurs_niche as ni

REGISTRE = Path("registre")
FICHIER = REGISTRE / "combinaisons-gdelt.jsonl"
RESUME = REGISTRE / "combinaisons-gdelt.json"
COUPURE = "2025-11-01"
DEBUT = date(2024, 9, 1)
FENETRE = 30
MANQUE_MAX = 3
MIN_AVANT = {"manifestations": 10, "emeutes": 5, "force": 5}
FAMILLE = {"manifestations": "mobilisation", "emeutes": "mobilisation", "force": "strategique"}


def charger() -> tuple[dict, set[str], set[str]]:
    """({(type, pays): {jour: compte}}, jours couverts manifestations, jours couverts paires)."""
    c: dict = {}
    for x in csv.DictReader(ni.GDELT_COMPTES.open(encoding="utf-8")):
        c.setdefault(("manifestations", x["pays"]), {})[x["jour"]] = int(x["manifestations"])
        c.setdefault(("emeutes", x["pays"]), {})[x["jour"]] = int(x["emeutes"])
    for x in csv.DictReader(ni.PAIRES_JOUR.open(encoding="utf-8")):
        f = int(x["force"])
        if f:
            d = c.setdefault(("force", x["b"]), {})
            d[x["jour"]] = d.get(x["jour"], 0) + f
    jm = set(ni.GDELT_JOURS.read_text(encoding="utf-8").split())
    jp = set(ni.PAIRES_JOURS.read_text(encoding="utf-8").split()) if ni.PAIRES_JOURS.exists() else set()
    return c, jm, jp


def somme(serie: dict, debut: date, n: int, couverts: set[str]) -> int | None:
    jours = [(debut + timedelta(days=k)).isoformat() for k in range(n)]
    if sum(1 for j in jours if j not in couverts) > MANQUE_MAX:
        return None
    return sum(serie.get(j, 0) for j in jours)


def mois(debut: date, fin: date) -> list[date]:
    out, d = [], debut
    while d <= fin:
        out.append(d)
        d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    return out


def questions(comptes: dict, jm: set[str], jp: set[str], dernier_jour: date) -> list[dict]:
    """Questions fabriquées, avec issue et B ; sans les mécanismes."""
    ancres = mois(DEBUT, dernier_jour - timedelta(days=FENETRE))
    out = []
    for (typ, pays), serie in sorted(comptes.items()):
        couverts = jp if typ == "force" else jm
        histo: list[tuple[date, int]] = []                     # (fin de la fenêtre « après », issue)
        for d0 in ancres:
            avant = somme(serie, d0 - timedelta(days=FENETRE), FENETRE, couverts)
            apres = somme(serie, d0, FENETRE, couverts)
            if avant is None or apres is None:
                continue
            issue = int(apres > avant)
            if avant >= MIN_AVANT[typ]:
                connus = [y for fin, y in histo if fin <= d0]
                p_b = (sum(connus) + 1) / (len(connus) + 2)
                out.append({"jeu": d0.isoformat(), "question_id": f"gdelt:{d0}:{typ}:{pays}", "pays": pays,
                            "cca2": pays, "type": typ, "famille": FAMILLE[typ], "avant": avant, "apres": apres,
                            "issue": issue, "p_B": round(p_b, 4), "n_histoire": len(connus)})
                histo.append((d0 + timedelta(days=FENETRE), issue))   # B : seulement les mois où la question se posait
    return out


def principal() -> int:
    if not ni.GDELT_COMPTES.exists() or not ni.PAIRES_JOUR.exists():
        print("Comptes GDELT absents.")
        return 1
    cache_riv: dict = {}
    brut = ni.rivalites
    ni.rivalites = lambda d0: cache_riv.setdefault((d0.year, d0.month), brut(d0))
    comptes, jm, jp = charger()
    dernier = date.fromisoformat(max(jm))
    debut_el = None
    if ni.ELECTIONS.exists():
        ds = [x["date"] for x in csv.DictReader(ni.ELECTIONS.open(encoding="utf-8"))]
        debut_el = min(ds) if ds else None
    qs = questions(comptes, jm, jp, dernier)
    print(f"{len(qs)} questions fabriquées ({DEBUT} → {dernier}) ; calendrier électoral depuis {debut_el}")
    cache: dict = {}
    REGISTRE.mkdir(exist_ok=True)
    with FICHIER.open("w", encoding="utf-8") as fo:
        for x in qs:
            cle = (x["cca2"], x["jeu"])
            if cle not in cache:
                cache[cle] = cb.etats(x["cca2"], "", date.fromisoformat(x["jeu"]), debut_el)
            x["etats"] = dict(cache[cle], M4=1 if x["type"] == "emeutes" else (0 if x["type"] == "manifestations" else None))
            fo.write(json.dumps(x, ensure_ascii=False) + "\n")
    r = cb.resumer(qs, coupure=COUPURE, k_bancs=2)
    r["source"] = "questions fabriquées sur les comptes GDELT (combinaisons_gdelt.py)"
    r["oui_par_type"] = {t: [sum(x["issue"] for x in qs if x["type"] == t), sum(1 for x in qs if x["type"] == t)]
                         for t in MIN_AVANT}
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    texte = [f"## Combinaisons de mécanismes, questions fabriquées (GDELT)\n",
             f"{r['questions']} questions ({r['exploration']} en exploration, {r['confirmation']} en confirmation) ; "
             f"{r['k_juges']} paires × familles jugées ; risque corrigé {r['risque_corrige']}.\n",
             "| Paire | Famille | Bon sens | Cases « les deux » (expl. / conf.) | Interaction (expl. / conf.) | Perte B → ajustée | Verdict |",
             "|---|---|---|---|---|---|---|"]
    for p in r["paires"]:
        texte.append(f"| {p['paire']} | {p['famille']} | {p['bon_sens']} | {p['exploration']['11']} / "
                     f"{p['confirmation']['11']} | {p.get('interaction_exploration', '—')} / "
                     f"{p.get('interaction_confirmation', '—')} | "
                     f"{str(p['perte_B']) + ' → ' + str(p['perte_ajustee']) if 'verdict' in p else '—'} | "
                     f"{p.get('verdict', 'non jugeable')} |")
    v = r["valeur_du_bon_sens"]
    texte.append(f"\nValeur du bon sens : {v['part_confirmees']} des {v['plausibles_jugees']} paires plausibles "
                 f"confirmées, contre {v['part_confirmes']} des {v['temoins_juges']} témoins.")
    print("\n".join(texte))
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fo:
            fo.write("\n".join(texte) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
