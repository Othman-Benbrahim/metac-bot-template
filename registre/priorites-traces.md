# Ordre des prochaines collectes (compartiments vides, niveaux rares d'abord)

Calculé par `priorites_traces.py` ; score = (relations débloquées + ½ × en attente) × (1 + rareté du niveau).

| # | compartiment | niveau | débloque | en attente | score | sources à brancher |
|---|---|---|---|---|---|---|
| 1 | `climat-extremes:saisons` | meteo | 1 | 14 | 15.33 | (aucune source écrite) |
| 2 | `alimentation-mondiale:cultures` | vegetal | 3 | 11 | 14.57 | prévisions de récolte publiques (FAO, USDA) |
| 3 | `eau-moyen-orient:rarete` | eau | 2 | 8 | 12.0 | indicateurs de stress hydrique (publics, annuels) |
| 4 | `humain:polarisation` | ideologie | 4 | 5 | 11.61 | part des électeurs vivant dans des circonscriptions très déséquilibrées |
| 5 | `humain:hierarchie` | statut | 5 | 3 | 11.17 | (aucune source écrite) |
| 6 | `humain:symboles` | convention | 4 | 3 | 10.27 | (aucune source écrite) |
| 7 | `securite-europeenne:defense` | statut | 4 | 4 | 10.15 | (aucune source écrite) |
| 8 | `inflation-mondiale:statistiques` | convention | 4 | 2 | 9.17 | (aucune source écrite) |
| 9 | `ormuz:milieu` | relief | 3 | 4 | 8.75 | (aucune source écrite) |
| 10 | `ormuz:force` | geopolitique | 5 | 2 | 8.37 | (aucune source écrite) |
| 11 | `crises-bancaires:confiance` | psychologique | 3 | 3 | 8.2 | attention médiatique et recherches en ligne sur une banque |
| 12 | `humain:conventions` | convention | 3 | 3 | 8.1 | violations publiques datées d'une norme (premier emploi d'une arme, rupture d'un cessez-le-feu, sortie d'un traité) |
| 13 | `non-proliferation:regime` | convention | 2 | 5 | 7.95 | documents publics des conférences d'examen (ONU) |
| 14 | `transport-maritime:ports` | technique | 4 | 2 | 7.86 | statistiques portuaires publiques (temps d'attente, volumes) |
| 15 | `oceans-et-fleuves:fleuves` | eau | 1 | 6 | 7.76 | débits publics des grands fleuves (USGS, services nationaux) |
| 16 | `sciences-techniques:ia` | technique | 2 | 6 | 7.71 | (aucune source écrite) |
| 17 | `humain:agenda` | statut | 3 | 3 | 7.5 | (aucune source écrite) |
| 18 | `iran-nucleaire:verification` | statut | 2 | 5 | 7.38 | rapports publics de l'Agence internationale de l'énergie atomique |
| 19 | `crises-bancaires:depots` | economie | 3 | 5 | 7.33 | (aucune source écrite) |
| 20 | `climat-extremes:tempetes` | meteo | 3 | 2 | 7.33 | avis des centres cycloniques (publics) |
| 21 | `humain:intention` | psychologique | 3 | 2 | 7.14 | aucune trace directe non intrusive en agrégat ; se lit dans les sondages d'intention publiés |
| 22 | `climat-extremes:vegetation` | vegetal | 3 | 3 | 7.07 | indices de végétation par satellite (publics) |
| 23 | `humain:disponibilite` | psychologique | 3 | 2 | 7.0 | (aucune source écrite) |
| 24 | `cycles-biogeochimiques:carbone` | chimique | 1 | 5 | 7.0 | (aucune source écrite) |
| 25 | `humain:opinion_publique` | societe | 3 | 3 | 6.9 | prises de position publiques datées (pétitions, déclarations, votes nominaux) |
