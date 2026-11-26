# Famille cyclique, épidémies : la rougeole (procédure écrite avant tout calcul)

Décisions de l'auteur, 2026-11-26 :
- 16 h 26 : les épidémies sont plutôt cycliques ; les cycles varient selon l'espace choisi, selon un circuit de
  diffusion par les réseaux de transport (avion, bateau, voiture, train) et selon la couverture médicale.
- 16 h 31 : sources OMS validées (cas de rougeole par pays, couverture vaccinale OMS/UNICEF) ; troisième variable à
  prendre en compte : l'âge ; « tu peux commencer ».

## Sources
- OMS, Global Health Observatory (API OData publique) : cas de rougeole déclarés par pays et par an (WHS3_62),
  couverture première dose (WHS8_110), seconde dose (MCV2).
- Banque mondiale (API publique, source déjà validée) : arrivées internationales (ST.INT.ARVL), taux de natalité
  (SP.DYN.CBRT.IN), population (SP.POP.TOTL), part des 0-14 ans (SP.POP.0014.TO.ZS).

## Unité et questions construites
Pays-année t (année cible), avec ce qui est connu à la fin de t−1. Seulement si les cas de t−1 sont d'au moins 10.
Question : « les cas de l'année t dépasseront-ils k × cas de t−1 ? », k ∈ {0,5 ; 1 ; 2 ; 5}.

## Variables (traduction de l'hypothèse de l'auteur)
- **Cycle de l'espace** : log des cas de t−1 ; années écoulées depuis le dernier pic (année dont les cas dépassent le
  double de la médiane des 10 années précédentes ; 10 si aucun) ; log du rapport entre le maximum des 5 années
  précédentes et les cas de t−1.
- **Couverture médicale** : couverture première et seconde dose en t−1 (seconde dose absente : remplacée par la
  première, avec un indicateur d'absence).
- **Âge** (renouvellement des enfants non protégés) : taux de natalité et part des 0-14 ans en t−1.
- **Connectivité** (circuit de diffusion par les transports) : log des arrivées internationales par habitant en t−1
  (absente : médiane de l'apprentissage, avec un indicateur d'absence).

## Modèles comparés (régression logistique, avec le cran k en variable)
(a) « comme l'an dernier » : part de oui de chaque cran k sur l'apprentissage ;
(b) le cycle seul ; (c) le cycle + couverture + âge + connectivité (mécanisme complet de l'auteur).

## Épreuve (une passe)
Apprentissage : années cibles 2001-2018. Épreuve : 2022-2025 (années Covid 2020-2021 sautées : les cas y ont chuté
partout pour une raison extérieure au mécanisme ; 2019 sautée, ses suites tombent en 2020).
Perte log ; intervalle à 90 % de l'écart (c) − (b) par rééchantillonnage des PAYS (1 000 tirages, graine 20261126).

## Décision
L'hypothèse est retenue si (c) bat (a) et (b) d'au moins 0,005 sur l'épreuve ET si l'intervalle de l'écart (c) − (b)
exclut 0. On rapporte les coefficients (sens attendu : couverture basse, natalité haute, connectivité haute → plus de
poussées ; longue durée depuis le pic → plus de poussées).

## Limites déclarées
Cas déclarés (sous-déclaration variable selon les pays) ; données annuelles (le cycle saisonnier n'est pas vu) ; la
connectivité est mesurée par le tourisme entrant, pas par le réseau de transport lui-même.

## Résultat du passage unique (2026-11-26, run 45850242432)
Apprentissage 6 864 questions, épreuve 1 376 (124 pays, 2022-2025).
- Perte log sur l'épreuve : (a) comme l'an dernier 0,6468 ; **(b) cycle seul 0,6229** ; (c) mécanisme complet 0,6340.
- (c) ne bat pas (b) (écart −0,011) : **non retenue.**
- Le **cycle** apporte un vrai gain sur « comme l'an dernier » (0,623 contre 0,647). Ses coefficients vont dans le sens
  attendu (plus de temps depuis le dernier pic → plus de poussées).
- Couverture première dose : sens attendu (couverture basse → plus de poussées, coefficient −1,41). Natalité : nul.
  Part des 0-14 ans et arrivées internationales : sens inverse de l'attendu (confusion probable avec le niveau de
  développement : les pays riches reçoivent plus de touristes et vaccinent plus).
- Doute sur les données : la seconde dose (MCV2) compte exactement autant de valeurs que la première (5 051), possible
  doublon de la série ; non vérifiable sans relance (règle : pas de relance sans dysfonctionnement avéré).
- Lecture : à l'échelle du pays et de l'année, le cycle se voit ; la diffusion par les transports et l'âge ne se voient
  pas avec ces mesures grossières (tourisme entrant, moyenne nationale). L'échelle de l'hypothèse de l'auteur (réseau de
  diffusion, espace local) est plus fine que celle des données.
