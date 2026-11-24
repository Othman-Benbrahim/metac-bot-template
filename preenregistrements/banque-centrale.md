# Brique « banque centrale : inertie de la Fed » — procédure écrite avant le calcul

Décision de l'auteur, 2026-11-24, 15 h 59 : « je te laisse le champ libre » (source federalreserve.gov et construction
de la brique). Procédure versée AVANT tout calcul sur les issues ; passée une fois ; décision de branchement prise sur ce
seul passage, sans retour.

## Mécanisme (carte : inflation mondiale, banques centrales)
La Fed bouge par petits pas, dans la même direction, avec des pauses. Échelle d'une réunion programmée :
B50 (baisse ≥ 50 points), B25, M (maintien), H25, H50 (hausse ≥ 50 points).

## Mesure (sources officielles, gratuites)
- Changements de cible : federalreserve.gov/monetarypolicy/openmarket.htm et openmarket_archive.htm
  → `ecosystemes/fed-changements-taux.csv` (1990-2026).
- Réunions programmées : federalreserve.gov/monetarypolicy/fomchistoricalAAAA.htm (1994-2002, 2007-2020) et
  fomccalendars.htm (2021-2026) → `ecosystemes/fomc-reunions.csv`. Conférences téléphoniques, réunions non programmées,
  votes par notation et réunion annulée (mars 2020) exclus.
- Limite : calendriers officiels 2003-2006 non accessibles depuis l'espace de travail → ces réunions ne sont pas
  comptées (les changements de ces années servent seulement à l'état de départ de 2007).
- Contrôles faits sur les données (pas sur les issues) : 8 réunions par an (7 en 2020) ; niveaux enchaînés ; chaque
  changement depuis 2015 retrouvé dans le taux effectif quotidien FRED DFF, aucun saut de DFF inexpliqué.
- Réunion → décision : changement daté du dernier jour de la réunion ou des deux jours suivants ; sinon maintien.
  Changement sans réunion programmée dans cette fenêtre = hors réunion (« urgence »).
- Réunions au plancher (borne haute ≤ 0,25 % avant la réunion) exclues de la mesure : la baisse y est impossible.

## Règle
- État avant une réunion : sens du dernier changement connu, « récent » s'il date de la réunion précédente ou après,
  sinon « pause » → baisse_recente, pause_apres_baisse, hausse_recente, pause_apres_hausse.
- Probabilité de chaque barreau par état : fréquences sur les réunions closes AVANT la date de la question, + 0,5 par case.
- Plusieurs réunions : chaîne de Markov sur ces états (énumération exacte).
- Nombre de baisses d'une année : en pas de 25 points (B50 = 2), plus les baisses déjà faites dans l'année.
- Séquence « cut-pause-cut in AAAA » sans mois : les trois dernières réunions programmées de l'année.
- Baisse d'urgence : taux annuel des baisses hors réunion, temps au plancher exclu ; loi de Poisson sur le reste de l'année.
- Abstention : présidence ou gouverneurs de la Fed, autres banques centrales, « decide differently », titre non reconnu.
- Pas de correction de saillance : les barreaux sont posés en échelle complète par le questionneur (pas de sélection).

## Évaluation (une seule passe)
- Questions : corpus résolu, titres distincts reconnus (47 à la lecture des titres, sans les issues).
- Groupe = période visée (mois de la réunion, ou année).
- Référence = part de oui des questions reconnues hors groupe.
- Mélange = un quart (log-odds) avec la référence, plafonné à 15 points.
- Branchement si les trois tiennent : (1) règle < référence sur l'ensemble ; (2) mélange plafonné < référence ;
  (3) règle < référence sur les questions de 2026 (confirmation).
- Si branchée : dans le bot, même mélange d'un quart avec la prévision du bot, plafond 15 points, journal scellé.
