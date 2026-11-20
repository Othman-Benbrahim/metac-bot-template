# Inflation de Tokyo : prochaine publication (préenregistrement, 2026-11-20, 21 h 45)

This service uses API functions from e-Stat, however its contents are not guaranteed by government.

Décision de l'auteur (21 h 10) : e-Stat accepté avec une clé gratuite en secret. Mécanisme déjà adopté pour les séries
américaines (`preenregistrements/indicateurs-lents.md`, 461 publications, 0,785 / 0,586), appliqué tel quel.

## Données
Variation sur un an de l'indice des prix hors produits frais (生鮮食品を除く総合, 前年同月比), arrondissements de Tokyo
(東京都区部), table base 2025 d'e-Stat (0004052037), série publiée raccordée de 1971 à 2026-10
(`registre/estat-tokyo-cpi.csv`, colonne base = 2025). C'est la base sur laquelle se résolvent les questions à venir.
Écart observé avec la base 2020 sur 2026 : au plus 0,2 point.

## Modèle (fixé, identique aux séries américaines)
Prochaine valeur = dernière valeur + quantiles empiriques des 36 dernières variations d'un mois au suivant
(`indicateurs_lents.fourchette_suivante`, h = 1).

## Calibrage (fixé)
Ancrage chaque mois de 2006-01 à 2026-09 (prévision du mois suivant). Critère : intervalle 80 % entre 0,75 et 0,85,
intervalle 60 % entre 0,55 et 0,65. Aucun réglage. Les mois touchés par une hausse de TVA (avril 2014, octobre 2019)
et leurs sorties un an après restent dans l'épreuve. Lancé une fois (`mise_au_point/inflation_tokyo_essai.py`).

## Résultat (2026-11-20, 21 h 46) : critère atteint
249 prévisions (2006-2026). Intervalle 80 % → 0,751 ; intervalle 60 % → 0,610. Dans les bornes (80 % de justesse,
du côté étroit).

## Règle d'application (0.10.407, décision de l'auteur du 2026-11-20, 22 h 01)
Comme pour le chiffre d'affaires (option 2) : le modèle ne remplace la réponse du bot que si la recherche du bot ne
contient pas de consensus des économistes ; sinon le bot garde sa réponse et le modèle est scellé en ombre
(`indicateur_ombre` dans le journal), pour comparaison à la résolution.
