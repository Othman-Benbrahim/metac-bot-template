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

## Unité (précisée le 2026-11-24 à 12 h 30, après lecture des colonnes de TiRADE v1.11, avant tout comptage)
Une mesure = une ligne TiRADE de rôle `first_statement` ou `modification` dont le type est `Threatened`, `Announced`
ou `Threatened / Announced`. Les lignes `Implemented` en première déclaration (77 sur 130) sont des actes, pas des
annonces : elles accomplissent ce qu'elles disent (le performatif) et sortent du calcul. Les reprises (`repeat`,
`duplicate`, `status_description`) ne comptent pas. Les menaces conditionnelles (`conditional = 1`, « si tel pays… »)
sont rapportées à part : leur condition peut ne jamais se réaliser.

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

## Règles de rapprochement (écrites le 2026-11-24 à 12 h 30, avant tout comptage)
- **Même cible :** les pays se recoupent (séparés par « ; », sans casse ; « All countries », « All foreign » et
  équivalents recoupent tout) ET les secteurs se recoupent (« All goods » recoupe tout).
- **Acte :** la première ligne postérieure ou du même jour, de type commençant par `Implemented`, de même cible, dans
  les 365 jours. Date de l'acte = sa date.
- **Vérification au Federal Register :** un document présidentiel signé à 3 jours près de la date de l'acte. Sans ce
  document, l'acte est noté « selon TiRADE seulement » et rapporté à part.
- **Recul :** une ligne `climbdown` de même cible entre l'annonce et l'acte (ou sans acte) : suspendue ou retirée. Un
  acte venu après le recul compte comme appliqué en retard, avec la mention du recul.
- **Modifiée :** taux appliqué inférieur au plus petit taux annoncé.
- **Date annoncée :** première date lisible dans `planned_for` (« Month D, YYYY », « D Month YYYY ») ; « immediate »
  ou « today » = date de l'annonce. Sans date lisible : délai rapporté, ponctualité non jugée.
- **En attente :** aucun acte, et date annoncée future, ou moins de 90 jours écoulés sans date annoncée.

## Ensuite (vérification en temps réel)
Un journal des nouvelles annonces, chaque semaine à la parution de TiRADE ; chacune est jugée à sa date annoncée ou à
90 jours. Ce journal, et non le relevé du passé, sert de test.

## Journal des passages
- **2026-11-24, 12 h 40, règle v1 (préenregistrée) : invalide.** 96 % des annonces « appliquées ». Artefact constaté en
  relisant les appariements : un acte général (« All countries », « All goods ») recoupait toute cible, et 74 actes sur
  99 étaient plus larges que l'annonce (l'acier pour tous « exécutait » une menace sur la Colombie). Résultat non retenu.
- **2026-11-24, 12 h 45, règle v2 (écrite après avoir vu l'artefact de v1) : borne basse.** L'acte doit nommer la
  cible. 46 % appliquées (IC95 37-56 %) sur 100 mesures jugées. Relecture des 23 « sans suite » non conditionnelles :
  une partie vient de libellés différents entre l'annonce et l'acte (« Letter countries (Japan, Korea…) », « Heavy
  Trucks », « Foreign automakers »), pas d'une absence d'acte. Les libellés de TiRADE sont du texte libre ; ni v1 ni v2
  ne les rapprochent correctement.
- **Suite proposée :** codage à la main des mesures non conditionnelles, chacune rapprochée d'un document du Federal
  Register (lien et date), une fois la collecte du Federal Register réparée.
