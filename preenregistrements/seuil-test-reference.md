# Brique « seuil d'un test de référence avant une date » (procédure écrite avant tout calcul)

Décision de l'auteur, 2026-11-26, 14 h 55 : « oui » (écrire la procédure). Données : hub des tests de référence
d'Epoch AI (CC BY), collecté le jour même (registre/epoch-bancs/), dont les horizons de tâche de METR. Aucun modèle de
langue.

## Questions visées
« Une IA atteindra-t-elle X sur le test B avant la date D ? » (FrontierMath, GPQA Diamond, horizon METR, SWE-bench…).
Le corpus résolu n'en compte qu'une dizaine : trop peu pour juger. Le banc porte donc, comme le duel tennis, sur des
questions construites à partir des séries elles-mêmes, nombreuses et datées.

## Séries
Record de la frontière R(t) = meilleur score parmi les modèles sortis avant t (date de sortie). Tests retenus (au moins
30 lignes et 18 mois) : gpqa_diamond, frontiermath, otis_mock_aime_2024_2025, swe_bench_verified, simpleqa_verified,
terminalbench_external (colonne « Accuracy mean »), metr_time_horizons_external (colonne « Time horizon », minutes).
ARC-AGI est écarté (plusieurs versions du test mêlées dans le même fichier). Scores en fraction (division par 100 si le
maximum dépasse 1,5).

## Questions construites
Pour chaque test, chaque premier du mois t (dès 9 mois d'historique), chaque horizon H ∈ {3, 6, 12} mois tel que t+H
soit avant la dernière date du fichier, et chaque seuil :
- tests en fraction : T = R(t) + δ, δ ∈ {0,02 ; 0,05 ; 0,10 ; 0,20}, si T < 1 ;
- METR : T = R(t) × k, k ∈ {1,5 ; 2 ; 4}.
Issue : R(t+H) ≥ T.

## Règle (tendance du record)
Échelle : logit du score (fraction), log de l'horizon (METR). Régression linéaire de l'échelle du record mensuel sur le
temps, sur les 24 mois précédant t (au moins 6 points). μ = max(échelle de R(t), prolongement de la droite à t+H) ;
s = σ_résidus × √(1 + H/12), plancher 0,1. P = 1 − Φ((échelle(T) − μ)/s), bornée à [0,02 ; 0,98].

## Référence
Part de « oui » des questions de même horizon H et même cran (δ ou k) sur les AUTRES tests (un test laissé de côté à
chaque fois).

## Décision (une passe)
La règle est retenue si sa perte log moyenne est inférieure à la référence sur l'ensemble ET sur au moins deux tiers
des tests. Elle est alors branchable pour les questions vivantes de seuil (test reconnu, seuil et date lus dans le
titre), sous le contradicteur et le juge ; le branchement reste une décision de l'auteur.

## Limites déclarées
Les questions construites se recouvrent (mêmes séries, mois voisins) : les pertes ne sont pas indépendantes. Les scores
d'Epoch dépendent de leur propre protocole, qui peut différer de celui d'une question (classement officiel du test).
