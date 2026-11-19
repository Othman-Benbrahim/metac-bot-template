# Ordre des prochaines collectes (compartiments vides, niveaux rares d'abord)

Calculé par `priorites_traces.py` ; score = (relations débloquées + ½ × en attente) × (1 + rareté du niveau).

| # | compartiment | niveau | débloque | en attente | score | sources à brancher |
|---|---|---|---|---|---|---|
| 1 | `humain:croyance_complot` | psychologique | 11 | 6 | 24.14 | attention publique aux récits de complot (pages vues Wikipédia d'une liste fixe d'articles) |
| 2 | `alimentation-mondiale:cultures` | vegetal | 5 | 9 | 16.29 | prévisions de récolte publiques (FAO, USDA) |
| 3 | `eau-moyen-orient:rarete` | eau | 5 | 5 | 13.68 | indicateurs de stress hydrique (publics, annuels) |
| 4 | `humain:conventions` | convention | 4 | 4 | 11.0 | violations publiques datées d'une norme (premier emploi d'une arme, rupture d'un cessez-le-feu, sortie d'un traité) |
| 5 | `humain:croyances` | ideologie | 4 | 4 | 10.4 | enquêtes publiques de religiosité (Pew Research, World Values Survey) ; calendriers des fêtes et jeûnes religieux (dates publiques) |
| 6 | `humain:agenda` | statut | 5 | 2 | 10.2 | (aucune source écrite) |
| 7 | `securite-europeenne:defense` | statut | 4 | 4 | 10.05 | (aucune source écrite) |
| 8 | `ormuz:force` | geopolitique | 6 | 1 | 9.07 | (aucune source écrite) |
| 9 | `inflation-mondiale:statistiques` | convention | 4 | 2 | 9.0 | (aucune source écrite) |
| 10 | `oceans-et-fleuves:fleuves` | eau | 3 | 4 | 8.82 | débits publics des grands fleuves (USGS, services nationaux) |
| 11 | `cycles-biogeochimiques:carbone` | chimique | 2 | 4 | 8.0 | (aucune source écrite) |
| 12 | `non-proliferation:regime` | convention | 2 | 5 | 7.95 | documents publics des conférences d'examen (ONU) |
| 13 | `climat-extremes:vegetation` | vegetal | 4 | 2 | 7.86 | indices de végétation par satellite (publics) |
| 14 | `transport-maritime:ports` | technique | 4 | 2 | 7.84 | statistiques portuaires publiques (temps d'attente, volumes) |
| 15 | `humain:opinion_publique` | societe | 3 | 4 | 7.74 | prises de position publiques datées (pétitions, déclarations, votes nominaux) |
| 16 | `sciences-techniques:ia` | technique | 2 | 6 | 7.7 | (aucune source écrite) |
| 17 | `climat-extremes:secheresses` | eau | 3 | 3 | 7.68 | indices de sécheresse (moniteurs publics) |
| 18 | `iran-nucleaire:verification` | statut | 2 | 5 | 7.42 | rapports publics de l'Agence internationale de l'énergie atomique |
| 19 | `epidemies:malades` | personne | 1 | 5 | 7.0 | tableaux de bord publics de l'OMS et des agences nationales |
| 20 | `humain:tri` | societe | 4 | 1 | 6.82 | indices publics de ségrégation résidentielle (recensements) ; déplacements internes (IDMC) |
| 21 | `humain:intention` | psychologique | 3 | 2 | 6.76 | aucune trace directe non intrusive en agrégat ; se lit dans les sondages d'intention publiés |
| 22 | `humain:dilemme` | societe | 4 | 1 | 6.68 | respect daté d'accords de partage (quotas de pêche, eaux transfrontalières, quotas de l'OPEP+) |
| 23 | `politique-americaine:commerce` | economie | 5 | 0 | 6.64 | (aucune source écrite) |
| 24 | `relief-et-montagnes:chateaux_d_eau` | eau | 2 | 4 | 6.59 | couverture neigeuse par satellite (NASA MODIS) |
| 25 | `alimentation-mondiale:sols` | mineral | 1 | 5 | 6.56 | indices de végétation par satellite (NDVI, données publiques) |
