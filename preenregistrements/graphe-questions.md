# Préenregistrement : le graphe des questions, en correction finale à porte (idée de GraFT)
2026-11-19, bot 0.10.305, écrit avant tout calcul sur ces données.

Décision d'auteur du 2026-11-19, 1 h 22 (« d'accord, préenregistre les deux »). Source de l'idée : Pham et al.,
*Spatial-as-Refinement* (GraFT, github.com/vpham47/GraFT) : une prévision complète et autonome par capteur, PUIS une
correction par le graphe des voisins multipliée par une porte apprise α (y ← y + α·correction) ; α proche de 0 = le
graphe n'aide pas, retour à la prévision de base.

## Ce qui est déjà dans S (et ce qui ne l'est pas)
S (taux des semblables, banc_jugement) utilise DÉJÀ les ISSUES des questions semblables résolues avant le jeu. Le
graphe testé ici ajoute autre chose : les ERREURS récentes de S sur les questions qui partagent une entité nommée
(même dirigeant, même pays, même institution). Hypothèse : quand S s'est trompé récemment dans le même sens sur le même
acteur, un régime a changé, et S se trompera encore dans ce sens.

## Données
- Questions distinctes (première date de jeu) de la cohorte complète du jeu de données (registre/jugement-questions.jsonl),
  toutes années, quatre plateformes ; base S. Aucun appel à un modèle, aucune cote.
- Entités : banc_wikipedia.entites(titre) (au plus 2 groupes de noms propres, règle déjà écrite en 0.10.298).
- Voisines de la question i : les questions j ≠ i qui partagent au moins une entité avec i ET sont résolues et closes
  avant le jeu de i, dans les 180 jours qui précèdent ce jeu (aucune fuite : l'issue de j est connue au jeu de i ;
  p_S de j est calculé à la date de jeu de j).

## Règle (fixée)
c_i = Σ (issue_j − p_S_j) / (n_i + 3)        (n_i voisines ; rétrécissement K = 3 ; c_i = 0 sans voisine)
p' = σ(logit(p_S) + α·c_i), α sur la grille −2 à 4 (pas 0,2), appris SANS la question jugée.

## Critère
Écart = perte log de p' − perte log de S, sur toutes les questions (celles sans voisine ont p' = S) ; intervalle par
question, un seul regard (tout_juger), risque corrigé des essais ouverts (essai graphe_questions). Adoption seulement
si l'intervalle corrigé est entièrement sous zéro ; alors proposition pour APRÈS le tournoi (décision du 2026-11-18,
19 h 40), sur décision datée de l'auteur. Rapportés : α appris, nombre de questions avec voisines, écart sur ces
seules questions (descriptif), par plateforme.

## Limites connues
Les entités sont tirées des majuscules des titres : bruit (sigles, mots en tête de phrase). Polymarket pèse lourd.
