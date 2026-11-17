# Combinaisons de mécanismes : grille de bon sens (proposée le 2026-11-17)

**Statut : PROPOSITION de Claude, à corriger puis valider par l'auteur. Rien n'est calculé.** La date du commit prouve
que cette grille précède toute mesure.

## Origine
Théorie de l'auteur (2026-11-17, 11 h 44) : une situation complexe est un agrégat de situations simples, chacune avec
sa causalité, emboîtées comme une matriochka ; il faut trouver la bonne combinaison causale. Méthode décidée par
l'auteur (11 h 52, validée 11 h 55) : **d'abord le bon sens, le calcul ensuite, en appoint** ; une combinaison
trouvée au hasard ne vaut que si elle se vérifie sur d'autres situations aux mêmes variables. Fondement : H. Simon,
« The Architecture of Complexity » (1962), systèmes presque décomposables ; contre-thèse : Cynefin (le complexe ne se
décompose pas). Détail : `claude/hypotheses-concurrentes.md` (projet).

## Les quatre étapes
1. **Bon sens** : cette grille, écrite et datée avant toute mesure. Deux mécanismes par combinaison (rasoir d'Ockham).
2. **Exploration** : sur les jeux ForecastBench les plus anciens, pour chaque paire et chaque famille de questions,
   quatre cases (aucun, l'un, l'autre, les deux), OUI observés contre OUI attendus sous B corrigé ; consistance et
   couverture à la manière du QCA (Ragin).
3. **Confirmation** : les paires retenues sont rejouées sur des jeux plus récents, jamais vus, avec la règle
   d'adoption commune (risque corrigé par le nombre de paires essayées, plausibles ET témoins).
4. **Explication** : seulement pour ce qui passe l'étape 3.

## Les verdicts possibles du bon sens (fixés d'avance)
- **renforcement** : les deux ensemble font plus que la somme de leurs effets séparés ;
- **additif** : effets indépendants, la case « les deux » vaut à peu près la somme ;
- **annulation** : l'un efface l'effet de l'autre ;
- **redondant** : les deux mesurent en partie la même chose ; la case « les deux » n'apporte rien de plus ;
- **témoin** : combinaison sans raison d'agir (domaines disjoints), calculée quand même. Si les témoins réussissent
  aussi souvent que les combinaisons plausibles, **le bon sens n'apporte rien** : c'est la mesure de sa valeur.

## Les six mécanismes retenus (ceux qui ont un historique sur les questions déjà au banc)
| Code | Mécanisme | Indicateur, état « présent » | Familles concernées | Sens seul |
|---|---|---|---|---|
| M4 | B surestime les émeutes | question de la famille émeutes (sans indicateur extérieur) | mobilisation (émeutes) | − |
| M10 | Élection nationale proche | élection dans les 30 jours avant la date | mobilisation | + |
| M11 | Les troubles des voisins gagnent le pays | voisins en hausse (14 j contre 14 j, × 1,5) | mobilisation | + |
| M14 | Dates de mémoire | date du calendrier dans les 14 jours | mobilisation, violence | + |
| M17 | Rapprochement militaire avec le rival d'une puissance | `alignement_rival` ≥ 2 | stratégique, violence | + |
| FC | Démonstration de force chinoise (relais de la NGA) | `force_chinoise` ≥ 1 | stratégique, violence | + |

## La grille (15 paires)
| Paire | Verdict proposé | Raison (une phrase) | Sens attendu de la case « les deux » |
|---|---|---|---|
| M4 × M10 | additif | La surestimation des émeutes tient à la forme des comptes, l'élection au contexte : deux causes sans lien. | entre les deux effets |
| M4 × M11 | additif | Même raison : forme des comptes contre contagion. | entre les deux effets |
| M4 × M14 | additif | Même raison : forme des comptes contre calendrier. | entre les deux effets |
| M4 × M17 | témoin | Émeutes contre coopération militaire : domaines disjoints. | aucun |
| M4 × FC | témoin | Émeutes contre démonstration de force chinoise : domaines disjoints. | aucun |
| M10 × M11 | **renforcement** | Une campagne électorale ouvre une fenêtre de mobilisation : la contagion venue des voisins trouve des relais (attribution d'opportunité, *Dynamics of Contention*). | plus que la somme (+) |
| M10 × M14 | additif | Une date de mémoire peut être exploitée en campagne, mais les deux tombent rarement ensemble ; pas de raison d'un effet de plus. | somme (+) |
| M10 × M17 | **renforcement** | Une puissance choisit le moment électoral du pays aligné avec son rival pour montrer sa force (exercices chinois autour des élections taïwanaises de 1996 et de 2024). | plus que la somme (+) |
| M10 × FC | **renforcement** | Même raison : la démonstration de force se concentre autour du scrutin. | plus que la somme (+) |
| M11 × M14 | additif | Contagion et calendrier : deux causes sans lien. | somme (+) |
| M11 × M17 | témoin | Manifestations des voisins contre coopération militaire : domaines disjoints. | aucun |
| M11 × FC | témoin | Même raison. | aucun |
| M14 × M17 | renforcement, faible | Dans les pays baltes, une date de mémoire et un rapprochement avec l'OTAN peuvent appeler ensemble une démonstration russe ; cas rares. | plus que la somme (+), peu de cas |
| M14 × FC | témoin | Calendrier de mémoire d'Europe orientale contre force chinoise : sans lien. | aucun |
| M17 × FC | **redondant** | La démonstration de force chinoise passée est en partie l'issue que M17 annonce : les deux mesurent le même épisode. | pas plus que le plus fort des deux |

Bilan : 4 renforcements (dont 1 faible), 5 additifs, 1 redondant, 5 témoins.

## Réserves déclarées avant la mesure
- **Peu de questions par case.** Les questions au banc sont surtout des questions ACLED (environ 200 fraîches, plus
  celles des autres bancs, à dédoublonner) ; M17 et FC ne concernent que quelques pays d'Asie de l'Est. Beaucoup de
  cases « les deux » seront vides ou minuscules : elles seront déclarées non jugeables, pas lues.
- **Les états de M17 et de FC** seront calculés par les indicateurs de niche (premier passage prévu ce soir).
- **Le témoin n'est pas parfait** : deux mécanismes de domaines disjoints sont rarement présents ensemble ; leur case
  « les deux » peut manquer d'effectif plus que les autres.

## Validation de l'auteur
_(à remplir : corrections éventuelles, date et heure de la décision)_
