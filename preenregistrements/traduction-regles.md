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

## Critère (fixé)
Perte log brute, une ligne par question ; adopté si l'intervalle à 90 % (bootstrap par question) de C − S est
entièrement sous 0 : alors, quand la carte robot trouve une règle traduisible, le point de départ de M devient C au
lieu de S (en ombre d'abord sur le flux réel). R − S est décrit.

## Limite connue d'avance
37 questions : seul un effet grand (de l'ordre de 0,1 de perte log) sortira de l'intervalle. Le résultat sera
surtout descriptif : quelles règles tirent dans le bon sens, lesquelles non, et pourquoi. Élargir demande de traduire
davantage de règles (les règles de sondages, par exemple, ont besoin des chiffres des sondages, absents du titre).
