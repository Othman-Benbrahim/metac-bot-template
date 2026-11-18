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

## Réplication sur les séries (ajout du 2026-11-18, 4 h 08, AVANT le calcul ; décision d'auteur, 4 h 06)
Premier passage (2026) : non tranché de justesse (−0,015, [−0,034 ; +0,001]), gain surtout sur Polymarket et INFER.
Choisir ces plateformes APRÈS avoir vu le résultat serait un choix a posteriori ; on le soumet donc à des données qui
n'ont jamais servi à cette comparaison : les questions des jeux de 2025 (cohorte complète).
- Questions : Polymarket et INFER seulement, jeux du 2025-01-01 au 2025-12-31.
- Comparaison : p_SD contre p_S (mêmes calculs qu'au premier passage), bootstrap par question, risque
  `es.risque_corrige(1)` ; « sans doublons meilleure sur les séries » si la borne haute < 0.
- Si c'est confirmé : la variante devient le départ pour ces deux plateformes seulement (décision d'auteur datée) ;
  sinon, le gain de 2026 est tenu pour du hasard.

### Résultat de la réplication (2026-11-18, 4 h 10)
1 158 questions (Polymarket 1 031, INFER 127 ; 8 % de oui) : semblables 0,306, sans doublons 0,312 ; écart +0,006,
intervalle corrigé [−0,007 ; +0,014] → **non reproduit** (même sens contraire sur les deux plateformes). Le gain de 2026
est tenu pour du hasard ; les semblables actuelles restent le départ partout.
