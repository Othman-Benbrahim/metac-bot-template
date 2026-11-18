# Préenregistrement : tendance de l'attention GDELT à grande échelle
2026-11-18, bot 0.10.290, écrit avant la requête des comptes et tout calcul sur les issues de ces questions.

Décision d'auteur du 2026-11-18, 19 h 53 : « le but c'est de grappiller, même un petit décalage peut faire la
différence ; à tester sur une plus grande échelle ». Premier banc (tendance-attention.md, run 44373600462, 119
questions, base M) : −0,007, intervalle corrigé [−0,050 ; +0,036], rang tendance / issue 0,18, β appris +0,55. Sens
attendu, échantillon trop petit.

## Données
- Questions : toutes les questions distinctes de 2026 du jeu de données (registre/jugement-questions.jsonl,
  première date de jeu, cohorte complète) : 892, dont 600 Polymarket, 155 Manifold, 127 Metaculus, 10 INFER.
  Une partie des questions Metaculus figurait déjà au premier banc (pas indépendant pour celles-là).
- Comptes : `gdelt_bq.py --mode comptes_jeu`, même filtre et même mesure que le premier banc (90 jours avant le jeu).
- Base : taux des semblables S (sans modèle, sans cote ; banc_jugement). Secondaire, affiché : R1.

## Règle (inchangée)
tendance = ln((articles des 10 derniers jours / 10 + 0,1) / (articles des 80 précédents / 80 + 0,1)), 0 sans
article ; p' = σ(logit(p_S) + β·tendance), β sur la grille −1 à 1 (pas 0,05) appris SANS la question jugée.

## Critère
Écart = perte log de p' − perte log de S ; intervalle par question, un seul regard (tout_juger), risque corrigé des
essais ouverts (essai tendance_attention_large). Adoption seulement si l'intervalle corrigé est entièrement sous zéro ;
alors proposition d'utiliser la tendance dans le bot APRÈS le tournoi (décision du 2026-11-18, 19 h 40 : rien ne
change côté Metaculus avant), sur décision datée de l'auteur. Rapportés : par plateforme, profil des erreurs, β appris.

## Limite connue
Polymarket pèse les deux tiers ; ses titres (sport, crypto) sont mal couverts par GDELT. Le résultat par plateforme
est affiché pour le voir.
