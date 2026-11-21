# Taille des mises à jour de M (préenregistrement, 2026-11-21)

Décision de l'auteur (2026-11-21, 12 h 53) : intégrer les pistes tirées de Learning Bayesian Statistics. Celle-ci
vient de l'idée « reverse Bayes » (épisode 164, Gelman, Vehtari, McElreath) : demander quelle confiance justifierait
la conclusion d'un modèle.

## Rasoir d'Ockham
1. Une phrase : M s'écarte du taux des semblables ; cet écart est peut-être systématiquement trop grand ou trop petit.
2. Paramètres : un seul, k (k = 1 : M tel quel).
3. Sens fixé d'avance : aucun ; les deux sens sont plausibles (les modèles de langue sont souvent trop sûrs d'eux ; mais
   le constat du 2026-11-20 est que les semblables eux-mêmes sont trop confiants).
4. Domaine : questions binaires de jugement où M est posté.
5. Plus simple ? Non : c'est déjà la forme la plus simple de recalibrage.

## Données et méthode (fixées)
Banc de M existant (`registre/banc-jugement-alphabet.jsonl`), une ligne par question (son premier jeu), 119
questions, jeux du 2026-01-04 au 2026-09-27. p_k = σ(logit p_B + k·(logit p_M − logit p_B)), k sur la grille 0 à 2 par
pas de 0,05, appris par perte log minimale sur les questions antérieures, en 5 tranches chronologiques à fenêtre
élargie (au moins 20 questions apprises) ; chaque tranche jugée par le k appris avant elle.
Script : `mise_au_point/taille_mises_a_jour_m.py`. Aucun appel de modèle. Lancé une fois.

## Critère (fixé)
Écart moyen de perte log (p_k − M) sur les questions jugées, intervalle à 90 % par bootstrap par question.
Adopté si l'intervalle est entièrement sous 0 : alors le k appris sur tout le banc s'applique à M posté.
Sinon rien ne change. Le k appris sur tout le banc et le k de chaque tranche sont décrits.

## Limite connue d'avance (verification_a_priori.puissance)
Sur ce banc, σ ≈ 0,31 de perte log par question : une centaine de questions jugées ne voit qu'un écart d'environ
0,07 ou plus. Un recalibrage utile mais petit (0,01 à 0,02) ne se verra pas : un résultat « non adopté » ne dira pas
que k = 1 est juste, seulement que l'écart n'est pas grand.
