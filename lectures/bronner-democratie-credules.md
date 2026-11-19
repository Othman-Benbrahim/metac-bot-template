# Bronner — La démocratie des crédules

## Référence
Gérald Bronner, *La démocratie des crédules*, PUF, 2013. Lu en epub (envoyé par l'auteur le 2026-11-19). Déjà croisé au
carnet d'appoint (marché cognitif, millefeuille argumentatif). Mémo dans nos mots.

## Thèse en trois phrases
L'offre d'information a explosé. Mais le biais de confirmation et notre avarice mentale font que cette abondance aide
surtout chacun à trouver ce qui confirme ce qu'il croit déjà. Sur ce marché cognitif dérégulé, les croyants motivés
produisent plus que les sceptiques, des arguments faibles s'empilent en « millefeuilles » convaincants, et la
concurrence entre médias pousse à publier avant de vérifier. La démocratie elle-même (droit de savoir, de dire, de
décider) amplifie ces effets quand la parole des plus motivés passe pour celle de tous.

## Mécanismes retenus (fiche `humain`)
Pour chaque mécanisme : niveau d'organisation · relation · paramètre éventuel.

1. **Théorème de la crédulité informationnelle et courbe FIC** (fiabilité selon la concurrence, ch. I et III).
   - Niveau : technique.
   - Relation : marche_cognitif → croyance_complot (+, seuil).
   - Paramètre : seuil 1,5.
2. **Paradoxe d'Olson appliqué aux croyances** (ch. II).
   - Niveau : technique.
   - Relation : croyance_complot → marche_cognitif (+, saturation).
   - Effet : une boucle qui s'entretient.
3. **Temps d'incubation réduit** (ch. II) : une version conspirationniste paraît quelques jours après l'événement.
   - Relation : passage_acte → croyance_complot (+).
4. **Effet râteau et négligence de la taille de l'échantillon** (ch. II-III).
   - Relation : disponibilite → croyance_complot (+).
5. **Effet Othello** (ch. IV) : un récit rend crédible une conclusion improbable.
   - Relation : symboles → croyance_complot (+).
6. **Emballements médiatiques** (ch. III) : France Télécom, « leucémies nucléaires ».
   - Relation : marche_cognitif → disponibilite (+).
7. **Ponts.**
   - Le marché cognitif et information-cyber:recits sont le même phénomène.
   - croyance_complot → observateur-mesure:biais. L'opinion visible en ligne n'est pas l'opinion. C'est à garder en tête
     pour toute question qui s'appuie sur des réactions en ligne.

## Ce qui a été écrit (bot 0.10.343)
- `ecosystemes/humain.yaml` :
  - un compartiment marche_cognitif (niveau technique) ;
  - 6 relations ;
  - 2 ponts.
- Aucun code nouveau.

## Limites
- Les mesures du livre (premières pages de résultats pour la psychokinèse, le monstre du Loch Ness, l'aspartame,
  l'astrologie) datent de 2012. Les moteurs et les réseaux ont changé depuis.
- La courbe FIC est un schéma qualitatif, pas une courbe mesurée. Nous la traduisons en une règle à seuil, à calibrer.
