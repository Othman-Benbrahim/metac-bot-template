# Préenregistrement : B par retour vers la moyenne (Ornstein-Uhlenbeck) sur les séries
2026-11-18, bot 0.10.283, écrit avant le premier passage de banc_ou.py.

Décision d'auteur du 2026-11-18, 19 h 08 (« on teste, c'est gratuit »), à partir d'un post sur sept modèles de
calcul stochastique. Bilan avant test : Brownien (≈ B), AR(1) sur les variations (essai b_autoregressif, non adopté),
Chronos (non adopté), sauts et queue lourde (essai richardson, non adopté) ; Heston et la volatilité sans objet (nos
questions portent sur le SENS du mouvement). Jamais testé : le rappel du NIVEAU vers son équilibre.

## Règle (banc_forecastbench.b_ou, fixée avant toute mesure)
- Mêmes points que B : 5 ans, strictement avant la date d'information ; pas natif, k = arrondi de h / écart médian.
- Moindres carrés v_t = a + b·t + φ·v_(t−1) + e (t = rang de l'observation) ; φ borné à [0 ; 0,999] (ajustement
  refait avec φ fixé à la borne si besoin). La tendance linéaire évite de « rappeler » à tort une série qui croît
  (prix, PIB) : avec φ proche de 1, le modèle redevient une marche aléatoire avec dérive.
- Espérance itérée sur k pas, variance σ²(1 − φ^(2k))/(1 − φ²) ; P(hausse) = (1 − part des intervalles sans
  changement) × Φ(écart attendu / écart-type) ; bornée à 0,001–0,999.

## Comparaison
Questions de séries ForecastBench résolues (FRED, DBnomics), jeux postérieurs au 2026-07-01, même ordre que le banc de
la classe de référence (banc_bn.py). Critère des ombres de B (score_registre.critere_ombre_b, essai b_ou, n = 100,
second regard à 200), blocs jeu × source, risque corrigé des essais ouverts. Adoption seulement si l'intervalle corrigé
est entièrement sous zéro, puis décision datée de l'auteur. Rapportés aussi par source (FRED, DBnomics).

## Ce qu'on attend
Peu de chose. Les questions de séries sont presque à pile ou face (B 0,68–0,69, pile ou face 0,693). Gain possible sur
les séries qui reviennent vers un niveau (taux, chômage, écarts de crédit) ; perte possible sur les séries
saisonnières (températures de Météo-France dans DBnomics), que la règle ne voit pas.

## Défaut connu, constaté avant le banc (série simulée, pas une issue réelle)
Sur une marche aléatoire avec dérive simulée (400 points, dérive +0,1 par pas), φ estimé à 0,99 et P(hausse à 7
pas) = 0,47 au lieu d'environ 0,6 : l'estimation de φ par moindres carrés est biaisée vers le rappel quand la série
n'en a pas (biais de Dickey-Fuller). La règle n'est PAS modifiée pour autant ; le banc tranchera.

## Amendement du 2026-11-18, 19 h 30 (avant le premier passage du banc)
Décision d'auteur (« oui »), à partir d'un post sur l'AIC et le BIC. Variante AFFICHÉE, NON JUGÉE (pas d'essai de
plus) : pour chaque série, BIC gaussien sur son seul historique (5 ans avant la date) du modèle de rappel (a, b, φ, σ :
4 paramètres) contre la marche aléatoire avec dérive (Δv = c + e : 2 paramètres), sur les mêmes n points. Le rappel
n'est utilisé que si son BIC est plus bas d'au moins 2 points ; sinon B. But : corriger série par série le défaut
noté plus haut (rappel vu à tort sur les séries qui dérivent). Si la variante fait nettement mieux que le rappel
appliqué partout, un essai propre sera préenregistré ; elle ne peut pas être adoptée sur ce banc.
