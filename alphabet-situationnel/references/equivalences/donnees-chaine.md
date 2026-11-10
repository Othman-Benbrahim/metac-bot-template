# Équivalents · strate 6 — données de jetons (banc sans texte)

> Version : 0.7.65

> Décision d'auteur du 2026-11-10 (`validation.md` §32). Ces équivalents traduisent les marqueurs des cartes en
> termes de **relevés de données** (faits de série, §31) pour les jetons de la chaîne Solana du banc
> `alphabet-chaine`. Ils **précisent** les marqueurs du noyau (`cartes.md`), ils ne les remplacent pas : la
> définition de la carte doit se lire dans la configuration des relevés. Les seuils chiffrés sont des conventions
> fixées avant toute issue. Tous sont **Proposés** (plafond de force A3). Ce fichier n'est chargé que par le banc
> (réglage `ALPHABET_EQUIV_DONNEES`) tant que l'auteur n'en a pas décidé autrement (§32).

| Carte | Équivalent | Marqueur dans les relevés | Statut | Référence |
|---|---|---|---|---|
| CROISSANCE | emballement puis saturation | au moins 3 bougies successives où le prix ou le volume varie dans le même sens (taux estimable) ; un pic suivi d'au moins 2 bougies en baisse est la **saturation ou le déclin** de la carte (sa définition les inclut), pas sa contradiction | Proposé | — |
| PROPORTION | concentration de l'offre | part des 10 premiers portefeuilles, du créateur ou des initiés dans l'offre ; ou rapport achats / ventes lu dans au moins deux fenêtres, pour voir s'il se conserve | Proposé | — |
| RÉSEAU | grappe d'initiés | réseau d'initiés détecté par la source, d'au moins 3 comptes reliés par des transferts | Proposé | — |
| POLARITÉ | acheteurs contre vendeurs | déséquilibre d'au moins 2 contre 1 entre achats et ventes dans une fenêtre d'au moins 10 transactions, **inversé** dans une fenêtre voisine | Proposé | — |
| HIÉRARCHIE | pouvoir du créateur sur les détenteurs | autorité d'émission ou de gel **non renoncée** : le créateur peut diluer ou bloquer les autres détenteurs (détenir beaucoup n'est pas commander : la concentration est une PROPORTION) | Proposé | — |
| CONTRAINTE | règle de la plateforme | autorité de gel active ; ou jeton sur courbe de lancement : l'échange reste limité à la courbe tant que le seuil de graduation n'est pas atteint. Un plafond de la série sans cause nommée est une saturation (CROISSANCE), pas une CONTRAINTE | Proposé | — |
| RÉSONANCE | ruée synchrone | une bougie concentre au moins 40 % du volume de la série, avec au moins 20 acheteurs distincts dans la fenêtre qui la contient | Proposé | — |
| PÉRIODICITÉ | vagues récurrentes | au moins 3 pics de volume dans la série, à intervalle approximativement constant | Proposé | — |
| SEUIL | migration, retrait de liquidité | pool sur une plateforme hors courbe (graduation) ; réserve en chute de plus de 80 % entre deux relevés | Proposé | — |
| TRACE·MÉMOIRE | réputation du créateur | autres jetons lancés par le même créateur, selon la source | Proposé | — |
| ÉMERGENCE | — | aucun marqueur dans ces relevés (pas de régularité collective nommable sans discours) | Vide | décision d'auteur, 2026-11-10 |
| INCERTITUDE | — | aucun marqueur dans ces relevés (conduites organisées par l'indétermination invisibles) | Vide | décision d'auteur, 2026-11-10 |
| COMMUNAUTÉ | — | aucun marqueur dans ces relevés (ni bien commun nommé ni règles d'appartenance) | Vide | décision d'auteur, 2026-11-10 |
| RÉCIPROCITÉ | — | aucun marqueur dans ces relevés (contre-transferts entre mêmes parties non identifiés) | Vide | décision d'auteur, 2026-11-10 |
| RÉCURSIVITÉ | — | aucun marqueur dans ces relevés (pas de représentation du système par lui-même) | Vide | décision d'auteur, 2026-11-10 |
| TRANSFORMATION | — | aucun marqueur dans ces relevés (la migration est un SEUIL) | Vide | décision d'auteur, 2026-11-10 |
