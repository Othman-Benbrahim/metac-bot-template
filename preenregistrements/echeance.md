# B à l'échéance : la règle de résolution réelle des séries (préenregistrement, 2026-11-19, 19 h 20)

Décision d'auteur du 2026-11-19, 18 h 58 (« tu peux tout faire »), à la suite de la feuille de route « mesures et
indicateurs » (points 1 et 8 : distance au seuil, mécanique de résolution). Essai `b_echeance`. Aucun modèle de langue.
Ombre : rien dans le bot.

## Ce qui est corrigé
ForecastBench résout « la valeur au jour T dépassera-t-elle la valeur au jour D ? » en prenant, pour un jour sans
observation, la DERNIÈRE observation antérieure. Le B actuel (`b_hausse`) compare chaque point au premier point
postérieur à t + h : pour une série mensuelle à 7 jours, il compare deux mois successifs (environ une chance sur deux de
hausse), alors qu'à la résolution, sans observation datée dans la fenêtre, la valeur n'a pas bougé et la réponse est
« non ». Constat qui a motivé l'essai (descriptif, vu AVANT la règle) : sur 105 questions DBnomics du rétrospectif, 26 %
de « oui » ; l'audit de B signalait déjà une série à 56 % annoncés pour 19 % observés.

## Règle (fixée ici, code : `banc_forecastbench.b_echeance`)
- Mêmes points que B : 5 ans strictement avant D. Valeur d'un jour = dernière observation datée ≤ ce jour.
- Calendrier des observations par l'écart médian s : ≤ 4 jours ou 5 à 10 jours → jour de la semaine ; 25 à 35 → jour du
  mois ; 80 à 100 → (mois mod 3, jour) ; 170 à 190 → (mois mod 6, jour) ; 350 à 380 → (mois, jour). Clés relevées sur
  les deux dernières années. Autre écart : pas de B_echeance (question écartée de la comparaison).
- Classe d'une fenêtre (a, a + h] : contient-elle au moins un jour dont la clé est observée ?
- Historique : chaque jour civil d des 5 ans tel que d + h ≤ dernière observation ; « hausse » si valeur(d + h) >
  valeur(d), comptée dans la classe de sa fenêtre. P = (k + ½)/(n + 1) dans la classe de la fenêtre (D, D + h].
  Moins de 10 fenêtres dans la classe : pas de B_echeance.

## Critère
Celui des ombres de B (`score_registre.critere_ombre_b`, perte log, bootstrap par blocs « jeu × source », risque
corrigé d'`essais.py`) : B_echeance remplace B si l'intervalle de l'écart est entièrement sous 0 sur les 100 premières
questions admissibles (second regard : 200). Descriptif publié à part : par source et par classe de fenêtre. Même en cas
de succès, le passage en officiel est une décision d'auteur datée, et rien côté Metaculus avant le tournoi.
