# Brique « occurrence dans une fenêtre » (préenregistrement, 2026-11-20)

Décisions de l'auteur : 2026-11-19 (écosystème d'acteurs sur quatre axes ; brique valable seulement pour des cas homologues à la même échelle ; tests reproductibles, automatisables, lancés une fois) ; 2026-11-20, 01 h 17 (« Let's go ») après le décompte par structure (`registre/structures-questions.md` : environ 70 % des questions résolues de Metaculus demandent si un fait se produira avant une date ; les élections, 8 %). Objectif fixé par l'auteur : battre le taux de base, puis la moyenne pondérée.

Essai `brique_fenetre`. Ombre : rien dans le bot, rien côté Metaculus avant le tournoi.

## 1. Questions
Registre des questions de jugement (Metaculus, Manifold, Polymarket, INFER ; cohorte complète, questions combinées exclues), structure « occurrence » : autre, procédure, événement rare, maintien (`structures_questions.structure`). Confirmation : jeu à partir du 2026-01-01. Couverture comptée sans les issues le 2026-11-20 : 2 127 questions d'occurrence, dont 969 en confirmation.

## 2. La brique
- Axe taille, avec sa vitesse propre : l'acteur qui doit agir, par règles écrites sur le titre, ordre fixe : militaire, judiciaire, législatif, international, chef, État, exécutif, entreprise, nature, autre.
- Axe vitesse : la longueur de la fenêtre (≤ 7, 8-30, 31-90, 91-180, > 180 jours).
- Probabilité : taux de « oui » MESURÉ dans la case acteur × fenêtre, sur les seules questions d'occurrence résolues et closes avant la date jugée. Case de moins de 30 questions passées : on remonte à l'acteur ; acteur de moins de 30 : taux de base (p_R1). Chaque niveau est rétréci vers le niveau supérieur (poids 5). Bornes [0,02 ; 0,98].

## 3. Comparaisons et critère
- Principal : brique contre les semblables (p_S, base actuelle du bot), perte log, intervalle de l'écart corrigé (risque d'`essais.py`) entièrement sous 0.
- Second : brique contre le taux de base (p_R1), même critère.
- Descriptif : la foule (valeur au gel, jamais une entrée), par acteur, par fenêtre.

## 4. Variables déclarées, hors de ce test
Fait programmé ou non (calendrier), régime (inertie des régimes fermés), saillance du moment. Elles seront testées ensuite, une par une, comme corrections de cette brique.
