# Pré-enregistrement — recalibrage de A et silence de la presse, conflits (bot 0.10.123)

**Décision d'auteur du 2026-11-15 (11 h 27).** Deux constats faits sur les 150 questions ACLED du banc du bras A, à
confirmer sur des questions JAMAIS lues :
1. **Calibrage** : A annonce 30 % en moyenne pour 12 % de OUI ; recalibré (Platt), il gagne en validation croisée
   (perte log 0,414 contre 0,443).
2. **Silence** (idée de l'auteur : ce qui n'est pas dit est une information) : sans aucun extrait de presse trouvé
   avant la date (80 questions), 7,5 % de OUI pour 11,8 % annoncés par A recalibré ; avec 1 à 3 extraits, 21 % pour
   13 %.
Commité AVANT tout passage sur les questions nouvelles.

## Paramètres figés ici (appris sur les 150 questions antérieures, `juge_silence.py`)
- A recalibré : logit(p) = −1,354 + 0,775·logit(A).
- Silence : logit(p) = logit(A recalibré) − 0,4405·S ; S = 1 si l'étape d'extraction du banc du langage n'a trouvé
  aucun extrait de presse avant la date.

## Questions
Questions ACLED du banc du bras A (gpt-5-mini) absentes de `silence-vus.txt` (les 285 lues au moment du commit), dans
l'ordre du banc. Passage prévu : banc du bras A (sources `acled`), puis banc du langage (qui donne le nombre d'extraits).

## Critères (règle d'adoption commune, niveau corrigé ; second regard à 200)
1. **`recalibrage_conflits`** : sur les 100 premières questions nouvelles, perte log de A recalibré inférieure à celle
   de A, intervalle de l'écart (bootstrap par blocs « jeu ») entièrement sous 0.
2. **`silence`** : sur les 100 premières questions nouvelles qui ont le nombre d'extraits, perte log du modèle du
   silence inférieure à celle de A recalibré, aux mêmes conditions.

## Limites déclarées
Une partie du silence peut venir du moteur de recherche (petits territoires peu couverts) : silence réel et angle mort
ne sont pas distingués. S'il ne reste pas 100 questions ACLED nouvelles, le verdict attend les jeux suivants.
