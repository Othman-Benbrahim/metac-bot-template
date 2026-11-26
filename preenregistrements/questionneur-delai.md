# Questionneur × délai : la part de « oui » selon la forme de la question ET le temps restant (procédure avant calcul)

Décisions de l'auteur, 2026-11-26 : 15 h 41 (on ne définit pas un sujet après sa publication : travailler par familles,
pas par sujets a posteriori) ; 15 h 43 (« oui » au test du calendrier, puis traiter par famille).

## Idée
Une question dont le délai est plus court que les étapes nécessaires finit presque toujours par « non ». Mesurer les
étapes demanderait un modèle de langue ; le premier test, gratuit, porte sur ce qui se compte sans lui : le temps
restant (champ « horizon », jours entre la date de jeu et la résolution) à l'intérieur de chaque forme de question
(`structures_questions.structure`, déjà utilisée par le questionneur du dossier).

## Données
registre/jugement-questions.jsonl, questions résolues (Metaculus, Manifold, Polymarket, INFER ; CC BY-SA via
ForecastBench). Tranches d'horizon : ≤ 7 jours, 8-30, 31-90, 91-365, > 365.

## Modèles comparés
- **Forme seule** (le questionneur actuel) : part de « oui » de la forme, apprise sur l'apprentissage.
- **Forme × délai** : part de « oui » de la case (forme, tranche), rétrécie vers la forme seule avec le poids n/(n+20).
Probabilités bornées à [0,02 ; 0,98].

## Évaluation (une passe)
- Apprentissage : date de jeu avant le 2025-11-01 ; test : à partir du 2025-11-01 (coupure du banc « classe par
  fiche », où la dérive de la part de oui avait écrasé le signal ; on la reprend pour comparer honnêtement).
- Perte log moyenne sur le test, ensemble et sous-ensemble Metaculus ; intervalle à 90 % de l'écart par rééchantillonnage
  des questions (1 000 tirages, graine 20261126).
- **Retenue si** forme × délai fait mieux que forme seule d'au moins 0,005 sur l'ensemble du test ET sur Metaculus, et
  si l'intervalle de l'écart sur l'ensemble exclut 0. Elle remplacerait alors la ligne du questionneur dans le dossier.

## Étape suivante prévue (si retenue ou non)
Le calendrier proprement dit (étapes nécessaires contre jours restants) demande de lire la question : test séparé, sur
un petit échantillon et un modèle bon marché, avec sa propre procédure.

## Résultat du passage unique (2026-11-26, vers 15 h 50)
Apprentissage 1 395 questions (part de oui ≈ 14 % hors tranche > 365 j), test 2 823 (31 % de oui).
- Ensemble : forme × délai 0,7274 contre forme seule 0,7124 — **pire** (gain −0,015, IC90 [−0,020 ; −0,010]).
- Metaculus : 0,5686 contre 0,5703 (gain +0,002, IC90 [−0,009 ; +0,013]) — rien de net.
- **Non retenue.** Le temps restant seul n'apporte rien : la part de oui est à peu près la même de 7 jours à un an
  (11 à 14 %), sauf au-delà d'un an (53 %). Ce n'est pas le nombre de jours qui compte, mais ce qu'il faut accomplir
  dans ces jours : cela demande de lire la question (étape suivante prévue).
