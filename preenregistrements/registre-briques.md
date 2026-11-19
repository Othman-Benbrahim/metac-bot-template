# Le registre des briques : course et seuil (préenregistrement, 2026-11-19, 21 h 35)

Décisions de l'auteur du 2026-11-19 :
- 21 h 20 : les critères changent selon les échelles (exemple : les sondages des primaires). Une brique ne vaut que dans des cas homologues à la même échelle. L'axe d'échelle dépend de la structure (la taille pour les élections, un autre ailleurs). Définir le mécanisme de façon automatisée, en prenant l'élection comme exemple et non comme référentiel.
- 21 h 26 : « je valide, on commence ».

Code : `registre_briques.py`. Sortie : `registre/briques.json`. Ombre : rien dans le bot, rien côté Metaculus avant le tournoi.

## Une brique = structure × axe d'échelle × tranche
Pour chaque case on publie : n, perte de la brique, perte de la référence, écart, intervalle, et un statut :
- **valide** : l'intervalle de l'écart (brique − référence), au risque corrigé d'`essais.py`, est entièrement sous 0 ;
- **nuit** : l'intervalle est entièrement au-dessus de 0 ;
- **non tranché** : l'intervalle contient 0 ;
- **insuffisant** : moins de 30 questions jugées dans la case. La brique s'abstient, et la référence s'applique.

Aucune prévision ne se calcule avec une information postérieure à sa date (apprentissage sur le seul passé, à chaque date).

## Structure « seuil » (une série franchit-elle une barre ?)
- **Questions** : les questions de séries ForecastBench résolues (FRED, DBnomics) de `registre/banc-echeance.jsonl`.
- **Brique** : B, le comptage des hausses sur cinq ans, déjà calculé.
- **Référence** : la part de « oui » de la même source sur les jeux antérieurs (le statu quo statistique). 0,5 tant qu'il n'existe aucun jeu antérieur.
- **Axe d'échelle : la vitesse.** Tranches :
  - fréquence de la série : quotidienne (écart médian ≤ 4 jours), hebdomadaire (5 à 10 jours), mensuelle ou plus lente ;
  - horizon : 7 jours ou moins, plus de 7 jours.

## Structure « course » (qui gagne, qui finit à tel rang)
- **Questions** : les questions électorales de la brique « scrutin » qui ont un sondage archivé (version Wikipédia datée).
- **Brique** : le calcul de la brique scrutin, avec une erreur σ₀ propre à chaque tranche. σ₀ est choisi parmi {2,5 ; 4 ; 6 ; 9 ; 13 ; 20} points, en maximisant la vraisemblance des issues des questions **résolues avant la date** dans la même tranche. S'il y en a moins de 10 dans la tranche, on prend toute la structure ; s'il y en a moins de 10 au total, σ₀ = 2,5.
- **Référence** : les semblables (p_S).
- **Axe d'échelle : la taille.** Tranches :
  - national (présidentielle, législatives, parlement) ;
  - infranational (gouverneur, État, région, maire) ;
  - primaire ou investiture.

  Règles écrites sur le titre, dans le code.

## Garde contre les « deux poches »
Les tranches sont fixées ici et ne changent pas après lecture des résultats. Toute nouvelle tranche, toute nouvelle structure : nouveau préenregistrement.
