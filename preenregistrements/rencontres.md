# Brique « rencontres » (COLT) — procédure écrite avant le calcul

Décisions de l'auteur, 2026-11-24 : « On commence » (16 h 52) ; banc COLT lancé (18 h 09). Une passe ; sans retour.
Lus avant : les en-têtes COLT et les titres de la famille, sans leurs issues. Questions couvertes : 4 (Zelensky–Putin
deux fois, Trump–Putin, Russie–Inde–Chine) ; les rencontres d'envoyés États-Unis–Iran (6) et la présence au sommet de
l'OTAN (2) restent sans mesure (niveau non couvert par COLT).

## Règle (rencontres_regle.py)
Rencontre entre pays au niveau des chefs d'État ou de gouvernement : visite avec rencontre de l'hôte (dans un sens ou
l'autre) ou présence au même endroit les mêmes jours ; distinctes si 3 jours d'écart ou plus ; trois pays : les trois
présents ensemble. λ = (rencontres dans les 5 ans avant min(date de la question, 2025-12-31) + 0,5) / 5 ans ;
P = 1 − exp(−λ·h). Abstention : rencontre « diplomatique », envoyés, ministres, présence à un sommet, « not meet ».
Limites déclarées : COLT s'arrête fin 2025 ; la co-présence à un sommet multilatéral compte comme rencontre (un
« trilatéral » dédié est plus exigeant : surestimation possible).

## Évaluation (une passe)
Référence = part de oui de tout le corpus résolu hors groupe ; mélange d'un quart plafonné à 15 points ; branchement si
(1) règle < référence, (2) mélange < référence, (3) règle < référence sur 2026 (ecosystemes/rencontres-branchee.json) ;
dans le bot, même mélange avec sa prévision, même plafond, journal scellé.
