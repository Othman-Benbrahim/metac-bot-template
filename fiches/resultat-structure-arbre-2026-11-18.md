sources: registre/banc-structure-arbre.json
constantes: 7; 1; 4
# Résultat : premier apprentissage de la structure de l'arbre (2026-11-18)

Banc descriptif banc_structure_arbre.py, bot 0.10.291, préenregistrement preenregistrements/structure-arbre.md.
Réseau bayésien entre les 7 notes de cartes (1 à 4) et l'issue ; score BDeu, recherche K2, au plus 2 parents ;
stabilité sur 500 rééchantillonnages des questions (lien stable ≥ 70 %). Méthode : Kochenderfer et al., ch. 5.

## Lecteur gpt-5-mini (119 questions distinctes, 27 oui)
- Aucun lien vers l'issue, ni sur l'échantillon complet, ni sous aucun des 20 ordres des notes. Le plus fréquent :
  PROPORTION → issue dans 24 % des tirages, DÉCLENCHEUR 20 %, tendance 19 %, freins 17 %.
- Un seul lien stable entre notes : engagements (RÉCIPROCITÉ) → décideurs (HIÉRARCHIE), 78 %.
- Prévision de l'issue par le graphe appris = issue seule (0,544 = 0,544).

## Lecteur Claude Haiku (75 questions, 15 oui)
- Sur l'échantillon complet, freins (CONTRAINTE) → issue, et sous les 20 ordres ; mais seulement 21 % des tirages :
  instable. La prévision par ce lien est PIRE que l'issue seule (0,540 contre 0,514) : surajustement.
- Liens stables entre notes : tendance → proportion 100 %, tendance → engagements 84 %, décideurs → freins 71 %.
  Les notes de Haiku sont bien plus liées entre elles que celles de gpt.

## Lecture
1. Aucune carte, notée librement par un modèle, n'a de lien stable avec l'issue sur 119 questions (gpt). C'est ce que le
   livre annonce pour si peu de cas, et ce que disaient déjà nos examens des cartes.
2. Les liens entre notes décrivent d'abord le LECTEUR, pas le monde : un modèle qui note « tendance favorable »
   remonte aussi « proportion » et « engagements » (effet de halo, très fort chez Haiku). Les 7 notes valent en
   pratique 2 ou 3 impressions générales.
3. Deux associations se retrouvent chez les deux lecteurs : engagements ↔ décideurs (78 % / 56 %) et tendance ↔
   proportion (48 % / 100 %). Elles ont un sens (ceux qui décident sont ceux qui s'engagent ; une tendance rapproche
   du seuil), mais la direction n'est pas lisible dans ces données (§ 5.3).

## Conséquence pour l'arbre
Apprendre la structure de l'arbre à partir des impressions d'un modèle ne marchera pas : il faut des variables
FACTUELLES (faits datés et vérifiés, comme ceux des cartes ancrées, ou des cas historiques codés) et beaucoup plus de
cas (plusieurs milliers d'après le livre). Le code du banc est prêt à recevoir de telles données.
