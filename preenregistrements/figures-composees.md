# Préenregistrement : figures composées (compétition, intention, convention) dans le lecteur
2026-11-22, commit 0.10.428, écrit avant tout calcul avec ces figures.

Décision d'auteur du 2026-11-22, 5 h 07 et 5 h 16 : les structures manquantes « ne rentrent pas dans le cadre des
universaux établis à la fois anthropologiquement et mathématiquement » ; ce sont des règles induites ; les introduire
comme lettres déséquilibrerait l'alphabet. Elles ne seront admises « qu'à une condition, si elles prouvent leur utilité
dans le lecteur ». Donc : AUCUNE nouvelle carte. Trois FIGURES, écrites comme compositions de cartes existantes.

## Ce qui motive le banc (données déjà au registre, lues le 2026-11-22 à 5 h 14)
Banc de couverture étendue (registre/banc-couverture-etendue.jsonl), arrêté par l'auteur le 19 novembre à 51
situations utiles, titres seuls. Avec les candidates disponibles : COMPÉTITION κ = 0,843 entre codeurs, INTENTION
0,385, CONVENTION 0,251 (règle de passage du préenregistrement cartes-candidates-ombre : atteinte pour les trois) ;
CAPACITÉ 0,187 et MARCHÉ trop rare : non retenues ici. La meilleure des 16 cartes plafonnait à 0,373. Quand les
candidates sont offertes, elles remplacent des cartes existantes (HIÉRARCHIE chez gpt 29 → 16 ; SEUIL chez Haiku
37 → 3 ; CONTRAINTE 26 → 10) : chaque codeur recomposait la structure avec des lettres différentes. Hypothèse :
nommer la composition rend la lecture commune et utile, sans toucher aux lettres.

## Les trois figures (définies ici, par leurs composants ; aucune donnée de ce banc ne les a façonnées)
- COMPÉTITION = CONTRAINTE (la ressource ou la position ne peut revenir à toutes les parties) + HIÉRARCHIE (la règle
  d'attribution — vote, score, classement, combat, enchère — produit un ordre entre les parties) ; avec POLARITÉ quand
  les parties sont deux.
- INTENTION = HIÉRARCHIE (un acteur identifiable occupe la position qui décide l'issue) + INCERTITUDE (pour les autres,
  son choix reste indéterminé) + l'absence d'une CONTRAINTE qui dicterait ce choix.
- CONVENTION = ÉMERGENCE (une régularité collective acceptée) ou HIÉRARCHIE (une autorité qui déclare) + une règle
  (CONTRAINTE formelle) : le fait existe parce qu'il est accepté ou déclaré, et peut changer par décision sans que rien
  de matériel ne bouge (Searle 1995).

## Plan
Questions : celles du banc jugement_alphabet (Metaculus, 2026, cohorte complète, résolues), non exclues, dans l'ordre
fixé de ce banc, avec recherche gelée seulement (aucune recherche neuve). Mêmes entrées que la matriochka M.
Pour chaque question, gpt-5-mini (Azure), température 0,2 :
1. NOTES : un appel qui note les sept critères de M (consigne inchangée) PLUS les trois figures, chacune de 1 à 4 avec
   sa composition écrite et une justification ; pour chaque figure, 1 = absente, 4 = présente et décisive pour l'issue,
   avec le SENS (vers OUI ou vers NON) ;
2. M7 : le jugement final de M (consigne inchangée) avec les sept notes seules ;
3. M10 : le même jugement final avec les sept notes et les trois figures.
M7 et M10 partagent les MÊMES sept notes : l'écart ne vient que des figures.
Sur les 60 premières questions seulement : un second appel NOTES de gpt-5-mini (stabilité) et un appel NOTES de Claude
Haiku 4.5 (accord entre modèles, si les crédits Bedrock sont encore actifs ; sinon rapporté comme manquant).

## Critères (fixés)
1. UTILITÉ (essai figures_composees, celui qui décide) : perte log M10 − M7 ; verdict sur les 150 premières questions
   admissibles (second regard à 300), intervalle à 90 % de l'écart par bootstrap par question entièrement sous 0, au
   risque corrigé pour le nombre d'essais ouverts (score_registre.critere_ombre_b, bloc_par="question").
2. ACCORD (descriptif) : κ pondéré quadratique par figure, R1-R2 et R1-X ; lu avec les seuils du banc accord-lecteur
   (stabilité 0,6 / 0,4 ; accord 0,4 / 0,2).
3. Rapportés : perte de M7 et de M10 contre B (semblables) ; discrimination ; part des notes « 1 » par figure.

## Ce qu'une réussite permet, et ce qu'elle ne permet pas
Réussite = la condition de l'auteur remplie pour l'ensemble des trois figures : elles PEUVENT entrer dans le lecteur
par décision d'auteur datée, comme figures composées, jamais comme lettres. Échec ou non tranché : elles restent en
ombre. Aucune carte n'est ajoutée ni retirée par ce banc ; rien dans le bot.

## Limites connues
Les questions ont déjà servi au banc jugement_alphabet (M contre A) ; les figures, elles, n'y ont jamais été lues, et
leurs compositions viennent de définitions, non de ces issues. Un seul lecteur pour l'utilité (gpt-5-mini).
Budget : Azure 5 $, Bedrock 1 $ au plus.
