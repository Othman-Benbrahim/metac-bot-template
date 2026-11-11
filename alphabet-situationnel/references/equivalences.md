# Alphabet situationnel — Équivalents par strate (index, couche 1)

> Version : 0.7.67

> Les équivalents locaux des 16 cartes sont rangés **par strate**, un fichier par strate :
> `equivalences/strate-01.md` à `equivalences/strate-13.md`. Raison : la procédure va des faits vers les
> strates, puis vers les cartes candidates de chaque strate ; on ne charge donc que les strates où se
> trouvent des faits (O1). Vue par carte, pour l'audit :
> `python3 scripts/moteur.py equivalences --carte SEUIL`.

---

## 1. Contenu d'une case

| Colonne | Contenu |
|---|---|
| Équivalent | la traduction locale de la carte |
| Marqueur local | ce qui ancre la carte dans cette strate (A1) ; il précise le marqueur abstrait du noyau (`cartes.md`), il ne le remplace pas |
| Statut | Attesté, Documenté, Proposé ou Vide (§2) |
| Référence | la référence bibliographique qui fonde un statut Documenté, ou les identifiants (deux au moins, d'événements distincts) des cas qui fondent un statut Attesté |

---

## 2. Statuts (règle A3)

**Le problème que le statut Proposé nomme (0.7.17).** Une carte est décrite à partir de corpus situés ; dans
une strate dont l'organisation n'est pas celle de ces corpus, on ne sait pas quels traits du marqueur sont
critériels et lesquels sont contingents. C'est le **problème de spécificité** (Shevlin 2021, « Non-human
consciousness and the specificity problem », *Mind & Language*), repris pour les systèmes d'IA par
Chandaria et al. (2026). Le statut Proposé et le plafond de force qui l'accompagne y répondent : la
correspondance est tenue pour candidate tant qu'un texte de la strate ne dit pas ce qui y est critériel.

**Un équivalent est un objet-frontière, pas une traduction (0.6.0).** Il doit être reconnaissable par
un praticien de la strate qui ne connaît pas la carte. Une référence de théorie générale qui *parle
de* la carte ne suffit pas à Documenté : il faut un texte de la discipline qui nomme le phénomène dans
son vocabulaire. `audit` refuse un équivalent Documenté ou Attesté dont la colonne Référence ne porte
pas ce nom local entre guillemets « … ».

| Statut | Définition | Ce que le statut permet (A3) |
|---|---|---|
| **Attesté** | deux cas réels au moins de la base, d'**événements distincts**, l'ancrent avec la force F sur des faits corroborés par des sources indépendantes (0.7.46, `protocole.md` A3) ; colonne Référence = identifiants des cas | ancrage F ou f ; emprunt T4 |
| **Documenté** | connu de la littérature **de la discipline** ; colonne Référence = référence vérifiable d'un texte du champ (manuel, revue), suivie du **nom local** entre guillemets : la phrase par laquelle le champ nomme le phénomène dans son propre vocabulaire, sans le mot de la carte | ancrage F ou f ; emprunt T4 |
| **Proposé** | plausible, non vérifié | ancrage F ou f, signalé ; aucun emprunt |
| **Vide** | rien de convaincant trouvé ; l'ancrage passe par le noyau seul | ancrage f ; aucun emprunt |
| **Hors domaine** | la carte ne s'applique pas aux objets de la strate ; décision d'auteur, motif en colonne Référence | aucun ancrage ; aucun emprunt |

**État courant** (recalculé par `audit`) : 0 Attesté, 13 Documenté, 181 Proposé, 14 Vide, 0 Hors domaine. Les 117
anciennes cases Documentées sans référence vérifiée ont été rétrogradées en 0.4.0. Leurs références manquantes sont
conservées comme dette documentaire, jamais comme preuve. Une promotion demande de lire une source
qui soutient la traduction exacte et ses marqueurs. Prioriser quelques événements dans une strate ;
un concept mentionné dans une bibliographie générale ne justifie pas toutes ses transpositions.

---

## 3. Bilan par strate

