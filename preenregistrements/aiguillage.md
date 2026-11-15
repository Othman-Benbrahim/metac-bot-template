# Pré-enregistrement — aiguillage A / B selon la nature de la question (2026-11-15)

**Décision d'auteur du 2026-11-15.** Le jugement du modèle (A) ne s'applique que là où trois conditions sont réunies :
le phénomène est humain, les textes en parlent avant qu'il arrive, l'information n'est pas déjà intégrée dans un chiffre
(prix, moyenne). Ailleurs, le taux de base (B). Le tri est fait par le CODE, sur un critère connu avant l'issue.

## Origine, déclarée
L'idée vient d'un résultat vu : au premier passage du banc du bras A (109 questions), A bat B surtout sur ACLED (34
questions, perte log 0,435 contre 0,472). C'est un sous-groupe repéré après coup ; il doit être confirmé sur des
questions jamais lues. Ce document est commité pendant le second passage du banc A (exécution 43659010064, en cours,
résultats non consultés).

## Règle d'aiguillage (fixée ici)
- Questions ACLED (conflits, manifestations, émeutes : événements humains couverts par la presse) : **A**.
- Toutes les autres sources (séries économiques, températures, actions) : **B**.

## Critère
Sur les **100 premières questions ACLED nouvelles** du banc du bras A (hors questions listées dans
`aiguillage-vus.txt`, mêmes modèles A : gpt-5-mini), dans l'ordre du banc (entrelacé) : perte log de A inférieure à celle
de B, et intervalle de l'écart (bootstrap par blocs « jeu », 2 000 tirages, graine 0) entièrement sous 0 au niveau
corrigé de la règle d'adoption commune. Second regard à 200. Hors ACLED, l'aiguillage donne B : aucun écart à juger.
Si le critère tient : décision d'auteur datée pour que le bot poste A sur les questions de ce type.
