# Préenregistrement : bras M posté en compétition, règle d'arrêt (2026-11-18, bot 0.10.253)

Décision d'auteur du 2026-11-18, 5 h 55 : « Oui, je valide » (les trois usages proposés : M officiel sur les questions
de jugement, A en ombre ; les trois cartes démontrées pondérées, testées sur questions neuves ; les cartes dans les
commentaires). Fondement : banc des questions de jugement Metaculus, 309 questions, M 0,362, A 0,381, foule 0,384 ;
critère préenregistré NON atteint (intervalle corrigé [−0,075 ; +0,031]). L'adoption est une décision d'auteur, pas un
résultat de banc : elle est écrite comme telle.

## Ce qui est posté
Sur chaque question binaire du tournoi : M (bras_m.py) remplace A, et B tiré de la seule vue du modèle. M ne remplace
jamais un B calculé (compte des puits, vue fixée par un banc) ni C. Si M échoue, la règle précédente s'applique.
A est toujours calculé et scellé avant toute carte ; M est journalisé dans la même ligne (champ bras_M).

## Règle d'arrêt (fixée avant la première question postée)
- Questions comptées : celles où M a été posté et qui sont résolues ; une ligne par question (la dernière).
- Après 100 questions : si la perte log moyenne de M dépasse celle de A de plus de 0,03, **retour en arrière**
  (POSTER_M = False) ; l'auteur en est averti et date la décision. Sinon M est maintenu.
- Aucun regard intermédiaire ne déclenche l'arrêt (pas de jugement sur bruit) ; le suivi est affiché au score
  (regle_arret_M) à titre descriptif.
- Le seuil de 0,03 est la borne haute de l'intervalle corrigé du banc : au-delà, le banc est contredit.

## Différences avec le banc, connues d'avance
Modèle : le modèle principal du bot (gpt-5-mini dans le banc). Recherche : celle du bot (Exa bornée dans le banc).
A du tournoi n'a pas le taux de départ que A du banc recevait. Ces écarts peuvent jouer dans les deux sens ; la règle
d'arrêt est là pour ça.
