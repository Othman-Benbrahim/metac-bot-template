# Pré-enregistrement — ombre « absence » sur les états nuls (2026-11-13, bot 0.10.70)

**Décision d'auteur du 2026-11-13.** Critère entré dans le code au commit `b2be8b8`.

## Constat qui l'a fait naître (exploratoire, ne juge pas l'hypothèse)
Banc ForecastBench, jeu du 2026-10-25 (résolution 2026-11-01), 134 questions distinctes résolues :
- B est calibré sur l'ensemble : 60 OUI pour 59,5 attendus.
- États nuls d'absence (structure absente, carte visée absente) : 11 questions, 1 OUI pour 3,9 attendus selon B
  (P ≤ 4,5 % unilatéral ; environ 13 % une fois corrigé pour trois groupes regardés après coup).
- Angles morts : 5 questions, 4 OUI pour 2,3 attendus (surtout des duels d'actions à B = 0,5) ; indéterminés : 8, 3
  OUI pour 4,0.
- Questions où C monte au-dessus de B : 34, 13 OUI ; C en annonçait 20, B 14,2.

## Hypothèse
Sur les états nuls d'absence **à venir**, l'ombre « B avec sa cote × 0,5 » bat B en perte log.

## Règles
- Facteur 0,5 fixé, jamais ajusté sur les données.
- Seules comptent les lignes écrites à partir de la version 0.10.70 du bot ; les 11 lignes ci-dessus sont rapportées
  à part (« avant enregistrement »).
- Lecture : séquence de confiance de `score_registre` (e-valeur, hypothèse principale de sa famille, niveau 0,05).
- L'ombre n'est jamais postée : un état nul poste B ; elle reste une ombre jusqu'à une décision d'auteur datée.
- Portée : si elle tient, c'est un premier élément pour rouvrir la décision 9 (multiplicateurs ≥ 1, C ne peut que
  monter).
- Depuis le 2026-11-14 (0.10.98) : soumise à la règle d'adoption commune (`regle-adoption.md`).
