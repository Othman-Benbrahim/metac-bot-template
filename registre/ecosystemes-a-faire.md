# Écosystèmes : liste de travail (écrite par ecosystemes.py, ne pas retoucher)

Bilan : {'themes': 1, 'compartiments': 10, 'relations': 12, 'ponts': 7, 'ponts_en_attente': 7, 'relations_a_verifier': 12, 'compartiments_sans_trace_collectee': 2}

## Thèmes à écrire (ponts en attente)
- **energie-mondiale** (1 pont(s)) : ormuz:prix → energie-mondiale:prix (le prix du brut relie Ormuz à tous les importateurs)
- **inflation-mondiale** (1 pont(s)) : ormuz:prix → inflation-mondiale:energie (l'énergie entre dans l'inflation et donc dans les banques centrales)
- **iran-nucleaire** (1 pont(s)) : ormuz:interieur_iran → iran-nucleaire:negociations (le programme nucléaire et les sanctions se négocient ensemble)
- **rivalite-sino-americaine** (1 pont(s)) : ormuz:puissances → rivalite-sino-americaine:energie (la sécurité des approvisionnements chinois)
- **guerre-levant** (1 pont(s)) : ormuz:force → guerre-levant:iran (les fronts régionaux de l'Iran et de ses alliés)
- **transport-maritime** (1 pont(s)) : ormuz:navigation → transport-maritime:detroits (Ormuz)
- **eau-moyen-orient** (1 pont(s)) : ormuz:milieu → eau-moyen-orient:rarete (la rareté de l'eau douce dans la région)

## Compartiments sans trace collectée (à notre portée ? ou oubliés ?)
- ormuz:milieu : températures et vents (Open-Meteo ou réanalyses) (a_brancher)
- ormuz:prix : prix quotidien du Brent (FRED (a_brancher)

## Relations à vérifier sur une source relue
- ormuz:milieu → ormuz:flux_energie [contrainte] le goulet concentre le flux sur un seul passage étroit
- ormuz:flux_energie → ormuz:prix [forcage] une baisse du flux fait monter les prix mondiaux
- ormuz:force → ormuz:navigation [predation] saisies
- ormuz:navigation → ormuz:prix [forcage] assurance et fret transmettent le risque aux prix avant tout arrêt physique
- ormuz:puissances → ormuz:riverains [competition] rivalité États-Unis–Iran (style à mesurer au banc de la réciprocité
- ormuz:puissances → ormuz:interieur_iran [mutualisme] Chine–Iran
- ormuz:droit → ormuz:flux_energie [forcage] les sanctions réduisent et détournent les exportations iraniennes sans les arrêter
- ormuz:prix → ormuz:interieur_iran [forcage] les recettes de l'Iran dépendent du prix autant que des volumes vendus
- ormuz:interieur_iran → ormuz:force [forcage] une pression intérieure peut pousser à l'escalade extérieure ou à la retenue
- ormuz:milieu → ormuz:interieur_iran [forcage] chaleur et rareté de l'eau pèsent sur la vie et la contestation
- ormuz:recits → ormuz:prix [forcage] une menace verbale bouge les prix avant tout fait
- ormuz:force → ormuz:recits [mutualisme] démonstrations de force et récits se nourrissent (signalisation)
