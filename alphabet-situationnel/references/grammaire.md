# Alphabet situationnel — Grammaire (couche 2)

> Version : 0.7.53

> Notation, syntaxe formelle, critères des liaisons et liste de contrôle. Les règles sont G1–G6
> (`protocole.md`) ; ce fichier les rend applicables.

---

## 1. Les symboles

| Id | Nom canonique | Glyphe | Abréviation admise en entrée |
|---|---|---|---|
| 01 | SEUIL | ⊥ | SEU |
| 02 | RÉCIPROCITÉ | ⊗ | REC |
| 03 | PÉRIODICITÉ | ↻ | PER |
| 04 | RÉCURSIVITÉ | ↺ | RCS |
| 05 | ÉMERGENCE | ⊙ | EME |
| 06 | HIÉRARCHIE | ✦ | HIE |
| 07 | RÉSEAU | ⊛ | RES |
| 08 | POLARITÉ | ⥀ | POL |
| 09 | INCERTITUDE | Ø | INC |
| 10 | CONTRAINTE | ⊘ | CTR |
| 11 | PROPORTION | ◯ | PRO |
| 12 | TRANSFORMATION | ∿ | TRA |
| 13 | TRACE·MÉMOIRE | ◊ | TRC |
| 14 | CROISSANCE | ▲ | CRO |
| 15 | COMMUNAUTÉ | ⟶ | COM |
| 16 | RÉSONANCE | ✶ | RSN |

**F/f est une confiance de codage, pas une intensité physique.** Une intensification exige une
grandeur mesurée distincte. L’état, ses faits et leurs dates doivent correspondre aux champs JSON.

**Le nom canonique fait foi.** Les glyphes sont des projections d'affichage, dont plusieurs se
confondent à l'écran (`⊘`/`Ø`, `↻`/`↺`, `✦`/`✶`). En sortie, la ligne des noms est obligatoire ; la
ligne glyphique est facultative. Les abréviations ne servent qu'en entrée et dans les fiches JSON.

Strates : entiers 1 à 13 (`strates.md` ; borne lue dans `nombre_strates`, §H) ; équivalents par strate : `equivalences/strate-NN.md`.

---

## 2. Syntaxe formelle

```
état         ::= "[" date " | " fenêtre "]" " " corps
corps        ::= "∅" | mot { " + " mot }
mot          ::= carte "@" strate "[" intensité "]" [ " " qualifs ]
intensité    ::= "F" | "f"
qualifs      ::= "{" qualif "}" [ " {" qualif "}" ]
qualif       ::= "rétroaction amplifiante" | "rétroaction stabilisante"
               | "multi-échelle" | "délai" | "multi-strate"
séquence     ::= état { " ⇒ " état }
liaison      ::= mot-court " —" type "→ " mot-court
mot-court    ::= carte "@" strate
type         ::= "renforcement" | "conflit" | "inclusion" | "appui" | "reproduction"
               | "indépendance" | "tension" | "transfert" | "écho"
positions    ::= "tient: " mot-court " / bouge: " mot-court " / manque: " mot-court
date         ::= AAAA-MM | AAAA-MM-JJ
fenêtre      ::= nombre " " ("jour" | "jours" | "semaine" | "semaines" | "mois" | "an" | "ans")
```

Espaces : une espace de chaque côté de `+`, `⇒`, `/`. Le séparateur `+` n'ordonne rien. Les dates
sont validées par le calendrier civil et l’écart entre états doit être celui de leur fenêtre. Elles sont lues au jour près ; `7 jours` et `1 semaine` désignent la même fenêtre.

---

## 3. Exemples

Mot : `SEUIL@7[F]` — un point de non-retour géopolitique, ancré avec la force F (Fort).

Mot qualifié : `CROISSANCE@6[F] {rétroaction amplifiante}`

Les cinq qualificatifs, chacun avec sa ligne Q (G1) :

