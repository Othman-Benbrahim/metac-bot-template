# Pré-enregistrement — motifs ordinaux et combinaison avec A (bot 0.10.108)

**Décision d'auteur du 2026-11-15.** Hypothèse : « l'état précède l'essence » — les structures utiles à la prévision
doivent être découvertes dans les états observés, puis nommées, et non stipulées d'avance. Test le moins coûteux :
un alphabet découvert dans les séries elles-mêmes, par une méthode publiée, avec ses réglages usuels. Commité AVANT
tout calcul ; la date du commit fait foi.

## Méthode et origine de chaque réglage (`banc_o.py`)
| Élément | Valeur | Origine |
|---|---|---|
| Symboles | motifs ordinaux (ordre des valeurs) | Bandt et Pompe, *Phys. Rev. Lett.* 88, 174102 (2002) |
| Ordre d | 3 (6 motifs) | plus petit ordre usuel ; la littérature recommande 3 à 7 avec assez de points par motif |
| Délai | 1 (observations natives) | réglage par défaut de la méthode |
| Fenêtre | 5 ans avant la date d'information D | celle de B (aucun réglage nouveau) |
| Probabilité | (hausses + ½)/(occurrences + 1), au moins 5 occurrences | estimateur de Jeffreys, déjà celui de B |
| Prévisibilité | entropie de permutation normalisée | Bandt et Pompe (2002) ; Garland, James et Bradley, *Phys. Rev. E* 90, 052910 (2014) |
| Score | perte logarithmique | règle propre (Gneiting et Raftery, *JASA* 102, 2007) |
| Test apparié | intervalle bootstrap par blocs « jeu × source » ; Diebold et Mariano (*JBES* 13, 1995), erreur type robuste par blocs | règle d'adoption commune ; test standard de comparaison de prévisions |

Deux versions : **O_local** (les occurrences du motif dans la même série) et **O_transversal** (dans toutes les AUTRES
séries du même jeu, même date D, donc sans donnée postérieure). O_transversal teste l'idée de structures transversales
prise par le bas ; O_local est rapporté sans verdict.

## Questions
Séries FRED et DBnomics résolues des jeux postérieurs au 2026-07-01, hors jeux vus par le banc de l'alphabet (2026-09-27,
10-11, 10-25), avec un B calculé par le code. Ordre pour le critère : entrelacé entre les jeux (rang de la question dans
son jeu selon l'empreinte SHA-1 de son identifiant, puis jeu), pour que les 100 premières couvrent des blocs variés.

## Critères (`score_registre.critere_ombre_b`, règle d'adoption commune)
1. **Essai `motifs_ordinaux`** : sur les 100 premières questions où O_transversal existe, perte log de O_transversal
   inférieure à celle de B, intervalle de l'écart entièrement sous 0 au niveau corrigé. Second regard à 200.
2. **Essai `combo_abo`** : sur les questions où le bras A existe aussi (même série gpt-5-mini, `registre/banc-a.jsonl`),
   dans l'ordre du banc du bras A : la combinaison ⅓A + ⅓B + ⅓O_transversal (moyenne des logits, poids fixés ici) bat
   ½A + ½B, aux mêmes conditions. Mesure directe de « l'information supplémentaire » apportée par les motifs à A.

## Ce qui n'est pas fait dans ce passage
La variante SAX (Lin, Keogh et al., *Data Min. Knowl. Discov.* 15, 2007) est déclarée mais non calculée ; elle ne
pourrait l'être qu'en ombre descriptive, sans critère, ou comme un nouvel essai pré-enregistré.

## Attente déclarée avant calcul
Faible sur ces séries : le B autorégressif vient d'échouer sur les mêmes données, signe de peu de mémoire à court
horizon. Un résultat nul ne réfute pas l'hypothèse « l'état précède l'essence » ; il dit que ces séries-là sont proches
du hasard à cet horizon.

## Clôture de l'essai `motifs_ordinaux` (2026-11-15, exécution 43658780674)
585 questions de séries (12 blocs « jeu × source »). Perte log : O_transversal 0,702, O_local 0,699, B 0,686.
Second regard (200 premières, ordre entrelacé) : écart O_transversal − B = +0,020, intervalle corrigé (98,75 %)
[−0,016 ; +0,064]. **Critère non atteint : non adopté.** Diebold-Mariano sur tout l'échantillon : z = 1,10 (p = 0,27) ;
sur FRED, O_transversal est significativement moins bon que B (z = 2,35, p = 0,019) ; sur DBnomics, écart −0,007 non
significatif. Entropie de permutation moyenne 0,912 (1 = hasard complet) : à l'ordre 3, ces séries sont presque sans
structure ordinale exploitable à court horizon. L'essai `combo_abo` reste ouvert (75 questions communes avec A au
premier passage, sous le premier regard ; écart provisoire ABO − AB = +0,015).

## Clôture de l'essai `combo_abo` (2026-11-15, décision d'auteur)
Clos avant son premier regard, sans adoption : les motifs ont échoué seuls, et l'écart provisoire allait contre eux.
Une clôture sans adoption ne peut produire aucun faux positif ; elle relâche la correction pour les essais restants.
