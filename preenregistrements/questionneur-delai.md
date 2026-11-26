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
