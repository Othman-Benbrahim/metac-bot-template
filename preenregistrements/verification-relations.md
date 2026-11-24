# Couche écosystème, étape 1 : vérification des relations des fiches — procédure écrite avant le calcul

Décision de l'auteur, 2026-11-24, 18 h 54 (« Yep ») sur le schéma en cinq étapes (vérifier les relations, rattacher
les questions, lire l'état de l'amont, appliquer là où le sens du oui est lisible, tester là où la carte diverge du
bot). Une passe ; sans retour. Lus avant : le nombre de relations testables (226) et quelques exemples, aucun calcul.

## Règle (mise_au_point/verifier_relations.py)
- Relation testable : les deux compartiments ont une trace collectée avec adaptateur ; première série de chacun.
- Effet « + » ou « − » seulement ; « ± » non testable.
- Délai écrit dans la fiche → fréquence (semaine, mois) et décalages ; délais d'années ou plus : non testables.
- Statistique : corrélation moyenne, sur les décalages, entre variation de l'amont et variation de l'aval décalée.
- n ≥ 20 périodes ; seuil |r̄| > 2,5/√n.
- Verdicts : vérifié (bon signe, seuil dépassé), contesté (signe opposé, seuil dépassé), non tranché, non testable.

## Limites déclarées
Corrélation de variations, pas causalité ; 226 relations testées au même seuil : quelques « vérifiées » peuvent l'être
par hasard (au seuil 2,5, environ 1 sur 80 pour une relation nulle) ; une seule série par compartiment ; les relations
lentes (années) restent non testables.

## Application
Le calcul n'écrit aucun statut. Ensuite : statut des relations vérifiées → « verifie », contestées → « conteste »,
dans les fiches (statuts admis par ecosystemes.py), carte régénérée ; seules les relations « verifie » entreront dans
la couche du bot (étapes 2 à 5, procédure à part).
