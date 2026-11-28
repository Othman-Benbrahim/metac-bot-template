# Garde-fou des briques : jugé comme une assurance (préenregistrement, 2026-11-28)

Décision de l'auteur (01 h 30 - 01 h 37) : le garde-fou n'est pas fait pour augmenter le score moyen, mais pour éviter
qu'il se brise ; mesure d'urgence posée sans test (0.10.517, seuils fixés avant tout résultat : brique au-delà de
10 % / 90 %, contredite de plus de 40 points par le bras A, ramenée à 10 % / 90 %). Ce texte fixe **comment le juger sur
ce rôle**, avant toute issue. Aucun modèle de langue, aucun crédit.

## Données
`registre/journal-garde-fou.jsonl` : chaque déclenchement, avec la probabilité de la brique avant (p_brique) et après
(p_garde_fou) le garde-fou. Issues : `registre/issues.jsonl`. Seules les questions où le garde-fou s'est déclenché comptent.

## Mesures (rapportées, sans critère de branchement : le garde-fou reste en place sauf décision de l'auteur)
1. **Coût de l'assurance** : somme des pertes logarithmiques supplémentaires quand la brique avait raison
   (perte(p_garde_fou) − perte(p_brique) > 0).
2. **Sinistres évités** : somme des pertes évitées quand la brique avait tort.
3. **Bilan net** : 2 − 1.
4. **Pire cas** : la plus grosse perte sur une seule question, avec et sans garde-fou.

## Regard
Une première fois à 10 déclenchements résolus, puis à 30. Les déclenchements seront rares ; le verdict peut prendre
des mois, ce qui est acceptable pour une assurance.

## Lecture prévue
- Bilan net positif, ou pire cas nettement réduit : le garde-fou fait son travail.
- Bilan net négatif **et** aucun pire cas évité à 30 déclenchements : l'auteur décide s'il resserre les seuils
  (par exemple 5 % / 95 %) ou s'il le retire. Les exemptions par famille (`GF_EXEMPTES`) se décident sur ces mêmes
  chiffres, famille par famille.

Conflit d'intérêts déclaré : la procédure est rédigée par un modèle d'Anthropic.
