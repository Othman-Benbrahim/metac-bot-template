# Taux d'exécution des annonces — droits de douane américains (préenregistrement, 2026-11-24)

Décision de l'auteur : mesure validée le 2026-11-23 à 18 h 05 ; terrain et sources laissés au choix de Claude le
2026-11-24 à 12 h 11. Rédigé avant tout téléchargement des données. Rien n'entre dans le bot.

## Question
Quelle part des annonces de droits de douane du président américain est suivie d'effet, dans quel délai, et sous
quelle forme ? Taux de départ pour les questions du type « X fera-t-il ce qu'il a annoncé d'ici telle date ? ».

Position de l'auteur (grappe du temps du texte, 22 novembre) : l'annonce est déclarative, elle ne prédit rien par
elle-même ; la tenue des annonces est une propriété de l'émetteur. C'est cette propriété qu'on mesure.

## Sources (deux producteurs indépendants)
- **Annonce :** TiRADE (Global Linkages Lab, Brown University), dernière version, instantané conservé avec son empreinte.
- **Fait :** Federal Register (proclamations, décrets, avis de l'USTR), dates et liens seulement.
TiRADE code lui-même les actes appliqués à partir des décrets : son statut « Implemented » n'est donc pas une source
indépendante. Le fait est jugé sur le Federal Register ; TiRADE sert au rapprochement.

## Unité
Une mesure = une ligne TiRADE de rôle `first_statement` (menace ou annonce d'un taux, pour une cible). Les reprises de
la même mesure sur d'autres canaux ne comptent pas. Les annonces de rôle `modification` comptent comme mesures à part.

## Classement (fixé avant de voir les chiffres)
1. **Appliquée à la date annoncée** (à 3 jours près) ;
2. **appliquée en retard** (délai en jours) ;
3. **appliquée, modifiée** : taux plus bas, ou exemptions qui retirent l'essentiel de la cible ;
4. **suspendue ou retirée** (rôle `climbdown`, ou aucun acte et une suspension annoncée) ;
5. **sans suite** : aucun acte au Federal Register ;
6. **en attente** : date annoncée pas encore atteinte, ou moins de 90 jours écoulés sans date annoncée.
Une menace sans date annoncée est jugée à 90 jours.

## Ce qui est rapporté
- Les parts de chaque classe, séparément pour les menaces et les annonces, avec intervalle de Wilson à 95 %.
- Le délai médian entre l'annonce et l'acte.
- Les mêmes chiffres par canal (discours, Truth Social, déclaration écrite).
- Aucune pondération, aucun score unique.

## À préciser avant tout calcul
Les règles de rapprochement entre une ligne TiRADE et un document du Federal Register (cible, taux, fenêtre de dates)
seront écrites ici après lecture des colonnes, et avant tout comptage.

## Ensuite (vérification en temps réel)
Un journal des nouvelles annonces, chaque semaine à la parution de TiRADE ; chacune est jugée à sa date annoncée ou à
90 jours. Ce journal, et non le relevé du passé, sert de test.
