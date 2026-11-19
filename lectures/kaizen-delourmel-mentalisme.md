# Kaizen et Delourmel — détection des mensonges et mentalisme

## Références
- Philippe Kaizen, *Détection des mensonges vs mentalisme*, Books on Demand, 2011 (ISBN 978-2-8106-1478-3), epub.
- Vincent Delourmel, *Les Secrets du mentalisme*, « vidéo-book », 2008, PDF de 52 pages.

Les deux ont été envoyés par l'auteur le 2026-11-19. Mémo dans nos mots.

## Ce que valent ces livres, selon la règle « chiffres et faits »
Aucun des deux n'apporte de mesure.
- **Kaizen** s'appuie sur des anecdotes : un conflit social, une interview télévisée, deux séances de voyance, deux appels à une émission. Il lit les gestes (recul, « fermeture », auto-massage) comme des signes de mensonge. Ses seuls chiffres sont invérifiables : « 95 % des voyants sont des charlatans », et la répartition des clients d'une voyante selon l'âge et le sexe, rapportée de mémoire.
- **Delourmel** est un recueil de tours de magie : forçages, prédictions à double sortie, carré magique.

Leur intérêt n'est pas factuel. Ils décrivent les **mécanismes** qui font paraître juste une lecture ou une prédiction qui ne l'est pas. Ce que l'on retient va donc au registre des mécanismes (`claude/mecanismes-a-connaitre.md` dans le projet), pas dans les relations chiffrées des fiches.

## Ce que dit la recherche, pour corriger Kaizen
Repères tirés de la littérature, et non des livres :
- **Bond et DePaulo (2006)**, méta-analyse de 206 documents et 24 483 juges : les gens repèrent un mensonge dans **54 %** des cas, à peine mieux que le hasard. Les « experts » ne font guère mieux.
- **DePaulo et al. (2003)** : sur 158 indices du mensonge étudiés, la plupart n'ont qu'un lien faible ou nul avec le mensonge. Lire les gestes (bras croisés, regard fuyant) ne détecte pas le mensonge, cela détecte le stress, qui a d'autres causes.
- **Forer (1949)** : 39 étudiants reçoivent le même portrait vague, présenté comme leur portrait personnel. Ils le jugent juste en moyenne à **4,26 sur 5**. C'est l'effet Barnum, le moteur de la « lecture à froid ».

Conséquence : **aucun indicateur tiré de la gestuelle n'entre dans le bot ni dans les fiches.** Ce serait une note de qualité, que l'on a déjà écartée pour le ton GDELT.

## Mécanismes retenus (registre des mécanismes)

1. **La lecture à froid (effet Barnum).** Des phrases vraies pour presque tout le monde (« vous donnez trop aux autres »), ajustées aux grandes préoccupations de chaque âge (amour, travail, santé), passent pour une connaissance intime. *Pour nous* : une lecture symbolique d'une situation qui conviendrait à toutes les situations ne dit rien. C'est le risque propre d'un alphabet de symboles. La garde est déjà là : chaque lecture doit produire une probabilité notée sur l'issue réelle.

2. **La fausse prédiction à forte probabilité de réussite** (Kaizen, ch. 4). Une prédiction qui a l'air précise, comme « vers le 20 décembre, une femme à lunettes », mais dont chaque élément est fréquent. Avec beaucoup de prédictions, on fait quelques coups mémorables, et la réputation se bâtit sur eux.
   - *Pour nous* : le score sur toutes les prévisions, et non le souvenir des réussites. C'est ce que fait la règle de notation de Metaculus.

3. **La mémoire sélective du client.** Il retient ce qui a touché juste et oublie le reste. Sa détresse le rend coopératif : il complète lui-même les indices vagues.
   - *Pour nous* : ne jamais juger un outil sur des exemples choisis. On le juge sur le registre complet des questions résolues.

4. **Les deux poches (« multiple outs »)** (Delourmel, « Avec un journal »). On écrit deux prédictions, une dans chaque poche, et on ne sort que celle qui correspond au choix du spectateur.
   - *Pour nous* : multiplier les variantes, les bancs ou les ombres, puis ne retenir que celle qui a réussi. C'est le jardin des sentiers qui bifurquent.
   - Garde déjà en place : le préenregistrement de chaque essai, et le risque corrigé selon le nombre d'essais ouverts (`essais.py`).

5. **Le forçage (le choix illusoire)** (Delourmel : carré magique, forçage « Patéo », forçage par la somme des chiffres). Le spectateur croit choisir librement, mais toutes les voies mènent au même résultat.
   - *Pour nous* : le rédacteur d'une question choisit les options, le seuil et la date. La forme de la question peut forcer l'issue, et la saillance du moment pousse à surestimer le « oui ». C'est lié au point 7 de la feuille de route (« pourquoi cette question existe maintenant ») et au banc du rédacteur.

6. **La communication volontaire** (Kaizen, ch. 3). Une tenue et une image préparées pour produire une impression (décontraction, simplicité), que le comportement peut contredire. C'est l'écart entre le dit et le compté, à l'échelle d'une personne.
   - *Pour nous* : l'écart entre l'image publique d'un acteur et ses actes comptés. Pour les personnalités publiques et les institutions seulement, par leurs faits publics.

7. **Le détournement d'attention (« misdirection »).** On fait regarder ailleurs au moment où se fait le geste qui compte. C'est, à l'échelle d'un État ou d'un média, l'événement qui occupe l'attention pendant qu'une décision passe. On peut le tester avec nos séries d'attention : pages vues, GDELT, Federal Register un jour de forte actualité.
