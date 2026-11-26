# Le calendrier tient-il ? Étapes nécessaires contre temps restant (procédure écrite avant tout appel)

Décisions de l'auteur, 2026-11-26 : 15 h 43 (tester le calendrier, puis traiter par famille) ; 15 h 46 (« Haiku, ça
ira »). Suite du banc « questionneur × délai » (non retenu : le nombre de jours seul ne dit rien).

## Questions
Questions de Metaculus résolues (registre/jugement-questions.jsonl) **résolues à partir du 2025-08-01**, après les
données d'entraînement de Claude Haiku 4.5 (juillet 2025), pour qu'il ne connaisse pas l'issue : 699 éligibles ;
**200 tirées au hasard** (graine 20261126). Aucune recherche : le modèle ne lit que le titre et les dates.

## Lecture (Claude Haiku 4.5, anthropic/claude-haiku-4-5, température 0, une passe)
On lui donne : le titre, « aujourd'hui » = date de jeu, l'échéance = date de jeu + horizon. Réponse JSON fermée :
- `verdict` : « tient » (les étapes nécessaires peuvent tenir dans le temps restant), « ne_tient_pas » (même au plus
  vite, elles ne tiennent pas), « sans_objet » (rien n'a besoin d'être accompli : maintien, seuil de marché, etc.) ;
- `etapes` (liste courte) et `duree_min_jours` (entier), pour la trace.
Réponse illisible : comptée « sans_objet ».

## Mesure
- Référence : le questionneur actuel (part de oui de la forme de question, apprise sur les questions de Metaculus
  résolues AVANT le 2025-08-01).
- Ajusté : pour « ne_tient_pas », la part de oui de cette classe (estimée en laissant chaque question de côté,
  rétrécie vers la référence avec le poids n/(n+10)) ; les autres classes gardent la référence.
- Perte log ; intervalle à 90 % du gain par rééchantillonnage (1 000 tirages).

## Décision (une passe)
**Retenu si** au moins 15 questions « ne_tient_pas », dont la part de oui est au plus la moitié de celle de la
référence sur les mêmes questions, ET gain ≥ 0,005 avec un intervalle qui exclut 0. Retenu, le verdict « ne tient pas »
entrerait dans le dossier du juge comme un repère de famille (procédure du juge à amender par l'auteur).

## Coût
200 appels courts à Haiku (crédits Anthropic de l'auteur) : de l'ordre de quelques centimes. Conflit d'intérêts déclaré
(modèle d'Anthropic, comme Claude qui a écrit la procédure) ; étiquettes absentes : l'issue n'est jamais montrée.

## Résultat du passage unique (2026-11-26, run 45842640497)
| Verdict de Haiku | Questions | Oui | Part de oui | Référence moyenne |
|---|---|---|---|---|
| tient | 79 | 18 | 23 % | 34 % |
| ne_tient_pas | 99 | 15 | 15,2 % | 30 % |
| sans_objet | 22 | 9 | 41 % | 31 % |
- Gain sur le score : +0,118, IC90 [0,063 ; 0,175] ; perte 0,797 → 0,678.
- Mais la part de oui des « ne tient pas » (15,2 %) dépasse d'un cheveu la moitié de la référence (15,0 %) : **critère
  non tenu, non retenu** (règle écrite avant, appliquée sans retouche).
- Lecture : l'essentiel du gain vient de ce que la référence est trop haute sur cette période (part de oui réelle des
  200 questions : 21 %, contre ≈ 31 % prévus par le questionneur appris avant août 2025) ; toute correction vers le bas
  aurait gagné. Le verdict sépare un peu (15 % contre 23 % pour « tient »), loin du « presque toujours non » attendu.
  Le signal le plus net est ailleurs : le questionneur appris sur le passé surestime le oui récent (dérive déjà vue le
  24 novembre).
