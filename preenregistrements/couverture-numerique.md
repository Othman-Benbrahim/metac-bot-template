# Préenregistrement : couverture des fourchettes du bot (questions numériques et de date)
2026-11-18, bot 0.10.293, écrit avant toute résolution de ces questions (aucune n'est encore résolue).

Décision d'auteur du 2026-11-18, 20 h 52 (« oui, aux deux »). Idée tirée d'un post sur le mouvement brownien
géométrique (test des bandes 5–95 % hors échantillon). Suivi DESCRIPTIF : rien ne change dans ce que poste le bot
(décision du 2026-11-18, 19 h 40).

## Mesure (couverture_numerique.py, lancé par le score quotidien)
- Pour chaque question numérique ou de date du journal du bot (registre/journal-autres.jsonl), la PREMIÈRE
  distribution postée ; centiles déclarés 10, 20, 40, 60, 80, 90.
- Valeur réelle (registre/issues-autres.jsonl) ; « au-dessous de la borne » et « au-dessus de la borne » comptent
  comme queues ; questions annulées ou ambiguës écartées.
- Rang de la valeur dans la distribution déclarée, interpolé entre centiles.
- Attendu si le bot est calibré : 10 % sous le centile 10, 80 % entre 10 et 90, 10 % au-dessus du centile 90.

## Signal (fixé ici)
À partir de 30 questions résolues : « fourchettes trop étroites » si plus de 30 % des valeurs tombent hors de la
fourchette 10–90 ET si la probabilité d'en voir autant chez un bot calibré (binomiale, p = 0,2) est sous 5 %.
Le signal ne change rien seul : il ouvre, APRÈS le tournoi, une proposition datée à l'auteur (par exemple élargir
les fourchettes d'un facteur appris sur ces questions).
