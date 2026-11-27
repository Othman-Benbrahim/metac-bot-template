# Football, vainqueur d'un championnat : Elo, classement et matchs restants (préenregistrement, 2026-11-27)

Décisions de l'auteur :
- 11 h 42 : « On y va » (famille sport, après la grille des familles) ;
- 11 h 45 : ClubElo validé ;
- 11 h 48 : option A, chantier complet, football-data.co.uk validé.

Une passe. Aucun modèle de langue, aucun crédit. Rédigé avant tout calcul. Les issues des questions n'ont pas été regardées ; seul leur nombre l'a été.

## Question
Pour « X gagnera-t-il le championnat L de la saison S ? », la simulation des matchs restants (force Elo, classement à la date) fait-elle mieux que la brique actuelle « un parmi N » ?

## Données
- **football-data.co.uk** : fichiers CSV gratuits de tous les matchs de Premier League (E0), Liga (SP1), Serie A (I1), Bundesliga (D1) et Ligue 1 (F1), saisons 2015/16 à 2025/26.
- **ClubElo** : `api.clubelo.com/<AAAA-MM-JJ>`, classement Elo de tous les clubs à une date.
- Le robots.txt de chaque site est lu avant toute requête. En cas de refus, le banc s'arrête et le dit.
- Pause d'une seconde entre les requêtes. Rien n'est écrit au registre : le rapport sort en artefact.

## Méthode M (simulation)
À la date D (exclue) :
1. **Classement** : points (3, 1, 0) des matchs du fichier joués avant D.
2. **Matchs restants** : ceux du fichier datés de D ou après. Seule leur affiche est utilisée, jamais leur résultat.
3. **Force** : Elo ClubElo à D.
4. **Match** :
   - écart dr = Elo domicile − Elo extérieur + H ;
   - score attendu E = 1 / (1 + 10^(−dr/400)) ;
   - nul p_N ;
   - victoire max(0,02 ; E − p_N/2), défaite max(0,02 ; 1 − E − p_N/2), puis normalisation.
5. **H et p_N** sont fixés par championnat sur les saisons de développement, 2015/16 à 2018/19, et jamais sur les saisons d'épreuve :
   - p_N = part de nuls ;
   - H = valeur qui reproduit la part de victoires à domicile (recherche sur une grille de 0 à 150, pas de 5).