| Strate | Documenté | Proposé | Vide | Hors domaine |
|---|---|---|---|---|
| 1 Matière | 0 | 13 | 3 | 0 |
| 2 Vivant | 0 | 15 | 1 | 0 |
| 3 Psyché | 0 | 13 | 3 | 0 |
| 4 Relations | 0 | 16 | 0 | 0 |
| 5 Organisations | 0 | 16 | 0 | 0 |
| 6 Économie | 0 | 16 | 0 | 0 |
| 7 Géopolitique | 13 | 1 | 2 | 0 |
| 8 Droit | 0 | 15 | 1 | 0 |
| 9 Culture | 0 | 16 | 0 | 0 |
| 10 Technique | 0 | 16 | 0 | 0 |
| 11 Climat | 0 | 13 | 3 | 0 |
| 12 Histoire longue | 0 | 15 | 1 | 0 |
| 13 Politique intérieure | 0 | 16 | 0 | 0 |

Les 14 cases Vides (carte : strates) : RÉCIPROCITÉ (1, 3, 11) ; RÉCURSIVITÉ (1, 2, 11) ; COMMUNAUTÉ (1, 3) ; ÉMERGENCE (3) ; RÉSONANCE (7, 8, 12) ; HIÉRARCHIE (11) ; CROISSANCE (7). CROISSANCE@7 a été rétrogradée en 0.7.7 : les textes lus ne soutiennent pas la carte. Huit sur quatorze portent sur
RÉCIPROCITÉ, RÉCURSIVITÉ et COMMUNAUTÉ, cartes qui supposent des agents, et sept sur quatorze sont dans les
strates sans agents (1, 2, 11). RÉSONANCE est Vide dans trois strates sociales (7, 8, 12) : la
synchronisation par couplage est peut-être rare hors du vivant, de la psyché et de l'économie. Question posée (`CHANGELOG.md`) : ces cartes sont-elles universelles,
ou universelles aux seuls systèmes à agents ?

**Clôture d'une case Vide (0.6.5).** Une case Vide déclare ses recherches dans la colonne Référence :
`recherches : N — (1) … ; (2) …`, chacune avec ses sources, sa date et le marqueur testé. À trois
recherches indépendantes sans équivalent (`vide_recherches_cloture`, §H), la case est **close, non
concluant** : elle reste Vide, compte comme traitée pour la complétude d'une strate (`bilan`), et ne se
rouvre que sur une source nouvelle. Ce critère est symétrique d'A2 (trois occurrences pour ajouter une
carte) : on ne déclare pas l'échec d'une carte sur moins de preuves qu'il n'en faut pour en ajouter une.
Il ne conduit pas à Hors domaine pour les cartes à agents (décision 1b) ; pour les autres, Hors domaine
reste une décision d'auteur motivée. Une case Vide sans mention a zéro recherche documentée.

**Une case Proposé ne se « clôt » pas (0.7.6).** Il n'y a pas d'état « Proposé clos » : il compterait comme
traitée une correspondance qu'aucun texte lu ne soutient. Deux situations, deux suites. Un candidat existe
mais n'est pas lu (texte fermé) : la case reste Proposé, non traitée, jusqu'à lecture. Les textes lus ne
soutiennent pas la carte : la case **devient Vide**, ses lectures comptées comme recherches
(`recherches : N — …`), puis close à trois. CROISSANCE@7 est dans ce second cas (Choucri 2017 et Altman
2017 lus, carte non soutenue) : rétrogradation à faire par l'auteur, avec la troisième recherche.

