# Accords requis, question par question (préenregistrement, 2026-11-20, plan B des acteurs de veto)

Décision de l'auteur : « On fait le B donc » (17 h 08) ; « fais ce que tu as à faire » (17 h 09, absent). Suite du plan A (`acteurs-de-veto.md`, clos : la mesure par pays captait l'identité du pays, pas le nombre d'accords). Première mesure du réseau d'acteurs sur des cas réels, à l'échelle de la question.

## Fondement
Tsebelis (*Veto Players*, 2002) : un acteur de veto est un acteur dont l'accord est nécessaire pour changer le statu quo ; plus d'accords nécessaires, plus de stabilité. Ici, le nombre d'accords nécessaires est lu sur la question elle-même, pas sur le pays.

## Codage (fixé à 17 h 09, avant toute lecture des issues ; `accords_requis.py`)
Règles écrites sur le titre, ordre fixe :
1. décision à l'unanimité (UE, OTAN, « unanimous ») → « 3+ » ;
2. loi complète (« become law », « signed into law », « enact ») → « 3+ » aux États-Unis ou si les deux chambres sont nommées, sinon « 2 » ;
3. les deux chambres → « 2 » ;
4. confirmation ou ratification → « 2 » ; ratification par tous les membres → « 3+ » ;
5. acte unilatéral (annoncer, se retirer, juger, déclarer, suspendre…) → « 1 » ;
6. accord, traité, cessez-le-feu, rencontre, négociation → « 2 » ; « 3+ » si trois pays ou plus sont nommés ;
7. sinon → « 1 ».
Recensement (structure seule) : 667 questions « procédure » Metaculus et GJOpen 2015-2024 : « 1 » 571, « 2 » 61, « 3+ » 35. Erreurs de codage connues et acceptées (règles écrites, pas un jugement par question).

## Partie volonté (non codable sur le titre)
Savoir si l'acteur qui a la main VEUT la décision demande l'information du moment : pas sur le titre, pas de modèle payant sur l'échantillon. Elle sera mesurée sur les questions réelles du bot, avec les notes déjà produites par le bras M (« décideurs », « freins », notées de 1 à 4 par le modèle), à mesure des résolutions du journal.

## Calcul (fixé, identique au plan A)
Témoin I (80 % semblables + 20 % taux de base) ; variante V : taux de base remplacé par le taux de oui des questions « procédure » passées de la même tranche, rétréci vers le taux de base (poids 5), au moins 30 passées sinon témoin. Perte log ; intervalle à 90 % par question. Descriptif : part de oui par tranche (la théorie prédit une part décroissante).

## Critère
Candidat si V − I < 0 et l'intervalle à 90 % exclut 0 ; confirmation contre la sortie réelle du bot (journal, e-processus, α = 5 %). Sens contraire à la théorie : clos.

## Résultat (2026-11-20, 17 h 15) : non candidat
667 questions (528 avec une tranche d'au moins 30 passées). V − I = +0,0050, intervalle à 90 % [+0,0022 ; +0,0081] : la variante fait moins bien que le témoin. Part de oui : « 1 » 0,303 (571) ; « 2 » 0,328 (61) ; « 3+ » 0,171 (35) ; sans les États-Unis : 0,285 ; 0,250 ; 0,152. Descriptif : le sens prédit apparaît seulement pour « 3+ » (35 questions, trop peu pour une classe de 30 passées la plupart du temps) ; « 2 » ne se distingue pas de « 1 ». Le remplacement du taux de base par le taux d'une tranche coûte sur la grande tranche « 1 » (571 questions), sans gain ailleurs. Fichier : `registre/mise-au-point/accords-requis.json`. Reste ouvert : la partie volonté, sur les questions réelles du bot (notes « décideurs » et « freins » du bras M).
