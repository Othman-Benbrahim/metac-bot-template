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
