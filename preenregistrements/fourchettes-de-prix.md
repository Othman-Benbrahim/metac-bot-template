# Fourchettes de prix pour les questions numériques (préenregistrement, 2026-11-20, 20 h 04)

Décision de l'auteur (20 h 04) : laisser les seuils d'actions en oui/non (gain négligeable : une question sur 38) et
construire la branche numérique (six questions sur 38 dans le journal : clôtures de Nvidia, du Nasdaq, d'Anthropic,
entreprises à mille milliards, résultats d'entreprises).

- Modèle : même log-normal sans dérive que les seuils (σ sur 30 rendements), percentiles 10, 20, 40, 60, 80, 90
  (`seuils_prix.quantiles`).
- Calibrage : pour chaque actif, une date d'ancrage tous les 7 jours depuis 2018 ; clôture réelle à 7 et 14 jours
  calendaires ; part dans l'intervalle 10-90 (attendu 0,80) et 20-80 (attendu 0,60).
- Critère, par famille (FRED : cryptomonnaies, Brent, indices ; actions : Twelve Data, cours non ajustés) : couverture de
  l'intervalle 80 % entre 0,75 et 0,85 et de l'intervalle 60 % entre 0,55 et 0,65, à 7 et 14 jours. Si une famille
  sort de ces bornes, ses fourchettes ne sont pas branchées (pas de réglage de σ sur ces mêmes données).
- Si le critère est atteint : branchement dans le bot pour les questions numériques « clôture de l'actif à une date »,
  avec la distribution du bot scellée à côté.

## Résultat, famille FRED (2026-11-20, 20 h 15) : critère atteint, de justesse
2 772 ancrages par horizon (six actifs, 2018-2026). Intervalle 80 % : 0,751 à 7 jours, 0,763 à 14 jours ; intervalle
60 % : 0,580 et 0,579. Dans les bornes, mais du côté bas : les fourchettes sont un peu trop étroites (queues épaisses).
Par actif, le Nasdaq à 7 jours sort des bornes (0,725 ; 0,541) ; décision par famille, comme préenregistré.
Branché dans le bot en 0.10.401 pour les clôtures de bitcoin, éther, Brent, Nasdaq, S&P 500, Dow Jones.
Actions : passage à faire dans GitHub (workflow banc_fourchettes_actions.yaml).
