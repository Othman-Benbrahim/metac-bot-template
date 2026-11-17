# Pré-enregistrement : jugement aveugle au taux de base (2026-11-17)

**Décision d'auteur du 2026-11-17 (14 h 16)**, après la lecture de R. S. Sinclair, *Thinking and Writing: Cognitive
Science and Intelligence Analysis* (CIA, Center for the Study of Intelligence, 1984 ; réédition 2010) : « Oui, c'est
tout ce qui concerne l'indépendance des sources et de leur appréhension. » Fiche de lecture :
`claude/reference-sinclair-thinking-writing.md` (projet).

## L'hypothèse
Un modèle qui voit le taux de base B s'y ancre : son jugement n'est plus une source indépendante de B, et le combiner
avec B revient à compter B deux fois. Constat d'origine : lors de l'erreur ACLED du 2026-11-15, le bras A « s'ancrait »
sur le B faux qu'on lui montrait. Appui : Sinclair (le conservatisme des « chunks » : chaque donnée nouvelle est lue à
travers le cadre déjà posé) ; Meehl et Dawes (combinaison mécanique) ; essai des jugements intermédiaires (B + notes,
sans jugement global, était le meilleur en descriptif).

## Ce qui est comparé (mêmes questions, même recherche, même modèle gpt-5-mini, température 0,2)
- **A_voit** : la consigne du bras A, inchangée (`banc_a.consigne_a`).
- **A_aveugle** : la même consigne, sans la ligne « TAUX DE BASE CALCULÉ PAR LE CODE » et avec « Juge d'après les
  données et les recherches » au lieu de « Pars du taux de base, puis ajuste… ». La série brute reste (une donnée ; B
  est notre lecture de cette donnée).
- **C_aveugle** = logit moyen de A_aveugle et de B, poids 0,5 fixé ici, rien d'appris.

## Questions
ACLED « une fois » de ForecastBench, jeux postérieurs au 2026-07-01 (connaissances du modèle), qu'aucun banc à modèle
de langue n'a lues (registres `banc-*.jsonl` hors bancs d'indicateurs, et `silence-vus.txt`). Les jeux 2026-09-27,
2026-10-11 et 2026-10-25 sont admis bien que « vus par le banc de l'alphabet » : ce qui y a été regardé (la lecture C)
n'a servi à fixer aucun élément de cet essai. Effectif connu avant tout passage (comptage seulement) : 131 questions,
dont 122 dans ces trois jeux. Ordre : entrelacé par empreinte de la question (comme le banc des jugements
intermédiaires). Une question où le modèle dit connaître l'issue est exclue.

## Critère
Principal : C_aveugle contre A_voit, perte log, règle d'adoption commune (100 premières questions, intervalle par
blocs au risque corrigé pour le nombre d'essais ouverts ; `score_registre.critere_ombre_b`, essai `jugement_aveugle`).
« Critère atteint » : C_aveugle meilleur que A_voit au niveau corrigé. Même alors, rien ne change dans ce que le bot
publie sans décision d'auteur datée (le bot publie B aujourd'hui).
Descriptif, hors verdict : A_voit, A_aveugle, C_aveugle et B ; distance moyenne |A − B| des deux bras (un ancrage se voit
comme une distance plus courte quand le modèle voit B).

## Réserves
- 131 questions seulement : un seul regard possible à 100 ; le second (200) attendra de nouveaux jeux.
- Les trois quarts des questions viennent des trois jeux les plus récents : peu de blocs indépendants.
- Code : `banc_aveugle.py` (bot 0.10.227), workflow « Banc du jugement aveugle ».
