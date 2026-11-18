# Préenregistrement : variantes de M (avocat du OUI, formulation neutre) et réplique sur Claude Haiku 4.5
2026-11-18, bot 0.10.254, écrit avant le premier passage de banc_jugement_variantes.py.

Décisions d'auteur du 2026-11-18 : 5 h 55 (explorer les autres angles morts à moindre coût, avant la fin des crédits
Bedrock le 23) ; 6 h 09 (gpt-5-mini pour les tests comparables ; trouver un usage aux crédits Bedrock) ; 6 h 13
(Claude Haiku 4.5 : « apporter le maximum d'information avec des dépenses minimums »).

## Pourquoi ces deux variantes
Contrôle du 2026-11-18 sur les 309 questions : sur 50 « oui », M en a mis 22 à 23 % ou moins (A : 13). M gagne par
le statu quo et perd sur les ruptures, l'angle mort n° 2 de l'état de l'art. Les deux variantes visent ce point.

## Questions et ordre
Les 309 questions valides du banc jugement_alphabet, dans le même ordre (empreinte). Une recherche bornée avant la
date du jeu par question, partagée par tous les bras. Notes gpt-5-mini reprises du banc (pas de nouvel appel).
Premier regard sur les 150 premières ; second regard à 300 si le premier ne conclut pas (règle des essais).

## Essais (type intervalle, critère critere_ombre_b, risque corrigé pour les essais ouverts)
1. **avocat_oui** (gpt-5-mini) : M_avocat contre M_refait (même recherche, même modèle, mêmes notes).
2. **formulation_neutre** (gpt-5-mini) : M_neutre contre M_refait. Ordre des deux issues tiré par empreinte (moitié
   « remplis » d'abord) pour neutraliser l'effet de position.
3. **replique_haiku** (Claude Haiku 4.5) : M contre A, mêmes consignes que le banc. Succès de la réplique : critère
   atteint ; à défaut, on rapporte si l'écart va dans le même sens que sur gpt-5-mini (−0,019).

## Rapportés sans être jugés
- Haiku : M_avocat contre M (descriptif ; la variante se juge sur gpt-5-mini).
- Nombre de « oui » mis à 23 % ou moins par chaque bras (cible des variantes).
- Examen des cartes sur les notes de Haiku (même procédure, seuil 0,05/7) ; **accord des statuts avec gpt-5-mini**
  (PROPORTION, HIÉRARCHIE démontrées ; TENDANCE sur les échéances) : c'est la réponse à la réserve de Li & Webb
  (une carte démontrée sur un seul lecteur peut être un raccourci de ce lecteur).

## Ce qu'on sait d'avance
Avec 13 essais « intervalle » ouverts, l'intervalle corrigé est à 99,2 % (99,6 % au second regard) : un gain de
l'ordre de 0,02 ne sera pas démontrable. Une variante qui n'atteint pas le critère n'est pas réfutée pour autant ;
elle est écrite « non démontrée ». Pas d'adoption sans décision datée de l'auteur.

## Coût prévu
gpt-5-mini : 4 appels par question (M refait, avocat, jugement avec avocat, neutre), environ 0,02 $, soit environ
3 $ pour 150 questions. Haiku : 5 appels par question, sur les crédits Bedrock (environ 0,05 $ par question).
