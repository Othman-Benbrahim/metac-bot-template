---
license: cc-by-sa-4.0
language: [en]
task_categories: [text-classification]
tags: [forecasting, judgmental-forecasting, base-rates]
pretty_name: Questions de jugement résolues (alphabet situationnel)
---
# Questions de jugement résolues — v0

Questions de prévision « de jugement » (lois, élections, décisions, échéances) posées sur Metaculus, Manifold,
Polymarket et INFER, avec leur issue (1 = oui, 0 = non). Construit par le projet « alphabet situationnel »
(visiondufutur.com) à partir de ForecastBench.

- Lignes : 3651 (une par question et par date de jeu) ; questions distinctes : 1878.
- Parties : apprentissage = jeux avant le 2026-01-01 (1790 lignes) ; test = à partir du 2026-01-01 (1861 lignes).
- Part de « oui » : 21.6%.

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