```
Q · CROISSANCE@6 {rétroaction amplifiante} : hausse des prix de mars → hausse des achats spéculatifs d'avril → hausse des prix de mai (deux tours datés) ; contre-observation : volumes physiques stables (marginale)
Q · CONTRAINTE@6 {rétroaction stabilisante} : chaque dépassement du plafond est suivi d'une correction de la banque centrale dans le mois, deux fois en 2026 ; contre-observation : aucune trouvée (cherchée dans les communiqués)
Q · HIÉRARCHIE@5 {multi-échelle} : même rapport d'autorité au niveau de l'équipe, du service et de la direction (trois organigrammes datés) ; contre-observation : un service en gestion collégiale (marginale)
Q · SEUIL@7 {délai} : sanction adoptée le 2026-03-02, rupture diplomatique le 2026-05-18 (77 jours) ; contre-observation : rupture annoncée comme liée à un autre incident (substantielle)
Q · SEUIL@7 {multi-strate} : SEUIL@6 ancré par le défaut du 2026-04-10, SEUIL@7 par la rupture du 2026-05-18 ; contre-observation : aucune trouvée
```

Dans la quatrième ligne, la contre-observation substantielle **retire** le qualificatif (un
qualificatif n'a pas de force Faible) : le mot s'écrit alors `SEUIL@7[F]` sans `{délai}`.

État : `[2026-09 | 3 mois] CONTRAINTE@6[F] + POLARITÉ@7[f] + RÉSEAU@10[F]`

Liaisons de cet état :
```
CONTRAINTE@6 —transfert→ POLARITÉ@7   (faits : plafond de prix adopté le 2026-07-02 ; rétorsion annoncée le 2026-07-20 ; mécanisme : perte de recettes)
RÉSEAU@10 —écho→ CONTRAINTE@6
```

Positions : `tient: RÉSEAU@10 / bouge: POLARITÉ@7 / manque: RÉCIPROCITÉ@7`

Séquence : `[2026-03 | 3 mois] CONTRAINTE@6[F] ⇒ [2026-06 | 3 mois] CONTRAINTE@6[F] + POLARITÉ@7[f]`

État nul : `[2026-09 | 1 mois] ∅`

---

## 4. Critères des liaisons (G3)

**Dans une même strate** (relations reprises de NEXUS-ARCHÊ) :

| Relation | Critère observable |
|---|---|
| renforcement | chaque structure produit des faits qui ancrent l'autre |
| conflit | les faits de l'une entravent ceux de l'autre sur le même objet |
| inclusion | l'une est un cas ou une partie de l'autre (`antagonismes.md` §4bis) |
| appui | les faits de l'une fournissent un élément constitutif de l'autre, sans réciprocité |
| reproduction | (a) chaque fait d'ancrage de B est déclenché par une occurrence de A, datée ; (b) après ce fait, l'effet décrit dans l'ancrage de A est de nouveau observé |
| indépendance | les deux structures portent sur des objets distincts, nommés |
| tension | la paire figure dans `antagonismes.md` §4 |

**Entre strates** (enchevêtrement) :

| Type | Critère observable | Défaut |
|---|---|---|
| transfert | un fait daté dans la strate source, puis un fait daté dans la strate cible, et un mécanisme nommé qui relie l'un à l'autre | — |
| écho | même carte ou cartes liées dans les deux strates, sans lien causal démontré | **verdict par défaut** quand le transfert n'est pas établi |
| conflit | l'ancrage dans une strate entrave l'équivalent dans l'autre, fait à l'appui | — |

Pourquoi l'écho est le défaut : le transfert est l'affirmation la plus forte, et la plus tentante.
Deux structures simultanées dans deux strates ne prouvent pas que l'une cause l'autre.

Une paire incompatible (`antagonismes.md` §3) sur le même objet exige de rejeter un des ancrages.
« indépendance » ne devient recevable que pour deux objets distincts nommés.

---

## 5. Positions et configurations (G4)

Les positions demandent au moins trois mots ancrés. *tient* exige F ; *manque* s'ancre par un **effet**
de l'absence (« aucun pont entre les deux groupes : les décisions de l'un sont apprises par l'autre en
assemblée »), jamais par le seul constat de l'absence.

