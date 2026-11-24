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

## Résultat du passage unique (2026-11-24, 18 h 56) et application décidée par l'auteur (18 h 58)
226 relations : 4 « vérifiées », 7 « contestées », 63 non tranchées, 152 non testables (76 historique commun trop
court, 61 effet « ± », 15 délai d'années).
Défaut de la procédure, reconnu : elle n'excluait pas les relations dont les deux bouts portent la même série, ou une
série et sa propre composante. Trois des quatre « vérifiées » en relèvent (passage_acte → passage_acte et
disponibilite → disponibilite : même série, corrélation 1 au décalage 0 ; navires d'Ormuz → pétroliers d'Ormuz : un
total et sa partie). Elles ne sont pas des vérifications.
Application (décision de l'auteur) :
1. energie → prix_conso (inflation mondiale) : statut « verifie » (Brent → inflation américaine sur 12 mois,
   r = 0,267, n = 128 mois, seuil 0,221) ; champ « verification » dans la fiche.
2. Les sept « contestées » ne sont pas marquées contestées : la série choisie représente sans doute mal le compartiment
   (ex. le taux à 10 ans pour le « budget ») ; champ « verification » : « série à revoir ».
3. Règle ajoutée pour tout passage futur : relation exclue si les deux bouts ont la même série, ou si l'une est une
   composante de l'autre (même source et même lieu, ex. portwatch:ormuz:*).
