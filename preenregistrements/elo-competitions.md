# Brique « compétitions : force mesurée (Elo) » : procédure écrite avant le calcul

Décisions de l'auteur, 2026-11-24 :
- 23 h 24 : sources validées (résultats internationaux CC0, NFL nflverse CC BY, Club Elo, tennis Sackmann) ;
- 23 h 21 : licences non commerciales acceptées ;
- 23 h 53 : « On peut commencer ».

La procédure est versée AVANT tout calcul sur les issues, passée une fois, et la décision de branchement est prise sur ce seul passage, sans retour.

## Mécanisme (carte : compétitions-culture, classements_force → forme ; regles → classements_force)

Une note de force résume les résultats passés. Le favori gagne plus souvent, mais pas toujours. Le format (poules, élimination directe, nombre de tours) fixe la part du hasard. On simule donc la compétition telle que son format la dessine, à partir des notes connues à la date de la question.

## Périmètre de ce premier passage (données disponibles)

- **Coupe du monde 2026** (sélections nationales). Formes de question reconnues :
  - « X win the (2026 FIFA) World Cup » ;
  - « X reach the final / semifinals / quarterfinals » ;
  - « X make it out of the group stage » ;
  - « X win Group L » ;
  - « champion first-time winner » / « country that has never won before » ;
  - « any host nation (USA, Mexico or Canada) reach the semifinals ».
- **NFL, saison 2025** :
  - « X win Super Bowl (LX / 2026) » ;
  - « X win the AFC/NFC Championship » ;
  - « X win the <division> ».
- **Abstention** (non reconnu) : joueurs (buteur, MVP, prix individuels), entraîneurs, faits hors terrain (boycott, présence d'un dirigeant, carton bleu, record), confédération du vainqueur, matchs isolés, toute autre compétition. Les clubs et le tennis attendent leur collecte.

## Notes (Elo) à la date de la question

Elles sont recalculées sur les seuls matchs joués AVANT la date de jeu de la question.
- **Sélections** : formule publique du World Football Elo, comme dans `collecte_elo.py`. K selon la compétition, majoré par l'écart de buts, avantage du terrain 100.
- **NFL** : K = 20, terrain 48, multiplicateur d'écart de points, retour d'un tiers vers 1505 à chaque saison.

## Modèle de match (paramètres fixés ici, avant tout calcul)

- Espérance du favori : We = 1 / (1 + 10^(−dr/400)).
- **Football, poules** :
  - nul D = 0,27 · (1 − |2We − 1|) ;
  - victoire We − D/2 ;
  - défaite 1 − We − D/2.
- **Football, élimination directe** : vainqueur avec la probabilité We (prolongation et tirs au but inclus dans We).
- **Terrain** : les pays hôtes (États-Unis, Mexique, Canada) ont +100 dans tous leurs matchs. Les autres matchs de la Coupe du monde sont neutres. NFL : +48 pour l'équipe à domicile du calendrier, terrain neutre au Super Bowl.

## Format simulé (20 000 tirages par question)

### Coupe du monde 2026

Format : 48 équipes, 12 poules de 4, les 2 premiers et les 8 meilleurs troisièmes vont en seizièmes, puis élimination directe.

**Le champ** dépend de la date de jeu :
- avant le 2026-04-01 (fin des barrages, donc équipes non toutes connues) : les 48 meilleures notes, hôtes compris, avec des poules tirées au hasard à chaque simulation ;
- à partir du 2026-04-01 : les poules réelles, lues dans les rencontres de la Coupe du monde 2026 de la phase de poules (11 au 27 juin 2026) du fichier de résultats. Une poule est une composante connexe des équipes qui s'y rencontrent.

**Pendant la compétition** :
- les matchs déjà joués avant la date de jeu sont gardés avec leur score ;
- une équipe battue en élimination directe avant la date de jeu vaut 0 ;
- le reste est simulé.

**Approximations déclarées** :
- le tableau des seizièmes est apparié au hasard parmi les qualifiés (le vrai tableau dépend de la table FIFA des troisièmes) ;
- départage en poule : points, puis différence de buts simulée (buts : vainqueur 1 à 3 de plus, tiré uniformément), puis hasard.

« Champion first-time winner » : vainqueur hors des anciens vainqueurs (Uruguay, Italie, Allemagne, Brésil, Angleterre, Argentine, France, Espagne).

### NFL, saison 2025

On part du calendrier réel (nflverse) :
- matchs joués avant la date : résultat réel ;
- matchs restants : simulés avec les notes à la date, sans mise à jour en cours de tirage.

Les divisions sont celles de la NFL depuis 2002, dans une table écrite à la main.

Les séries éliminatoires :
- par conférence, 4 vainqueurs de division (têtes de série 1 à 4 au nombre de victoires) et 3 repêchés (5 à 7) ;
- 2-7, 3-6, 4-5, puis la tête de série 1 contre la plus faible restante ;
- finale de conférence, puis Super Bowl neutre.

Égalités au hasard (approximation déclarée, au lieu des règles officielles de départage).

## Évaluation (une seule passe)

- **Questions** : corpus résolu (`registre/jugement-questions.jsonl`), titres distincts reconnus. On lit les titres sans les issues pour décider de la reconnaissance.
- **Groupe** : `groupe()` (mots capitalisés).
- **Référence** : part de oui des questions reconnues hors groupe.
- **Mélange** : un quart en log-cote avec la référence, plafonné à 15 points. C'est le critère historique, gardé pour comparer.
- **Branchement si les trois critères tiennent** :
  1. règle < référence sur l'ensemble ;
  2. mélange plafonné < référence ;
  3. règle < référence sur les questions de 2026.
- **Si branchée** : la règle sert de base dans le bot (décision de l'auteur du 2026-11-24, 22 h 12), puis passe par le juge informé et son plafond. Journal scellé : `registre/journal-elo.jsonl`.

Notes de version dans le bot : `registre/elo/*.csv.gz` (fin de mois, plus le dernier relevé), mises à jour chaque nuit.

## Limites déclarées

- L'échantillon est petit (environ 50 questions) et vient surtout de marchés de prédiction recopiés (Polymarket, Manifold), dont les questions « X gagnera-t-il ? » portent souvent sur des outsiders. La référence est donc basse, et la règle gagne facilement sur ces questions-là. Le critère 3 (2026) limite ce biais sans l'effacer.
- Le paramètre du nul (0,27) et l'avantage des hôtes (+100) ne sont pas mesurés ici : ils sont fixés avant tout calcul.
