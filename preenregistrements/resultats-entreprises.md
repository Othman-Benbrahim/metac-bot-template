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
