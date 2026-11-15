# Pré-enregistrement — taux de base par modèle de fondation (Chronos-2), séries (bot 0.10.132)

**Décision d'auteur du 2026-11-15 (14 h 14)** : « Oui » (ombre « B Chronos » proposée après lecture de Kaljevic,
Arzola et Zhang, arXiv 2610.07232, 2026 : Chronos-2 meilleur en prévision de charge électrique à court terme, sans
réentraînement). Commité AVANT tout calcul.

## Idée
Chronos-2 (Amazon, modèle ouvert, Apache 2.0) est pré-entraîné sur un grand nombre de séries et donne, sans
réentraînement, une distribution de la valeur future. La question ForecastBench « la série sera-t-elle plus haute dans
h jours ? » se lit directement sur cette distribution. Attente honnête : sur les séries financières, proches d'une
marche au hasard, un comptage simple est difficile à battre ; les séries régulières (températures, saisons) sont le
terrain le plus favorable.

## Règle (fixée ici, `banc_chronos.py`)
- Points de la série strictement avant D (ceux de B), les 1 024 derniers au plus (pas de limite de 5 ans : les séries
  mensuelles ont besoin de plus d'histoire).
- Pas = observations natives ; k = arrondi de h / écart médian entre observations (au moins 1), comme le B
  autorégressif.
- Modèle `amazon/chronos-2`, `chronos-forecasting` 2.3.2, sur processeur, quantiles d'entraînement du modèle ;
  F = fonction de répartition de la valeur au pas k, interpolée linéairement entre quantiles (bornée aux quantiles
  extrêmes).
- P(hausse) = (1 − part des intervalles de h jours sans changement, comptée comme B) × (1 − F(dernière valeur)),
  bornée à 0,001–0,999.
- Au moins 30 points, sinon rien.

## Questions
Questions de séries FRED et DBnomics de ForecastBench résolues, jeux postérieurs au 2026-07-01, ordre entrelacé fixé
d'avance (rang SHA-1 de l'identifiant dans son jeu, puis jeu). Toutes les formes comptent (l'idée ne vient pas de ces
questions). Ces questions ont déjà servi à d'autres essais sur B ; Chronos n'y a jamais été calculé.

## Critère (règle d'adoption commune, niveau corrigé ; second regard à 200)
**`b_chronos`** : sur les 100 premières questions, perte log de B Chronos inférieure à celle de B, intervalle de
l'écart (bootstrap par blocs « jeu × source ») entièrement sous 0.

## Descriptif
Résultat par source (FRED, DBnomics) ; combinaison ½ B + ½ Chronos (logits), sans verdict.

## Limites déclarées
Les données d'entraînement de Chronos-2 peuvent contenir des séries publiques proches (FRED) jusqu'à sa date de
publication (octobre 2025), donc antérieures à nos jeux (après le 2026-07-01) : pas de fuite d'issue, mais une
familiarité possible avec les séries.
