# Banc d'essai du compte des puits de données

Même principe que `banc/attribution/` : juge verrouillé (`juge.py`), un seul fichier modifiable (`alphabet_compte.py`),
chaque essai mesuré, gardé s'il fait baisser le score, annulé sinon ; journal : `resultats.tsv`.

**Juge** : des séries simulées dont la vraie probabilité est connue, au format des relevés des puits.
- E : événements (processus de Poisson, taux de 0,2 à 30 par an, 3 à 30 ans d'historique), un tiers avec une tendance ;
- N : niveaux (marche aléatoire mensuelle), seuil au-dessus de la dernière valeur.
Score : divergence de Kullback-Leibler moyenne (millinats) entre la vraie probabilité et l'estimation ; une abstention
compte comme 0,5. 400 cas de travail, 200 cachés (autres graines).

**Première boucle (2026-11-10, 10 essais)**

| | E | E avec tendance | N | score |
|---|---|---|---|---|
| travail, départ | 23,6 | 41,1 | 459,7 | 244,6 |
| travail, après | 4,7 | 17,5 | 8,9 | 8,9 |
| **caché, départ** | 34,8 | 20,7 | 520,1 | **275,0** |
| **caché, après** | 8,4 | 10,3 | 8,3 | **8,7** |

Ce qui a changé : pour une série de niveaux, le seuil se juge par rapport à la **dernière** valeur (l'ancien compte
l'ignorait), et la probabilité vient d'un bootstrap des pas réellement observés ; pour des événements, un taux
d'arrivée sur tout l'historique (Poisson), pondéré vers le récent seulement si les deux moitiés de l'historique
diffèrent nettement.

**Limite** : le juge simule des pas indépendants et des événements de Poisson ; le bootstrap suppose aussi des pas
indépendants. De vraies séries ont de l'inertie (une hausse de taux en appelle d'autres) : le gain réel sera plus
faible que sur le banc. L'erreur principale de l'ancien compte (ignorer le niveau actuel) est, elle, indépendante du
simulateur.

**Juge 2 (2026-11-11)** : `juge2.py`, verrouillé à son tour ; le juge 1 reste tel quel. Il ajoute quatre pièges
repérés sur une vraie question (FYONET, dépenses fédérales) : C croissance relative, R choc ponctuel, M retour vers
la moyenne, B série bornée (pourcentage). 600 cas de travail, 300 cachés.

| | E | Et | N | C | R | M | B | score |
|---|---|---|---|---|---|---|---|---|
| travail, départ (0.10.18) | 7,1 | 11,4 | 11,9 | 93,2 | 9,2 | 57,5 | 145,4 | 54,2 |
| travail, après (0.10.20) | 7,1 | 11,4 | 9,4 | 22,2 | 7,6 | 13,6 | 5,8 | 11,1 |
| **caché, départ** | 5,5 | 23,7 | 7,5 | 41,6 | 9,7 | 48,3 | 200,1 | **53,3** |
| **caché, après** | 5,5 | 23,7 | 6,3 | 18,8 | 5,7 | 13,3 | 7,1 | **10,7** |

Juge 1 : travail 8,9 → 8,1 ; caché 8,7 → 9,3 (les niveaux N du juge caché perdent un peu, 8,3 → 9,6 : le mélange
avec l'AR(1) se trompe parfois sur une marche aléatoire courte). Prix accepté : les vraies séries ont ces pièges.

Ce qui a changé (`alphabet_compte._niveaux`) : chemins simulés sur l'échelle log pour une croissance relative (pas
plus homogènes en log, ou dérive très nette), sur l'échelle logit pour une série bornée déclarée ; chocs ponctuels
(plus de 6 MAD) retirés des pas rejoués ; AR(1) estimé quand le retour vers la moyenne est net (t < −3,5), mélangé
avec la marche aléatoire entre −2,5 et −3,5 ; bootstrap LISSÉ (noyau de Silverman), qui dépasse le plus grand pas
observé. Limite : un seul choc par série dans le juge ; des chocs répétés (crises cycliques) seraient à tort retirés.
