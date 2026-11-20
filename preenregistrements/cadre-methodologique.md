# Cadre méthodologique (décision de l'auteur, 2026-11-20, 16 h 50)

Ce cadre précède tout nouveau test. Il s'ajoute aux règles d'adoption (`essais.py`, `regle-mise-au-point-confirmation.md`).

## 1. Mécanismes pour les questions Metaculus : partir de ce que Metaculus demande et de l'endroit où le bot perd
1. Classer les questions du tournoi par forme et par fréquence.
2. Sur les questions déjà résolues, chercher où le bot perd le plus de points, et pourquoi.
3. Ne tester que des mécanismes qui visent ces pertes-là, toujours contre la sortie réelle du bot (journal scellé), même en rétrospectif.
4. Un mécanisme vérifié à son niveau d'application entre dans le bot (choix d'auteur, pari assumé) ; sa sortie brute reste scellée pour pouvoir revenir en arrière.

Origine : trois semaines de bancs sur des questions fabriquées (GDELT, UCDP, FRED…) dont la forme n'existe presque pas sur Metaculus (ex. : classe de référence pondérée, solide sur « événements au niveau habituel en 30 jours », forme absente du tournoi) ; à l'inverse, « un candidat parmi N », tiré d'une forme réelle et fréquente, a donné un effet net.

## 2. Règles de prédictibilité : observer d'abord, expliquer ensuite, tester une fois
Révisé le 2026-11-20 à 18 h 07 (décision de l'auteur), après les essais acteurs de veto (plans A et B, clos) ; la version
de 16 h 50 (« fonder les hypothèses prioritairement sur des travaux de recherche existants ») est remplacée.
1. **Observer** : partir des observations empiriques sur nos données réelles (questions de Metaculus, pertes du bot).
   L'état précède l'essence.
2. **Expliquer** : une observation n'est retenue que si un mécanisme plausible l'explique ; la recherche existante sert
   à vérifier ce mécanisme, pas à fournir le point de départ.
3. **Tester** une fois, contre la sortie réelle du bot.

Origine :
- Ce qui a marché est parti d'une observation de nos données (« un candidat parmi N », vu sur des questions « Who
  will… ? » qui sortaient anormalement).
- Ce qui a échoué est parti d'une théorie transposée hors de son échelle ou de sa forme de question (géographie : front
  de diffusion, signes avant-coureurs, Richardson ; classe pondérée ; acteurs de veto de Tsebelis).
- L'empirique seul a son piège : le faux gain des classes homologues était une observation sans mécanisme (un pronom
  « who » classé en épidémies). Le pas 2 est là pour l'arrêter.

## 3. Suite
Travail écosystémique sur les facteurs causaux multiples, dans les deux cadres ci-dessus.

## 4. Sources : décisions de l'auteur du 2026-11-20 (21 h 10)
- Les prévisions d'experts (consensus des analystes, prévisions publiées par les entreprises ou les institutions) sont
  permises en entrée. Restent interdites : les cotes des marchés de prédiction et les prévisions de foule.
- EDGAR (SEC) : adresse de contact gardée en secret (SEC_CONTACT_EMAIL), jamais écrite dans le dépôt.
- e-Stat (statistiques officielles du Japon) : clé gratuite, gardée en secret (ESTAT_APP_ID).
