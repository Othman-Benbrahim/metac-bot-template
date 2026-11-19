# Haidt — The Righteous Mind (extrait en roumain)

## Référence
Jonathan Haidt, *The Righteous Mind: Why Good People Are Divided by Politics and Religion*, 2012 ; traduction
roumaine *Mintea moralistă. De ce ne dezbină politica și religia*, Humanitas, 2015. Le PDF envoyé le 2026-11-19
(annoncé en italien, il est en roumain) ne contient que le chapitre 12 (« Ne pourrions-nous pas nous contredire de
façon plus constructive ? ») et la conclusion, environ 54 pages. Mémo dans nos mots ; seuls ces deux passages ont été
lus, le reste du livre est rappelé seulement là où le chapitre 12 le résume.

## Thèse en trois phrases
Les intuitions viennent d'abord, le raisonnement ensuite (l'éléphant et son cavalier) : on ne change pas l'avis de
quelqu'un par des arguments, mais en changeant d'abord ses intuitions, par les liens. Les camps politiques s'appuient
sur des fondements moraux pesés différemment (soin, équité, liberté, loyauté, autorité, pureté) ; la morale unit un
groupe et l'aveugle à ce que voit l'autre. La polarisation américaine vient en partie d'un réalignement inévitable des
partis et en partie de changements réversibles : disparition des liens personnels entre élus, tri géographique en
enclaves, règles des primaires, découpage et financement.

## Mécanismes retenus
Format : phrase · niveau · relation (fiche `humain`) ou code · paramètres · trace.

1. **Polarisation, compartiment de niveau idéologie.** · ideologie · compartiment polarisation · — · écart entre
   partis au Congrès (Voteview), électeurs dans des circonscriptions déséquilibrées (à brancher).
2. **Tri en enclaves.** La part des Américains vivant dans des États très déséquilibrés a fortement augmenté entre 1976
   et 2008 (chiffres du chapitre, non repris ici). · ideologie · tri → polarisation (+) ; rejoint le modèle de Schelling
   déjà posé · — · —
3. **La morale unit et aveugle.** · ideologie · morale → polarisation (+) ; six fondements ajoutés au compartiment
   morale · — · —
4. **Boucle camp-frontière.** · polarisation → nous_eux (+, forte), nous_eux → polarisation (+, saturation) · — · —
5. **Remède indirect par les liens.** Changer les intuitions par des relations personnelles entre camps plutôt que par
   des chartes de bonne conduite. · treve → polarisation (−) · — · —
6. **Blocage.** · polarisation → agenda (−), polarisation → hierarchie (+ : contestation permanente), pont vers
   politique-americaine:congres ; pont entrant politique-americaine:regles_electorales → polarisation · — · —
7. **L'interrupteur de la ruche.** Synchronie, rituel, menace commune font se fondre dans le groupe. · élément ajouté
   à nous_eux · — · —

## Ce qui a été écrit dans le programme (bot 0.10.331)
- `ecosystemes/humain.yaml` : compartiment polarisation ; 7 relations ; éléments ajoutés à morale et nous_eux ; 1 pont
  sortant ; 1 pont entrant (politique-americaine).
- Aucun code nouveau : les mécanismes s'expriment avec les outils déjà en place (simulation, masse critique, tri).
- Test : un tri maintenu fait monter la polarisation et la contestation du rang (l'agenda, lui, est poussé par la rue autant que bloqué : effet net à mesurer).

## Limites et critiques connues
- Extrait seulement ; la théorie des fondements moraux (chapitres 6 à 8) n'est connue ici que par son rappel au
  chapitre 12.
- Le questionnaire des fondements moraux et sa structure à six facteurs sont discutés ; l'opposition « libéraux sur
  deux fondements, conservateurs sur six » est contestée et dépend des échantillons américains.
- Analyse centrée sur les États-Unis.
