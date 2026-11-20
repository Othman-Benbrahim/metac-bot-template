# Résultats d'entreprise : fourchette du chiffre d'affaires trimestriel (préenregistrement, 2026-11-20, 21 h 15)

Décisions de l'auteur : viser le mécanisme et non l'acteur (21 h 05) ; EDGAR accepté avec une adresse de contact gardée
en secret (21 h 07). Prévisions des entreprises et des analystes : non utilisées (pas de flux gratuit pour les premières ;
question de règle ouverte pour les secondes).

## Mécanisme (fixé, commun à toutes les entreprises)
Prochain chiffre d'affaires trimestriel = dernier trimestre publié × exp(quantiles empiriques des variations
logarithmiques d'un trimestre au suivant, 12 derniers trimestres, au moins 8) (`indicateurs_lents.fourchette_suivante`
sur le logarithme). Le BPA n'est pas traité (il n'est pas additif et dépend d'éléments ponctuels).

## Calibrage (fixé)
Données : EDGAR « companyfacts », 50 entreprises (`collecte_edgar.py`), trimestres consécutifs seulement, quatrième
trimestre déduit de l'année quand le 10-K ne le donne pas. Critère sur l'ensemble : intervalle 80 % entre 0,75 et 0,85,
intervalle 60 % entre 0,55 et 0,65. Lancé une fois, dans GitHub (workflow collecte_edgar.yaml), qui enregistre les données
(publiques) et le résultat.

## Limite connue
Le mécanisme ignore la prévision publiée par l'entreprise, souvent l'information la plus précise : il donne une
fourchette de départ honnête, pas la meilleure possible.

## Résultat (2026-11-20, 21 h 30) : critère manqué, fourchettes trop ÉTROITES
Collecte EDGAR complète (50 entreprises, 4 486 valeurs trimestrielles ; quelques séries courtes ou vides : CRWD et GS
sans chiffre d'affaires reconnu, XOM et UBER 4 trimestres). 1 403 prévisions d'un trimestre. Intervalle 80 % → 0,731
(hors borne, sous 0,75) ; intervalle 60 % → 0,550 (sur la borne basse). Contrairement aux comptes cumulés, l'écart est
du côté RISQUÉ (trop sûr de soi). Rien dans le bot. Décision de l'auteur attendue.

## Version 2 (préenregistrée le 2026-11-20 à 21 h 35, décision de l'auteur : « on peut essayer »)
Correction tirée de la LITTÉRATURE comptable, pas réglée sur les données vues : les chiffres trimestriels sont
saisonniers, et le modèle de référence compare chaque trimestre au même trimestre de l'année précédente (Foster,
« Quarterly Accounting Data: Time-Series Properties and Predictive-Ability Results », *The Accounting Review*, 1977 ;
Brown et Rozeff, *Journal of Accounting Research*, 1979).
- Modèle (Foster avec φ = 1, sans dérive), sur le logarithme x du chiffre d'affaires : croissance sur un an
  g(s) = x(s) − x(s−4) ; prochain trimestre = x(t−3) + g(t) + ε, où ε suit les quantiles empiriques des variations de
  cette croissance d'un trimestre au suivant, g(s) − g(s−1), sur les 20 derniers trimestres (au moins 12). Fenêtre
  plus longue que la v1 (12), fixée ici et non réglée.
- Données jugées : 25 entreprises JAMAIS utilisées (ajoutées à la collecte, liste dans `collecte_edgar.py`,
  NOUVELLES_V2), trimestres consécutifs seulement. Les 50 anciennes et la v1 sur les nouvelles sont rapportées à
  titre descriptif, sans effet sur la décision.
- Critère inchangé : intervalle 80 % entre 0,75 et 0,85, intervalle 60 % entre 0,55 et 0,65, sur les nouvelles.
- Lancé une fois (`mise_au_point/resultats_entreprises_v2_essai.py`, workflow collecte_edgar.yaml).

## Résultat v2 (2026-11-20, 21 h 37) : critère atteint sur les entreprises jamais vues
25 nouvelles entreprises (LMT, T, ABBV, VZ : séries trop courtes ou vides), 427 prévisions : intervalle 80 % → 0,766 ;
60 % → 0,595. Descriptif : v1 sur les mêmes 0,704 / 0,533 (la correction saisonnière fait la différence) ; v2 sur les
50 anciennes 0,776 / 0,600.
