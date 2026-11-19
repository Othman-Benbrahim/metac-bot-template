# La carte aide-t-elle à prévoir ? Proxémie situationnelle sur les questions résolues (préenregistrement, 2026-11-19, 14 h 50)

Décision d'auteur du 2026-11-19, 14 h 40 (« fais cela ») sur la piste n° 1 du topo : relier la carte des écosystèmes
aux questions. Code : `banc_proxemie.py` ; essai `proxemie_carte`. Aucun modèle de langue. Ombre : rien dans le bot.

## Données
Les questions de jugement résolues de ForecastBench (`registre/jugement-questions.jsonl`), même cohorte complète et mêmes
garde-fous que `jugement_semblables` (clôture prévue passée depuis 30 jours ; apprentissage sur le seul passé admis).
Les questions combinées (« We are presenting you with two probability questions… ») sont EXCLUES (leçon du banc de
couverture). Confirmation : jeux de 2026.

## La carte au jour du jeu, sans fuite
Pour chaque date de jeu d, l'état de la carte est recalculé avec les seules valeurs datées ≤ d de chaque série (même
règle d'écart à l'habitude que `carte.py`), sans la calibration (mesurée sur toute la période : elle fuirait).

## Situer une question (règles fixées ici, avant tout passage)
Une question est rattachée aux fiches dont une expression régulière (anglais) touche son titre : ormuz, iran-nucleaire,
russie-ukraine, guerre-levant, liban-institutions, energie-mondiale, inflation-mondiale, crises-bancaires,
politique-americaine, rivalite-sino-americaine, economie-chinoise, securite-europeenne, climat-extremes, epidemies,
elections-amerique-latine, alimentation-mondiale, humain, sciences-techniques, information-cyber, transport-maritime,
dette-emergents, non-proliferation, migrations-demographie (expressions dans le code, `REGLES`).

## Traits tirés de la carte
Sur les compartiments mesurés des fiches touchées, au jour d :
- T : moyenne des |z| (plafonnés à 4) ;
- M : maximum des |z| ;
- B : plus petite marge de bascule des relations à seuil ou à masse critique de ces fiches (bornée à [−3 ; 3]) ;
- touchee : 1 si au moins une fiche est touchée.

## Modèles comparés (régression logistique L2, λ = 1, réapprise à chaque jeu sur le passé admis)
- P (référence) : recalibrage des questions semblables S seules : 1, logit(S).
- C (candidat) : les mêmes plus la carte : 1, logit(S), T, M, B, touchee.
La différence C − P isole ce que la carte ajoute, à recalibrage égal.

## Critère (un seul regard)
Perte log C − P sur les questions de confirmation, bootstrap par question, risque `es.risque_corrige(1)` ; C meilleur si
la borne haute < 0. Rapportés : la part de questions touchées, l'écart sur les seules questions touchées, par
plateforme (Metaculus à part), les coefficients appris avant la coupure.

## Attendu (Claude, avant le passage)
Pas de gain net d'ensemble : la carte ne voit qu'une partie des questions, avec des séries souvent courtes, et l'état
« loin de l'habitude » ne dit pas le sens de l'issue. Un petit gain possible sur les questions touchées de la géopolitique
et de l'énergie, où nos séries sont les plus longues. Un résultat nul ne réfute pas l'idée : il dirait que la carte, en
l'état, ne porte pas d'information au-delà des questions semblables.
