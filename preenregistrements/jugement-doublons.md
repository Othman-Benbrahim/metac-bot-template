# Questions semblables sans doublons (préenregistrement, 2026-11-18, 4 h 05)

Décision d'auteur du 2026-11-18 (4 h 02, « Oui, tu peux y aller »), d'après un schéma de Sandijs Aploks (LinkedIn,
prévision par récupération de souvenirs avec filtrage des doublons) et DuoTS (« diversity-aware retrieval »).
Code : `banc_jugement.py` (p_SD) ; essai `jugement_doublons`. Aucun modèle de langue.

## Le défaut visé
Parmi les 50 voisines d'une question, une même question peut revenir plusieurs fois (reposée dans plusieurs jeux) ou
sous des formes presque identiques (« avant mars », « avant juin ») : une seule issue pèse alors plusieurs fois.

## Variante, fixée ici
Mêmes voisines candidates que SEMBLABLES (résolues et closes avant le jeu, jamais la même question), parcourues de la
plus semblable à la moins semblable ; une voisine est retenue sauf si (1) une instance de la même question (même
plateforme, même identifiant) est déjà retenue, ou (2) son cosinus TF-IDF avec une voisine déjà retenue dépasse 0,8.
On s'arrête à 50 voisines retenues. p_SD = (Σ w·issue + 5·R1) / (Σ w + 5), w = cosinus avec la question jugée.

## Jugement
Perte log SD − S (la version actuelle, adoptée comme départ) sur la cohorte complète des jeux de 2026, bootstrap par
question, risque `es.risque_corrige(1)` ; meilleure si la borne haute < 0, moins bonne si la borne basse > 0. Rapportés :
par plateforme, et sur les seules questions Metaculus.

## Attendu (Claude)
Petit gain ou rien : les doublons ne touchent que les questions qui ont des séries ; la variante peut aussi perdre, si la
répétition d'une série porte une information réelle (une série qui finit toujours « non »).