**Décision 1b (27 octobre 2026) : les cartes à agents sont universelles.** La question ouverte ci-dessus
est tranchée : leurs cases Vides sont des lacunes de recherche, à combler. *Lecture précisée en 0.7.13 :*
la décision vaut **politique de recherche** — les cases Vides sont des lacunes à combler, pas des
absences établies. *Précisé en 0.7.13* (audit comparatif) : c'est une hypothèse de
travail sous P1, pas un résultat. Une définition qui exige un contre-transfert **obligé** (RÉCIPROCITÉ)
ne se transpose pas d'elle-même à une interaction physique ; pour qu'une case Vide d'une strate sans
agents passe Documenté, il faudra soit une définition abstraite commune à toutes les strates et, pour
chaque traduction locale, ce qu'elle en **conserve** (`apports-theoriques.md` §17), soit accepter un
domaine d'application limité. La décision ne dispense d'aucune des deux voies. Le tableau suivant
(rapport « Intuition Machine », annexe A) est conservé pour mémoire : ses propositions « Hors domaine »
pour les cartes à agents sont écartées par cette décision ; les anomalies de définition (ÉMERGENCE@3,
RÉSONANCE@8 et @12, HIÉRARCHIE@11) et le cas contesté (RÉCURSIVITÉ@2) restent à instruire.

| Case | Cause proposée | Traitement proposé |
|---|---|---|
| RÉCIPROCITÉ@1, @11 | pas de boucle normative dans la matière ni le climat | Hors domaine |
| RÉCURSIVITÉ@1, @11 | pas de représentation de soi | Hors domaine |
| COMMUNAUTÉ@1 | pas de collectif intentionnel | Hors domaine |
| RÉCIPROCITÉ@3, COMMUNAUTÉ@3 | la carte exige au moins deux (ou plus de deux) parties ; un individu n'en est qu'une | Hors domaine, motif d'échelle |
| ÉMERGENCE@3 | statut de la conscience comme émergence non tranché | anomalie à instruire |
| RÉSONANCE@8, @12 | indécision de définition | anomalie à instruire |
| RÉSONANCE@7 (0.6.4) | sources lues : la vague révolutionnaire est une diffusion par émulation, pas une synchronisation | lacune de recherche (décision 1b) |
| HIÉRARCHIE@11 | le climat a des ordres imbriqués ; la définition sociale de la carte (autorité, préséance) contredit sa structure mathématique (ordre partiel) | anomalie de **définition** : Hors domaine détruirait l'information |
| RÉCURSIVITÉ@2 | le vivant se représente-t-il son fonctionnement ? | cas contesté |

## 4. Érosion des marqueurs — épreuve de P1 (0.7.12)

P1 tient les cartes pour des structures transversales **candidates** ; le tableau des équivalents est
l'endroit où l'hypothèse se teste. Il peut aussi s'y **ajuster** : quand une source ne soutient qu'une
partie du marqueur, on retire le reste et la case passe Documenté. Chaque retrait est consigné
(`feuille-de-route.md` §5.1, colonne « Écart à trancher ») ; jusqu'en 0.7.11, ils n'étaient pas comptés
(audit V34, D3).

**Compte, strate 7** (seule strate documentée) : 6 cartes Documentées sur 13 l'ont été après
modification de l'équivalent ; 3 ont perdu au moins deux éléments nommés du marqueur.

| Carte | Éléments retirés | Nombre |
|---|---|---|
| SEUIL | « rupture diplomatique », « annexion déclarée » | 2 |
| ÉMERGENCE | « sans puissance dominante », « sans traité » | 2 |
| HIÉRARCHIE | veto, préséance | 2 |
| RÉCURSIVITÉ | sécuritisation (intitulé changé) | 1 |
| TRANSFORMATION | transition de régime pactée (renvoyée en strate 13) | 1 |
| TRACE·MÉMOIRE | griefs (intitulé réduit aux frontières héritées) | 1 |

Un changement d'intitulé sans retrait (RÉSEAU) et un complément (CONTRAINTE) ne comptent pas.

**Règle proposée, non appliquée** (décision d'auteur) : une carte qui perd au moins deux éléments nommés
de son marqueur dans au moins deux strates n'est pas transversale au sens de P1, mais une famille
d'homonymes à scinder ou à redéfinir. Avec une seule strate documentée, la règle ne peut pas encore
mordre : elle se tient dès la deuxième strate sourcée, et le compte se publie à chaque promotion.
Un retrait n'est pas toujours une érosion — une source peut préciser un marqueur trop large — ; c'est
pourquoi la règle porte sur la répétition à travers les strates, non sur un retrait isolé.
