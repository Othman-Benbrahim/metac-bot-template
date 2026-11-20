# Cotes des marchés de prédiction, en ombre (préenregistrement, 2026-11-20, 23 h 15)

Décision de l'auteur (23 h 11) : « en ombre donc ». Les cotes n'entrent JAMAIS dans la prévision postée ni dans la
recherche du bot (le filtre `alphabet_recherche.sans_foule` reste). Elles sont relevées après le calcul de la prévision,
scellées dans `registre/journal-cotes.jsonl`, et ne servent qu'à mesurer, à la résolution, ce qu'elles auraient
rapporté ou coûté, et combien d'appariements étaient faux.

Origine : un bot concurrent du tournoi tire l'essentiel de son gain des cotes (+25 points contre 50 % sur 52 questions
Metaculus), mais sa pire question coûte −264 points : une erreur d'appariement est sûre d'elle et invisible.
L'auteur refuse ce risque sur ce qui est posté ; la mesure en ombre dira s'il est réel.

## Source
Polymarket seulement (argent réel), API publique « Gamma » (sans clé), fichier robots respecté. Manifold (monnaie
fictive) et Kalshi exclus.

## Appariement (fixé, strict : dans le doute, rien)
Questions binaires seulement. Un marché n'est retenu que s'il remplit TOUT :
1. marché binaire Oui/Non, ouvert, mise cumulée ≥ 50 000 $ ;
2. mêmes nombres dans les deux intitulés (seuils, jours, années), à l'unité près ;
3. mêmes mots de sens contraire (not, no, fail, remain, stay, leave, lose, without, before/after…) des deux côtés ;
4. similarité des mots pleins (Jaccard) ≥ 0,6 ;
5. date de fin du marché à moins de 31 jours de la date de résolution de la question ;
6. un seul marché candidat après ces filtres (deux ou plus : ambigu, rien).

## Mesure (fixée)
À la résolution : nombre de questions binaires avec un appariement ; perte logarithmique de la cote (bornée à
[0,01 ; 0,99] pour la mesure seulement) contre celle de la prévision postée ; pire écart ; appariements faux, repérés
quand le marché Polymarket se résout autrement que la question Metaculus. Descriptif tant qu'il y a moins de 30
questions appariées résolues ; à 30, l'auteur décide, sur ces chiffres, d'ouvrir ou de fermer la porte.
