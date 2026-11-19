# Ajzen — Attitudes, Personality and Behavior

## Référence
Icek Ajzen, *Attitudes, Personality and Behavior*, McGraw Hill / Open University Press, coll. Mapping Social
Psychology, édition 2025. Lu en epub (envoyé par l'auteur le 2026-11-19). Mémo dans nos mots.

## Thèse en trois phrases
Les attitudes et les traits généraux prédisent mal un acte isolé mais bien un ENSEMBLE d'actes (principe
d'agrégation) ; un acte précis se prédit par une disposition mesurée au même niveau de précision, même action, même
cible, même contexte, même temps (principe de compatibilité). L'intention est le meilleur prédicteur d'un acte qui
dépend de la volonté ; elle se forme sur trois piliers, l'attitude envers l'acte, la norme perçue et le contrôle
perçu, dont les poids varient selon l'acte et la population (théorie du comportement planifié). Le contrôle perçu
agit deux fois : sur l'intention, et sur le passage de l'intention à l'acte ; le comportement répété dans un contexte
stable devient habitude.

## Mécanismes retenus
Format : phrase · niveau · relation (fiche `humain`) ou code · paramètres · trace.

1. **Trois piliers de l'intention.** · psychologique · compartiments attitude, norme_percue, controle_percu,
   intention ; attitude → intention (+), norme_percue → intention (±), controle_percu → intention (+) · paramètre
   `poids` de chaque pilier (départ 0,6 ; 0,4 ; 0,5), que `carte.poids_de` utilise à la place de la force en mots
   tant qu'aucune mesure ne le remplace · sondages d'intention publiés (à brancher).
2. **Le contrôle modère le passage à l'acte.** · psychologique · intention → passage_acte (+, seuil) et modulation
   controle_percu ⇢ (intention → passage_acte) · `seuil` 1,5, `gain` 0,4 · coupures et censure (OONI) comme obstacle
   concret. Test : une attitude favorable sans contrôle ne produit pas d'acte ; avec contrôle, si.
3. **D'où viennent les piliers.** opinion_privee → attitude (+) ; opinion_publique → norme_percue (+) ; conventions →
   norme_percue (+) ; falsification → norme_percue (+, ignorance collective : chacun surestime l'adhésion des autres) ;
   hierarchie → controle_percu (±) ; stress_chronique → controle_percu (−). · psychologique · — · —
4. **Habitude.** L'acte répété dans un contexte stable nourrit l'intention suivante. · passage_acte → intention (+,
   faible) · — · —
5. **Agrégation.** Les dispositions prédisent des agrégats, pas des actes isolés. · méthode · déjà la règle de la
   fiche (populations seulement) ; confirme qu'on ne lit aucune personne · — · —
6. **Compatibilité.** Une mesure ne prédit une autre que si elles portent sur la même action, cible, contexte et
   temps. · méthode · `calibrer.lieux` et `calibrer.compatibles` : dans la fiche humain et ses ponts, une relation
   mesurée entre séries de pays différents est déclarée « incompatible » et la carte ne l'utilise pas (premier
   passage : 3 relations, dont manifestations américaines contre conflit au Soudan) ; ailleurs (géopolitique,
   finance) relier deux pays est le propos même et n'est pas contrôlé ; la clé `series` d'une relation impose la
   paire compatible · — · —

## Ce qui a été écrit dans le programme (bot 0.10.330)
- `ecosystemes/humain.yaml` : 4 compartiments, 12 relations dont une modulation.
- `carte.py` : `poids_de` (mesure, sinon paramètre `poids`, sinon force en mots).
- `calibrer.py` : principe de compatibilité (verdict « incompatible », compté au bilan).
- Tests : lieux et compatibilité ; poids écrit utilisé ; contrôle nul bloque l'acte.

## Limites et critiques connues
- L'écart entre intention et acte reste grand dans les méta-analyses (une part importante des intentions ne se
  réalise pas) ; la théorie explique mieux l'intention que l'acte.
- Mesures déclaratives sujettes aux biais de présentation de soi (Ajzen le traite au ch. 1 ; Kuran le radicalise).
- Théorie de l'individu ; son passage à des populations (nos agrégats) est notre hypothèse, cohérente avec son propre
  principe d'agrégation.
