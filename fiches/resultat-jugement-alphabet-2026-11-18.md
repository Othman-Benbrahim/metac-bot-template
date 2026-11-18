sources: registre/banc-jugement-alphabet.json, registre/psychometrie-alphabet.json
constantes: 90; 0,03; 100
# Questions de jugement Metaculus : bot standard contre alphabet (2026-11-17 et 2026-11-18)

> CORRIGÉ le 2026-11-18 (audit des chiffres, 22 h) : la version précédente comptait 309 « questions » qui étaient
> 309 lignes pour 119 questions distinctes, et gardait des intervalles et un examen des cartes calculés par ligne.
> Chiffres ci-dessous recalculés par question ; détail dans claude/correctif-questions-distinctes-2026-11-18.md.

Préenregistrements `preenregistrements/jugement-alphabet.md` et `preenregistrements/psychometrie-alphabet.md` (écrits
avant les passages). Runs 44166010892, 44223001921, 44232305621. Modèle gpt-5-mini, une recherche bornée avant la date
du jeu, mêmes entrées pour A et M ; départ des questions semblables (B). La prévision de la communauté n'a jamais été
transmise au modèle ; elle n'est lue qu'après coup, comme repère.

## Verdict final (second regard) : critère non atteint, essai clos le 2026-11-18
309 lignes pour 119 questions distinctes, 27 questions résolues oui.
| | Perte log | Discrimination |
|---|---|---|
| B, questions semblables | 0,453 | 0,015 |
| A, bot standard (lit l'actualité) | 0,381 | 0,209 |
| **M, alphabet en matriochka** | **0,362** | 0,197 |
| Foule Metaculus (repère après coup, mêmes lignes) | [journal: 0,384] | — |
- Critère préenregistré, second regard : M − A = −0,019 ; intervalle 90 % par question [−0,053 ; +0,017] ;
  intervalle corrigé (niveau 99,64 %) [−0,074 ; +0,044] → **critère non atteint ; essai clos**.
- Constat descriptif, sans valeur de preuve : M devant A à chaque regard ([journal: −0,037 au premier regard]) ; l'écart
  s'est réduit en doublant l'échantillon. Face à la foule, écart non significatif.

## Décision d'auteur du 2026-11-18, 5 h 55 : M POSTÉ en compétition (bot 0.10.253)
L'auteur adopte M malgré le critère non atteint : le pari est favorable et le pire cas plausible est petit.
- M remplace A (et B tiré de la seule vue du modèle) sur les binaires du tournoi ; jamais un taux calculé ni C.
- A reste calculé et scellé avant toute carte. Règle d'arrêt préenregistrée (`preenregistrements/m-officiel.md`) :
  après 100 questions résolues où M a été posté, retour en arrière si M perd plus de 0,03 sur A.
- Les sept cartes (note et raison) figurent dans chaque commentaire posté, que M soit posté ou non.

## Examen des cartes, par question distincte (119 questions, seuil corrigé 0,0071)
Aucune carte démontrée sur gpt-5-mini. La plus proche : PROPORTION (distance à la résolution), effet +0,158,
p = 0,041 (bon sens, non démontrée). Les autres : HIÉRARCHIE p = 0,1179, CROISSANCE p = 0,1904, SEUIL p = 0,3103.
Toutes vont dans le bon sens. Aucune carte n'est retirée (décision d'auteur du 2026-11-17).
