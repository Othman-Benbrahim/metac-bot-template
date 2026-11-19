# Écosystèmes : liste de travail (écrite par ecosystemes.py, ne pas retoucher)

Bilan : {'themes': 2, 'compartiments': 20, 'relations': 25, 'ponts': 14, 'ponts_en_attente': 12, 'relations_a_verifier': 25, 'relations_avec_intensite': 9, 'compartiments_sans_trace_collectee': 6}

## Thèmes à écrire (ponts en attente)
- **inflation-mondiale** (2 pont(s)) : energie-mondiale:prix → inflation-mondiale:energie (l'énergie entre dans l'inflation et dans les décisions des banques centrales) ; ormuz:prix → inflation-mondiale:energie (l'énergie entre dans l'inflation et donc dans les banques centrales)
- **transport-maritime** (2 pont(s)) : energie-mondiale:transport → transport-maritime:detroits (le système des passages maritimes) ; ormuz:navigation → transport-maritime:detroits (Ormuz, Bab-el-Mandeb, Suez forment un même système de passages)
- **russie-ukraine** (1 pont(s)) : energie-mondiale:decisions → russie-ukraine:sanctions (sanctions et plafond de prix sur le pétrole russe)
- **economie-chinoise** (1 pont(s)) : energie-mondiale:demande → economie-chinoise:activite (la Chine est le premier importateur)
- **climat-extremes** (1 pont(s)) : energie-mondiale:climat → climat-extremes:saisons (hivers, ouragans, vagues de chaleur)
- **politique-americaine** (1 pont(s)) : energie-mondiale:decisions → politique-americaine:energie (réserves stratégiques, sanctions, prix à la pompe et élections)
- **iran-nucleaire** (1 pont(s)) : ormuz:interieur_iran → iran-nucleaire:negociations (le programme nucléaire et les sanctions se négocient ensemble)
- **rivalite-sino-americaine** (1 pont(s)) : ormuz:puissances → rivalite-sino-americaine:energie (la sécurité des approvisionnements chinois)
- **guerre-levant** (1 pont(s)) : ormuz:force → guerre-levant:iran (les fronts régionaux de l'Iran et de ses alliés)
- **eau-moyen-orient** (1 pont(s)) : ormuz:milieu → eau-moyen-orient:rarete (la rareté de l'eau douce dans la région)

## Compartiments sans trace collectée (à notre portée ? ou oubliés ?)
- energie-mondiale:production : communiqués des réunions de l'OPEP+ (a_brancher), nombre de forages actifs (publication hebdomadaire publique) (a_brancher)
- energie-mondiale:stocks : stocks hebdomadaires américains (publication officielle publique) (a_brancher)
- energie-mondiale:prix : prix quotidien du Brent (données publiques) (a_brancher)
- energie-mondiale:climat : températures et prévisions saisonnières (données publiques) (a_brancher)
- ormuz:milieu : températures et vents (Open-Meteo ou réanalyses) (a_brancher)
- ormuz:prix : prix quotidien du Brent (FRED, données publiques) (a_brancher)

## Relations à vérifier sur une source relue
- energie-mondiale:production → energie-mondiale:prix [forcage] plus de production fait baisser les prix ; quand la capacité inutilisée s'épuise, le moindre arrêt fait bondir les prix
- energie-mondiale:demande → energie-mondiale:prix [forcage] une demande forte fait monter les prix
- energie-mondiale:stocks → energie-mondiale:prix [forcage] les stocks amortissent les chocs ; bas, ils n'amortissent plus
- energie-mondiale:transport → energie-mondiale:prix [forcage] un goulet fermé ou menacé fait monter les prix
- energie-mondiale:conflits → energie-mondiale:transport [forcage] attaques et menaces sur les routes
- energie-mondiale:conflits → energie-mondiale:raffinage [forcage] frappes sur les raffineries et terminaux (drones)
- energie-mondiale:raffinage → energie-mondiale:prix [forcage] un arrêt de raffinage fait monter les produits plus que le brut
- energie-mondiale:decisions → energie-mondiale:production [forcage] les quotas de l'OPEP+ et les sanctions décident de la production réelle
- energie-mondiale:prix → energie-mondiale:decisions [ambivalent] les producteurs réagissent aux prix (baisse de quotas quand les prix chutent) ; boucle de régulation
- energie-mondiale:prix → energie-mondiale:demande [forcage] des prix hauts finissent par freiner la demande
- energie-mondiale:climat → energie-mondiale:demande [forcage] un hiver froid fait monter la demande de gaz et de fioul
- energie-mondiale:climat → energie-mondiale:production [forcage] ouragans dans le golfe du Mexique, arrêts de plateformes
- energie-mondiale:recits → energie-mondiale:prix [forcage] annonces et menaces bougent les prix avant les flux
- ormuz:milieu → ormuz:flux_energie [contrainte] le goulet concentre le flux sur un seul passage étroit
- ormuz:flux_energie → ormuz:prix [forcage] une baisse du flux fait monter les prix mondiaux
- ormuz:force → ormuz:navigation [predation] saisies, menaces et mines pèsent sur la navigation (prédation : la force gagne un levier)
- ormuz:navigation → ormuz:prix [forcage] assurance et fret transmettent le risque aux prix avant tout arrêt physique
- ormuz:puissances → ormuz:riverains [competition] rivalité États-Unis–Iran (style à mesurer au banc de la réciprocité, paire USA–IRN)
- ormuz:puissances → ormuz:interieur_iran [mutualisme] Chine–Iran, pétrole contre devises et soutien diplomatique (relation propre à la Chine, pas à toutes les puissances)
- ormuz:droit → ormuz:flux_energie [forcage] les sanctions réduisent et détournent les exportations iraniennes sans les arrêter
- ormuz:prix → ormuz:interieur_iran [forcage] les recettes de l'Iran dépendent du prix autant que des volumes vendus
- ormuz:interieur_iran → ormuz:force [forcage] une pression intérieure peut pousser à l'escalade extérieure ou à la retenue
- ormuz:milieu → ormuz:interieur_iran [forcage] chaleur et rareté de l'eau pèsent sur la vie et la contestation
- ormuz:recits → ormuz:prix [forcage] une menace verbale bouge les prix avant tout fait
- ormuz:force → ormuz:recits [mutualisme] démonstrations de force et récits se nourrissent (signalisation)
