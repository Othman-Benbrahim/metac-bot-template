# Front de diffusion : Hägerstrand à la bonne échelle (préenregistrement, 2026-11-17, 20 h 10)

Décision d'auteur du 2026-11-17 (20 h 00, « Oui, c'est parti »), après l'échec de M11 entre pays : « adapter ces
théories à nos appareils, en se servant de la bonne mesure à la bonne échelle ». La diffusion d'Hägerstrand est locale
(contagion de proximité, probabilité de contact décroissant avec la distance) : on la mesure entre carreaux PRIO-GRID de
0,5° (environ 55 km) avec les événements localisés d'UCDP GED, et on s'en sert pour prévoir le pays.

## Données
`collecte_ucdp_grille.py` : 25 pays en conflit (ceux du banc des sources), 2015 → aujourd'hui, une requête par pays et
par année (pages suivies jusqu'au bout), version annuelle puis candidates mensuelles de 2026.

## Questions et référence
- Par pays, premier de chaque mois depuis 2016-01-01 : « plus d'événements dans les 30 jours après qu'avant ? »,
  posée si au moins 1 événement avant.
- B = classe de référence pondérée (méthode adoptée, gagnante sur UCDP au banc des sources).

## Indicateur, fixé ici
FRONT = 1 si le nombre de carreaux actifs dans les 30 jours avant d0, inactifs dans les 150 jours précédents, et
voisins (8 directions) d'un carreau actif de cette période, est au moins max(2, ¼ des carreaux actifs des 30 jours).

## Jugement
δ sur FRONT = 1 en exploration (d0 avant 2024-01-01), appliqué en logit à B en confirmation (à partir de 2024-01-01) ;
au moins 10 questions par étape ; bootstrap par mois ; risque `es.risque_corrige(1)` ; confirmé si la borne haute < 0.
Attendu : δ > 0.

## Réserves écrites d'avance
- Les versions annuelles d'UCDP révisent le passé : le test lit la version actuelle, pas celle publiée à chaque date
  (fuite de révision, sans doute faible pour la localisation des événements).
- La classe pondérée capte déjà l'élan du pays ; FRONT n'apporte quelque chose que si la FORME spatiale de l'élan
  (s'étendre de proche en proche, plutôt que s'intensifier sur place) compte.
- Ensuite, si FRONT est confirmé : la version hiérarchique (capitale, grandes villes), puis les signes avant-coureurs de
  Scheffer sur les séries mensuelles longues, et le calendrier saisonnier par pays.
