# Seuils de chaleur des cultures, cohérence sur nos propres mesures (préenregistrement, 2026-11-21, 18 h 35)

Décision de l'auteur (2026-11-21, 18 h 10-18 h 29) : compartiment agricole de l'écosystème « alimentation mondiale ».
Règles sourcées : `seuil_chaleur_mais_soja_coton` (Schlenker et Roberts 2008-2009) et `seuil_chaleur_ble` (Asseng et
al. 2015 ; Lobell et al. 2012), dans ecosystemes/regles-coutumieres.yaml. Écrit AVANT la première collecte ERA5-Land :
aucune donnée de température vue.

## Rasoir d'Ockham
1. Une phrase : plus une saison passe de chaleur au-dessus du seuil de la culture, plus le rendement national tombe
   sous sa tendance.
2. Paramètres : aucun appris ; seuils et périodes fixés par les sources et ci-dessous.
3. Sens fixé d'avance : corrélation négative.
4. Domaine : trois couples, un point ERA5-Land chacun ; un point représente mal tout un pays (limite assumée).
5. Plus simple ? La tendance seule (aucune chaleur) : c'est ce que mesure l'écart à la tendance.

## Données et méthode (fixées)
- Maïs américain : point « iowa » (42,03 ; −93,62), juin-août, seuil 29 °C ; rendement national (USDA PSD, Corn,
  United States).
- Blé américain : point « kansas » (38,50 ; −98,50), mai-juin, seuil 34 °C ; rendement national (Wheat, United States).
- Blé indien : point « pendjab » (30,90 ; 75,85), mars-avril, seuil 34 °C ; rendement national (Wheat, India).
Exposition : somme des degrés de la température maximale du jour au-dessus du seuil sur la période (approximation du
temps passé au-dessus du seuil, faute de séries horaires gardées). Écart de rendement : % par rapport à la tendance
linéaire 1990-2025 estimée sans l'année. Années 2005-2025, complètes seulement (campagne 2026 exclue, encore
provisoire). Spearman, bootstrap sur les années (5 000 tirages). Script `mise_au_point/seuils_agro_essai.py`, une fois.

## Critère (fixé)
Pour chaque couple : mécanisme confirmé sur nos mesures si l'intervalle à 90 % de la corrélation est entièrement sous
0. Rien n'entre dans le bot : l'essai dit seulement si la règle se lit dans nos données, condition avant toute
traduction en probabilités.

## Limites connues d'avance
21 années par couple : seul un effet net sortira de l'intervalle. Un point unique ; la sécheresse joue avec la chaleur
(2012 aux États-Unis) sans être séparée ; l'irrigation (Pendjab) amortit la chaleur.
