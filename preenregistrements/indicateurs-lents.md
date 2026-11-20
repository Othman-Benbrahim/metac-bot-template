# Indicateurs qui bougent lentement : fourchette de la prochaine publication (préenregistrement, 2026-11-20, 21 h)

Décision de l'auteur (20 h 56) : traiter les indicateurs lents (inflation de Tokyo, sondage Gallup en Corée) et les
résultats d'entreprise, en cherchant parmi les sources disponibles.

## Modèle (fixé)
Fourchette de la prochaine publication = dernière valeur publiée + quantiles empiriques des variations entre deux
publications successives (36 dernières ; au moins 18). C'est la marche au hasard empirique, référence habituelle des
prévisions à une période (un indicateur lent bouge peu d'une publication à l'autre ; persistance).

## Calibrage (fixé)
Séries mensuelles FRED déjà collectées : chômage américain (UNRATE), confiance des ménages (UMCSENT), inflation sur un an
(CPIAUCSL) et inflation sous-jacente sur un an (CPILFESL), 2015-2026. Pour chaque mois, fourchette de la publication
suivante ; part des valeurs réelles dans l'intervalle 80 % et 60 %. Critère sur l'ensemble : 0,75-0,85 et 0,55-0,65.
Les séries de la question elle-même (inflation de Tokyo, Gallup Corée) seront vérifiées à part quand leurs données
seront collectées.

## Résultat (2026-11-20, 21 h 05) : critère atteint
461 publications (quatre séries). Intervalle 80 % → 0,785 ; 60 % → 0,586. Chômage 0,835 et 0,636 ; confiance 0,803 et
0,574 ; inflation 0,761 et 0,587 ; inflation sous-jacente 0,734 et 0,541 (un peu étroit).
Branché en 0.10.404 pour les questions numériques sur ces séries américaines (prochaine publication), distribution du bot
scellée à côté. Inflation de Tokyo : série non collectée (e-Stat demande une clé gratuite). Gallup Corée : la page
Wikipédia des sondages a environ deux mois de retard ; utilisable pour l'historique, pas pour la dernière valeur.

## Règle d'application (0.10.407, décision de l'auteur du 2026-11-20, 22 h 01)
Comme pour le chiffre d'affaires (option 2) : le modèle ne remplace la réponse du bot que si la recherche du bot ne
contient pas de consensus des économistes ; sinon le bot garde sa réponse et le modèle est scellé en ombre
(`indicateur_ombre` dans le journal), pour comparaison à la résolution.
