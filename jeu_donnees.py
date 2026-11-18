"""Jeu de données ouvert des questions de jugement résolues (bot 0.10.267), sans aucun modèle de langue.

Décision d'auteur du 2026-11-18, 14 h 48 (« d'accord, je valide ») : construire d'abord le jeu brut, gratuit, en
Python seul (perspective : publication sur Hugging Face par l'auteur, puis entraînement d'un modèle propre).
Source : ForecastBench (Forecasting Research Institute), CC BY-SA 4.0 ; le jeu dérivé garde la même licence.

Une ligne par question et par jeu (date à laquelle la question était posée) ; la première apparition est marquée.
Colonnes calculées par le code, sans fuite (voisines closes et résolues avant le jeu, cohorte complète) :
forme, tranche d'horizon, taux de la plateforme (R0), taux plateforme × forme × horizon (R1), taux des questions
semblables (S, TF-IDF). JAMAIS de prévision de foule ni de cote (freeze_datetime_value n'est pas récolté), aucun
texte d'article. Partie « apprentissage » / « test » coupée dans le temps (jeu avant ou après COUPURE).

    python jeu_donnees.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import alphabet_pipeline as ap
import banc_jugement as bj

VERSION = "v0"
RACINE = Path("donnees/jeu-jugement")
COUPURE = "2026-01-01"
COLONNES = ["source", "id", "jeu", "premiere_apparition", "partie", "titre", "forme", "horizon_jours", "tranche",
            "cloture", "resolue_le", "issue", "taux_plateforme_R0", "taux_forme_horizon_R1", "taux_semblables_S"]

FICHE = """---
license: cc-by-sa-4.0
language: [en]
task_categories: [text-classification]
tags: [forecasting, judgmental-forecasting, base-rates]
pretty_name: Questions de jugement résolues (alphabet situationnel)
---
# Questions de jugement résolues — {version}

Questions de prévision « de jugement » (lois, élections, décisions, échéances) posées sur Metaculus, Manifold,
Polymarket et INFER, avec leur issue (1 = oui, 0 = non). Construit par le projet « alphabet situationnel »
(visiondufutur.com) à partir de ForecastBench.

- Lignes : {n} (une par question et par date de jeu) ; questions distinctes : {d}.
- Parties : apprentissage = jeux avant le {coupure} ({na} lignes) ; test = à partir du {coupure} ({nt} lignes).
- Part de « oui » : {oui:.1%}.

## Colonnes
| Colonne | Sens |
|---|---|
| source, id | plateforme et identifiant de la question |
| jeu | date à laquelle la question était posée (information disponible jusqu'à ce jour) |
| premiere_apparition | 1 pour la première date où la question apparaît |
| partie | apprentissage ou test (coupure dans le temps) |
| titre | texte de la question |
| forme, tranche, horizon_jours | forme de la question (échéance, élection, justice, seuil, autre), horizon |
| cloture, resolue_le, issue | clôture prévue, date de résolution, issue |
| taux_plateforme_R0 | part de « oui » de la plateforme, sur les questions closes avant le jeu |
| taux_forme_horizon_R1 | idem par plateforme, forme et tranche d'horizon |
| taux_semblables_S | part de « oui » des 50 questions les plus semblables (mots communs), closes avant le jeu |

Les taux sont calculés sans fuite : seules comptent les questions closes ET résolues avant la date du jeu, et
seules les questions dont la clôture est passée depuis au moins 30 jours figurent (biais de censure corrigé).

## Ce que ce jeu ne contient pas
Aucune prévision de foule ni cote de marché ; aucun texte d'article ; aucune donnée personnelle.

## Avertissement pour l'entraînement
Un modèle dont les connaissances couvrent les dates des questions peut connaître leur issue : n'évaluer que sur
des questions postérieures à la date de fin des connaissances du modèle, et respecter la coupure dans le temps.

## Licence et source
CC BY-SA 4.0. Source : ForecastBench, Forecasting Research Institute (Karger et al., arXiv 2409.19839).
"""


def construire() -> list[dict]:
    xs = [json.loads(l) for l in bj.REGISTRE.read_text(encoding="utf-8").splitlines() if l.strip()]
    xs = bj.cohorte_complete(xs)
    bj.calculer(xs)
    vus, lignes = set(), []
    for x in sorted(xs, key=lambda x: (x["source"], x["id"], x["jeu"])):
        cle = (x["source"], x["id"])
        lignes.append({"source": x["source"], "id": x["id"], "jeu": x["jeu"], "premiere_apparition": int(cle not in vus),
                       "partie": "apprentissage" if x["jeu"] < COUPURE else "test", "titre": x["titre"],
                       "forme": x["forme"], "horizon_jours": x["horizon"], "tranche": x["tranche"],
                       "cloture": x.get("cloture", ""), "resolue_le": x["resolue_le"], "issue": x["issue"],
                       "taux_plateforme_R0": round(x["p_R0"], 4), "taux_forme_horizon_R1": round(x["p_R1"], 4),
                       "taux_semblables_S": round(x["p_S"], 4)})
        vus.add(cle)
    return lignes


def principal(version: str = VERSION) -> int:
    """0.10.270 : version donnée en argument (la publication mensuelle utilise « AAAA-MM »)."""
    DOSSIER = RACINE / version
    ls = construire()
    DOSSIER.mkdir(parents=True, exist_ok=True)
    with (DOSSIER / "questions.jsonl").open("w", encoding="utf-8") as f:
        for l in ls:
            f.write(json.dumps(l, ensure_ascii=False) + "\n")
    with (DOSSIER / "questions.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLONNES)
        w.writeheader()
        w.writerows(ls)
    n = len(ls)
    (DOSSIER / "README.md").write_text(FICHE.format(
        version=version, n=n, d=sum(l["premiere_apparition"] for l in ls), coupure=COUPURE,
        na=sum(l["partie"] == "apprentissage" for l in ls), nt=sum(l["partie"] == "test" for l in ls),
        oui=sum(l["issue"] for l in ls) / n), encoding="utf-8")
    print(f"{n} lignes, {sum(l['premiere_apparition'] for l in ls)} questions distinctes → {DOSSIER}")
    return 0


if __name__ == "__main__":
    import argparse
    a = argparse.ArgumentParser()
    a.add_argument("--version", default=VERSION)
    sys.exit(principal(a.parse_args().version))
