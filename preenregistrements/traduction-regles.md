# Traduction algorithmique des règles en probabilités (préenregistrement, 2026-11-21)

Décision de l'auteur (2026-11-21, 15 h 07-15 h 09) : la question n'est pas de savoir si les faits et mécanismes
« améliorent M », mais comment les traduire algorithmiquement en probabilités ; si une traduction échoue, on en change,
on ne renie pas les faits. Ce test essaie une traduction par le code seul, à côté de la traduction par un modèle de
langue (banc position écosystémique).

## Rasoir d'Ockham
1. Une phrase : une règle sourcée chiffrée, convertie à l'horizon de la question, corrige le taux des semblables.
2. Paramètres : aucun appris ; conversions et combinaison (moyenne des logits à poids égaux) fixées dans
   `traduction_regles.py` avant tout regard sur les issues.
3. Sens fixé d'avance : C (combinaison) meilleur que S (semblables seuls).
4. Domaine : questions dont la carte robot retient une règle traduisible (fréquence, part historique, fenêtre).
5. Plus simple ? S seul : c'est le témoin.

## Données (fixées)
Questions de jugement de 2026 couvertes par la carte robot (`registre/carte-robot-jugement2026.json`), une par
question (son premier jeu), dont au moins une règle se traduit : 37 questions (treize règles traduisibles sur 53),
dont 16 sur les décisions de la Fed.
Aucun appel de modèle. Script `mise_au_point/traduction_regles_essai.py`, lancé une fois.

