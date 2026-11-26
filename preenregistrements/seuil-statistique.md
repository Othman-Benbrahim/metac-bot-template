# Brique « seuil d'une statistique officielle à une date » (procédure écrite avant tout calcul)

Décision de l'auteur, 2026-11-26, 16 h 04 : « c'est bon » (piste 1 du recoupement familles × carte : c'est en suivant
cette piste qu'on aura les fondements les plus solides, sur le moyen et le long terme).

## Pourquoi
La famille « seuil sur une quantité » fait 13 % des questions de Metaculus et n'est couverte par une brique qu'à 3 %.
La brique des prix (marche aléatoire sans dérive sur la volatilité passée) est notre meilleure (0,14 contre 0,72). On
éprouve le même mécanisme sur les statistiques officielles mensuelles : la valeur publiée dans h mois est la dernière
valeur plus un pas aléatoire dont l'ampleur est celle des pas passés de la même série.

## Séries (registre/fred.csv, mensuelles, 2015-2026)
Taux (en points) : UNRATE (chômage) ; inflation sur un an calculée depuis CPIAUCSL et CPILFESL ; hausse sur un an des
salaires horaires (CES0500000003). Niveaux (en logarithme) : UMCSENT (confiance des ménages), et les prix mensuels des
matières (PFOODINDEXM, PCOPPUSDM, PNICKUSDM, PURANUSDM, PALUMUSDM, PIORECRUSDM, PZINCUSDM, PWHEAMTUSDM, PMAIZMTUSDM).

## Questions construites (comme le duel tennis)
Pour chaque série, chaque mois t (dès 36 mois d'historique), chaque horizon h ∈ {1, 3, 6, 12} mois disponible :
- taux : seuils T = dernière valeur ± δ, δ ∈ {0,1 ; 0,3 ; 0,5 ; 1,0} point ;
- niveaux : T = dernière valeur × (1 ± r), r ∈ {2 ; 5 ; 10 ; 20} %.
Issue : la valeur du mois t+h est au-dessus du seuil (question « au-dessus » pour les seuils plus hauts, « en dessous »
pour les plus bas).

## Règle
Pas de dérive. Écart-type σ_h des variations sur h mois de la même série, sur les 36 mois précédant t (au moins 24
variations). P = Φ(écart au seuil / σ_h) selon le sens, bornée à [0,02 ; 0,98].

## Référence
Part de « oui » des questions de même nature (taux ou niveau), même cran et même horizon, sur les AUTRES séries.

## Décision (une passe)
Retenue si la perte log de la règle est inférieure à la référence sur l'ensemble ET sur au moins deux tiers des séries.
Branchement ensuite (décision de l'auteur) pour les questions vivantes dont la série est reconnue, sous le contradicteur
et le juge, au même rang que la brique des prix.

## Limites déclarées
Les valeurs de FRED sont révisées ; une question se tranche souvent sur la première publication : léger écart. Les
questions construites se recouvrent (pertes non indépendantes). Peu de séries mensuelles : la couverture des questions
vivantes dépendra des séries collectées (à étendre par famille, procédure à part).

## Résultat du passage unique (2026-11-26, vers 16 h 15)
43 936 questions construites, 14 séries. Perte log : règle 0,5055 contre référence 0,4963 ; la règle ne gagne que sur
4 séries sur 14 (inflation CPI, confiance des ménages, prix alimentaires, minerai de fer). **Non retenue.**
Lecture : la règle n'est pas mal calibrée (annoncée sous 0,2 : 10 % de oui ; 0,2-0,4 : 29 % ; 0,4-0,6 : 41 %), mais la
volatilité propre de chaque série, mesurée sur 36 mois (fenêtres qui traversent le choc de 2020-2023), n'apporte rien
de plus que la fréquence de franchissement d'un même pas sur les autres séries. Sur les statistiques mensuelles, « de
combien ça bouge d'habitude » se mesure aussi bien en mettant les séries en commun qu'en les prenant une par une.
