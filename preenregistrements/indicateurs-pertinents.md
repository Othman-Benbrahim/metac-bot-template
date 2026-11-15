# Pré-enregistrement — indicateurs placés là où ils ont un sens, conflits « une fois » (bot 0.10.129)

**Décision d'auteur du 2026-11-15 (13 h 12)** : « je valide la pluie comme indicateur pertinent » ; « calculer
l'influence que peut avoir chaque indicateur pris à part, sur chaque événement, puis faire des combinaisons, et voir
celles qui fonctionnent le mieux ». Commité AVANT tout passage sur les questions fraîches.

## Exploration (76 questions « une fois » déjà lues, 18 oui ; B corrigé seul : 0,4753)
Chaque indicateur sur chaque type d'événement et chaque famille (violence : combats, explosions, violences contre les
civils, morts ; mobilisation : manifestations, émeutes ; stratégique), effet appris sur logit(B) gardé tel quel, un
jeu laissé de côté. Meilleurs effets seuls : conseils aux voyageurs × violence (−0,0126), pluie × émeutes (−0,0101),
pluie × mobilisation (−0,0086). Combinaisons (298, jusqu'à trois cases) : la meilleure gagne 0,0289 ; mais 15 % des
recherches refaites avec les indicateurs mélangés au hasard font aussi bien. **L'exploration seule ne distingue pas
ces gains du hasard** : c'est l'objet du test.

## Modèle figé (choisi pour la combinaison de deux cases au sens interprétable, appris sur les 76 questions)
logit(p) = logit(B) − 0,4096·z_fcdo·[violence] − 0,4837·z_pluie·[mobilisation]
- z_fcdo : (changements de sécurité des conseils aux voyageurs du Royaume-Uni sur 30 jours − 0,1343) / 0,3410 ;
- z_pluie : (écart de pluie sur 90 jours, en écarts-types − 0,2702) / 1,3246 ;
- indicateur non mesuré : z = 0.
Lecture : pluie au-dessus de la normale → moins de manifestations et d'émeutes (la rue se vide) ; conseils aux
voyageurs durcis dans le mois → moins de violence ensuite qu'attendu (le conseil suit souvent le pic, et le niveau
retombe). La case pluie × violence, présente dans la meilleure combinaison, est écartée : son sens (+) n'a pas
d'explication.

## Questions
ACLED de ForecastBench, forme « une fois », jeux postérieurs au 2026-07-01, absentes de `silence-vus.txt` (199 au
2026-11-15), ordre entrelacé fixé d'avance (rang SHA-1 de l'identifiant dans son jeu, puis jeu). Aucun modèle de langue.

## Critère (règle d'adoption commune, niveau corrigé ; second regard à 200)
**`indicateurs_pertinents`** : sur les 100 premières questions fraîches, perte log du modèle figé inférieure à celle de
B corrigé, intervalle de l'écart (bootstrap par blocs « jeu ») entièrement sous 0.

## Descriptif
Résultat par famille ; nombre de questions effectivement touchées (seules les questions de violence et de mobilisation
avec un indicateur mesuré changent de probabilité).

## Limites déclarées
Peu de questions touchées par la pluie (environ une sur six) : un vrai effet modeste peut ne pas franchir le niveau
corrigé à 100 ou 200 questions. Les coefficients viennent de 76 questions et sont sans doute trop forts (sur-ajustement) ;
ils sont figés quand même, pour que le test soit honnête.

## Amendement du 2026-11-15 (13 h 40), avant tout passage (aucune ligne fraîche n'existe)
L'auteur conteste l'exclusion de la case pluie × violence : la météo règle le passage à l'acte (« on ne manifeste et
on n'est violent que quand il fait beau »). Vérification de la littérature : l'effet de **court terme** (le jour même,
la pluie vide la rue) est documenté pour les manifestations ; sur une **saison** (notre indicateur : 90 jours),
Hendrix et Salehyan (*Journal of Peace Research* 2012) et Salehyan et Hendrix (*Global Environmental Change* 2014)
trouvent au contraire plus de violence politique les années humides que les années sèches. Deux mécanismes, deux
échelles de temps : la case a une explication, et son sens observé (+) est celui de la littérature, non celui de
l'intuition du jour même. Elle est réintégrée. Modèle figé, coefficients réappris sur les mêmes 76 questions :

logit(p) = logit(B) − 0,4151·z_fcdo·[violence] − 0,4837·z_pluie·[mobilisation] + 0,4695·z_pluie·[violence]

Critère inchangé. La meilleure combinaison de l'exploration est donc testée telle quelle ; l'avertissement sur le
hasard (15 % des recherches au hasard font aussi bien) vaut d'autant plus.
