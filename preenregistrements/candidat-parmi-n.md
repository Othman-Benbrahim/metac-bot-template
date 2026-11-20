# « Un candidat parmi N » : partir de 1/N (préenregistrement, projet du 2026-11-20, en attente de validation de l'auteur)

Origine : correction des motifs de classement (commit 992eb95). Le gain des classes homologues sur Metaculus/GJOpen venait de questions « Who will… ? » rangées par erreur en « épidémies » ; ces questions, une par candidat d'une liste, sont résolues OUI dans 9,7 % des cas (31 sur 319), contre 28,5 % pour les autres (904 sur 3 168). Hypothèse : c'est la **forme** de la question qui porte l'information, pas l'écosystème. Règle candidate, explicable : pour une question qui demande si tel candidat l'emporte parmi N candidats exclusifs, partir de 1/N.

Phase : **mise au point** (échantillon `registre/mise-au-point/questions.jsonl`), conformément à `regle-mise-au-point-confirmation.md`. La confirmation se fera une seule fois, sur des questions publiées après le 2026-11-20 (`essais.CONFIRMATION_DEPUIS`).

## Questions (fixées sans regarder les issues)
- Source : Metaculus de l'échantillon (les seules à porter la forme « titre (option) » hors Manifold) ; Manifold rapporté à part, à titre descriptif.
- Groupe de questions sœurs : même source, même titre une fois retirée la parenthèse finale ; N = nombre de sœurs présentes dans l'échantillon. Groupes de N ≥ 2 seulement.
- Recensement (structure seule, issues non lues) : 75 groupes Metaculus, 590 questions.
- **Exclusif** (un seul gagnant possible), décidé sur le seul titre par une expression fixée d'avance : le titre contient « who will win », « who will be (the next) », « which (party|parties|team|country|candidate|company) … win|control », et ne contient pas « these ». Les autres groupes (« Which of these countries will… », « Who will Twitter unban… ») sont **non exclusifs** : plusieurs OUI possibles, aucune règle 1/N.

## Calcul (fixé)
- Témoin I : prévision actuelle de mise au point (rétrécissement vers le taux de base, comme dans `classes_homologues_essai.py`).
- Variante K : pour les questions d'un groupe exclusif, p = 1/N ; sinon, p = témoin I.
- Variante K½ : pour les groupes exclusifs, moyenne des log-cotes de 1/N et du témoin (poids 0,5 / 0,5) ; sinon témoin.
- Probabilités bornées à [0,01 ; 0,99]. Perte log.
- Intervalle à 90 % par rééchantillonnage **par groupe** (les sœurs d'un même groupe ne sont pas indépendantes).

## Critère
- Candidat à la confirmation si K − I (ou K½ − I) < 0 et l'intervalle à 90 % exclut 0. Une seule des deux variantes est retenue pour la confirmation : celle dont l'écart moyen est le plus bas, fixée avant la confirmation.
- Diagnostic, sans effet sur le critère : part des groupes « exclusifs » où exactement une sœur est résolue OUI (contrôle de l'expression), et part des groupes où N est vraisemblablement incomplet (aucune sœur résolue OUI).

## Limites connues
- N peut être sous-estimé : des options manquent dans l'échantillon (filtres de collecte, option « autre »). 1/N est alors trop haut.
- 1/N ignore les favoris : c'est un point de départ, pas une prévision ; une amélioration éventuelle (cotes, sondages) serait un autre essai.
- Rien n'entre dans le bot ; aucun modèle de langue ; aucune cote de marché ni prévision de foule en entrée.
