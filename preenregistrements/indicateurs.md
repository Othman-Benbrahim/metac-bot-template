# Pré-enregistrement — indicateurs indirects (signaux faibles), conflits (bot 0.10.119)

**Décision d'auteur du 2026-11-15.** Les signaux faibles (Ansoff, *California Management Review*, 1975) ne se voient
qu'à travers des indicateurs qui précèdent les événements sans en parler. Sources vérifiées par la sonde du 2026-11-15
(exécution 43671902014), gratuites, avec historique. Commité AVANT tout calcul.

## Indicateurs (mesurés avant la date d'information ; absent = 0)
- **wiki** : log(vues moyennes des 14 derniers jours / vues moyennes des 90 jours précédents), article Wikipedia anglais
  du pays (Wikimedia REST).
- **ioda** : log(1 + alertes de coupure d'internet IODA dans les 30 jours avant la date) (Georgia Tech).
- **fcdo** : nombre de changements des conseils aux voyageurs du Royaume-Uni dans les 30 jours avant la date dont la note
  parle de sécurité (manifestation, troubles, violence, couvre-feu, « advise against », terrorisme…) (gov.uk).
- **pluie** : écart des précipitations des 90 derniers jours à la moyenne des mêmes 90 jours des 10 années précédentes,
  en écarts-types, à la capitale (Open-Meteo ; coordonnées restcountries.com).
Écartés : FMI via DBnomics (un an de retard) ; GDELT (0 point rendu) ; OpenSky (instantané seulement : à collecter).

## Modèles (fixés ici), validation croisée « un jeu laissé de côté »
- Référence : A recalibré, logit(p) = a + b·logit(A).
- Indicateurs : logit(p) = a + b·logit(A) + Σ βk·zk ; a priori normal 0, écart-type 1 sur les βk (2 sur a et b, b
  centré sur 1).
La référence est A RECALIBRÉ, pas A brut : on mesure ce que les indicateurs ajoutent au-delà du calibrage.

## Critère (essai `indicateurs`)
Questions ACLED du banc du bras A (gpt-5-mini), ordre du banc. Sur les 100 premières : perte log du modèle à indicateurs
inférieure à celle de A recalibré, intervalle de l'écart (bootstrap par blocs « jeu ») entièrement sous 0 au niveau
corrigé. Second regard à 200 si assez de questions. Coefficients par indicateur rapportés sans verdict.

## Limites déclarées
Beaucoup de « pays » ACLED sont des territoires ou des océans (indicateurs absents). Le calibrage de A a été mis en
évidence sur ces mêmes 150 questions (2026-11-15) : la référence en tient compte, la validation croisée aussi.