| Configuration | Condition | Ce qu'elle signale | Question à l'utilisateur |
|---|---|---|---|
| Scission | même carte en *tient* et *manque*, sur deux objets nommés | la structure existe mais n'atteint pas l'objet où elle manque | qu'est-ce qui l'empêche de passer d'un objet à l'autre ? |
| Reproduction | *tient* et *bouge* liés par reproduction (§4) | le mouvement reconduit la structure stable | ce changement s'est-il déjà produit ainsi lors d'un cycle précédent ? |
| Lacune contradictoire | *tient* et *manque* incompatibles, même objet | ce qui manque ne peut apparaître sans déplacer ce qui tient | êtes-vous prêt à perdre ce qui tient pour obtenir ce qui manque ? |

Une configuration est une hypothèse signalée, jamais un verdict. Dans la version courante, elle ne
modifie pas le calcul des probabilités (`graphe.md` §2.1).

---

## 6. Signature (bloc symbolique)

La signature est la projection compacte d'un état pour le bloc symbolique. Elle **ne porte ni strate
ni intensité ni chiffre** (P9) :

```
Signature : CONTRAINTE + POLARITÉ + RÉSEAU {multi-strate}
            ⊘ + ⥀ + ⊛
```

Avec positions : `RÉSEAU / POLARITÉ / RÉCIPROCITÉ` (tient / bouge / manque). Une carte ancrée dans
plusieurs strates n'apparaît qu'une fois, avec `{multi-strate}` si le qualificatif est ancré.

La signature n'est pas une phrase STÈLE ; pour en obtenir une, la confier au skill `stele`.

---

## 7. Liste de contrôle de bonne formation (G6)

Une phrase entre dans la base ou dans un calcul seulement si toutes les cases sont cochées.

- [ ] Date et fenêtre présentes ; fenêtre identique pour tous les états d'une séquence.
- [ ] Chaque mot a un fait d'ancrage cité, avec sa source (A5, B1).
- [ ] Chaque mot F a sa ligne A6 complète (toutes les voisines de `cartes.md`).
- [ ] Chaque mot F repose sur un fait suffisant (`test` : pistolet ou double) ; un fait qui remplit
      seulement le marqueur est un cerceau, il donne f.
- [ ] Chaque mot F a sa garantie (mécanisme, attendu, contredirait), et rien de ce qui la contredirait
      ne figure dans les faits cités.
- [ ] Chaque mot F nomme un acteur et l'option ouverte ou fermée (pertinence, O1).
- [ ] Chaque mot a sa contre-observation classée (A7).
- [ ] Chaque mot F de cas actif cite le passage qui le soutient (`passage` : localisation, relation
      `soutient`) ; un soutien partiel donne f ; une pièce qui contredit va en A7 (`protocole.md` A6).
- [ ] Premier état d'un cas réel : au moins une question qui départage deux cartes, ou une carte et
      l'indétermination (`questions` : `{question, si_oui, si_non}`, l'une au moins dans l'état). Une bonne
      lecture rend évidente la question qui la mettrait en défaut ; une question dont la réponse est
      déjà dans les faits cités ne départage rien.
- [ ] Chaque question dit ce qui y répondrait (`resolution` : observation et source) et, pour chaque
      branche qui mène à une carte, pourquoi cette réponse l'établit (`justification`). **« Non A » ne
      vaut pas « B »** : l'absence d'un troisième groupe n'établit pas la polarité (fragmentation et
      alliances changeantes restent possibles) ; si la réponse ne tranche pas, la branche mène à
      `indetermine`, qui décrit l'état de l'information, pas une issue du monde à laquelle donner une
      probabilité. Une question qui cherche la preuve manquante d'un ancrage est de `type`
      `documentation` : elle s'ajoute à la question qui départage, ne la remplace pas.
- [ ] Une carte apparaît au plus une fois par strate.
- [ ] Un même fait n'ancre qu'un mot par strate (`strates.md` §4).
- [ ] Chaque qualificatif a sa ligne Q ; au plus deux par mot.
- [ ] Chaque liaison est d'un type du §4, avec ses faits ; aucune liaison devinée.
- [ ] Aucune paire incompatible sur le même objet ; indépendance seulement pour des objets distincts.
- [ ] Positions : seulement avec ≥ 3 mots ; *tient* en F ; *manque* ancré par un effet.
