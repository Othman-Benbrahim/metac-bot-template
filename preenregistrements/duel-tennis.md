# Duel des méthodes de force : tennis (procédure écrite avant tout calcul)

Décisions de l'auteur, 2026-11-26 :
- 12 h 05 : les résultats sportifs varient ; valider ou invalider une méthode sur un point fixe (une saison) n'est pas la
  bonne méthode.
- 12 h 08 : se baser plutôt sur les résultats récents pondérés par le classement de chaque équipe (méthode inductive),
  qu'il pense plus fiable qu'un « truc général ».
- 12 h 09 : « je valide » le duel : 1/N contre Elo contre forme récente pondérée par le classement, testé saison par
  saison sur l'historique, chaque méthode n'utilisant que ce qui était connu avant.

Périmètre : tennis seulement. Le foot de clubs attend ses données : la collecte Club Elo échoue chaque nuit (délai
dépassé) et Club Elo ne donne pas les résultats de matchs nécessaires à la forme récente. Aucun modèle de langue : zéro
crédit.

## Données
Matchs ATP et WTA de Jeff Sackmann (CC BY-NC-SA 4.0), par l'adresse déjà validée de `collecte_elo.py` (GitHub, sinon le
miroir Hugging Face), 1990 à 2026. Colonnes lues : tourney_id, tourney_date, tourney_level, draw_size, round, winner_name,
loser_name, winner_rank, loser_rank, score.

## Tournois prévus
ATP : niveaux G (Grand Chelem) et M (Masters 1000). WTA : niveau G, plus les niveaux de catégorie supérieure présents
dans les fichiers (PM, T1) ; la liste des niveaux effectivement trouvés est imprimée. Saisons de test : 2010 à 2025, et
2026 en saison partielle (déclarée à part).

