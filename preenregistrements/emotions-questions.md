# Les émotions dans la formulation des questions (préenregistrement, 2026-11-19, 21 h 10)

Décision d'auteur du 2026-11-19, 21 h 02 (« oui », usage 3 d'EmoAtlas). Essai `emotions_questions`. Ombre.

## Hypothèse
Mécanisme n° 8 du registre (le forçage) : le rédacteur choisit les mots d'une question. Une question chargée d'émotions négatives (peur, colère, tristesse, dégoût) est souvent écrite sous le coup de l'actualité ; la saillance pousse à surestimer le « oui ». Si c'est vrai, la charge émotionnelle du titre porte une information sur l'issue que le taux de base des questions semblables n'a pas.

## Mesure (fixée avant tout calcul)
- Titres seuls, en anglais, de la cohorte complète des questions de jugement (mêmes exclusions que le banc de proxémie).
- EmoAtlas (Stella et al.), modèle spaCy `en_core_web_sm` 3.7.1, émotions de Plutchik (lexique NRC) : décompte par émotion.
- Les scores d'EmoAtlas sont des écarts au hasard (z) ; seule leur part positive compte. Trois traits : log(1 + négatives), log(1 + positives : confiance, joie, attente), log(1 + surprise).

## Comparaison
Comme le banc de proxémie : régression logistique réapprise à chaque jeu sur le seul passé admis ; P = recalibrage des semblables seul, E = le même plus les trois traits. Confirmation : jeux de 2026.

## Critère
Les traits aident si l'intervalle de l'écart de perte (E − P), au risque corrigé d'`essais.py`, est entièrement sous 0 ; ils nuisent s'il est entièrement au-dessus. Descriptif publié à part : part de « oui » et pertes pour les titres chargés et neutres. Même en cas de succès, rien dans le bot avant le tournoi.
