# Préenregistrement : titres GDELT (BigQuery) en complément de la recherche
2026-11-18, bot 0.10.280, écrit avant le premier passage de banc_gdelt_complement.py.

Décision d'auteur du 2026-11-18, 17 h 32. Contexte : la requête groupée BigQuery (filtre resserré, run 44347715141)
donne des titres à 91 des 130 questions distinctes des bancs ; dates sûres (vues par GDELT avant la question).

## Comparaison
Sur chaque question distincte qui a au moins un titre GDELT, deux jugements finaux de M (gpt-5-mini), mêmes notes de
cartes, même taux de départ, même part de recherche gelée : SANS les titres, AVEC les titres (bloc de 1 500 caractères
au plus, la recherche gelée étant raccourcie d'autant dans les DEUX bras).

## Règle
- Écart = perte log AVEC − perte log SANS ; intervalle par question (bloc_par="question"), un seul regard sur toutes
  les questions (tout_juger), risque corrigé des essais ouverts.
- Si l'intervalle corrigé est entièrement sous zéro : les titres sont proposés en complément dans le bot (décision
  datée de l'auteur). Sinon : ils restent un relais, utilisé seulement quand les autres moteurs ne trouvent rien.
- Rapportés : profil des erreurs (ratés, fausses alertes, perte par côté), unités (questions distinctes).
- Limite connue : moins de 100 questions ; seul un effet net sera détectable.
