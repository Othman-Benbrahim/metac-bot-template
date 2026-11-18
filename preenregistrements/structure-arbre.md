# Préenregistrement : premier apprentissage de la structure de l'arbre (réseau bayésien notes → issue)
2026-11-18, bot 0.10.291, écrit avant tout calcul de structure sur ces données.

Décision d'auteur du 2026-11-18, 20 h 31 (« je valide, ça fait avancer nos recherches »). Méthode : Kochenderfer,
Wheeler, Wray, Algorithms for Decision Making, ch. 5 (claude/reference-kochenderfer-algorithms-decision-making.md).

## Nature
Banc DESCRIPTIF : il ne propose rien au bot, n'ouvre aucun essai, ne change pas la correction des essais. Il dit quels
liens entre cartes, et entre cartes et issue, résistent aux données que nous avons, et lesquels ne tiennent pas.

## Données
- Principal : les 7 notes de cartes (tendance/CROISSANCE, engagements/RÉCIPROCITÉ, décideurs/HIÉRARCHIE,
  déclencheur/SEUIL, freins/CONTRAINTE, durée/PÉRIODICITÉ, proportion/PROPORTION ; 1 à 4) données par gpt-5-mini au
  banc du jugement, une ligne par question distincte (première date de jeu), lignes exclues retirées, issue connue.
- Réplique : les notes de Claude Haiku (banc des variantes), mêmes règles.

## Méthode (fixée ici)
- Score BDeu (prior de Dirichlet, taille d'échantillon équivalente 1), recherche K2, au plus 2 parents par nœud.
- Ordre : les notes dans l'ordre des critères, puis l'issue en dernier (une note peut expliquer l'issue, jamais
  l'inverse). La direction entre deux notes n'a PAS de sens causal (§ 5.3 du livre : les données d'observation
  n'orientent pas une flèche) ; seule la direction vers l'issue est voulue.
- Stabilité : 500 rééchantillonnages des questions (graine 0) ; un lien est « stable » s'il apparaît dans au moins
  70 % des tirages. Sensibilité à l'ordre : 20 ordres des notes tirés au hasard, l'issue toujours en dernier ; on
  compte combien de fois chaque note devient parent de l'issue.
- Vérification prédictive, affichée et non jugée : issue prévue par ses parents appris SANS la question jugée
  (fréquence de oui dans la case, Jeffreys) contre l'issue seule.

## Ce qu'on attend (écrit avant)
Avec environ 120 questions, le livre montre que le graphe presque vide l'emporte : peu ou pas de liens stables. Ce ne
serait pas une preuve d'absence. Si un lien vers l'issue apparaît, PROPORTION et DÉCLENCHEUR sont les candidats
(seules cartes à apport propre à l'examen façon RAPM).
