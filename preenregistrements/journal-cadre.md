# Cadre écosystémique + lecture du bot, sur le journal d'ombre (préenregistrement, 2026-11-20)

Décisions de l'auteur, 2026-11-20 : le bot ne poste rien sur Metaculus tant qu'il n'est pas au point (02 h 00) ; préenregistrer maintenant le test du journal (02 h 02). Origine (révision séquentielle : veille du 2026-11-20, dépôt « spikewatch ») : les deux bancs de la nuit (`brique_fenetre`, `brique_fenetre_etat`) montrent que la structure seule ne rattrape pas la foule (0,39 à 0,33 contre 0,57 à 0,65) ; la foule lit le contenu de l'actualité. Hypothèse : la couche écosystémique ne remplace pas cette lecture, elle la cadre.

Essai `journal_cadre`, inscrit dans `essais.py` le jour du lancement seulement (pour ne pas compter dans le risque corrigé tant qu'il attend).

## Questions
Prévisions binaires d'ombre du bot, scellées (`registre/journal-bot.jsonl`, sceau vérifié), une par question (la dernière), issues relevées par `score_registre.py --metaculus --enregistrer`. Au 2026-11-20 : 12 questions binaires, aucune résolue.

## Calcul (fixé, aucun réglage sur les issues)
- Lecture : bras A (modèle de langue avec recherche).
- Cadre : p_S, questions semblables du registre de jugement, avec les seules questions résolues et closes avant la date d'information.
- Mise en commun : moyenne des log-cotes à poids égaux (0,5 / 0,5).

## Suivi et critère (révisé le 2026-11-20 à 11 h 37, avant toute résolution, décision de l'auteur)
- Suivi **séquentiel valable à tout instant** : e-processus par pari (Waudby-Smith et Ramdas, « Estimating means of bounded random variables by betting », JRSS B, 2024). Écart par question d = perte(commun) − perte(bot), probabilités bornées à [0,01 ; 0,99], questions dans l'ordre de leur résolution ; mise prévisible, calculée sur les écarts précédents seulement.
- On peut regarder après chaque résolution sans gonfler le risque (inégalité de Ville). **Verdict positif** dès que la richesse du pari atteint 1/α, avec **α = 5 %** (révision du 2026-11-20 à 11 h 50, avant toute résolution, décision de l'auteur : le journal est un échantillon à part, qui ne sert à aucun autre essai ; une seule hypothèse, déclarée d'avance ; la correction du registre ne s'applique pas). **Arrêt sans verdict positif** à 100 questions résolues.
- Puissance, dite d'avance : seuil de richesse 20 ; un gain faible sur 100 questions peut rester « non tranché ». Le grappillage des petits gains se fait sur l'échantillon de mise au point (17 009 questions), pas ici.
- Hypothèse de travail déclarée : les questions sont traitées comme une suite d'épreuves, dans l'ordre des résolutions.
- Descriptif : perte du cadre seul.

## Limite connue
Au rythme actuel (12 questions binaires en trois semaines), 100 questions résolues demanderont plusieurs mois ; le rythme dépend du nombre de passages d'ombre du bot.
