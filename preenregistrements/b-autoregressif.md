# Pré-enregistrement — B autorégressif pour les séries (bot 0.10.92 ; critère 0.10.97)

**Décision d'auteur du 2026-11-14.** Le but n'est pas de prouver C contre B mais de trouver la meilleure prévision ;
le taux de base lui-même est challengé. Règle entrée dans le code au commit `8394e21`, critère au commit `84ab44f`.

## La règle (fixée avant toute mesure, `banc_forecastbench.b_ar`)
Pour les questions de séries (FRED, DBnomics) : mêmes points que B (5 ans, strictement avant la date d'information) ;
AR(1) à constante sur les différences, φ borné à ±0,95 ; loi gaussienne de la somme des k variations à venir (k =
horizon / écart médian entre observations) ; P(hausse) = (1 − part des intervalles sans changement) ×
Φ(moyenne / écart-type) ; borné à 0,001–0,999.

## Test rétrospectif (2026-11-14, exécution 43611855888)
188 questions de séries déjà résolues, jeux 2026-09-27, 2026-10-11 et 2026-10-25.
- Perte log : B_AR 0,666, B 0,690 ; écart −0,024 ; intervalle à 90 % : [−0,043 ; −0,005] par question,
  [−0,043 ; −0,002] par blocs (5 blocs).
- Par bloc : FRED 10-25 0,691 → 0,628 (l'essentiel du gain) ; FRED 10-11 0,722 → 0,696 ; FRED 09-27 0,633 → 0,616 ;
  DBnomics 09-27 0,666 → 0,650 ; DBnomics 10-11 0,688 → 0,696 (moins bon).
- Les deux sont proches du pile ou face (0,693) ; φ moyen ≈ 0,015.
- Toutes ces données ont été vues : ce test ne peut plus servir de jugement.

## Critère d'adoption (`score_registre.critere_b_ar`)
Sur les **100 premières questions de séries de jeux non vus** par le test (autres que 2026-09-27, 10-11, 10-25) :
1. perte log de B_AR inférieure à celle de B ;
2. intervalle de l'écart (bootstrap par blocs « jeu × source », 2 000 tirages, graine 0) entièrement sous 0, au niveau
   corrigé de la règle d'adoption commune (96,7 % tant que trois essais à intervalle sont ouverts).
Second regard possible sur les 200 premières, au risque partagé. Si le critère tient : décision d'auteur datée pour
poster B_AR à la place de B sur les séries. Sinon, B reste.
