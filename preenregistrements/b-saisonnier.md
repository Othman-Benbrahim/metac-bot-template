# Pré-enregistrement — B saisonnier pour les séries (bot 0.10.104)

**Décision d'auteur du 2026-11-15** : jouer sur les marges de manœuvre réelles de la prévision, d'abord le taux de base.
Ce document est commité AVANT tout calcul de B saisonnier ; la date du commit fait foi.

## Constat qui motive l'essai (vu, ne sert pas de jugement)
Sur les questions résolues du banc (jeux 2026-09-27, 10-11, 10-25), DBnomics : 103 questions, 26 % de OUI, perte log de
B 0,688 contre 0,575 pour la constante du taux observé. B compte les hausses sur toute l'année ; ces séries sont surtout
des températures Météo-France, saisonnières. Ces jeux sont donc exclus du jugement (mêmes jeux vus que le B
autorégressif, `JEUX_VUS_B_AR`).

## La règle (fixée avant toute mesure, `banc_forecastbench.b_saison`)
Points strictement avant la date d'information D, sur les 10 dernières années. Intervalles de h jours qui commencent à
±15 jours de la même date du calendrier que D dans une année passée (au moins 300 jours avant D) et finissent avant D ;
même appariement que B (premier point à t + h ou après). P(hausse) = (hausses + ½) / (intervalles + 1). Au moins 5
intervalles, sinon pas de valeur.

## Critère d'adoption (`score_registre.critere_ombre_b`, essai `b_saisonnier`)
Sur les **100 premières questions de séries (FRED, DBnomics) de jeux non vus**, dans l'ordre fixé par `banc_b.py` (jeux
du plus ancien au plus récent, puis identifiant de question) :
1. perte log de B saisonnier inférieure à celle de B ;
2. intervalle de l'écart (bootstrap par blocs « jeu × source », 2 000 tirages, graine 0) entièrement sous 0, au niveau
   corrigé de la règle d'adoption commune (`essais.py`).
Second regard possible sur les 200 premières, au risque partagé. Si le critère tient : décision d'auteur datée. Sinon,
B reste. Le critère est jugé sur toutes les séries ; un effet propre à DBnomics est rapporté par bloc, sans verdict.

## Banc gratuit
`banc_b.py` (workflow « Banc du taux de base ») calcule B, B autorégressif et B saisonnier par le code, sans modèle de
langue, sur toutes les questions de séries résolues ; registre à part `registre/banc-b.jsonl`. Son ordre des questions
vaut aussi pour le critère du B autorégressif (précision du 2026-11-15, avant tout calcul sur ce banc).


## Clôture (2026-11-15) — banc du taux de base, exécution 43653595776
Mêmes 400 questions. Premier regard : écart moyen +0,012 (B saisonnier moins bon), intervalle par blocs
[−0,015 ; +0,033] ; second regard : +0,034, intervalle corrigé [−0,014 ; +0,098]. **Critère non atteint : non adopté.**
Rapporté par bloc, sans verdict : le saisonnier gagne sur DBnomics dans 4 blocs sur 4 de taille utile (0,696 → 0,690 ;
0,699 → 0,682 ; 0,690 → 0,679 ; 0,694 → 0,658) et perd lourdement sur FRED (jusqu'à 0,756 → 0,877), où les séries
financières n'ont pas de saison et où une dizaine d'intervalles seulement donnent des valeurs extrêmes. Une règle
limitée à DBnomics serait un NOUVEL essai, à pré-enregistrer avant de regarder des jeux non encore lus.
