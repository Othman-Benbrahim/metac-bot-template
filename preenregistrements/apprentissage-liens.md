# Protocole — apprentissage empirique des liens carte → événement

**Enregistré le 2026-11-14, avant toute lecture d'apprentissage** (bot 0.10.80, commit `6396b72`,
`apprentissage_liens.py`). Modifications datées en bas de page.

## Principe (décision d'auteur)
Le sens et la portée d'un lien entre une carte ancrée et la carte de l'événement ne se décident pas : ils se mesurent
sur les issues de tests rétrospectifs.

Origine : diagnostic de la surconfiance de C (2026-11-14) — la levée de C au-dessus de B ne porte pas d'information ;
les liens les plus fréquents (CTR→SEU, HIE→POL) sont observés à l'inverse de la matrice.

## Données
- Banc ForecastBench ; duels d'actions exclus ; sources sans B calculé par le code exclues (0.10.86).
- Lecteur unique : Mistral Medium (`mistral/mistral-medium-latest`).
- Seules comptent les lignes écrites à partir de la version 0.10.80 du bot.
- Volume visé : 300 à 400 lectures. Plafond de 15 $ par passage (0.10.85).

## Variables
- Événement « apparaît » : un indicateur par lien « carte ancrée dans la strate de l'événement → carte de
  l'événement ».
- Événement « persiste » ou « disparaît » : un indicateur « persiste:CARTE » ou « disparait:CARTE ».

## Modèle
logit P(OUI) = logit(B) + Σ β_lien · présence. A priori normal centré sur 0, écart-type 0,5 sur chaque β (fixé). β
négatif permis.

## Découpage (modifié le 2026-11-14, 0.10.89, commit `c0cefd2`)
Les jeux ForecastBench les plus récents, **en entier**, jusqu'à couvrir au moins le tiers des lectures, servent au
jugement ; les jeux plus anciens à l'apprentissage. Un jeu n'est jamais coupé en deux.

## Statut de chaque lien (sur l'apprentissage)
Intervalle à 90 % (Laplace) : « pousse » au-dessus de 0, « retient » au-dessous, « ne dit rien » s'il contient 0 avec
au moins 30 cas, « indéterminé » sinon.

## Critère d'adoption (sur le jugement, lu une seule fois à la fin de l'apprentissage)
Au moins 100 lectures de jugement ; perte log du « C empirique » inférieure à celle de B ; intervalle de l'écart
apparié (bootstrap, 2 000 tirages, graine 0) entièrement sous 0, au niveau corrigé de la règle d'adoption commune
(`regle-adoption.md`). Même alors : d'abord en ombre ; le remplacement de la matrice est une décision d'auteur datée.

## Ombres calculées à côté (n'entrent pas dans le critère)
- Stabilité bootstrap (0.10.87) et par blocs (0.10.88) : descriptives (Neirz et al. 2026 : le bootstrap sur un seul
  échantillon donne des faux positifs persistants).
- Doubles permutés (0.10.96) : chaque lien comparé à 100 doubles de même rareté.
- Ancien découpage (0.10.89).

## Modifications datées
- **2026-11-14, 0.10.89 (décision d'auteur)** : découpage par jeux entiers. Motif : la coupe au nombre de lignes,
  triée par identifiant, mettait au jugement presque uniquement les questions FRED du dernier jeu. Les résultats des
  trois variantes avaient été vus avant la décision ; la règle a été choisie sur le principe, non sur les chiffres.
- **2026-11-14, 0.10.98** : critère au niveau corrigé, lecture unique à la fin.
