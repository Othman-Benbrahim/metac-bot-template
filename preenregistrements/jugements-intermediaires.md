# Pré-enregistrement — jugements intermédiaires avant le jugement global, conflits (bot 0.10.124)

**Décision d'auteur du 2026-11-15 (11 h 37)** : « Cible ce qui nous intéresse, et sert toi en » (thèse d'Olivier
Sibony, *Comprendre et prévenir l'erreur récurrente dans les processus de décision stratégique*, Paris-Dauphine, 2017,
NNT 2017PSLED039, chap. 4 § 4.3-4.5 et chap. 5 cas n° 5). Commité AVANT tout passage.

## L'idée
Dans un comité qui décide d'un bloc, chacun prend position puis cherche des raisons : l'effet de halo et la
« cohérence exagérée » rendent le tableau plus simple et plus sûr qu'il n'est. La méthode des **jugements
intermédiaires** (Sibony, cas « VC Co. » ; Kahneman, Lovallo et Sibony, *HBR* 2019) sépare la décision en quelques
critères fixés d'avance, notés **un par un par rapport à une classe de référence** (quartiles), et ne laisse le
jugement global qu'**après**, les notes sous les yeux. Effet décrit : des décideurs **moins confiants**, parce que les
faiblesses restent visibles.

Notre constat sur les conflits va dans le même sens : A annonce 30 % en moyenne pour 12 % de OUI. Hypothèse : si le
modèle note d'abord des critères séparés, son jugement final sera moins gonflé, sans recalibrage appris.

C'est aussi un rôle direct pour l'alphabet : les critères sont des cartes (CROISSANCE, RÉCIPROCITÉ, TRACE·MÉMOIRE,
SEUIL, CONTRAINTE, PÉRIODICITÉ, PROPORTION), utilisées comme **grille de jugement**, pas comme multiplicateurs.

## Protocole (banc_m.py)
Pour chaque question ACLED, une seule recherche bornée avant la date, puis, sur les MÊMES entrées :
- **A'** : la consigne du bras A, inchangée (un appel) ;
- **M** : deux appels. (1) Sept notes de 1 à 4, chacune par rapport à l'ordinaire de ce pays pour ce type
  d'événement sur l'année passée, avec une phrase de justification, **sans aucune probabilité** ; (2) le jugement
  final, qui voit le taux de base calculé, les derniers points de la série et les sept notes, mais plus les extraits
  bruts.
Modèle : gpt-5-mini (Azure), température 0,2.

Les sept critères : tendance (CROISSANCE), engagements datés (RÉCIPROCITÉ), couverture et fraîcheur des informations
(TRACE·MÉMOIRE), déclencheur proche (SEUIL), freins et riposte adverse (CONTRAINTE), calendrier (PÉRIODICITÉ),
distance au seuil de résolution (PROPORTION).

## Questions
Questions ACLED de ForecastBench résolues, jeux postérieurs au 2026-07-01 hors jeux vus par le banc de l'alphabet,
**absentes de `silence-vus.txt`** (les 285 questions ACLED déjà lues : le constat de surconfiance vient d'elles).
Ordre fixé d'avance : entrelacé entre les jeux (rang SHA-1 de l'identifiant dans son jeu, puis jeu), comme au banc A.

## Critère (règle d'adoption commune, niveau corrigé ; second regard à 200)
**`jugements_intermediaires`** : sur les 100 premières questions nouvelles, perte log de M inférieure à celle de A',
intervalle de l'écart (bootstrap par blocs « jeu ») entièrement sous 0.

## Descriptif seulement (pas de verdict)
- M contre A' recalibré avec les paramètres figés de `silence-et-calibrage.md` (logit p = −1,354 + 0,775·logit A') :
  la structure fait-elle mieux, ou aussi bien, qu'un recalibrage appris ?
- Modèle linéaire sans jugement global (Meehl, Dawes) : logit p = w₀ + w₁·logit(B) + Σ βₖ·(noteₖ − 2,5), appris en
  validation croisée « un jeu laissé de côté », a priori normal (w₀ : 0 ± 1 ; w₁ : 1 ± 1 ; βₖ : 0 ± 0,5).
- Probabilité moyenne annoncée par A' et par M, contre la fréquence observée.

## Limites déclarées
Les deux appels de M ne suppriment pas tout halo (les sept notes sont données dans le même appel). Le jugement final de
M ne voit plus les extraits bruts : un gain ou une perte peut venir de cette information retirée autant que de la
structure ; c'est le prix d'une séparation nette. A' n'est pas la même série que le A du banc A (autre recherche),
d'où sa présence dans le même passage. S'il ne reste pas 100 questions nouvelles, le verdict attend les jeux suivants.
