# Combinaisons de mécanismes : grille de bon sens (proposée le 2026-11-17)

**Statut : VALIDÉE par l'auteur le 2026-11-17 (12 h 00), avec une réserve (ci-dessous). Grille proposée par Claude,
commitée avant toute mesure (commit 711d600) ; la validation ne change aucun verdict.**

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
Décision du 2026-11-17 (12 h 00) : « D'accord, je valide à part pour les dates de mémoire qui viennent se rajouter.
L'additif me semble bancal et risque de ne pas fonctionner, le reste tient la route. Tu peux conserver les deux
additifs, mais je ne les considère pas comme de bons candidats. »
- Les deux paires additives avec les dates de mémoire, **M10 × M14** et **M11 × M14**, sont gardées et calculées,
  marquées « additif (faible selon l'auteur) ». C'est un second pronostic, celui de l'auteur, que la mesure pourra
  confirmer ou démentir. (Lecture de Claude : la troisième paire additive avec M14, M4 × M14, n'est pas visée ; à
  corriger si c'était le cas.)
- Tout le reste de la grille est validé tel quel.

## Ce qui a été fixé en codant (avant tout passage)
- Questions : ACLED de ForecastBench, forme « une fois », tous les jeux depuis le 2024-07-21 ; B corrigé.
- Exploration : jeux avant le 2026-01-01 ; confirmation : jeux à partir du 2026-01-01.
- Ajustement de la case « les deux » : δ = ln((O + 0,5) / (E + 0,5)) fixé sur l'exploration, ajouté en logit à B.
- Jugée si au moins 10 questions dans la case « les deux » à chacune des deux étapes ; risque de la règle d'adoption
  commune (5 % / nombre d'essais ouverts) divisé encore par k, k = nombre de paires × familles jugées ; bootstrap par
  jeu, 2 000 tirages, graine 0.
- M17 n'est mesurable qu'à partir de juillet 2025 (12 mois de rivalités) ; M10 seulement si le calendrier électoral
  couvre la fenêtre (rattrapage Wikidata depuis le 2024-06-01).
- Code : `combinaisons.py` (bot 0.10.225), workflow « Combinaisons de mécanismes ».

## Second banc : questions fabriquées sur GDELT (décision d'auteur du 2026-11-17, 13 h 50)
Constat avant tout passage : environ 23 questions ACLED « une fois » par jeu ForecastBench, donc environ 390 en
exploration ; la case « les deux » compterait souvent moins de 10 questions. L'auteur a décidé de fabriquer des
questions à partir des comptes GDELT déjà collectés. Fixé avant tout passage (`combinaisons_gdelt.py`, bot 0.10.226) :
- pour chaque pays et chaque premier du mois depuis le 2024-09-01 : plus de manifestations (posée si ≥ 10 dans les
  30 jours avant), plus d'émeutes (≥ 5), plus de démonstrations de force visant le pays (≥ 5, famille stratégique),
  dans les 30 jours suivants que dans les 30 jours précédents ; au plus 3 jours GDELT manquants par fenêtre ;
- B : part des « oui » du même pays et du même type parmi les mois où la question se posait et dont l'issue était
  connue avant la date, lissée (k + 1) / (n + 2) ;
- exploration avant le 2025-11-01, confirmation ensuite ; jugement identique (combinaisons.resumer) ;
- les DEUX bancs jugent la même grille : le risque de chacun est divisé par deux en plus ;
- effectif connu avant toute mesure (comptage des questions seulement) : 5 526 questions, 198 pays, 24 mois
  (manifestations 1 404 + 1 466, émeutes 505 + 561, force 829 + 761, exploration + confirmation).
Réserves : issue mesurée par GDELT et non par ACLED ; pour M11, indicateur et issue viennent de la même presse (aucun
volume de presse total par pays n'est collecté pour le contrôler) ; questions d'un même mois corrélées (bootstrap par
mois).

## Troisième étape : balayage exhaustif comparé au hasard (décision d'auteur du 2026-11-17, 14 h 30)
Constat (premier passage du banc GDELT, 14 h 26) : 11 tests jugés, aucune combinaison confirmée ; ce constat ne
distingue pas « rien à trouver » de « trop peu pour voir ». L'auteur demande de tester toutes les combinaisons, hors
bon sens. Fixé avant tout passage (`combinaisons_balayage.py`, bot 0.10.228) :
- huit indicateurs (M10, M11, M14, M17, force chinoise, contre-mesures chinoises ≥ 3 en 90 jours, actes hostiles russes
  ≥ 3 en 30 jours, élan propre des manifestations log > 0,4), seuls, par paires et par triplets : 92 combinaisons × 3
  types de questions fabriquées (manifestations, émeutes, force) ;
- même ajustement δ que le banc GDELT, exploration avant le 2025-11-01, au moins 10 questions par étape ;
- « réussite » : gain de perte log négatif sur la confirmation ;
- hasard : 200 redistributions des états entre pays du même mois (graine 0) ; p global sur le nombre de réussites et
  sur le gain total ; p corrigé par combinaison selon le meilleur gain de chaque tirage (Westfall-Young).
Lecture prévue : si les réussites ne dépassent pas le hasard (p ≥ 0,05), il n'y a pas, dans ces indicateurs, plus de
structure que le hasard n'en produit ; une combinaison n'est retenue comme piste que si son p corrigé est < 0,05, puis
elle est soumise au bon sens (explication) et à l'observatoire avant toute décision.
