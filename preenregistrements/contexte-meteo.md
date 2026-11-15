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

## Seconde version (décision d'auteur du 2026-11-15, 17 h 34), pré-enregistrée avant tout calcul
**Pourquoi.** Premier passage (212 questions) : météo 0,645 contre B 0,694, gain net dans 5 lots sur 7, pertes
lourdes dans 2 (2 et 16 août) : après des jours chauds, la prévision à 7 jours annonçait un fort rafraîchissement qui
n'est pas venu. Deux causes, connues et documentées par un travail public sur la même source
(chensirui3/kalshi-weather-forecaster, 2026) : (1) une prévision lointaine se rapproche de la moyenne saisonnière,
donc comparer une prévision à 1 jour (pour D) à une prévision à 7 jours (pour D+7) fabrique une baisse artificielle
en été ; (2) un seul modèle, une incertitude fixe : trop sûr les jours où la prévision est fragile.

**Rasoir d'Ockham.** Aucun paramètre appris ; σ₀ = 2,7 °C reste celui de la première version.

**Règle (`banc_meteo.prevision2`).**
- Cinq modèles mondiaux d'Open-Meteo (Previous Runs API) : `gfs_global`, `ecmwf_ifs025`, `icon_global`,
  `gem_global`, `meteofrance_arpege_world` ; au moins trois disponibles, sinon rien.
- Pour chaque modèle m : Δₘ = moyenne horaire du jour D+7 prévue 7 jours avant − moyenne horaire du jour D prévue
  7 jours avant (`temperature_2m_previous_day7_m`) : **même échéance**, le biais vers la moyenne saisonnière s'annule.
- Δ = moyenne des Δₘ ; s = écart-type des Δₘ entre modèles ; σ = √(σ₀² + s²).
- P(hausse) = Φ(Δ / σ), bornée à 0,01–0,99.
- Prix assumé : la prévision pour le jour D a une semaine (moins fraîche que celle de la première version).

**Questions et critère.** Seulement les jeux POSTÉRIEURS au 2026-09-27 (aucune question vue n'a inspiré ou ne juge la
règle), ordre entrelacé fixé d'avance. Essai **`contexte_meteo_v2`** : sur les 100 premières questions, perte log de
la seconde version inférieure à celle de B, règle d'adoption commune (niveau corrigé ; second regard à 200). La
première version reste calculée et décrite à côté. Limite : environ 30 questions de température par jeu, un jeu toutes
les deux semaines, et les stations d'un même jeu partagent la même météo : le verdict demandera plusieurs mois.

### Amendement du 2026-11-15 (17 h 50), avant tout calcul de la seconde version : questions construites
Constat : les jeux ForecastBench postérieurs au 2026-09-27 ne contiennent plus de questions de température (le jeu du
2026-10-11 porte sur des taux). La seconde version risquait de ne jamais être jugée. On construit donc des questions
de même forme sur les mêmes séries Météo-France (DBnomics), à des dates que rien n'a regardées :
- **dates** D = chaque jour à partir du 2026-10-04 (premier jour dont la semaine D…D+7 est entièrement postérieure au
  dernier jeu vu), tant que les valeurs de D et D+7 sont publiées ; les dates à venir s'ajoutent à chaque passage ;
- **une seule station par date**, tirée par l'empreinte SHA-1 de la date parmi les stations du premier passage
  (questions presque indépendantes : deux dates voisines ne partagent ni la station ni, au-delà d'une semaine, la
  météo) ;
- **issue** : valeur de la série à D+7 strictement supérieure à la valeur à D ; question écartée si l'une manque ;
- **B** : même règle que le banc (part des hausses sur 7 jours dans les 5 ans avant D, Jeffreys) ;
- **ordre** : chronologique ; blocs du bootstrap = semaine ISO de D ;
- les questions ForecastBench postérieures au 2026-09-27, s'il en vient, comptent aussi.
Critère inchangé (`contexte_meteo_v2`, 100 puis 200 questions). Environ 40 dates existent au 2026-11-15 : le premier
regard viendra vers la mi-janvier 2027 si aucun jeu ForecastBench n'en apporte.
