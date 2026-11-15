# Pré-enregistrement — le langage comme acte, le désaccord comme signal (bot 0.10.112)

**Décision d'auteur du 2026-11-15.** Deux idées neuves, gratuites hors coût de modèle, testées là où le jugement du
modèle apporte déjà de l'information : les questions de conflits (ACLED). Commité AVANT tout passage du banc.

## Idées
1. **Langage comme acte** : séparer ce qui ENGAGE (annonces datées, menaces, promesses, ultimatums, appels, décisions
   à venir) de ce qui DÉCRIT. Hypothèse : les actes portent sur la suite une information que la description n'a pas.
2. **Désaccord comme signal** : quand les sources suggèrent des issues différentes, l'incertitude réelle est plus
   grande que ne le dit A ; A devrait alors se rapprocher du taux de base B.

## Mesure (`banc_l.py`)
Questions : les questions ACLED du banc du bras A (gpt-5-mini) qui ont A, B et une issue. Pour chacune : recherche bornée
avant la date d'information, puis un appel à gpt-5-mini qui qualifie chaque extrait (acte ou description ; sens hausse,
baisse ou neutre ; probabilité suggérée par l'extrait seul ; au plus 12 extraits). Variables : E = (actes en hausse −
actes en baisse) / (actes + 1) ; D = écart-type des probabilités suggérées (0 si moins de deux extraits).

## Modèles (un paramètre chacun, fixés ici)
- acte : logit(p) = logit(A) + β·E
- désaccord : logit(p) = logit(A) + γ·D·(logit(B) − logit(A))
Paramètre appris par maximum a posteriori (a priori normal centré sur 0, écart-type 1). Prédictions hors échantillon par
**validation croisée « un jeu laissé de côté »** : chaque jeu est prédit par un paramètre appris sur les autres jeux.

## Critères (`score_registre.critere_ombre_b`, règle d'adoption commune)
Sur les **100 premières questions** dans l'ordre du banc du bras A : perte log du modèle inférieure à celle de A seul, et
intervalle de l'écart (bootstrap par blocs « jeu », 2 000 tirages, graine 0) entièrement sous 0 au niveau corrigé.
Second regard à 200 s'il y a assez de questions. Deux essais : `langage_acte`, `desaccord`.

## Limites déclarées
Le même modèle qualifie les extraits et produit A : leurs erreurs peuvent être corrélées. La qualification
acte/description n'est pas vérifiée par un second codeur dans ce passage.
