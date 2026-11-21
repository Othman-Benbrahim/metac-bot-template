# M avec position écosystémique contre M sans (préenregistrement, BROUILLON du 2026-11-21, à valider par l'auteur)

Décisions de l'auteur : piste écosystémique (2026-11-21), aucun test tant que la sélection n'est pas calibrée ; carte
v5 jugée calibrée à la relecture (≈ 94 % de rattachements justes sur le banc de M) ; option (b) : élargir aux questions
de jugement de 2026 pour donner de la puissance au test (14 h 26). Hypothèse de l'auteur : le modèle n'est pas
inopérant, il est inachevé ; il manque l'information ciblée sur le bon écosystème au bon moment.

## Rasoir d'Ockham
1. Une phrase : donner à M les règles sourcées qui gouvernent l'événement de la question, depuis sa situation de
   départ, améliore sa prévision.
2. Paramètres : aucun appris ; les règles sont choisies par la carte v5 (choix fermé, validé par le code).
3. Sens fixé d'avance : M1 meilleur que M0, et meilleur que le placebo M2.
4. Domaine : questions dont l'événement et la situation de départ sont ceux d'une règle sourcée (carte v5).
5. Plus simple ? Le placebo M2 (règles quelconques) mesure l'explication plus simple : « un texte de règle en plus,
   quel qu'il soit, change la réponse ».

## Données (fixées)
Questions de jugement résolues de ForecastBench posées en 2026 (cohorte complète), couvertes par la carte v5
(`registre/couverture-regles-jugement2026-v5.json`), une ligne par question (le jeu de la carte). Recherche bornée
et gelée ; taux de départ des semblables ; cotes et prévisions de foule jamais transmises. Exclusion : le modèle dit
connaître l'issue. Les règles citant 2026 ou après sont exclues du catalogue (pas de fuite).

## Bras (fixés)
Mêmes notes du comité pour les trois bras. M0 : synthèse finale actuelle de M. M1 : la même, avec le bloc des règles
retenues (situation de départ, événement, texte). M2 : la même, avec autant de règles tirées au hasard (graine fixe)
parmi celles d'objet différent. Modèle : gpt-5-mini, comme les autres bancs. Script `banc_position_ecosysteme.py`.

## Critère (fixé)
Lecture principale à la manière de Metaculus : perte log brute, toutes les lignes, une par question.
Adopté si l'intervalle à 90 % (bootstrap par question) de M1 − M0 est entièrement sous 0 ET si M1 fait mieux que M2 en
moyenne. Alors, dans le bot : les règles retenues par la carte entrent dans la synthèse de M, en ombre d'abord sur le
flux réel. Sinon rien ne change. Descriptif : M2 − M0, détail par règle et par source de question.

## Puissance (verification_a_priori)
À compléter avec le nombre de questions couvertes par la carte (σ ≈ 0,1 à 0,3 par question selon la proximité des
bras). Plafond de coût : 8 $ (4 appels par question, recherche gelée réutilisée quand elle existe). Lancé une fois.
