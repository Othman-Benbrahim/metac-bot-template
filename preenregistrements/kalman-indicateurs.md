# Niveau et tendance (filtre de Kalman) contre le modèle actuel des indicateurs lents (préenregistrement, 2026-11-21)

Décision de l'auteur (2026-11-21, 12 h 53) : intégrer les pistes tirées de Learning Bayesian Statistics (épisode 124,
Jesse Grabowski, modèles espace d'états). L'invité dit lui-même que le simple bat souvent le complexe : on teste.

## Rasoir d'Ockham
1. Une phrase : un indicateur a un niveau et une pente qui dérivent lentement ; les suivre fait une meilleure
   distribution de la prochaine valeur que « dernière valeur + un écart passé ».
2. Paramètres : trois variances, estimées à chaque date sur les 60 dernières valeurs (aucun réglage à la main).
3. Sens fixé d'avance : aucun ; le modèle actuel est déjà calibré (couverture 0,751 et 0,610 sur Tokyo).
4. Domaine : prochaine publication (un pas) des séries déjà branchées : chômage, confiance des ménages, inflation et
   inflation sous-jacente américaines (FRED), inflation de Tokyo hors produits frais (e-Stat).
5. Plus simple ? Le modèle actuel est plus simple ; il reste en service sauf preuve contraire.

## Données et méthode (fixées)
Mêmes séries et mêmes dates que les essais `indicateurs-lents.md` et `inflation-tokyo.md` (Tokyo : 2006-01 à
2026-09, base 2025). À chaque date, les deux modèles prévoient la valeur suivante avec la seule histoire passée.
Score : CRPS (règle propre qui juge toute la distribution). Script `mise_au_point/kalman_indicateurs_essai.py`.
Aucun appel de modèle. Lancé une fois.

## Critère (fixé)
Écart relatif de CRPS sur l'ensemble des séries (Kalman / actuel − 1), intervalle à 90 % par bootstrap par blocs de
12 mois de chaque série (les erreurs voisines se ressemblent). Adopté si l'intervalle est entièrement sous 0 : le
Kalman remplace alors le modèle actuel pour ces séries, aux mêmes conditions de branchement (option 2 : seulement sans
consensus d'experts dans la recherche). Sinon rien ne change. Couvertures et détail par série : descriptifs.

## Limite connue d'avance
Le Kalman suppose des chocs gaussiens ; une rupture brusque (2020, 2022) le pénalise. Les années récentes pèsent autant
que les anciennes.

## Résultat (2026-11-21, run 44905356688) : le Kalman fait PIRE, le modèle actuel reste
666 prévisions sur cinq séries. CRPS : actuel 0,580, Kalman 0,621 ; écart relatif +7,1 %, intervalle à 90 %
[+1,3 % ; +14,6 %], entièrement au-dessus de 0 : le Kalman est nettement moins bon. Par série : chômage +92 % (le
choc de 2020 gonfle ses variances, fourchettes trop larges ensuite : 92 % des valeurs dans l'intervalle à 80 %),
confiance des ménages ≈ égalité, inflation +4 %, inflation sous-jacente −4 % (non significatif), Tokyo +5 %.
Couvertures : le Kalman élargit ses fourchettes (0,811 et 0,652 contre 0,764 et 0,583). Lecture : comme le disait
l'invité de l'épisode, le simple bat le complexe ici ; la distribution des écarts passés suit mieux les ruptures
qu'un modèle à chocs gaussiens. Rien ne change dans le bot.
