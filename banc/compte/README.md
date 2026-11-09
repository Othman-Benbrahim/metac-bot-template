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
