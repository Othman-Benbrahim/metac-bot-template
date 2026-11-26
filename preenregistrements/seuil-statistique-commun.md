# Seuil d'une statistique : fréquence de franchissement commune (procédure écrite avant tout calcul)

Décision de l'auteur, 2026-11-26, 16 h 07 : « les deux » (élections et cette version). Suite du banc
`seuil-statistique.md` : la référence (fréquence de franchissement d'un même pas sur les autres séries) y a battu la
marche aléatoire propre à chaque série. Elle a gagné sur les mêmes données qui la font choisir : il faut une épreuve
neuve, dans le temps.

## Règle candidate
Pour une question « la série S dépassera-t-elle (ou passera-t-elle sous) T dans h mois ? » : P = part des fois où un pas
de même taille (même cran, même nature : taux en points, niveau en pourcentage) et même horizon a été franchi sur les
AUTRES séries, en n'utilisant que les données ANTÉRIEURES au mois de la question.

## Épreuve dans le temps
Mêmes séries, mêmes crans, mêmes horizons que `seuil-statistique.md`. Table de fréquences apprise sur les questions dont
le mois cible t+h est avant le 2022-01-01 ; épreuve sur les questions dont le mois de départ t est à partir du
2022-01-01 (après le choc de 2020-2021, pendant le pic d'inflation : épreuve dure, déclarée).
Concurrents sur l'épreuve :
1. la fréquence commune apprise avant 2022 ;
2. la marche aléatoire propre à la série (règle du banc précédent) ;
3. la part de oui constante de l'apprentissage (tous crans confondus), comme plancher.

## Décision (une passe)
La fréquence commune est retenue si elle bat les deux autres sur l'épreuve, sur l'ensemble ET sur au moins deux tiers
des séries. Elle deviendrait alors la brique des seuils de statistiques (branchement : décision de l'auteur), avec les
mêmes crans ; un seuil hors des crans prend le cran le plus proche (interpolation linéaire entre crans).

## Résultat du passage unique (2026-11-26, vers 16 h 25)
Apprentissage 18 336 questions (cible avant 2022), épreuve 23 584 (départ à partir de 2022).
- Épreuve, perte log : fréquence commune 0,4904 ; marche aléatoire propre à la série 0,4771 ; constante 0,5359.
- La fréquence commune ne bat les deux autres que sur 5 séries sur 14. **Non retenue.**
- Lecture : sur la période récente, c'est la marche aléatoire propre à chaque série qui fait le mieux, l'inverse du banc
  précédent (calculé sur toute la période). Les deux règles battent nettement la constante (0,48-0,49 contre 0,54), mais
  aucune ne domine l'autre de façon stable : l'avantage change selon la période. Aucune ne passe son propre critère.
