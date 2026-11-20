# Moteur complet : semblables + brique « fenêtre » + état présent (préenregistrement, 2026-11-20)

Décision de l'auteur, 2026-11-20, 01 h 38 : « On teste le 2 déjà. La brique n'est pas complète » (après la clôture de `brique_fenetre` : la structure seule ne bat ni les semblables ni le taux de base ; la foule, qui connaît l'état présent, fait 0,33 contre 0,57).

Essai `brique_fenetre_etat`. Ombre : rien dans le bot, rien côté Metaculus avant le tournoi.

## Garde contre les deux poches (mécanisme 7)
L'attention a déjà été testée seule, comme correction des semblables : Wikipédia (`tendance_wikipedia`), GDELT (`tendance_attention`, `tendance_attention_large`, `sursauts_attention`), sans effet. Ce qui est nouveau ici : l'état présent est combiné à la structure acteur × fenêtre dans un seul moteur. Ce test est lancé une fois. S'il ne tranche pas, la conclusion écrite d'avance est : **l'attention (presse et public) ne porte pas l'état du système qui manque à la brique** ; on ne relance pas ce moteur avec une autre « pièce » d'attention.

## Questions
Questions d'occurrence de 2026 (structure autre, procédure, événement rare, maintien) dont l'état présent a été relevé à la date du jeu (`registre/gdelt-bq-comptes-jeu.json`, `registre/wikipedia-comptes.json`) : 424 lignes au 2026-11-20.

## Le moteur
Régression logistique (L2, `banc_redacteur.ajuster`) apprise à chaque date sur les seules questions passées (au moins 50, deux issues ; sinon p_S), sur : logit p_S (semblables), logit p_F (brique acteur × fenêtre), et l'état présent sur les 90 jours avant le jeu — presse (GDELT : tendance 10 contre 80 jours, niveau, présence), public (Wikipédia : tendance, niveau, présence), protections de page.

## Critère
Principal : moteur contre semblables, perte log, intervalle corrigé (risque d'`essais.py`) entièrement sous 0. Second : contre le taux de base. Descriptif : la foule, les coefficients, par acteur.
