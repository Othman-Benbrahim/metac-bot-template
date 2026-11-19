# Préenregistrement : la réciprocité entre États (Rapoport, Axelrod), banc de compréhension
2026-11-19, bot 0.10.312, écrit avant la requête des données et tout calcul.

Décision d'auteur du 2026-11-19, 3 h 10 (« ok, ça me va »). Source : Rapoport (donnant-donnant : coopérer d'abord,
riposter, pardonner), Axelrod (tournois de 1980, tournoi écologique), Goldstein et Freeman (*Three-Way Street*, 1990 :
réciprocité mesurée entre grandes puissances). Banc DE COMPRÉHENSION : il ne touche ni le bot ni les questions ;
aucun essai, aucune adoption. Il dit si la réciprocité se VOIT dans nos données d'événements, et avec quel style.

## Données (GDELT 2.0, table des événements, BigQuery, gratuit, essai à blanc et plafonds)
- Acteurs : gouvernements et armées seulement (Actor1Type1Code et Actor2Type1Code dans GOV, MIL), deux pays
  différents. Aucune personne, aucun acteur privé.
- Période : 2023-01-01 → 2026-10-31, par semaine. Les 40 paires de pays les plus actives (deux sens confondus) ;
  pour chaque sens : nombre d'événements, somme et moyenne de l'échelle de Goldstein (−10 conflit, +10 coopération),
  comptes par grande classe (coopération verbale, matérielle ; conflit verbal, matériel).

## Mesure
Pour chaque sens A → B et chaque semaine : y = somme Goldstein / (n + 5) (rétrécie vers 0 quand peu d'événements).

## Modèle (fixé)
Pour chaque sens B → A : y_BA[t] = c + φ·y_BA[t−1] + ρ·y_AB[t−1] (ρ = réponse de B au geste de A la semaine
d'avant), contre le modèle sans ρ. Apprentissage avant 2025-07-01, test à partir de cette date, une semaine à l'avance
avec les vraies valeurs passées. Écart = erreur quadratique moyenne de test avec ρ − sans ρ, par sens, puis moyenne.

## Lecture (fixée)
- La réciprocité « se voit » si l'intervalle à 90 % de l'écart moyen (rééchantillonnage des PAIRES, 2 000 tirages,
  graine 0) est entièrement sous zéro.
- Descriptif, par sens : ρ ; réponse aux gestes de conflit (ρ−, sur la partie négative de y_AB) et aux gestes de
  coopération (ρ+, sur la partie positive) ; style : « donnant-donnant » si ρ− > 0,05 et ρ+ > 0,05 ; « rancunier » si
  ρ− > 0,05 et ρ+ ≤ 0,05 ; « indifférent » si les deux ≤ 0,05 ; « conciliant » si ρ+ > 0,05 et ρ− ≤ 0,05.

## Limites connues
GDELT code souvent un même article dans les deux sens (A accuse B, B répond) ; le décalage d'une semaine réduit cet
écho sans l'annuler. Les volumes suivent l'attention des médias anglophones. Une semaine est un grain grossier pour
des échanges qui se font parfois en heures.
