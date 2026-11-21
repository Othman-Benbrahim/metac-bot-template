# M avec position écosystémique contre M sans (préenregistrement, BROUILLON du 2026-11-21, à valider par l'auteur)

Décisions de l'auteur : piste écosystémique (2026-11-21), aucun test tant que la sélection n'est pas calibrée ; carte
v5 jugée calibrée à la relecture (≈ 94 % de rattachements justes sur le banc de M) ; option (b) : élargir aux questions
de jugement de 2026 pour donner de la puissance au test (14 h 26). Hypothèse de l'auteur : le modèle n'est pas
inopérant, il est inachevé ; il manque l'information ciblée sur le bon écosystème au bon moment.

## Rasoir d'Ockham
1. Une phrase : donner à M les règles sourcées qui gouvernent l'événement de la question, depuis sa situation de
   départ, améliore sa prévision.
2. Paramètres : aucun appris ; les règles sont choisies par la carte robot (motifs figés, reproductibles).
3. Sens fixé d'avance : M1 meilleur que M0, et meilleur que le placebo M2.
4. Domaine : questions dont le titre contient l'événement et la situation d'une règle sourcée (carte robot).
5. Plus simple ? Le placebo M2 (règles quelconques) mesure l'explication plus simple : « un texte de règle en plus,
   quel qu'il soit, change la réponse ».

## Données (fixées)
Questions de jugement résolues de ForecastBench posées en 2026 (cohorte complète), couvertes par la **carte robot**
(`carte_robot.py`, `registre/carte-robot-jugement2026.json` : motifs Python écrits à la main et figés, aucun appel de
modèle ; décision de l'auteur du 2026-11-21, 14 h 45, après la mesure du halo : deux passages identiques de la carte v5
différaient sur 15 questions sur 119). 217 questions couvertes sur 929 ; 150 au plus sont jugées, dans l'ordre fixé par
empreinte. Une ligne par question (son premier jeu). Recherche bornée
et gelée ; taux de départ des semblables ; cotes et prévisions de foule jamais transmises. Exclusion : le modèle dit
connaître l'issue. Les règles citant 2026 ou après sont exclues du catalogue (pas de fuite).

## Bras (fixés)
Mêmes notes du comité pour les trois bras. M0 : synthèse finale actuelle de M. M1 : la même, avec le bloc des règles
retenues (situation de départ, événement, texte). M2 : la même, avec autant de règles tirées au hasard (graine fixe)
parmi celles d'objet différent. Modèle : Claude Haiku 4.5 sur les crédits Bedrock (décision de l'auteur, 14 h 36),
pour les trois bras ; le bot poste M avec gpt-5-mini : un effet trouvé sur Haiku devra être confirmé en ombre sur le
modèle du bot. Script `banc_position_ecosysteme.py`, 150 questions au plus.

## Critère (fixé)
Lecture principale à la manière de Metaculus : perte log brute, toutes les lignes, une par question.
Adopté si l'intervalle à 90 % (bootstrap par question) de M1 − M0 est entièrement sous 0 ET si M1 fait mieux que M2 en
moyenne. Alors, dans le bot : les règles retenues par la carte entrent dans la synthèse de M, en ombre d'abord sur le
flux réel. Sinon rien ne change. Descriptif : M2 − M0, détail par règle et par source de question.

## Puissance (verification_a_priori)
À compléter avec le nombre de questions couvertes par la carte (σ ≈ 0,1 à 0,3 par question selon la proximité des
bras ; avec σ ≈ 0,08, 150 questions voient un écart d'environ 0,016). Plafond : 15 $ de crédits Bedrock (4 appels par
question ; Haiku coûte environ trois à quatre fois plus par mot que gpt-5-mini). Lancé une fois.

## Résultat (2026-11-21, run 44910861817) : critère non atteint, rien ne change dans le bot
150 questions traitées (Claude Haiku 4.5, 4,53 $ de crédits Bedrock), 22 exclues (le modèle disait connaître
l'issue), 128 jugées. Perte log : semblables 0,683, M0 0,591, M1 (bonnes règles) 0,588, M2 (règles au hasard) 0,602.
M1 − M0 = −0,003, intervalle à 90 % [−0,030 ; +0,019] : pas d'effet net. M1 − M2 = −0,014 [−0,044 ; +0,014] ;
M2 − M0 = +0,011 [−0,003 ; +0,026] : des règles au hasard tendent à nuire, les bonnes règles sont neutres à légèrement
favorables (descriptif). Le modèle bouge peu sous l'effet des règles : écart moyen |M1 − M0| de 2,2 points de
probabilité. Par règle (descriptif, petits nombres) : règles de sondages −0,032 sur 41 questions, Fed −0,009 sur 13.
Lecture : donner les règles en texte à un modèle de langue n'est pas une traduction efficace (il en tient peu compte) ;
cela conforte la voie de la traduction par le code (traduction_regles.py). Les règles et les faits restent dans les
fiches. Puissance mesurée : σ ≈ 0,17 par question, l'essai voyait un écart d'environ 0,04.
