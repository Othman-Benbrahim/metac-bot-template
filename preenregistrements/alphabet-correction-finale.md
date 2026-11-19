# Préenregistrement : l'alphabet en correction finale à porte, au lieu de dans le jugement (idée de GraFT)
2026-11-19, bot 0.10.305, écrit avant tout calcul sur ces données.

Décision d'auteur du 2026-11-19, 1 h 22 (« d'accord, préenregistre les deux »). Source de l'idée : GraFT (voir
graphe-questions.md) : un signal bruité placé AU CŒUR du calcul propage son bruit partout ; placé APRÈS une prévision
complète, derrière une porte apprise, il ne peut que s'éteindre s'il n'aide pas. Chez nous, les notes de cartes
entrent dans le jugement du bras M ; le banc de la structure de l'arbre a montré un effet de halo dans ces notes.

## Données (déjà enregistrées, aucun nouvel appel)
Banc jugement_alphabet (registre/banc-jugement-alphabet.jsonl, lignes non exclues) : pour chaque ligne, p_A (jugement
sans alphabet), p_M (jugement avec les notes), p_B (semblables) et les 7 notes de 1 à 4 données par gpt-5-mini sur la
même recherche gelée. Réplique affichée : les notes de Claude Haiku (banc des variantes), mêmes questions.

## Règle (fixée)
score = moyenne des 7 notes centrées (n − 2,5) / 1,5, « freins » inversé (5 − n), donc dans [−1 ; 1], positif = pousse
vers OUI (sens écrit dans la consigne des notes).
p' = σ(logit(p_A) + α·score), α sur la grille −2 à 2 (pas 0,1), appris SANS la question jugée (toutes ses lignes).

## Critère
Principal : écart = perte log de p' − perte log de A ; intervalle par question, un seul regard (tout_juger), risque
corrigé des essais ouverts (essai alphabet_correction_finale). Secondaires affichés : p' contre M (correction finale
contre alphabet dans le jugement) ; même règle avec base B ; réplique Haiku. Adoption seulement si l'intervalle corrigé
principal est entièrement sous zéro, et alors seulement pour APRÈS le tournoi, sur décision datée de l'auteur.

## Limites connues
La moitié des questions de ce banc contient une fuite possible dans la recherche gelée (banc de la fuite, 0.10.300) ;
elle touche A, M et p' de la même façon. Le résultat sur les questions sans fuite stricte est affiché (descriptif).
