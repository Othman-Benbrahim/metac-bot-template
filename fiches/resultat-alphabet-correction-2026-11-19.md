sources: registre/banc-alphabet-correction.json
# Résultat : l'alphabet en correction finale à porte, au lieu de dans le jugement (idée GraFT) (2026-11-19)

Run 44433422760, bot 0.10.308, préenregistrement preenregistrements/alphabet-correction-finale.md. Aucun nouvel appel :
notes de cartes, p_A, p_M et p_B déjà enregistrés. 310 lignes pour 119 questions distinctes (27 oui) ; la preuve repose
sur les 119 questions.

## Critère principal : A corrigé par le score des notes, contre A
- Perte log : A 0,3804 ; A corrigé 0,3694. Écart −0,011 (sens attendu).
- Intervalle par question [−0,027 ; +0,006] ; corrigé [−0,038 ; +0,018]. Critère non atteint.
- Porte apprise : α = 1,4 (les notes poussent dans le bon sens).
- Sur les questions sans fuite stricte (164 lignes, descriptif) : 0,3896 → 0,3893, α = 0,9. Le petit gain disparaît
  là où la recherche ne contient pas l'issue.

## Secondaires (affichés, non jugés)
- Contre M (l'alphabet DANS le jugement) : M 0,3622 ; A corrigé 0,3704. M reste meilleur. L'inversion de GraFT ne se
  vérifie pas ici : chez nous, les cartes servent mieux en étapes de raisonnement (matriochka) qu'en score ajouté après.
- Base B (semblables) : 0,4517 → 0,3912, α = 2, au bord de la grille. Les notes portent beaucoup d'information au-delà
  des semblables, mais c'est l'information de la recherche, que A et M ont déjà, et dont une partie est une fuite.
- Réplique Haiku (120 lignes, 75 questions) : A 0,4762 → 0,4855, α = −0,1 (la correction nuit) ; M 0,4247 ;
  base B 0,4609 → 0,3992.

## Verdict
Non retenu. La correction finale ne bat pas A de façon distinguable, elle ne bat pas M, et Haiku ne la reproduit pas.
Ce que ce banc apprend : le diagnostic « l'alphabet dans le jugement propage du bruit » ne tient pas ; M, qui met les
cartes dans le raisonnement, reste la meilleure façon de les utiliser parmi celles testées. Essai alphabet_correction_finale
clos en 0.10.310.
