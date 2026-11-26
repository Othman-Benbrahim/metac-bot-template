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
