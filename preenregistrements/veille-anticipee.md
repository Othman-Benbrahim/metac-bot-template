# Veille anticipée des questions : critère écrit avant toute mesure (2026-11-26)

Décisions de l'auteur : 16 h 46 (idée : anticiper l'acteur et le domaine d'une question à partir de l'actualité, pour
préparer mécanismes et séries avant elle) ; 16 h 50 (« Yep » : voie prospective, sans reconstitution du passé).

## Dispositif (anticipation.py, branché dans collecte_rss)
Chaque jour : noms propres des titres d'articles nouveaux comptés (aucun titre gardé) ; liste des 40 entités au plus qui
montent (3 derniers jours contre les 14 précédents, au moins 5 articles) ; mesure sur chaque question du tournoi.

## Critère (point au bout de 4 semaines d'historique, vers le 2026-12-24)
- Réussite : au moins un nom propre du titre de la question figure dans une liste des 7 jours précédant sa date.
- **L'idée tient si au moins la moitié des questions du tournoi sont anticipées**, les listes restant à 40 entités au
  plus (une liste de mille noms réussirait toujours : la taille est plafonnée d'avance).
- Si elle tient : étape suivante, préparer automatiquement, pour chaque entité de la liste, la forme de question probable
  (questionneur) et les séries ou calendriers à brancher ; décision de l'auteur.
- Si elle ne tient pas : on rapporte les questions manquées et pourquoi (actualité absente de nos flux, calendrier
  plutôt qu'actualité, etc.).

## Limites déclarées
Les flux RSS suivis ne couvrent pas toute l'actualité ; les questions nées d'un calendrier (comptes trimestriels,
sommets prévus) ne passent pas forcément par une « montée » dans les titres : elles relèvent d'un calendrier à part.