6. **Simulation** : 10 000 tirages. Une égalité de points est tranchée au hasard (la différence de buts n'est pas simulée, limite déclarée).
7. **Noms** : correspondance automatique (clé normalisée, inclusion, table d'alias). Un club sans correspondance reçoit l'Elo médian des clubs de son championnat à D. Un championnat-date avec plus de deux clubs sans correspondance est exclu. Tous ces cas sont comptés.

## Comparaisons
- **Brique actuelle B** : 1/N avec la saillance k = 2 des sports d'équipe, soit 1 − (1 − 1/N)², avec N = 20 (18 pour la Bundesliga et la Ligue 1).
- **Témoin T** : la même simulation, avec des forces toutes égales. Il isole l'apport de l'Elo au-delà du classement.

## Épreuve 1 : questions construites
- Saisons 2019/20 à 2025/26.
- Le 1er de chaque mois, de septembre à mai.
- Pour chaque championnat et chaque club : « ce club gagnera-t-il ? ». L'issue est le champion réel, au plus de points à la fin du fichier ; une égalité de points est départagée par la différence de buts, puis par les buts marqués.
- Perte logarithmique par question, probabilités bornées à [0,01 ; 0,99].
- Rééchantillonnage par grappe (championnat × saison × date), 10 000 tirages, graine 20261127.
- **Critère : M − B < 0, avec un intervalle à 90 % qui exclut 0.** Si le critère est atteint, M devient la base des questions de vainqueur de championnat (comme l'Elo au tennis), après la porte de compatibilité. Sinon, rien ne change.
- Rapporté sans effet sur le critère :
  - M − T ;
  - le détail par mois (début, milieu, fin de saison) et par championnat.

## Épreuve 2 : questions réelles (rapportée, sans critère)
- Les 26 questions résolues du registre de jugement (Polymarket, Manifold) de la forme « X gagnera-t-il <championnat> ? », sur les cinq championnats.
- D = date d'information de la question. M, B et T sont calculés de la même façon. Une question dont le club ne trouve pas de correspondance est exclue et signalée.
- Les questions sur la Premier League indienne (cricket) sont exclues : elle est captée à tort par le motif « Premier League ».

## Diagnostic préalable, sans score
Le mode `--diagnostic` télécharge les données et imprime seulement les correspondances de noms manquantes (clubs et titres des questions). Aucune probabilité, aucune issue. Les alias peuvent être complétés après ce diagnostic. Le passage avec score n'a lieu qu'une fois.

## Limites déclarées
- Pas de différence de buts dans la simulation.
- L'Elo est figé à D pendant toute la simulation.
- H et p_N sont constants par championnat.
- L'Elo médian est attribué aux clubs sans correspondance.
- Les questions construites d'une même date sont liées (un seul champion), d'où le rééchantillonnage par grappe.

Conflit d'intérêts déclaré : la procédure est rédigée par un modèle d'Anthropic.

## Amendement du 2026-11-27 (12 h), avant tout calcul de score
Le premier diagnostic (run 45985888792) s'est arrêté avant tout téléchargement : le robots.txt de football-data.co.uk refuse notre robot. Ce refus est respecté, pas contourné.

**Nouvelle source des matchs : openfootball** (`github.com/openfootball/football.json`, domaine public), validée par l'auteur à 11 h 56. Codes des championnats : en.1, es.1, it.1, de.1 et fr.1.

**Couverture relevée** (nombre de matchs et de scores seulement, aucune issue regardée) : saisons 2015/16 à 2025/26 complètes, avec deux exceptions.
- Ligue 1 2019/20 : saison arrêtée par la COVID, 279 scores sur 380. Elle est exclue par la règle ci-dessous.
- Liga et Serie A 2024/25 : 370 scores sur 380, la dernière journée manque.

**Deux changements, dictés par la source, sans rapport avec les résultats :**
- Le champion est calculé sur les matchs qui ont un score. Une saison est exclue si plus de 5 % des scores manquent.
- La correspondance des noms passe par des jetons partagés : le candidat unique qui partage le plus de mots significatifs. La table d'alias est étendue aux noms longs d'openfootball.

Le reste de la procédure est inchangé.

## Amendement 2 du 2026-11-27 (12 h 26), avant tout calcul de score
Le diagnostic (run 45986813035) montre que ClubElo ne répond pas aux machines de GitHub : 23 minutes d'attente, aucun Elo reçu. openfootball, en revanche, a tout livré (55 saisons), et les 26 questions réelles retrouvent leur club.

Décision de l'auteur (12 h 26) : « On fait avec ce qu'on a ». **L'Elo est désormais calculé sur les résultats d'openfootball**, comme pour le tennis :
- **Départ** : 1500 pour tous en 2015/16. Les saisons 2015/16 à 2018/19 servent de chauffe et de développement.
- **Mise à jour** après chaque match joué avant D : K = 20 ; avantage du terrain de 60 points dans la mise à jour ; résultat 1, ½ ou 0.
- **Promus** : ils reçoivent l'Elo moyen, en fin de saison, des promus de la saison précédente. Un club qui revient est traité comme un promu.
- **Pas de retour vers la moyenne** entre deux saisons.
- **Clés** : les clubs sont identifiés par leur nom normalisé, ce qui supprime toute correspondance entre deux sources.
- **Limite déclarée** : l'Elo ne voit que les cinq championnats, ni les coupes d'Europe ni les autres divisions.

H et p_N de la simulation restent réglés sur les saisons de développement, désormais avec cet Elo. Le reste de la procédure est inchangé.

Vérification faite avant le score, sans aucune issue : têtes du classement Elo à quelques dates.
- Liverpool en tête en Angleterre au 1/1/2021.
- Barcelone et le Real Madrid en Espagne au 1/10/2023.
- Le Bayern en Allemagne au 1/3/2020.
- Le PSG en France au 1/9/2025.

## Résultat (passage unique, run 45990881636, 2026-11-27, 12 h 31)

**Réglages des saisons de développement :**

| Championnat | H (points) | Part de nuls |
|---|---|---|
| en.1 | 60 | 0,238 |
| es.1 | 70 | 0,248 |
| it.1 | 60 | 0,241 |
| de.1 | 60 | 0,246 |
| fr.1 | 65 | 0,269 |

Une seule saison est exclue : la Ligue 1 2019/20, arrêtée par la COVID.

**Épreuve 1** : 5 940 questions construites, 306 grappes. Pertes moyennes : M 0,066, B 0,219, T 0,089.

| Écart | Valeur | Intervalle à 90 % |
|---|---|---|
| M − B | −0,153 | [−0,159 ; −0,147] |
| M − T | −0,023 | [−0,028 ; −0,018] |

**Critère atteint.** L'Elo apporte un gain net au-delà du classement seul (M − T). Le gain sur T est le plus fort en début de saison (septembre : 0,112 contre 0,171) et se réduit vers la fin (mai : 0,028 contre 0,031).

**Épreuve 2** : 26 questions réelles, rapportées sans critère. Pertes : M 0,152, T 0,147, B 0,772. Sur ces questions posées surtout en fin de saison, M et T se valent ; les deux écrasent la brique actuelle.

**Conséquence prévue** : M devient la base des questions de vainqueur de championnat. **Obstacle constaté avant branchement** : pour la saison en cours (2026/27), openfootball ne contient des scores que jusqu'au 20 septembre 2026, soit plus de deux mois de retard. Une brique en direct n'aurait ni classement ni matchs restants à jour. Elle doit s'abstenir tant qu'aucune source fraîche des résultats n'est trouvée (règle de fraîcheur). La décision revient à l'auteur.
