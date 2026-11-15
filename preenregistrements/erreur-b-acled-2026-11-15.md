# Erreur du taux de base ACLED « dix fois plus » — constat et conséquences (2026-11-15, bot 0.10.127)

## L'erreur
Les questions ACLED de ForecastBench ont deux formes :
1. « plus d'événements que la moyenne sur 30 jours » : la valeur au gel m est la moyenne ; seuil m ;
2. « plus de DIX FOIS plus que UN PLUS la moyenne » : la valeur au gel m vaut 1 + moyenne ; le seuil est 10·m.

`b_acled` calculait P(N > m) pour les deux formes. Sur la forme 2, B annonçait environ 40 % au lieu d'une valeur
quasi nulle. Le bras A recevait ce B (« pars du taux de base ») et s'ancrait dessus. Corrigé en 0.10.127.

## Ampleur, sur les 150 questions ACLED du banc du bras A (perte log, plus bas = mieux ; descriptif)
| | n | oui | B ancien | B corrigé | A |
|---|---|---|---|---|---|
| dix fois | 74 | 0 | 0,511 | 0,001 | 0,415 |
| une fois | 76 | 18 | 0,475 | 0,475 | 0,471 |
| toutes | 150 | 18 | 0,493 | **0,241** | 0,443 |

Sur toutes les questions du banc A (284, avec FRED et DBnomics) : A 0,543 ; B corrigé 0,437 ; ½A+½B avec B corrigé
0,441. Sur FRED et DBnomics, A, B et ½A+½B sont à moins de 0,008 l'un de l'autre.

## Ce qui tombe ou doit être réexaminé (décisions de l'auteur à prendre)
- **Surconfiance de A sur les conflits (30 % annoncés pour 12 % observés)** : venait surtout de l'erreur. Sur la forme
  « une fois », A annonce 27 % pour 24 % de oui.
- **`recalibrage_conflits` et `silence`** : paramètres figés sur un A ancré sur le B faux ; leur prémisse ne tient plus.
- **`jugements_intermediaires`** : l'hypothèse (réduire la surconfiance de A) perd son appui principal ; le banc reste
  testable mais avec le B corrigé.
- **`aiguillage`** (A bat B sur les conflits) : verdict obtenu contre le B faux.
- **`a_plus_b`, adopté pour les strates 7 et 13 (`POSTER_AB`)** : la preuve venait en partie des questions ACLED où B
  était faux ; avec B corrigé, ½A+½B ne bat plus B sur ces données.
- **`indicateurs`** : le critère comparait à A recalibré sur le B faux ; voir ci-dessous.

## Indicateurs par pertinence (demande de l'auteur, 2026-11-15 ; 76 questions « une fois », 18 oui ; descriptif)
Correspondance fixée d'avance : coupures d'internet → manifestations, émeutes, combats ; conseils aux voyageurs →
tous les types de violence et de mobilisation ; pluie → manifestations et émeutes ; attention Wikipedia →
manifestations et développements stratégiques. B gardé tel quel, seul l'effet des indicateurs appris (un jeu laissé
de côté) :

| | perte log |
|---|---|
| B corrigé seul | 0,4753 |
| + 4 indicateurs partout | 0,4963 |
| + 4 indicateurs, cases pertinentes | 0,4744 |
| + pluie seule (manifestations, émeutes) | 0,4644 |
| + pluie et conseils aux voyageurs, cases pertinentes | **0,4605** |

Placés partout, les indicateurs dégradent ; placés là où ils ont un sens, ils cessent de nuire et la pluie apporte
un petit gain (13 questions seulement). Sens observé : pluie sous la normale → davantage d'émeutes et de
manifestations. Constat sur questions déjà lues, la pluie ayant été repérée avant ce calcul : à confirmer sur des
questions fraîches, pré-enregistrement à écrire.
