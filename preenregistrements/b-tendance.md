# Pré-enregistrement — taux de base récent (tendance), séries (bot 0.10.131)

**Décision d'auteur du 2026-11-15 (13 h 51)** : « Prépare l'étape 2 ». Commité AVANT tout calcul de B_tendance.

## Constat
Le garde-fou sur B (`audit_b.py`, 1 089 questions) ne signale qu'un défaut hors l'erreur ACLED corrigée : questions
« l'écart de crédit (option-adjusted spread) aura-t-il augmenté ? » (FRED), B annonce 40 %, 75 % observés, même sens
dans 7 jeux sur 9. B compte les hausses sur 5 ans et ignore la tendance des dernières semaines.

## Différence avec le B autorégressif (clos, non adopté)
Le B autorégressif modélisait l'inertie d'un pas au suivant, partout. Ici : le même comptage que B, en pesant les
intervalles récents, et SEULEMENT sur les séries assez fréquentes pour que les semaines récentes portent de
l'information (la bonne règle au bon endroit).

## Règle (fixée ici, `banc_forecastbench.b_tendance`)
- Mêmes intervalles de h jours que B (5 ans, strictement avant D, même appariement).
- Poids de chaque intervalle : 2^(−âge / 90), âge = jours entre la fin de l'intervalle et D.
- P = (Σ poids × hausse + ½) / (Σ poids + 1).
- Appliqué seulement si Σ poids ≥ 20 ; sinon B reste (question non comptée).

## Questions
Questions de séries FRED et DBnomics de ForecastBench résolues, jeux postérieurs au 2026-07-01, où B_tendance
s'applique, **hors forme « option-adjusted spread »** (elle a motivé l'essai : décrite à part, sans verdict). Ordre
entrelacé fixé d'avance (rang SHA-1 de l'identifiant dans son jeu, puis jeu). Ces questions ont déjà servi à d'autres
essais sur B (autorégressif, saisonnier) ; B_tendance n'y a jamais été calculé.

## Critère (règle d'adoption commune, niveau corrigé ; second regard à 200)
**`b_tendance`** : sur les 100 premières questions, perte log de B_tendance inférieure à celle de B, intervalle de
l'écart (bootstrap par blocs « jeu × source ») entièrement sous 0.

## Limites déclarées
Une tendance des derniers mois peut se retourner : la règle peut perdre sur les séries qui oscillent. Les questions
d'un même jeu sont corrélées (mouvements de marché communs) ; le bootstrap par blocs en tient compte.
