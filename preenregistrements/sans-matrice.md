# Pré-enregistrement — ombre « sans matrice » (bot 0.10.91)

**Décision d'auteur du 2026-11-14**, à mi-parcours de l'apprentissage des liens, « à condition que ce changement soit
réellement utile pour la suite ». Critère entré dans le code au commit `3e4efa5`, avant toute lecture sans matrice.

## Constat (registre, lecteur Mistral Medium, banc ForecastBench)
- 93 % des cartes ancrées dans la strate de l'événement (353 sur 378) sont des cartes que la matrice donne comme
  faisant apparaître la carte visée ; 93 % des candidates du plan aussi (393 sur 423). Au hasard, ce serait de l'ordre
  d'un quart.
- 32 lectures « CROISSANCE apparaît » sur 41 ancrent le même jeu (ÉMERGENCE, POLARITÉ, RÉCURSIVITÉ, RÉSONANCE, ou
  trois d'entre elles) : exactement les parents de CROISSANCE dans la matrice.
- Cause : la consigne du plan montre la matrice et dit « choisis au moins N candidates parmi ces cartes ». Le lecteur
  ancre ensuite les candidates.
- Conséquences : la surconfiance de C est en partie fabriquée ; l'apprentissage des liens ne peut observer aucun lien
  hors de la matrice, ni départager des cartes toujours ancrées ensemble.

## Ce que fait l'ombre
Sur une part des questions (`ALPHABET_SANS_MATRICE_TAUX` ; 1 au banc par défaut, 0 au tournoi) :
1. un second plan, sans la matrice ni la règle qui y fait choisir, propose 2 à 4 candidates par strate **d'après les
   faits** ; l'événement, les strates et les recherches du plan officiel sont gardés ;
2. une seconde lecture sur le **même corpus**, avec les étiquettes de cartes retirées des résultats montrés ;
3. réparateur, contrôles, moteur ; résultat dans `ombre_sans_matrice`, lecture brute dans le rejeu.
La lecture officielle, le p posté et l'apprentissage officiel ne changent pas.

## Critère d'utilité (mesuré par `score_registre`, sur les 50 premières lectures sans matrice)
- **Utile** : la part des parents de la matrice parmi les cartes ancrées (strate de l'événement) tombe à **60 % ou
  moins** (contre 93 % officiellement).
- **Inutile** : **80 % ou plus** ; l'ombre s'arrête (taux remis à 0).
- Garde-fou : les états nuls et refus de l'ombre ne dépassent pas ceux de l'officiel de plus de **15 points**.
- Entre 60 et 80 % : indécis ; un second regard sur les 100 premières (0.10.98), puis clos.

## Suite si « utile »
Apprentissage des liens en parallèle sur ces lectures (`apprentissage_liens.py --lecture sans_matrice`), même
protocole. Remplacer la lecture officielle serait une décision d'auteur datée.

## Limites déclarées
- Le corpus reste celui cherché pour les candidates officielles.
- La fiche d'index des cartes et l'exemple de dossier restent montrés aux deux lectures.
- Coût : deux appels de plus par question lue.

## Écart de protocole (2026-11-14, bot 0.10.99) — déclaré AVANT le calcul du résultat
Premier passage (bot 0.10.97, exécution 43617116754, jeu 2026-09-27) : 48 lectures sans matrice, dont **9 refusées
(19 %)** contre 0 pour la lecture officielle. Cause : la lecture officielle a droit à deux corrections quand le contrôle
la refuse ; l'ombre n'en avait aucune. Les refus étaient de ceux que la correction rattrape (carte de l'événement
ancrée pour un « apparaît » : 5 ; format de date ou d'adresse : 3 ; question renvoyant à deux cartes absentes : 1).
Le garde-fou « refus » aurait jugé le banc de test, pas l'absence de matrice.

Décision d'auteur, prise **avant** que la part de cartes de la matrice ne soit calculée sur ces lectures : l'ombre
reçoit la même boucle de correction que l'officiel (0.10.99), et le **compte repart à zéro** : le premier regard porte
sur les 50 premières lectures écrites par le bot 0.10.99 ou plus récent. Les 48 lectures antérieures sont rapportées à
part (`avant_ecart_de_protocole`), sans verdict.
