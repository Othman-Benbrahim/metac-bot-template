# Pré-enregistrement — contexte physique : prévision météo pour les températures Météo-France (bot 0.10.135)

**Décision d'auteur du 2026-11-15 (16 h 22)** : « Oui, tu peux le faire pour Météo-France ». Idée de l'auteur : une
série sans contexte ne donne rien ; le contexte (« l'ambiant ») fixe les conditions de la série, et les règles
causales reliées à ce contexte disent dans quel sens elle va. Pour une température, le contexte est l'état de
l'atmosphère, et les règles causales sont celles des modèles de prévision météo. Commité AVANT tout calcul.

## Rasoir d'Ockham
1. **Une phrase** : la température dans 7 jours dépend de l'atmosphère d'aujourd'hui, que décrit la prévision émise
   aujourd'hui.
2. **Paramètres** : aucun appris. L'incertitude σ = 2,7 °C est fixée d'avance (ordre de grandeur connu de l'erreur
   d'une prévision de température moyenne journalière à 7 jours, combinée à celle du jour même).
3. **Sens fixé d'avance** : par la physique (prévision plus chaude → hausse plus probable).
4. **Domaine** : questions DBnomics « daily average temperature at the French weather station at … will be higher
   on D + 7 than on D », horizon 7 jours seulement.
5. **Plus simple ?** : B (comptage des hausses sur 5 ans) est la référence ; aucune règle plus simple n'utilise
   l'état de l'atmosphère.

## Règle (`banc_meteo.py`)
- Station : nom tiré de la question, géocodé par Open-Meteo (pays FR), coordonnées mises en cache.
- Prévisions archivées avec leur échéance (Open-Meteo « Previous Runs API », modèle par défaut) :
  T̂(D) = moyenne des températures horaires du jour D prévues la veille (`temperature_2m_previous_day1`) ;
  T̂(D+7) = moyenne des températures horaires du jour D+7 prévues 7 jours avant (`temperature_2m_previous_day7`,
  donc émises le jour D).
- P(hausse) = Φ((T̂(D+7) − T̂(D)) / 2,7), bornée à 0,01–0,99.
- Prévision manquante : rien (la question n'est pas comptée).

## Questions
Questions de température Météo-France de ForecastBench résolues, horizon 7 jours, jeux postérieurs au 2026-07-01,
ordre entrelacé fixé d'avance (rang SHA-1 de l'identifiant dans son jeu, puis jeu). Elles ont servi à d'autres
essais sur B ; la prévision météo n'y a jamais été utilisée.

## Critère (règle d'adoption commune, niveau corrigé ; second regard à 200)
**`contexte_meteo`** : sur les 100 premières questions, perte log de B météo inférieure à celle de B, intervalle de
l'écart (bootstrap par blocs « jeu × source ») entièrement sous 0.

## Limites déclarées
Les heures du jour D+7 prévues « 7 jours avant » viennent de passages du modèle répartis sur la journée D : une
partie peut être émise quelques heures après le début du jour D (fuite d'information de quelques heures, au plus).
La moyenne horaire n'est pas exactement la moyenne journalière de Météo-France (souvent (Tmin + Tmax) / 2) ; écart
de mesure commun aux deux jours comparés. Coordonnées de station approchées par géocodage (quelques kilomètres).
