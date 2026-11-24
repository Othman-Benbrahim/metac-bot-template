# Taux de base par fiche de la carte (préenregistrement, 2026-11-24, 14 h 55)

Chantier C (décision de l'auteur du 2026-11-24). Rédigé avant le calcul ; passé une seule fois. Rien n'entre dans le bot.

## Observation qui motive l'essai
- La lecture des délais (part des chemins entrants qui tiennent dans l'horizon) ne sépare pas les issues : 27 % de oui
  sans chemin rapide, 23 % avec deux tiers de chemins rapides (registre/lecture-mecanique-corpus.json).
- En revanche, la part de oui varie nettement selon la fiche où la question est rattachée (corpus entier, vu avant cet
  essai) : compétitions 18 %, partis 44 %, politique américaine 39 %, élections d'Amérique latine 47 %. Mécanisme
  probable : le nombre d'issues concurrentes (« qui gagnera » se décline en une question par candidat).

## Méthode
- Questions : registre/jugement-questions.jsonl, titres distincts résolus, rattachés par mise_au_point/lecture_mecanique.py
  (termes validés et liste de rattachement validée le 2026-11-24).
- Coupure : apprentissage sur les questions jouées avant le 2025-11-01, essai sur celles jouées à partir de cette date
  (même coupure que le banc de la classe de référence).
- Prévision B (référence) : part de oui de toutes les questions d'apprentissage.
- Prévision F : pour chaque fiche rattachée, part de oui d'apprentissage rétrécie vers B, (k·B + oui) / (k + n) avec
  k = 20 ; moyenne sur les fiches rattachées ; B si aucune fiche. Probabilités bornées à [0,02 ; 0,98].
- Mesure : perte logarithmique moyenne ; écart F − B ; intervalle à 90 % par rééchantillonnage des questions (2 000 tirages).
- Critère : F adoptée comme repère si la borne haute de l'intervalle est sous 0. Sous-ensemble Metaculus rapporté à part
  (descriptif, trop petit pour un verdict).
