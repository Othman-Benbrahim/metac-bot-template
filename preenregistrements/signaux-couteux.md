# Pré-enregistrement — signaux coûteux contre parole gratuite (bot 0.10.114)

**Décision d'auteur du 2026-11-15.** Le banc du langage a appris un coefficient NÉGATIF pour les actes de langage
(β ≈ −0,49 sur 150 questions de conflits) : les engagements rapportés surestiment l'issue. Hypothèse de l'auteur :
l'intention de celui qui parle prime sur l'information principale. Théorie : la parole gratuite d'un acteur qui a
intérêt à peser est à réduire (Crawford et Sobel, *Econometrica* 50, 1982) ; une menace n'est crédible que si elle coûte
à son auteur, en lui liant les mains ou en le faisant payer d'avance (Fearon, *Journal of Conflict Resolution* 41,
1997). Commité AVANT tout passage.

## Mesure (`banc_signaux.py`)
Les mêmes questions de conflits (ACLED) du banc du bras A, recherche bornée avant la date. gpt-5-mini qualifie chaque
extrait : acte ou description, sens, qui parle (acteur concerné, adversaire, tiers, média), et ce que l'acte coûte à
son auteur (gratuit : parole seule ; coûteux : engagement public devant son camp, mobilisation, dépense, décision
officielle ou juridique). Variables : G (solde des actes gratuits) et K (solde des actes coûteux), chacun
(hausse − baisse) / (nombre + 1).

## Modèle (fixé ici)
logit(p) = logit(A) + βG·G + βK·K ; maximum a posteriori (a priori normal 0, écart-type 1) ; validation croisée « un jeu
laissé de côté ». Hypothèse sur les signes, rapportée sans verdict : βG < 0, βK > 0. Le locuteur est enregistré, sans
paramètre dans ce passage.

## Critère (essai `signaux_couteux`)
Sur les 100 premières questions (ordre du banc du bras A) : perte log du modèle inférieure à celle de A seul, et
intervalle de l'écart (bootstrap par blocs « jeu ») entièrement sous 0 au niveau corrigé. Second regard à 200 si
assez de questions.

## Limites déclarées
Mêmes questions que le banc du langage (dont il est la suite) : ce n'est pas une confirmation sur données fraîches.
Le même modèle qualifie les extraits et produit A. La distinction gratuit / coûteux n'est pas vérifiée par un second
codeur.
