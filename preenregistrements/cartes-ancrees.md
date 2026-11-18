# Préenregistrement : cartes ancrées (faits cités, vérifiés et notés par le code)
2026-11-18, bot 0.10.274, écrit avant le premier passage de banc_cartes_ancrees.py.

Décision d'auteur du 2026-11-18, 16 h 10. But de l'auteur : réduire au minimum la part d'interprétation et
d'hallucination du modèle. Constat de départ : sur les mêmes questions, gpt-5-mini et Claude Haiku notent les cartes
différemment (accord de rang des notes libres de 0,24 à 0,63 selon la carte) ; les apports propres des cartes
divergent entre lecteurs, sauf pour la distance à la résolution et, en partie, le déclencheur.

## Ce qui est testé
Pour le DÉCLENCHEUR et la DISTANCE À LA RÉSOLUTION, le modèle n'attribue plus de note : il extrait un fait (date d'un
événement prévu ; valeur, seuil et sens) avec la phrase exacte de la recherche. Le code (cartes_ancrees.py) rejette
toute phrase absente mot pour mot de la recherche, toute valeur absente de la phrase citée, et calcule la note par
une règle fixe écrite avant le passage :
- déclencheur : 1 aucun événement vérifié ou hors fenêtre ; 2 vérifié sans date ; 3 daté dans la fenêtre
  [jeu ; échéance] ; 4 daté dans la première moitié de la fenêtre ;
- distance (questions chiffrées seulement) : 4 déjà atteint ; 3 écart relatif ≤ 5 % ; 2 ≤ 20 % ; 1 au-delà.

## Questions et lecteurs
Questions DISTINCTES du banc jugement_alphabet (première date de jeu ; 119 au plus), recherche gelée ; les questions
sans recherche sont écartées (elles relèvent du banc de l'abstention). gpt-5-mini (Azure) et Claude Haiku 4.5
(Bedrock). Un appel par lecteur et par question.

## Mesures et règle
1. **Principal** : accord de rang (Spearman) entre les deux lecteurs, notes ancrées contre notes libres, sur les
   mêmes questions, pour le déclencheur. Ancrage retenu si le gain d'accord est d'au moins +0,15.
2. Rapporté : même mesure pour la distance (questions chiffrées, souvent peu nombreuses).
3. Rapporté : part des faits proposés que le code rejette (hallucination mesurée), par lecteur.
4. Rapporté (descriptif) : lien de chaque note ancrée avec l'issue.
Adoption dans le bot : décision datée de l'auteur. Échantillon petit (au plus 119 questions, dont celles où les deux
lecteurs ont des notes libres) : le gain d'accord est un ordre de grandeur, pas une preuve fine.
