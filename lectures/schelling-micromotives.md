# Schelling — Micromotives and Macrobehavior

## Référence
Thomas C. Schelling, *Micromotives and Macrobehavior*, W. W. Norton, 1978 ; nouvelle édition 2006 (préface nouvelle et
conférence Nobel en chapitre 8). Lu en epub (envoyé par l'auteur le 2026-11-19). Mémo dans nos mots.

## Thèse en trois phrases
Ce que fait une population n'est pas la somme de ce que veut chacun : quand chacun réagit à ce que font les autres, des
motifs individuels modestes produisent des résultats collectifs que personne n'a voulus (séparation, salle vide, ruée).
Ces systèmes se décrivent par des familles de modèles simples qui se retrouvent partout : masse critique et bascule,
thermostat, lemons, communs, prophéties autoréalisatrices, conventions, dilemmes à plusieurs. Certaines relations sont
des identités comptables qui tiennent quels que soient les motifs (les chaises musicales) et bornent ce qui est
possible avant toute psychologie.

## Mécanismes retenus
Format : phrase · niveau · relation ou code · paramètres · trace.

1. **Masse critique et bascule.** Chacun agit quand assez d'autres agissent ; les seuils individuels sont distribués ;
   la part qui agit demain est la répartition des seuils évaluée à la part d'aujourd'hui : équilibres stables, point de
   bascule instable, multiplicateur. Le « seuil » net n'en est que le cas limite. · societe · nouvelle règle
   d'intensité `masse_critique` (`carte.repartition`, `carte.equilibres`), relation passage_acte → passage_acte ·
   `mu`, `sigma` (départ 1,5 et 0,5 en |z|) · manifestations GDELT ; ajustement automatique dans `calibrer.py`
   (courbe en S contre droite, BIC).
2. **Tri et mélange.** Une préférence modérée pour les siens suffit à séparer, par départs en chaîne ; bascule vers
   l'extérieur et vers l'intérieur. · societe · nous_eux → tri (+, masse critique), tri → nous_eux (+), tri → treve (−)
   · `mu`, `sigma` · ségrégation résidentielle, déplacements internes (à brancher).
3. **Lemons et séminaire qui meurt.** Les meilleurs partent les premiers, la moyenne des restants baisse, d'autres
   partent. · societe · inscrit dans le compartiment tri ; même structure dans crises-bancaires (confiance) · — · —
4. **Thermostat.** Une boucle de rappel avec retard dépasse sa cible et oscille. · tous niveaux · `Carte.simuler`
   (simulation pas à pas, premier ordre, retards des relations) ; compte les changements de sens · retards, temps
   propres · toutes les traces branchées.
5. **Identités comptables (chaises musicales).** Une variation de stock égale l'entrée moins la sortie, quoi qu'en
   pensent les acteurs. · tous niveaux · clé de fiche `identites`, `Carte.verifier_identites` (incohérence ou sens
   impliqué) ; première identité : energie-mondiale, stocks = production − demande · coefficients · séries de stocks
   (identifiants FRED à trouver).
6. **Prophétie autoréalisatrice.** Si chacun s'attend à la ruée, la ruée a lieu. · psychologique · pont attente →
   crises-bancaires:confiance · — · confiance des ménages (UMCSENT).
7. **Conventions qui tiennent par l'attente.** Point focal, règle quelconque plutôt que pas de règle ; un tabou s'use à
   chaque violation (le non-emploi nucléaire depuis 1945, chapitre Nobel). · convention · conventions → passage_acte
   (−), passage_acte → conventions (−, hystérésis), symboles → conventions (+), pont vers non-proliferation:regime · —
   · violations publiques datées d'une norme (à brancher).
8. **Dilemme à plusieurs et communs.** Chacun gagne à faire défection ; k = la plus petite coalition qui gagne à
   coopérer ; la rareté pousse à prendre avant les autres. · societe · reciprocite → dilemme (+), hierarchie →
   dilemme (±), stress_chronique → dilemme (−, seuil), dilemme → treve (+) · `seuil` · respect daté des accords de
   partage (quotas OPEP+, pêche, eaux) (à brancher).

## Ce qui a été écrit dans le programme (bot 0.10.326)
- `ecosystemes.py` : règle `masse_critique` ; clé de fiche `identites` (validée, assemblée).
- `carte.py` : `repartition`, `equilibres` (équilibres, bascule, part haute), multiplicateur en S, modulateurs qui
  déplacent `mu` ; `simuler` (pas à pas ; une boucle sur soi plafonnée à 0,9 pour qu'elle ne bascule jamais seule) ;
  `verifier_identites` ; intensité observée plafonnée à |z| = 4 (une habitude presque nulle donne des z absurdes) ;
  ligne de commande `--simuler … [--maintenu]`.
- `calibrer.py` : `ajuster_masse_critique` ; une règle « seuil » mesurée devient « masse_critique » si la courbe en S
  gagne au BIC (Δ > 2).
- `ecosystemes/humain.yaml` : compartiments tri, conventions, dilemme ; 11 relations ; 3 ponts.
- `ecosystemes/energie-mondiale.yaml` : première identité.
- Tests : `tests/test_calibrer.py` (bascule selon l'ampleur sans état observé, oscillation d'un thermostat, identité,
  ajustement de la masse critique).

## Limites et critiques connues
- Modèles volontairement abstraits : ils montrent ce qui PEUT arriver, pas ce qui arrive ; les distributions de seuils
  réelles ne s'observent presque jamais directement (Schelling le dit lui-même au chapitre 4).
- Le modèle de ségrégation est souvent sur-interprété comme preuve que la ségrégation serait « naturelle » ; il montre
  seulement que des préférences faibles suffisent, il ne mesure pas les préférences ni les discriminations
  institutionnelles.
- Le chapitre sur le choix des gènes (ch. 6) est daté et n'entre pas dans la carte.
