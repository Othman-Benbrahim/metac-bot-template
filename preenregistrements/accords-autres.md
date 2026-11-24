# Sous-famille « autres accords » : consentements requis — procédure écrite avant le calcul

Décision de l'auteur, 2026-11-24, 16 h 52 : « On commence » (rencontres et autres accords, puis annonces et produits) ;
l'auteur est absent, travail sans relecture immédiate. Nouvel essai sur la sous-famille « autre » (11 questions ;
l'essai précédent, part de oui de la sous-famille, avait échoué sur 2026 de 0,008). Une passe ; sans retour.

## Règle (mise_au_point/accords_autres.py)
Tranche de consentements requis par les règles écrites de accords_requis.accords (2026-11-20, inchangées) : « 1 »
(un décideur seul), « 2 » (deux parties, deux chambres, une ratification), « 3+ ». Probabilité = part de oui des
questions de la même tranche sur tout le corpus résolu HORS famille accords, tirée vers la part de oui de ce corpus
(poids 5). Mesure extérieure aux 11 questions évaluées.

## Évaluation (une passe)
Référence = part de oui de la famille accords hors groupe ; mélange d'un quart plafonné à 15 points ; branchement si
(1) règle < référence, (2) mélange < référence, (3) règle < référence sur les questions de 2026. Les taux par tranche
sont écrits dans ecosystemes/accords-autres.json ; dans le bot, même mélange, même plafond, journal scellé.
