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
