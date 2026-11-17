# Classe de référence pondérée contre B (préenregistrement, 2026-11-17)

Décision d'auteur du 2026-11-17 (18 h 39) : « à tenter en ombre, ça ne nous coûte absolument rien ».
Source de l'idée : 0xnici/gta6-twitch-forecast (veille du 2026-11-17).

## L'hypothèse, en une phrase

Les mois passés ne se valent pas : ceux qui ressemblaient au mois présent, au moment de prévoir, en disent plus.

## B_noyau, fixé avant tout passage

- Classe : tous les pays, même type de question fabriquée (manifestations, émeutes, démonstrations de force), cas dont
  la fenêtre « après » est finie avant d0 et où la question se posait.
- Ressemblance mesurée sur deux nombres connus à d0 :
  - z = ln((avant + 1) / (moyenne des « avant » antérieurs du même pays + 1)), au moins 3 mois antérieurs ;
  - m = ln((avant + 1) / (avant du mois précédent + 1)).
- Poids w = max(0,005 ; exp(−½ Δz² − ½ Δm²)) (largeurs 1 et 1).
- p = (Σ w·issue + 1) / (Σ w + 2), le lissage de B.

## Jugement

- Questions : banc GDELT fabriqué (combinaisons_gdelt.py), celles où z et m existent.
- Confirmation : d0 à partir du 2025-11-01. Rien n'est ajusté sur l'exploration (aucun paramètre libre) ; elle est
  rapportée pour information.
- Écart de perte log B_noyau − B, bootstrap par mois, risque `es.risque_corrige(1)`.
- Meilleur que B si la borne haute < 0 ; moins bon si la borne basse > 0 ; sinon non tranché.
- Grille (0,5 ; 1 ; 2)² des largeurs : rapportée pour voir si le résultat tient sur un plateau ; elle ne sert pas à choisir.

## Réserves écrites d'avance

- Les issues viennent de GDELT, pas d'ACLED.
- Le noyau mêle tous les pays : il peut perdre ce que B sait d'un pays particulier.
- z capte surtout le retour vers la moyenne : si le noyau gagne, c'est la première lecture à vérifier.
- Reste en ombre jusqu'à une décision datée de l'auteur.

## Autres échelles (ajout du 2026-11-17, 18 h 50, avant tout passage de ces échelles ; décision d'auteur : « Let's go »)

Le premier passage (30 jours, GDELT) a donné B_noyau meilleur que B. Vérification à d'autres échelles, mêmes règles
sauf ce qui suit, tout fixé ici avant de calculer.

### Autre échelle de temps (GDELT, `cas_echelle`)
- Fenêtres de 7 jours (ancres chaque lundi depuis 2024-07-01) et de 90 jours (ancres chaque premier du mois).
- Seuils de question ⌈seuil × fenêtre / 30⌉ ; jours manquants tolérés ⌈3 × fenêtre / 30⌉.
- m = ln((avant + 1) / (fenêtre précédente de même longueur + 1)).
- Même noyau (largeurs 1 ; 1), même confirmation (à partir du 2025-11-01), bootstrap par mois ; les deux échelles sont
  jugées ensemble : risque `es.risque_corrige(1) / 2`.
- Lecture : si le gain tient à 7, 30 et 90 jours, c'est un mécanisme ; à 30 jours seulement, un accident.

### Autre domaine, questions réelles (séries FRED et DBnomics de ForecastBench, `banc_bn.py`, essai `b_noyau`)
- Classe : les intervalles de h jours de la même série sur 5 ans (ceux de B).
- z(t) = (valeur − moyenne de l'année avant t) / écart-type de l'année ; m(t) = (valeur − valeur h jours avant) / même
  écart-type ; w = max(0,005 ; exp(−½ Δz² − ½ Δm²)) ; P = (Σ w·hausse + ½) / (Σ w + 1).
- Critère des ombres de B (`critere_ombre_b`) : 100 premières questions, second regard à 200, blocs jeu × source.
- Réserve : en bourse, le retour vers la moyenne est faible ou inversé (élan) ; sur les températures, la saison domine.
  Le test peut échouer : c'est voulu.

## Sources d'événements du bot (ajout du 2026-11-17, 19 h 20, avant tout passage ; décision d'auteur : « plus on
## testera, mieux ce sera »)

Adoptée comme B du banc GDELT (19 h 10). Avant toute entrée dans le bot en direct : test sur les sources d'événements
que le bot interroge (`banc_cr_sources.py`, essai `classe_reference_sources`).
- Six sources, groupes fixés dans le code avant le passage : UCDP (25 pays), IODA (20 pays), USGS (M ≥ 4,5 et ≥ 5,5),
  GDACS (6 types d'aléa), lancements CelesTrak (7 propriétaires), sanctions OFAC (8 programmes).
- Questions : « plus d'événements dans les F jours après d0 que dans les F jours avant ? », posée si au moins 1 événement
  avant ; même noyau (largeurs 1 ; 1) ; la classe mêle les groupes d'une même source.
- Critère : par source, à 30 jours, au moins 30 questions de confirmation (d0 à partir du 2025-11-01) ; bootstrap par
  mois ; risque `es.risque_corrige(1) / k`, k = sources jugées. 7 et 90 jours : rapportés, non jugés.
- Une source « meilleure que B » devient candidate à l'entrée dans le bot ; l'entrée reste une décision datée.
- Attendu (Claude, avant le résultat) : gain sur UCDP, IODA, sanctions (rafales) ; rien ou perte sur les lancements
  (cadence régulière, tendance) ; incertain sur les séismes (répliques en rafales, mais fond poissonnien).
- Réserves : UCDP est lu au plus 5 pages de 1 000 événements par version (un pays très actif peut être tronqué) ; les
  dates des sanctions sont celles de la première apparition chez OpenSanctions.
