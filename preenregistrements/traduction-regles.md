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
question (son premier jeu), dont au moins une règle se traduit : 22 questions (douze règles traduisibles sur 53).
Aucun appel de modèle. Script `mise_au_point/traduction_regles_essai.py`, lancé une fois.

## Critère (fixé)
Perte log brute, une ligne par question ; adopté si l'intervalle à 90 % (bootstrap par question) de C − S est
entièrement sous 0 : alors, quand la carte robot trouve une règle traduisible, le point de départ de M devient C au
lieu de S (en ombre d'abord sur le flux réel). R − S est décrit.

## Limite connue d'avance
22 questions : seul un effet très grand (de l'ordre de 0,15 de perte log) sortira de l'intervalle. Le résultat sera
surtout descriptif : quelles règles tirent dans le bon sens, lesquelles non, et pourquoi. Élargir demande de traduire
davantage de règles (les règles de sondages, par exemple, ont besoin des chiffres des sondages, absents du titre).
