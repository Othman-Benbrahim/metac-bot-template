# Seuils de prix : calibrage sur les actions (préenregistrement, 2026-11-20, 19 h 55)

Suite de `seuils-de-prix-calibrage.md` (critère atteint sur cryptomonnaies, Brent et indices, −0,206). Décision de
l'auteur (19 h 49, option 1) : cours d'actions lus chez Twelve Data avec sa clé, sans écrire de cours brut dans le dépôt.

- Questions : mêmes règles de lecture (`mise_au_point/seuils_prix_essai.py --actions`), actifs de `seuils_prix.ACTIONS` ;
  recensement : 55 questions (Tesla 31, Apple 10, Nvidia 5, Microsoft 3, AMD 2, autres 4 ; « à la date » 33,
  « atteint avant » 22 ; Manifold 48).
- Calcul, témoin et critère : identiques au passage d'origine (M − I < 0, intervalle à 90 % excluant 0).
- Si le critère est atteint : `ACTIONS_DANS_LE_BOT = True` (règle de l'auteur : vérifié à son niveau → introduit).
- Lancé une fois, dans GitHub (workflow banc_seuils_actions.yaml) ; seul le fichier de résultats est enregistré.

## Passage 1 (2026-11-20, 19 h 54) : invalide, erreur de mesure prouvée
Run 44796864729 : M − I = +0,2996 [+0,0156 ; +0,6332]. Cause : Twelve Data renvoie par défaut des cours AJUSTÉS des
divisions d'actions (paramètre `adjust`, défaut `splits`, documentation : https://twelvedata.com/docs/llms/market-data/time-series.md),
alors que les seuils des questions sont écrits en prix de l'époque. Les pertes se concentrent exactement sur les actions
divisées pendant la période (Tesla 1,15 ; MicroStrategy 4,61 ; Apple 0,81), pas sur les autres (Nvidia 0,01 sur des
questions de 2023). Correctif : `adjust=none`. Fichier conservé : `registre/mise-au-point/seuils-prix-actions-passage1-errone.json`.
Un seul nouveau passage.

## Passage 2 (2026-11-20, 19 h 59) : critère non atteint
Run 44797643488, cours non ajustés. 55 questions (49 distinctes). Perte : témoin 0,6125 ; M (σ 30 j) 0,5631 ; σ 90 j
0,5832 ; σ × 1,5 0,6047. M − I = −0,0494, intervalle à 90 % [−0,2024 ; +0,1125] : dans le bon sens, non tranché.
« À la date » 0,575 contre 0,622 (33) ; « atteint avant » 0,545 contre 0,598 (22). Tesla 0,595 contre 0,617 (31) ;
Apple 0,810 contre 0,687 (10). `ACTIONS_DANS_LE_BOT` reste à False. Reprise possible sur des questions d'actions
nouvelles, quand elles seront assez nombreuses.