## Tableau
Il est reconstruit à partir des résultats : un match d'un tour a pour « enfants » les matchs du tour précédent gagnés
par ses deux joueurs ; un joueur sans match au tour précédent y entre directement (exemption). On calcule de façon
exacte (programmation dynamique sur l'arbre, sans tirage) la probabilité de chaque joueur de gagner le tournoi. Un
tableau incomplet (finale introuvable ou arbre incohérent) est écarté et compté.

## Les trois méthodes (état figé à la veille du tournoi)
1. **1/N** : chaque joueur du tableau vaut 1/N.
2. **Elo** : formule de `collecte_elo.py` (départ 1500, K = 250/(n+5)^0,4, forfaits exclus), mise à jour match par
   match après chaque tournoi ; probabilité de match 1/(1+10^(−Δ/400)).
3. **Forme récente pondérée par le classement** (méthode de l'auteur) :
   - forme F = moyenne des 10 derniers matchs (victoire 1, défaite 0), chaque match pondéré par v(r) = 1/ln(r+2), r le
     classement de l'adversaire (classement absent : 500) ; moins de 3 matchs : F = 0,5 ;
   - probabilité de match = logistique(a·(F_i − F_j) + b·(ln r_j − ln r_i)), r_i le classement du joueur au début du
     tournoi (absent : 500) ;
   - a et b sont ajustés par régression logistique sur tous les matchs des saisons antérieures à la saison prévue
     (réajustés au début de chaque saison), jamais sur la saison prévue.

## Score
Pour chaque tournoi : −ln p(vainqueur réel), p bornée à 0,0001. Moyenne par saison et sur l'ensemble.

## Décision (une passe, sans retour)
- Une méthode est retenue si elle bat 1/N sur l'ensemble ET dans au moins deux tiers des saisons de test (2010-2025).
- Entre l'Elo et la forme : la meilleure perte d'ensemble l'emporte ; on rapporte le nombre de saisons gagnées par
  chacune dans le duel. Si l'écart d'ensemble est inférieur à 0,02, on le déclare non concluant.
- Le branchement dans le bot reste une décision de l'auteur, et il bute sur une limite déclarée : les fichiers de
  Sackmann sont mis à jour avec retard (derniers matchs connus : mai 2026), donc l'état du jour peut manquer.

## Limites déclarées
- Les questions de Metaculus portent sur des tournois précis et des joueurs choisis par le rédacteur ; le banc porte sur
  tous les joueurs de tous les grands tournois : il mesure la méthode, pas la performance sur nos questions.
- Les paramètres de la forme (10 matchs, v(r), 500 pour un classement absent) sont fixés ici sans essai.

## Résultat du passage unique (2026-11-26, run 45808551960)

| Circuit | 1/N | Elo | Forme pondérée | Saisons battant 1/N (sur 16) | Duel, saisons gagnées |
|---|---|---|---|---|---|
| ATP (G, M ; 0 tableau écarté) | 4,389 | **2,093** | 2,255 | Elo 16, forme 16 | Elo 12, forme 4 |
| WTA (G, PM ; T1 absent ; 0 tableau écarté) | 4,608 | **2,956** | 3,228 | Elo 16, forme 13 | Elo 10, forme 6 |

- Les deux méthodes sont retenues contre 1/N : elles le battent sur l'ensemble et dans au moins deux saisons sur trois.
  En moyenne géométrique, la probabilité donnée au vrai vainqueur passe d'environ 1 % (1/N) à environ 12 % (Elo, ATP).
- Duel : l'**Elo** l'emporte sur l'ensemble (écart 0,16 à l'ATP, 0,27 à la WTA, au-delà du seuil de 0,02) et dans la
  majorité des saisons. La forme pondérée gagne certaines saisons (ATP 2019-2021 et 2024 ; WTA 2010, 2013, 2016, 2022).
- WTA : peu de tournois par saison certaines années (niveau PM seulement, T1 introuvable dans les fichiers) ; 2018 et
  2020 proches de 1/N pour les deux méthodes.
- Rien n'est branché : la décision revient à l'auteur, et les données de Sackmann s'arrêtent en mai 2026.

## Second passage : combinaison Elo + forme (écrit avant calcul, 2026-11-26, 12 h 20 ; décision de l'auteur, 12 h 19 :
« les deux » — tester la combinaison et chercher une source fraîche)
Constat qui motive le test : les deux méthodes ne se trompent pas les mêmes saisons.
- Méthode 4, **mélange** : pour chaque tournoi, moyenne simple des deux probabilités de titre, p = (p_elo + p_forme)/2.
  Poids fixé à 1/2, sans réglage.
- Même score, mêmes saisons, même passage de données.
- Décision : le mélange remplace l'Elo s'il fait mieux sur l'ensemble 2010-2025 d'au moins 0,02 ET dans au moins la
  moitié des saisons, sur chacun des deux circuits ; sinon l'Elo reste.

## Résultat du second passage (2026-11-26, run 45809824873)
- ATP : mélange 2,121 contre Elo 2,093 (moins bien de 0,029) ; meilleur que l'Elo dans 6 saisons sur 16.
- WTA : mélange 2,972 contre Elo 2,956 (moins bien de 0,016) ; meilleur dans 7 saisons sur 16.
- **Le mélange ne remplace pas l'Elo.** L'Elo seul reste la méthode retenue pour le tennis.

## Branchement (décision de l'auteur, 2026-11-26, 12 h 36 : « Ok, je valide »)
`tennis_elo_regle.py` : « X gagnera-t-il <Grand Chelem ou tournoi 1000> ? ». Le vrai tableau n'étant pas connu avant le
tirage, il est simulé (4 000 tirages ; 128 places, ou 96 joueurs dont 32 exemptés ; têtes de série placées selon l'Elo).
C'est une approximation du banc (qui utilisait les vrais tableaux), déclarée. La note sert de base (mesure), puis passe
par le contradicteur et le juge comme les autres briques. Abstention si le joueur n'a aucun match connu depuis 90 jours
(blessure ou retrait probable) : découvert sur Sinner, forfait à l'US Open 2026 sur blessure au genou, dont la dernière
note date de Wimbledon.

Copie figée datée par un tiers (Zenodo), procédure et deux passages compris : DOI 10.5281/zenodo.24559290.
