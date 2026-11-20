# Comptes cumulés : référence et calibrage (préenregistrement, 2026-11-20, 20 h 25)

Décision de l'auteur (20 h 23) : commencer les chiffres publiés par les comptes cumulés (cas de rougeole du CDC, votes
par correspondance, cumul de pluies… : 3 des 10 questions « chiffre publié » du journal).

## Ce qui est établi
- Prévision épidémiologique à une ou deux semaines : le modèle de référence des centres de prévision du CDC
  (« COVIDhub-baseline », Cramer et al., « Evaluation of individual and ensemble probabilistic forecasts of COVID-19
  mortality in the United States », *PNAS*, 2022) prend comme médiane la dernière incidence observée, et ses
  quantiles dans la distribution empirique des variations passées de l'incidence. Il est difficile à battre à courte
  échéance ; l'ensemble des modèles fait mieux surtout au-delà de deux semaines.
- Pour un compte CUMULÉ : total à l'échéance = dernier total publié + somme des incidences à venir. L'incertitude porte
  sur les incidences, jamais sur ce qui est déjà compté (un cumulé ne baisse pas, sauf correction).
- Calendrier : le chiffre qui compte est celui publié le jour de résolution (le CDC met à jour sa page chaque semaine,
  décompte arrêté le jeudi à midi) ; l'échéance utile est la dernière publication avant la résolution.

## Modèle (fixé)
Incidences par période de 7 jours. Médiane de l'incidence future = moyenne des 4 dernières périodes ; quantiles de
l'incidence d'une période = cette médiane multipliée par les rapports empiriques (incidence d'une période / moyenne
des 4 précédentes) observés sur les 52 dernières périodes de la même série. Total à h périodes = dernier total + somme
de h incidences tirées (simulation, 2 000 tirages, rapports tirés indépendamment).

## Calibrage (fixé)
Données disponibles : événements UCDP par jour, 25 pays, 2015-2026 (registre/ucdp-cellules.csv.gz) ; séries très
irrégulières, donc épreuve dure. Ancrage tous les 7 jours depuis 2017 ; cumul depuis le 1er janvier de l'année ;
échéances 1 et 2 périodes (7 et 14 jours). Critère : couverture de l'intervalle 80 % entre 0,75 et 0,85 et de
l'intervalle 60 % entre 0,55 et 0,65, aux deux échéances. Aucun réglage sur ces données.

## Limite
UCDP n'est pas la rougeole : si le modèle tient sur des comptes aussi irréguliers que des événements de conflit, il
devrait tenir sur des comptes plus réguliers ; l'inverse n'est pas garanti. Les données de rougeole elles-mêmes (CDC)
seront collectées ensuite pour un second contrôle.

## Résultat (2026-11-20, 20 h 35) : critère manqué de peu, du côté prudent
12 675 ancrages par échéance (25 pays, 2017-2026). À 7 jours : intervalle 80 % → 0,826 ; 60 % → 0,665 (hors borne, au-
dessus de 0,65 : fourchette un peu trop LARGE). À 14 jours : 0,767 et 0,585 (dans les bornes). Critère préenregistré
non atteint (une case sur quatre, de 1,5 point, du côté large). Rien dans le bot à ce stade.

## Version 2 (préenregistrée le 2026-11-20 à 20 h 30, décision de l'auteur : « corriger le modèle »)
Correction tirée de la LITTÉRATURE, pas réglée sur UCDP : la v1 s'écartait de la baseline publiée (moyenne de 4
périodes, rapports tirés indépendamment). La v2 suit la description de Cramer et al. (2022) : médiane = dernière
incidence ; marche au hasard dont les pas sont les variations symétrisées des 52 dernières périodes ; incidence bornée
à 0 ; les pas s'additionnent, donc la fourchette s'élargit avec l'échéance (`comptes_cumules.fourchette_cumul_v2`).
Test sur des données que le modèle n'a pas vues : manifestations GDELT par pays (ancrages depuis juillet 2025) et
séismes M4,5+ mondiaux USGS (depuis 2001). Même critère, sur chacune des deux sources. UCDP rapporté sans effet sur le
critère. Lancé une fois (`mise_au_point/comptes_cumules_v2_essai.py`).

## Résultat v2 (2026-11-20, 20 h 45) : critère non atteint, fourchettes trop LARGES
Manifestations GDELT (16 240 ancrages) : 7 j → 0,857 et 0,717 ; 14 j → 0,877 et 0,745. Séismes USGS (1 348) : 7 j →
0,790 et 0,600 (dans les bornes) ; 14 j → 0,858 et 0,694. UCDP (descriptif) : 7 j → 0,826 et 0,664 ; 14 j → 0,876 et
0,717. La v2 élargit trop à 14 jours (les pas tirés au hasard s'additionnent plus que les vraies séries ne varient).
Les deux versions se trompent surtout du côté large. Rien dans le bot.
