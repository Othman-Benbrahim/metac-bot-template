# Médiane de trois tirages du bras A, en ombre (préenregistrement, 2026-11-28)

Décision de l'auteur (01 h 37), qui revient sur sa position du 18/11 (ne pas compenser le bruit par plusieurs tirages)
après explication : mesurer d'abord, en ombre. Origine : effet de l'agrégation dans les analyses publiées (+1 799
points en 2025 sur 19 bots ; 86 % des gagnants de l'automne 2025 ; non significatif au printemps 2026), relayé dans
`claude/analyses-metaculus-reglages-2026-11-28.md`.

## Dispositif
- Variable du dépôt `ALPHABET_A_ESSAIS = 3` (réglée par l'auteur) : deux tirages de plus du bras A, même recherche,
  scellés dans le registre (`essais_A`), **jamais postés**. Coût : environ deux appels du modèle principal en plus par
  question binaire ; la recherche n'est pas refaite.
- Rien ne change dans ce qui est posté.

## Question
Sur les questions binaires publiées et résolues, la médiane des trois tirages de A fait-elle mieux que le tirage
unique de A ? La dispersion des tirages prédit-elle l'erreur ?

## Déclenchement
Une seule fois, à **60 questions binaires résolues** portant trois tirages de A. Second et dernier passage à 120.

## Critère
- **Perte logarithmique moyenne (médiane des 3 − tirage unique) < 0, intervalle à 90 % qui exclut 0** (rééchantillonnage
  des questions, 10 000 tirages, graine 20261128).
- Rapportés sans effet sur le critère : Brier ; corrélation de Spearman entre l'écart (max − min) des trois tirages et
  l'erreur |p − issue| de la médiane ; détail selon le bras posté (M, brique, autre).

## Conséquence prévue
Critère atteint : l'auteur décide si la médiane remplace le tirage unique dans le bras A (et donc dans ce qui en
dépend : M, juge, garde-fou). Sinon, rien ne change, et les tirages supplémentaires peuvent être éteints
(`ALPHABET_A_ESSAIS = 1`) pour économiser.

## Limites déclarées
- Trois tirages du même modèle sur le même dossier font des erreurs liées : la médiane réduit le bruit de tirage, pas
  une erreur commune au dossier (leçon de No-Stream). Des modèles différents seraient un autre essai.
- Le tirage unique de référence est le premier tirage, celui qui a été réellement utilisé.

Conflit d'intérêts déclaré : la procédure est rédigée par un modèle d'Anthropic.
