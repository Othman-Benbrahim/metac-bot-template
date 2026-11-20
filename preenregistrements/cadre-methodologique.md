# Cadre méthodologique (décision de l'auteur, 2026-11-20, 16 h 50)

Ce cadre précède tout nouveau test. Il s'ajoute aux règles d'adoption (`essais.py`, `regle-mise-au-point-confirmation.md`).

## 1. Mécanismes pour les questions Metaculus : partir de ce que Metaculus demande et de l'endroit où le bot perd
1. Classer les questions du tournoi par forme et par fréquence.
2. Sur les questions déjà résolues, chercher où le bot perd le plus de points, et pourquoi.
3. Ne tester que des mécanismes qui visent ces pertes-là, toujours contre la sortie réelle du bot (journal scellé), même en rétrospectif.
4. Un mécanisme vérifié à son niveau d'application entre dans le bot (choix d'auteur, pari assumé) ; sa sortie brute reste scellée pour pouvoir revenir en arrière.

Origine : trois semaines de bancs sur des questions fabriquées (GDELT, UCDP, FRED…) dont la forme n'existe presque pas sur Metaculus (ex. : classe de référence pondérée, solide sur « événements au niveau habituel en 30 jours », forme absente du tournoi) ; à l'inverse, « un candidat parmi N », tiré d'une forme réelle et fréquente, a donné un effet net.

## 2. Règles de prédictibilité : des hypothèses fondées sur des travaux de recherche sérieux
- Continuer à émettre des hypothèses et à bâtir des systèmes, en les fondant prioritairement sur des faits réels établis par des travaux de recherche existants, adaptés à notre travail.
- C'est ce cadre qui doit donner une avancée structurelle et statistiquement solide.

## 3. Suite
Travail écosystémique sur les facteurs causaux multiples, dans les deux cadres ci-dessus.