## Ajout du 2026-11-21, 15 h 30 (avant tout regard sur les issues) : décisions de la Fed
Décision de l'auteur (15 h 19) : commencer le chantier par la Fed. Réunions programmées 2021-2026 (calendrier officiel du
FOMC) ; décision de chaque réunion lue dans le taux effectif quotidien (FRED, DFF : médiane des 5 jours ouvrés après
moins médiane des 5 jours avant, arrondie au quart de point), seulement pour les réunions visibles avant le jeu ;
chaîne de Markov à trois états (baisse, pause, hausse) apprise sur ces décisions passées (lissage de Jeffreys), partant
de la dernière décision connue ; « au moins une baisse d'ici telle réunion » par la chaîne privée de l'état visé ;
taille du mouvement (25 contre 50 et plus) par la part observée parmi les mouvements de ce sens.
Aucune cote de marché ni prévision de foule (les contrats à terme sur les taux restent exclus, décision à prendre
par l'auteur).

## Ajout du 2026-11-21, 15 h 50 (avant tout regard sur les issues) : sondages électoraux
Moyenne des 5 derniers sondages terminés au moins 3 jours avant le jeu (collecte_sondages.py, pages de sondages de
Wikipédia, nombres seulement) ; erreur par candidat tirée des règles sourcées (environ 4 points à 150-200 jours, 3 à
50 jours, 2 la dernière semaine ; primaires américaines 8,7/√2) ; écart-type 1,25 × erreur ; 4 000 tirages
indépendants ; probabilité d'être premier, deuxième, troisième, dans les deux premiers, ou au-dessus d'un seuil.
Les questions de sièges (majorité, fourchettes) ne sont pas traduites. Limite : un sondage ajouté à la page après le
jeu mais terminé avant peut entrer (marge de 3 jours) ; les sièges sont approchés par le rang en voix.

## Critère (fixé)
Perte log brute, une ligne par question ; adopté si l'intervalle à 90 % (bootstrap par question) de C − S est
entièrement sous 0 : alors, quand la carte robot trouve une règle traduisible, le point de départ de M devient C au
lieu de S (en ombre d'abord sur le flux réel). R − S est décrit.

## Limite connue d'avance
37 questions : seul un effet grand (de l'ordre de 0,1 de perte log) sortira de l'intervalle. Le résultat sera
surtout descriptif : quelles règles tirent dans le bon sens, lesquelles non, et pourquoi. Élargir demande de traduire
davantage de règles (les règles de sondages, par exemple, ont besoin des chiffres des sondages, absents du titre).

## Ajout du 2026-11-21, 16 h 15 (avant tout regard sur les issues) : état de la collecte au lancement
Collecte corrigée sur quatre passages (44915155718, 44916010855, 44916476984, 44917505006), sans jamais regarder les
issues : une page par question avec le même type de course, l'année de l'élection (sans année : l'année du jeu ou la
suivante), un mot distinctif commun ; un seul tableau par question (celui du sujet, le plus récent), affiches générales
écartées pour les primaires de parti, matrices de duels écartées, tableaux dont les moyennes dépassent 110 % refusés ;
sondages de plus de 90 jours avant le jeu écartés. Allemagne : DAWUM (base structurée, ODbL) d'abord, Wikipédia en
contrôle. Questions sans nom d'élection : nom reconstruit à partir du pays et de l'année du jeu.
Compte au lancement (lignes sans les issues) : 80 questions traduisibles, dont 31 de sondages et 16 de la Fed.
Retrait fixé : manifold:Q9gNdcP2lc (Hongrie, en-têtes illisibles, Orbán lu à 2,3 %). La collecte et l'essai tournent
dans le même passage (workflow essai_traduction.yaml) ; le compte final peut gagner quelques questions de sondages
(Brésil sans nom d'élection, Suède, pays de Galles).

## Résultat (run 44917992026, 2026-11-21, 16 h 14) : ADOPTÉ
80 questions (31 de sondages au compte de lancement, 43 lignes portant une règle de sondages au passage final, 16 Fed,
21 fréquences). Perte log : S 0,617 ; R 0,530 ; C 0,458. C − S = −0,159, intervalle à 90 % [−0,259 ; −0,065] :
entièrement sous 0, critère rempli. R − S = −0,087 [−0,246 ; +0,084] : la règle seule ne suffit pas, c'est la
combinaison qui gagne.
Par famille (descriptif) : sondages S 0,659 → C 0,438 ; Fed 0,659 → 0,520 ; fréquences 0,497 → 0,451.
Contrôles descriptifs (non préenregistrés, ne changent pas le verdict) : bootstrap par élection (55 grappes, les
questions sœurs comptées ensemble) [−0,248 ; −0,056] ; hors sondages (37 questions) −0,086 [−0,186 ; +0,012], non
tranché.
Défaut de traduction constaté après coup : « Cornyn win … runoff by 9% » traduit comme « se qualifier pour le second
tour » (p 0,98, issue non). Corrigé pour la suite (écart de voix non traduit) ; l'essai n'est pas relancé.
Suite : C devient le point de départ de M quand la carte robot trouve une règle traduisible, en ombre d'abord sur le
flux réel.

## Ajout du 2026-11-21, 17 h 25 (AVANT le bilan de relecture) : contrôle après coup des lectures de sondages
Faute de méthode reconnue : la relecture automatique (colonne « Lead » des tableaux) n'existait pas lors de l'essai.
Les lectures utilisées par l'essai sont celles du commit 5c421cb (registre/sondages-questions.json). Elles sont
contrôlées par le passage de collecte suivant, qui porte la relecture, ainsi :
- DÉFAILLANCE PROUVÉE si, pour au moins une question de sondages de l'essai, (a) le tableau utilisé est refusé par la
  relecture (moins de 80 % d'accord sur au moins 3 lignes vérifiables), ou (b) la moyenne du sujet relue diffère de
  plus de 2 points de celle utilisée par l'essai, pour le même jeu (au-delà de 2 points, ce n'est plus une retouche
  de page mais une autre lecture), ou (c) le sujet est lu dans une autre colonne.
- Alors l'essai est relancé UNE fois, sur les lectures vérifiées, aux mêmes critères ; le second résultat est gardé,
  quel qu'il soit, et le premier est noté comme invalide.
- Une question dont le tableau n'a pas de colonne « Lead » n'est ni confirmée ni infirmée : elle est comptée à part,
  et son nombre est publié avec le bilan.
- Sans défaillance prouvée, le résultat du 16 h 14 tient.

## Bilan de relecture et relance (2026-11-21, 17 h 25 - 17 h 31)
Bilan (collecte du 16 h 22 UTC avec relecture « Lead ») sur les 43 questions de sondages du premier essai : 28
confirmées par la colonne « Lead », 2 lues dans DAWUM, 13 sans colonne « Lead » (non vérifiables). Aucune ne remplit
les critères (a)-(c) ; mais une lecture fausse est prouvée par vérification de la page : la question suédoise
(« Social Democratic Party (S) … most seats ») lue dans le tableau des chefs de parti (« Magdalena Andersson (S) »,
39 %), pas dans les intentions de vote. Défaut corrigé (commit 54d658c : un parti n'est jamais lu dans la colonne de
son chef). Décision de l'auteur (17 h 27) : relancer une fois. LE PREMIER RÉSULTAT (16 h 14) EST INVALIDE.

## Résultat de la relance (run 44924797777, 17 h 30) : ADOPTÉ — résultat retenu
78 questions (la suédoise sort faute de colonne lisible ; « Cornyn … runoff by 9% » n'est plus traduite). Perte log :
S 0,605 ; R 0,493 ; C 0,446. C − S = −0,159, intervalle à 90 % [−0,254 ; −0,069] : critère rempli. R − S = −0,112
[−0,261 ; +0,042].
Par famille (descriptif) : sondages (41) 0,640 → 0,414 ; Fed (16) 0,659 → 0,520 ; fréquences (21) 0,497 → 0,451.
Bootstrap par élection (53 grappes) : [−0,242 ; −0,068].
Suite décidée par l'auteur (17 h 17) : branchement direct (pas d'ombre) quand la lecture sera prête ; chaque question
vérifiée au moment où le bot la traite (relecture « Lead », alertes), sinon S.
