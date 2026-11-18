# Préenregistrement : tendance de l'attention GDELT sur Metaculus seul, rejugée sur les questions d'avant 2026
2026-11-18, bot 0.10.293, écrit avant la requête des comptes de ces questions et tout calcul sur leurs issues.

Décision d'auteur du 2026-11-18, 20 h 52 (« oui, aux deux »). Origine : banc de la tendance à grande échelle (run
44383204002) : gain sur Metaculus (S 0,5667 → 0,5564, −0,010), vu APRÈS coup ; le tournoi se joue sur Metaculus.

## Données
- Apprentissage (déjà vues) : les 127 questions Metaculus distinctes de 2026 et leurs comptes (gdelt-bq-comptes-jeu).
- Test (jamais utilisées pour cette règle) : les 109 questions Metaculus distinctes d'avant 2026 (jeux de juillet 2024
  à décembre 2025), comptes par `gdelt_bq.py --mode comptes_metaculus_2025` (même filtre, 90 jours avant le jeu).
  Coût estimé : 70 à 90 Go de BigQuery (offre gratuite).

## Règle
Même tendance et même ajustement que tendance-attention-large.md, base S. β est appris UNE fois sur l'apprentissage
(grille −1 à 1, pas 0,05) puis appliqué tel quel au test : aucun réglage sur les questions jugées.

## Critère
Écart = perte log ajustée − perte log de S sur le test ; intervalle par question, un seul regard (tout_juger), risque
corrigé des essais ouverts (essai tendance_metaculus). Adoption seulement si l'intervalle corrigé est entièrement sous
zéro ; alors proposition d'usage dans le bot APRÈS le tournoi (décision du 2026-11-18, 19 h 40), sur décision datée.

## Limite connue
109 questions : seul un gain net se verra ; GDELT de 2024 couvre peut-être autrement les mêmes sujets.
