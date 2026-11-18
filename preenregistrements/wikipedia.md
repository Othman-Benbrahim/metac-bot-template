# Préenregistrement : Wikipédia, attention du public (pages vues) et agitation anticipée (protections)
2026-11-18, bot 0.10.298, écrit avant toute collecte et tout calcul sur les issues.

Décision d'auteur du 2026-11-18, 22 h 30 (« je valide l'ensemble, mais avec plus de folie »). Sources officielles et
gratuites de la Wikimedia Foundation, données agrégées et DATÉES, donc sans fuite par construction (contrairement aux
recherches rétrospectives : ForecastGym, arXiv 2611.23045). Aucune personne privée : seulement les articles des
entités nommées dans les titres des questions.

## Données
- Questions : les 892 questions distinctes de 2026 du jeu de données (première date de jeu), base S (semblables),
  comme le banc de la tendance large GDELT (comparaison directe).
- Entités : au plus 2 groupes de noms propres du titre ; article Wikipédia anglais = premier résultat de la recherche
  de Wikipédia pour chaque entité.
- Pages vues (utilisateurs, tous accès) jour par jour, J−90 à J−1, sommées sur les articles retenus.
- Protections : nombre d'actions de protection inscrites au journal de ces articles sur la même fenêtre.

## Règle (jugée)
Même tendance que tendance-attention.md : ln((vues des 10 derniers jours / 10 + 0,1) / (vues des 80 précédents / 80
+ 0,1)), 0 sans article ; p' = σ(logit(p_S) + β·tendance), β sur la grille −1 à 1 (pas 0,05), appris SANS la question
jugée. Écart contre S, intervalle par question, un seul regard, risque corrigé des essais ouverts (essai
tendance_wikipedia). Adoption seulement si l'intervalle corrigé est entièrement sous zéro ; usage dans le bot
APRÈS le tournoi (décision du 2026-11-18, 19 h 40), sur décision datée de l'auteur.

## Affiché, non jugé
- Protections : part de oui et S moyen des questions avec au moins une protection, contre celles sans.
- Corrélation de rang entre la tendance Wikipédia et la tendance GDELT sur les mêmes questions (attention du public
  contre attention des médias).
- Résultat par plateforme.

## Limites connues
Le choix de l'article par la recherche de Wikipédia est fait aujourd'hui : un article créé après la question n'a pas
de pages vues avant elle (tendance 0, pas d'ajustement) ; pas d'autre fuite possible. Polymarket (sport, crypto)
pèse les deux tiers des questions.
