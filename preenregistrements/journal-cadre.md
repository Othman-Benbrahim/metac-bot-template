# Cadre écosystémique + lecture du bot, sur le journal d'ombre (préenregistrement, 2026-11-20)

Décisions de l'auteur, 2026-11-20 : le bot ne poste rien sur Metaculus tant qu'il n'est pas au point (02 h 00) ; préenregistrer maintenant le test du journal (02 h 02). Origine : les deux bancs de la nuit (`brique_fenetre`, `brique_fenetre_etat`) montrent que la structure seule ne rattrape pas la foule (0,39 à 0,33 contre 0,57 à 0,65) ; la foule lit le contenu de l'actualité. Hypothèse : la couche écosystémique ne remplace pas cette lecture, elle la cadre.

Essai `journal_cadre`, inscrit dans `essais.py` le jour du lancement seulement (pour ne pas compter dans le risque corrigé tant qu'il attend).

## Questions
Prévisions binaires d'ombre du bot, scellées (`registre/journal-bot.jsonl`, sceau vérifié), une par question (la dernière), issues relevées par `score_registre.py --metaculus --enregistrer`. Au 2026-11-20 : 12 questions binaires, aucune résolue.

## Calcul (fixé, aucun réglage sur les issues)
- Lecture : bras A (modèle de langue avec recherche).
- Cadre : p_S, questions semblables du registre de jugement, avec les seules questions résolues et closes avant la date d'information.
- Mise en commun : moyenne des log-cotes à poids égaux (0,5 / 0,5).

## Condition de lancement et critère
- Lancement unique quand au moins **100 questions binaires distinctes** sont résolues ; avant, `journal_cadre.py` compte et ne note rien.
- Critère : perte log de la mise en commun contre le bot seul, intervalle de l'écart corrigé (risque d'`essais.py` au jour du lancement) entièrement sous 0.
- Descriptif : perte du cadre seul.

## Limite connue
Au rythme actuel (12 questions binaires en trois semaines), 100 questions résolues demanderont plusieurs mois ; le rythme dépend du nombre de passages d'ombre du bot.
