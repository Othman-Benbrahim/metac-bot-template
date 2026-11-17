# Hypothèses géographiques et mathématiques (préenregistrement, 2026-11-17, 19 h 55)

Décision d'auteur du 2026-11-17 (19 h 47, « Oui, merci »), après le constat : M11 n'a été testé que sous une forme
fruste (nombre de voisins en hausse) et contre l'ancien taux de base ; les pistes géographiques
(claude/geographie-notions-et-cartes.md) et mathématiques (claude/regimes-causaux-principes-actifs.md,
claude/tri-imag-hal-2026-11-17.md) étaient restées en attente. Tout est fixé ici avant le moindre passage.
Référence pour les tests 1 et 2 : la classe de référence pondérée (adoptée comme B du banc GDELT).

## Test 1 — M11 en grappe (Hägerstrand ; balayage spatial, Smida et al.)
- Questions : banc GDELT « plus après qu'avant ? », manifestations et émeutes.
- Voisin en hausse : ln((14 j récents + 1) / (14 j précédents + 1)) > 0,4, même type d'événement.
- GRAPPE : au moins 2 voisins en hausse ET au moins la moitié des voisins couverts.
- Attendu : δ > 0 (plus de « oui » que B).

## Test 2 — Signes avant-coureurs d'un basculement (Scheffer et al., 2009)
- Questions d'escalade : « au moins 2 × le niveau habituel (médiane des fenêtres de 30 jours passées) dans les 30 jours ? »,
  posée si le niveau ≥ 3 ; manifestations, émeutes, force.
- B : classe pondérée (z, m sur les fenêtres ; même type, tous pays).
- ALERTE : sur les 90 jours avant d0, variance de la seconde moitié ≥ 1,5 × la première ET autocorrélation de rang 1
  plus haute d'au moins 0,1.
- Attendu : δ > 0.

## Jugement des tests 1 et 2
δ = ln((O + 0,5) / (E + 0,5)) sur la case « état présent » en exploration (avant 2025-11-01), appliqué à B en
confirmation ; jugé si au moins 10 questions aux deux étapes ; bootstrap par mois ; risque `es.risque_corrige(1) / k`
(k = cases jugées du test) ; confirmé si la borne haute < 0.

## Test 3 — Loi de Richardson (queue lourde des morts ; Valiquette et al., arXiv 2305.17095)
- Questions : morts UCDP (« best ») dans 30 jours, « au moins N ? », N = ⌈quantile 90 % des fenêtres passées⌉ (au moins
  12 fenêtres, depuis 2022-01-01) ; 25 pays ; relevés au plafond retirés.
- B_bot (fenêtres passées, règle de compter) contre B_ln (lognormale sur ln(x + 1)) ; B_bn (binomiale négative) rapportée.
- Critère : confirmation (d0 ≥ 2025-11-01), bootstrap par mois, risque `es.risque_corrige(1)` ; lognormale meilleure si
  la borne haute < 0. Seuil « 2 × médiane » rapporté.
- Attendu : B_ln ≥ B_bn ; face à B_bot, incertain (le bot compte des fréquences sans loi, ce qui ne sous-estime pas la
  queue par construction, mais est bruité à 12-40 fenêtres).

## Pas testé maintenant
Calendrier spatial (soudure, transhumance) : deux ans d'historique seulement, trop peu de répétitions des saisons.
Barrière linguistique : seulement si la grappe montre quelque chose (Ockham).

## Richardson à la bonne échelle (ajout du 2026-11-17, 20 h 15, avant tout passage ; décision d'auteur, 20 h 06)
Le test 3 (clos) ajustait une queue lourde aux morts MENSUELS d'un pays ; Richardson parle de la TAILLE des événements,
avec une loi commune à tous, la fréquence seule étant locale. `banc_richardson_evenements.py`, essai
`richardson_evenements` :
- unité : le plus grand événement d'un carreau PRIO-GRID un jour donné (UCDP, `max_morts`) ;
- questions par pays, premier de chaque mois depuis 2016 : « au moins un événement de T morts ou plus dans les 30 jours ? »
  (T = 100 jugé ; T = 25 rapporté) ;
- B_bot : fenêtres disjointes passées du pays (règle de compter) ;
- B_rich : 1 − exp(−λ · 30 · S(T)), λ = événements par jour du pays sur 365 jours, S(T) = S(10) · (T/10)^(−α), α de Hill
  sur les tailles ≥ 10 de TOUS les pays sur 5 ans avant d0 ; variante empirique (S(T) comptée) rapportée ;
- critère : confirmation d0 ≥ 2024-01-01, bootstrap par mois, risque `es.risque_corrige(1)` ; meilleur si borne haute < 0.
- Attendu : gain surtout pour les pays dont le passé ne compte aucun événement de cette taille (le bot dit alors 1/(2n),
  la loi universelle dit mieux).

## Richardson conditionnel (ajout du 2026-11-17, 20 h 30, AVANT toute question nouvelle ; décision d'auteur, 20 h 27)
Piste née d'un diagnostic a posteriori (run 44155280927, NON préenregistré) : la loi commune perd sur les pays sans
grand événement passé (0,300 contre 0,197 pour le bot) et gagne sur les pays au passé meurtrier (0,499 contre 0,572).
Règle fixée ici, jamais ajustée ensuite :
- si le pays a connu au moins un événement de 100 morts ou plus dans les 5 ans avant d0 : B_rich (loi de Pareto commune
  × fréquence du pays, mêmes calculs) ; sinon : le taux du bot ;
- questions NOUVELLES seulement, de deux sortes : (1) les pays UCDP hors des 25 déjà vus (aucune de leurs questions n'a
  servi au diagnostic), toutes périodes depuis 2016 ; (2) pour les 25 pays, les mois à venir (d0 ≥ 2026-11-01) ;
- critère : contre le taux du bot, « au moins un événement de 100 morts dans 30 jours ? », bootstrap par mois, risque
  `es.risque_corrige(1)` ; la partie (1) juge dès qu'elle a 30 questions du sous-groupe « passé meurtrier ».
