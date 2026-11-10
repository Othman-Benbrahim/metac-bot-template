# Alphabet situationnel — Exemples

> Version : 0.7.59

> Exemples 1–6 : démonstrations entièrement fictives du contrat courant. Exemples 7–10 : archives
> critiques de versions antérieures, non revérifiées et exclues des calculs actuels. Ne jamais
> mélanger ces deux catégories. Les valeurs **et le format de sortie** des exemples 1 et 3 ont été
> régénérés avec le moteur 0.6.5 : c'est le format qui sert de contrat.

| # | Mode | Objet |
|---|---|---|
| 1 | PRÉVOIR | base fictive, résultats courants et horizon |
| 2 | LIRE | résultat nul |
| 3 | PRÉVOIR | référence conditionnelle et partition |
| 4 | LIRE | confiance distincte de l'intensité |
| 5 | CODER | schéma actif et archives |
| 6 | SCORER | simulation exclue de V4 |
| 7–10 | Archives | France, Ukraine, Yémen, Alberta ; anciens rejouements |

---

## Exemple 1 — PRÉVOIR, deux strates, base fournie (ρ1)

```bash
python3 scripts/moteur.py calculer --demo --base assets/base-de-cas.exemple.jsonl \
 --etat "[2026-09 | 3 mois] POLARITÉ@7[F] + CONTRAINTE@6[F]" \
 --liaison "CONTRAINTE@6 echo POLARITÉ@7" --evenement "SEUIL@7 apparait" \
 --temporalite generique --json
```

Les forces F sont **stipulées dans un univers fictif** pour tester le calcul ; elles ne promeuvent
aucun équivalent réel. Date d'information 2026-09-01 ; échéance à un pas 2026-12-01.

Sortie humaine complète pour SEUIL@7 (sans `--json`) :

```
⚠ Prévision · cet outil prend un risque déclaré.
⚠ ρ1 · association · 10 cas distincts (H1) · p₀ 23 % · p ~22 % (large : 5–43) · échéance 2026-12-01 · journal [à attribuer]
Événement : SEUIL@7 apparait · ρ = provenance du chiffre, pas sa fiabilité
Lecture : association — si le motif observé dans les cas et les inerties se répète, alors cette fréquence ; aucun modèle causal, donc ni effet d'une intervention ni « ce qui se serait passé »
Comparateur au même horizon : 12 %
Sans cartes (inertie et fréquences seules) : 12 % — les cartes déplacent la probabilité de +10,0 points
Sensibilité du modèle : 19–28 % sur 6 variantes (multiplicateurs d'un cran, inerties ± 0,05, fréquence par défaut × ½ et × 2)
Trace : multiplicateur 2.16 · homologie H1 · c_A 10 · n_A 4.8 · n_E 1.0
Résolution (S1) : la source doit mesurer le marqueur local « franchissement d'un seuil reconnu par les parties (…) » (Franchissement d'un seuil d'escalade, Documenté) ; sinon reformuler l'événement
! DÉMONSTRATION FICTIVE — ne constitue ni une prévision réelle ni une preuve de calibration.
! Modèle expérimental : multiplicateurs hypothétiques, performance prospective non établie.
! Ancrage F sur équivalent non vérifié (Proposé) : CTR@6 — la lecture est tranchée, la correspondance reste à documenter (A3).
```

Quatre lignes portent les contrôles de 0.6 : le **barreau** (« association ») dans la ligne S5 et la
**lecture** qui en découle ; la **sensibilité** (19–28 %), plus étroite ici que l'intervalle bêta
(5–43 %) : sur ce calcul, le petit nombre de cas pèse plus que les hypothèses ; la **résolution**, qui
renvoie au marqueur local de la strate 7, Documenté depuis 0.6.4. La ligne S5 est recopiée telle
quelle (S5) ; le reste va dans le bloc analytique.

| Événement | p non arrondi | Intervalle | ρ | Barreau | Comparateur à un pas | Sensibilité |
|---|---|---|---|---|---|---|
| POL@7 persiste | 0.829776 | [0.6382104700744335, 0.972781425124053] | ρ1 | A | 0.8372000588523011 | 82,0–83,9 % |
| RES@6 apparait | 0.385858 | [0.16347417934298547, 0.6256057385536229] | ρ1 | A | 0.1468811573436136 | 36,7–41,6 % |
| SEU@7 apparait | 0.220379 | [0.051526739939626254, 0.43107479601396903] | ρ1 | A | 0.1208719900885371 | 19,5–27,8 % |
| HIE@7 apparait | 0.017164 | [2.898097861961586e-10, 0.05118650363637235] | ρ1 | A | 0.03343994985499495 | 1,0–3,0 % |

Aucune bande ne traverse 50 % ni ne dépasse 30 points : les quatre résultats sont « identifiés »
au sens du moteur, ce qui ne dit rien de la justesse de la matrice (`graphe.md` §2.3 : la
sensibilité est paramétrique et globale, pas structurelle).

Les quatre calculs retiennent H1 (10 cas distincts) : depuis 0.4.1, le niveau le plus strict qui
atteint 3 cas. En 0.4.0, le moteur prenait le niveau le plus peuplé (H1.5 ou H2, 12 à 18 cas) ; les
intervalles sont maintenant plus larges, c'est le prix d'une comparaison plus étroite.

**Résultat non identifié.** Le même SEUIL@7, au moins une fois en trois pas (`--pas 3 --semantique
au-moins-une-fois`, échéance 2027-06-01) :

```
⚠ ρ1 · association · 10 cas distincts (H1) · p₀ 23 % · p 53 % non identifié (variantes 48–62 % de part et d'autre de 50 %) · échéance 2027-06-01 · journal [à attribuer]
Comparateur au même horizon : 32 %
Sans cartes (inertie et fréquences seules) : 32 % — les cartes déplacent la probabilité de +20,6 points
Sensibilité du modèle : 48–62 % sur 6 variantes (…) — non identifié : la bande traverse 50 %
```

La ligne S5 ne dit pas « 53 % » : selon les hypothèses non calibrées, la réponse penche d'un côté ou
de l'autre. Le chiffre se journalise (non arrondi, avec `bande_sensibilite`), mais la restitution dit
que le sens de la réponse n'est pas identifié. Une bande qui ne traverse pas 50 % mais dépasse 30
points serait signalée « bande large » sur la ligne de sensibilité.

À quatre pas, présence finale de SEUIL : p=0.61208500, comparateur=None,
intervalle non estimé. Le comparateur est propagé au même horizon (2027-09-01).
Les trajectoires sont exécutables avec la même base et `--demo --pas 2` ; ne pas substituer leur
probabilité d'un état à celle d'un événement isolé.

---

## Exemple 2 — LIRE, résultat nul (A8)

« Toute l'équipe est démotivée » sans date, comportement ou mesure ne suffit pas à ancrer une carte.
Demander deux ou trois observations précises ; si elles manquent : état nul, aucune prévision.
Une demande de preuves n'autorise pas à fabriquer des départs, absences ou conflits.

---

## Exemple 3 — PRÉVOIR sans base, partition (ρ3 et ρ4)

Hypothèses **fictives** : persistance de POLARITÉ = 0,85 ; hausse de la grandeur parmi les épisodes
où elle persiste = 0,20. Intensification = 0,85 × 0,20 = 0,17. Les fréquences sont fournies sous les
clés distinctes `POL@7 persiste` et `POL@7 hausse|persiste`, avec sources explicitement fictives,
fenêtre et dates dans un fichier passé à `--references`. Fournir aussi la résolution chiffrée.
Sans référence conditionnelle, la sortie est non estimée. `--fref 0.2` ne sert pas aux deux composantes.

Pour une question binaire exhaustive « intensification / pas d'intensification », les probabilités
sont 0,17 et 0,83 ; il s'agit d'une partition de l'événement et de son complément. Pour deux événements
différents, ne pas fabriquer les quatre issues par indépendance sans justification jointe.
Le scoreur regroupe toute partition et exige une seule issue réalisée. Les hypothèses fictives restent
hors V4, même si les opérations arithmétiques sont exactes.

Sortie du moteur (fichier de références fictif au format de `graphe.md` §2.2, disponible le
2026-08-01 ; résolution chiffrée dans un fichier : grandeur, unité, comparaison, deux observations) :

```bash
python3 scripts/moteur.py calculer --etat "[2026-09 | 3 mois] POLARITÉ@7[F]" \
 --evenement "POLARITÉ@7 s'intensifie" --references R.json --resolution resolution.json \
 --temporalite generique
```

```
⚠ Prévision · cet outil prend un risque déclaré.
⚠ ρ3 · association · composé : persistance × référence conditionnelle · p 17 % [intervalle non estimé] · échéance 2026-12-01 · journal [à attribuer]
Événement : POLARITÉ@7 intensifie · ρ = provenance du chiffre, pas sa fiabilité
Lecture : association — si le motif observé dans les cas et les inerties se répète, alors cette fréquence ; aucun modèle causal, donc ni effet d'une intervention ni « ce qui se serait passé »
Comparateur au même horizon : 17 %
Résolution (S1) : la source doit mesurer le marqueur local « deux blocs, alignements exclusifs » (Système bipolaire, Documenté) ; sinon reformuler l'événement
! P(composé)=P(persiste) × P(changement | persiste). Intervalle conjoint non estimé.
```

Un composé fondé sur deux références externes n'a **pas de ligne de sensibilité** : il ne dépend
d'aucun multiplicateur ni d'aucune inertie du modèle, seulement des deux fréquences fournies. Son
incertitude est celle des références ; l'intervalle conjoint n'est pas estimé. La persistance seule
(`POLARITÉ@7 persiste`, même fichier) donne ρ3, p 85 %, bande 85–85 % : sans cas, les variantes du
modèle n'ont rien à déplacer.

---

## Exemple 4 — LIRE, lecture positive (statut Descriptif)

Une bibliothèque logicielle possède un graphe de dépendances documenté : RÉSEAU est une candidate.
L'équivalent local livré est Proposé : un ancrage F reste possible si A6 et A7 sont satisfaits (et,
pour un cas réel, garantie et option), signalé « équivalent non vérifié » (A3, depuis 0.4.1). Le
statut de l'équivalent dit si la traduction est sourcée, pas si la lecture est sûre.
Un nouveau document peut faire passer f à F **sans nouveau lien dans le graphe**. Pour prévoir une
intensification, définir une grandeur, par exemple le nombre de dépendances actives, avec ses limites.
Le statut Descriptif demande les preuves prévues par A6/A7 ; il ne peut pas être obtenu par simple
renommage d'une case Proposé. La signature résume les faits sans les transformer en probabilités.

---

## Exemple 5 — CODER, une fiche de cas

Le schéma complet courant est dans `base-de-cas.md` §2 ; il est construit à partir d'une fiche fictive
validée, et `audit` vérifie à chaque exécution qu'il passe `valider` (depuis 0.4.3). `valider assets/base-de-cas.exemple.jsonl` : 40 actifs fictifs recevables.
`valider assets/cas-reels.jsonl` : 4 archives (0.6.8), lisibles, exclues de tout calcul ;
le témoignage original est conservé, non réécrit, dans `assets/cas-reels-originaux.jsonl`. Un cas réel ne devient actif qu'après vérification des sources, fenêtres, objets et codage.

---

## Exemple 6 — SCORER, prévision manquée et non résolue

```bash
python3 scripts/moteur.py scorer assets/journal.exemple.jsonl
```

Sortie courante : 3 questions résolues fictivement,
1 non résolue, 0 éligible à V4,
0 épisode comparable. Statut : `non encore évalué`.
Les scores détaillés servent à tester l'arithmétique ; ils ne mesurent pas une calibration réelle.
Le journal est généré avec les probabilités non arrondies du moteur 0.4.0. Les empreintes identifient
ses paramètres, sa base et son code ; aucune preuve de prépublication n'est inventée.

---

## Exemple 7 — Cas réel rejoué : France, 19 → 25 octobre 2026

> Archive de versions antérieures : faits non revérifiés, ancien codage et anciens chiffres.
> Non recevable comme prévision 0.4.0 ; conservé pour comprendre les défauts historiques.

**Origine.** Test sur cas réel transmis par l'utilisateur le 2026-10-25 (mouvement « contre la vie
chère », violences du 17 octobre, budget de la Sécurité sociale). Les faits et leurs sources sont ceux
du rapport de test ; ils n'ont pas été revérifiés ici. **L'issue était connue avant le calcul** : ce
rejeu ne mesure pas la calibration de l'outil ; il montre l'effet des corrections sur un cas réel.
Fiche transmise ensuite : `assets/cas-reels.jsonl`, C-0001-S05 (identifiant initial C-0001-FRA). En
v0.3.2, le validateur y a relevé un changement de force non documenté (CONTRAINTE@8 f → F) ; l'entrée
ajoutée reprend les faits de la fiche et reste à confirmer par son codeur.

**État codé par le test.** `[2026-10-19 | 7 jours] COMMUNAUTÉ@5[f] + RÉSEAU@5[F] + INCERTITUDE@5[f] + CONTRAINTE@8[f]`,
liaison `RÉSEAU@5 —appui→ COMMUNAUTÉ@5`. Aucune base, aucune classe de référence : tout est ρ4.

**Ce que le test a révélé en v0.2.1, et la correction.**

| Défaut | v0.2.1 | v0.2.2 |
|---|---|---|
| Dates lues au mois près | la fiche hebdomadaire était refusée, la transition disparaissait sans erreur | dates au jour près ; fiche recevable |
| Inerties « par pas » quelle que soit la durée du pas | INCERTITUDE perdait 60 % de persistance en 7 jours ; statu quo 6,2 % | inerties définies sur 3 mois, ramenées à la fenêtre ; statu quo 80,5 % |
| Une fiche faisait monter f de 0,05 à 0,25 | p₀ de SEUIL@8 : 56 % avec une seule fiche | f lissée vers la référence ; instable sous 10 transitions |
| Un cas suffisait pour ρ1 | ρ1 avec c_A = 1 | ρ1 exige 3 cas distincts |
| `1 semaine` refusé | erreur de syntaxe | accepté ; `7 jours` = `1 semaine` |
| P2 « CONTRAINTE@8 apparaît » alors que le mot est présent | calculé | refusé (T1) : un passage f → F n'est pas un événement |

**Rejeu des prévisions** (`moteur.py calculer`, même état) :

| # | Événement | v0.2.1 | v0.2.2 | Issue | Brier v0.2.2 |
|---|---|---|---|---|---|
| P1 | SEUIL@8 apparaît | 17 % | 1,5 % | 0 | 0,0002 |
| P2 | CONTRAINTE@8 apparaît | 6 % | refusé | — | — |
| P3 | COMMUNAUTÉ@5 persiste | 65 % | 96,8 % | 1 | 0,0011 |
| P4 | INCERTITUDE@5 persiste | 40 % | 93,2 % | 1 | 0,0046 |
| P5 | TRACE·MÉMOIRE@5 apparaît | 5 % | 0,4 % | 1 | 0,9922 |

Brier moyen : 0,2835 en v0.2.1 (5 prévisions), 0,2495 en v0.2.2 (4 prévisions), contre 0,25 pour un
« 50 % » constant.

**Lecture honnête.**
- Les persistances sont désormais bien vues, parce que l'unité de temps est juste : c'est une
  correction d'unité, pas un réglage sur ce cas.
- Le score reste au niveau de la référence paresseuse, et il est dominé par une seule erreur : TRACE@5,
  que l'outil ne pouvait pas proposer (aucune carte présente ne mène à TRACE dans `dynamiques.md`).
- Cette erreur **n'est pas corrigée par un réglage** : ajouter une arête vers TRACE parce qu'un cas l'a
  montré serait ajuster le modèle sur l'issue connue, ce que V3 interdit (une révision se motive par des
  scores accumulés). Elle est consignée comme **première entrée du journal des lacunes**
  (`assets/journal-lacunes.md`) : un épisode borné et réversible qui modifie durablement les conduites
  sans franchir de seuil. Deux autres entrées indépendantes ouvriraient la procédure A2.
- Un vrai test de calibration demande l'inverse de ce rejeu : coder un état aujourd'hui, journaliser les
  prévisions, et ne les scorer qu'à l'échéance.

---

## Exemple 8 — Second cas réel rejoué : Ukraine, 19 → 25 octobre 2026

> Archive de versions antérieures : faits non revérifiés, ancien codage et anciens chiffres.
> Non recevable comme prévision 0.4.0 ; conservé pour comprendre les défauts historiques.

**Origine.** Test régressif transmis par l'utilisateur le 2026-10-25, avec sa fiche
(`assets/cas-reels.jsonl`, C-0002-S07). Faits et sources tels que rapportés ; issue connue avant le
calcul : **rejeu**.

**État.** `[2026-10-19 | 6 jours] POLARITÉ@7[F] + INCERTITUDE@7[F] + RÉSEAU@7[F] + CONTRAINTE@7[f]`,
liaison `RÉSEAU@7 —appui→ INCERTITUDE@7`. Issue : le canal de médiation passe de bilatéral à trilatéral
(annonce du 23 octobre), sans rupture ; TRANSFORMATION@7 apparaît.

**Ce que le test a mesuré en v0.2.2** : persistances à 94–99 % (justes), SEUIL à 2,3 % (juste),
TRANSFORMATION à 0,4 % (manquée). Brier 0,1992, dont 0,9920 pour la seule transformation.

**En v0.3.0** (`moteur.py calculer`, même état) :

| Question | Événement | p | ρ |
|---|---|---|---|
| le canal change-t-il de forme sans disparaître ? | `RÉSEAU@7 se transforme` (nouveau type) | 0,4 % | ρ4 |
| la transformation apparaît-elle ? | `TRANSFORMATION@7 apparaît` | 0,4 % | ρ4 |
| la contrainte suspendue redevient-elle active ? | `CONTRAINTE@7 se renforce` (nouveau type) | 1,5 % (0,3 % en v0.3.0) | ρ4 |
| une rupture survient-elle ? | `SEUIL@7 apparaît` | 2 % | ρ4 |

**Lecture.**
- La question « le canal change-t-il de forme ? » peut maintenant être posée telle quelle : c'était le
  manque d'expression relevé par les deux tests (un passage f → F en France, un changement de forme
  sans disparition en Ukraine).
- **La probabilité, elle, ne bouge pas.** Elle vient de la fréquence par défaut (5 % sur 3 mois, soit
  0,4 % sur 6 jours) multipliée par un rapport de vraisemblance proche de 1. C'est ce que valent toutes
  les apparitions ρ4 : un ordre de grandeur inventé, pas une estimation. Le moteur ne sait pas à quelle
  fréquence les canaux de médiation changent de format, parce que personne ne le lui a dit.
- Ce qui manque n'est donc pas d'abord une carte, ni une « classe de changement » : TRANSFORMATION
  existe, et l'événement est maintenant exprimable. Ce qui manque, c'est **une fréquence de référence
  pour les changements de forme** — une base de cas, ou une classe de référence externe (`--fref`).
  Avec une fréquence externe de 10 % par semaine pour « un format de négociation actif change de
  configuration », le même calcul donnerait 12 % (ρ3), et l'échec coûterait 0,77 au lieu de 0,99.
- Deux réserves sur la conclusion du test. Les deux échecs confiants portent sur des événements
  **choisis après avoir lu l'issue** ; dans un rejeu, ils sont sur-représentés par construction, d'où
  l'exclusion des rejeux de V4 (V1). Et les deux cartes manquées diffèrent (TRACE·MÉMOIRE,
  TRANSFORMATION) : elles forment peut-être une même classe, mais il faut un test à l'aveugle pour le
  montrer (`validation.md` §8).

---

## Exemple 9 — Troisième cas réel rejoué : Yémen, 19 → 25 octobre 2026

> Archive de versions antérieures : faits non revérifiés, ancien codage et anciens chiffres.
> Non recevable comme prévision 0.4.0 ; conservé pour comprendre les défauts historiques.

**Origine.** Test régressif transmis par l'utilisateur le 2026-10-25, avec sa fiche
(`assets/cas-reels.jsonl`, C-0003-S07). Faits et sources tels que rapportés ; **rejeu**.

**État.** `[2026-10-19 | 6 jours] POLARITÉ@7[F] + CONTRAINTE@7[F] + RÉSEAU@7[f] + CROISSANCE@7[f]`,
liaison `POLARITÉ@7 —renforcement→ CONTRAINTE@7`. Issue rapportée : frappes continues et plus
meurtrières, accord britanno-omanais sur Ormuz, aucune rupture.

**Ce que le test a trouvé en v0.3.0.** `se renforce` renvoyait 0,3 % pour toute carte et tout état : la
fréquence d'**apparition** par défaut, réutilisée pour une autre grandeur. Brier 0,3975, dont 1,99 sur
les deux renforcements.

**En v0.3.1** (même état) :

| # | Événement | v0.3.0 | v0.3.1 | Marqueur local que la résolution doit mesurer |
|---|---|---|---|---|
| P1 | CROISSANCE@7 se renforce | 0,3 % | 5,8 % | surfaces contrôlées en série datée |
| P2 | RÉSEAU@7 se renforce | 0,3 % | 1,5 % | État relais entre deux blocs ; médiation datée |
| P3 | POLARITÉ@7 persiste | 99 % | 99 % | deux blocs, alignements exclusifs |
| P4 | SEUIL@7 apparaît | 3,3 % | 1,9 % | rupture diplomatique, premier tir, annexion déclarée |
| P5 | TRANSFORMATION@7 apparaît | 0,4 % | 0,4 % | institutions changées par étapes, État conservé |
| — | POLARITÉ@7 s'intensifie (nouveau) | — | 33 % | série chiffrée de frappes, même source |

**Lecture.**
- Les changements de force ne sont plus une constante : la référence est le rythme propre de la carte
  (CROISSANCE change plus vite que RÉSEAU), modulé par les sources présentes.
- **Le rejeu reste mauvais, et c'est attendu** : avec les issues codées par le test, le Brier vaut 0,3715.
  La raison n'est pas le moteur. P1 était résolu par « au moins deux attaques en 6 jours », alors que le
  marqueur de CROISSANCE@7 est « surfaces contrôlées en série datée » : la prévision calculait une chose
  et la résolution en mesurait une autre. C'est ce décalage, et non le modèle, qui produit l'écart de
  ×1 628 selon le codage relevé par le test.
- La question que le test voulait poser — « l'escalade continue-t-elle de s'intensifier ? » — se pose en
  v0.3.1 avec `POLARITÉ@7 s'intensifie`, résolue par une série chiffrée de frappes (même source, deux
  semaines comparées). Sans fréquence externe, 33 % est un énoncé d'indifférence (hausse, stabilité ou
  baisse), pas une estimation : c'est l'ordre de grandeur honnête d'une ignorance, au lieu d'un 0,3 %
  qui en avait l'apparence. L'issue de cet événement n'est pas scorée ici : le test ne fournit pas la
  série de frappes de la semaine précédente.

---

## Exemple 10 — Quatrième cas réel rejoué : Alberta, 18 → 25 octobre 2026 (sans événement)

> Archive de versions antérieures : faits non revérifiés, ancien codage et anciens chiffres.
> Non recevable comme prévision 0.4.0 ; conservé pour comprendre les défauts historiques.

**Origine.** Test régressif transmis par l'utilisateur le 2026-10-25, avec sa fiche
(`assets/cas-reels.jsonl`, C-0004-S05, `sans_evenement: true`). Faits et sources tels que rapportés ;
**rejeu** : le référendum du 19 octobre était tenu au moment du codage.

**État.** `[2026-10-18 | 6 jours] POLARITÉ@5[F] + CONTRAINTE@8[F] + RÉSEAU@5[f]`, liaison
`POLARITÉ@5 —conflit→ CONTRAINTE@8`. Issue : même état, rien n'a changé.

**Calcul (reproduit en v0.3.2).**

| # | Événement | p | o | Marqueur local affiché (S1) | Résolution du test | S1 |
|---|---|---|---|---|---|---|
| P1 | SEUIL@8 apparaît | 1,30 % | 0 | décision définitive, délai de recours expiré | le gouvernement engage la procédure constitutionnelle | **non** : engager une procédure n'est pas une décision définitive |
| P2 | CONTRAINTE@8 persiste | 99,31 % | 1 | acte interdit ou imposé, sanction prévue | le référendum reste non contraignant | oui |
| P3 | POLARITÉ@5 persiste | 98,94 % | 1 | deux factions nommées, alignements opposés répétés | les deux camps restent identifiables | oui |
| P4 | RÉSEAU@5 se renforce | 0,83 % | 0 | personne-pont entre deux groupes | une organisation rejoint la coalition | **non** : adhésion à un groupe, pas pont entre groupes |
| P5 | TRANSFORMATION@5 apparaît | 0,34 % | 0 | organigramme modifié, mission et membres conservés | le fédéral modifie le cadre fédéral-provincial | **non** : cela relève de la strate 8, pas des organisations |

**Lecture.**
- Brier 0,00008, justesse 5/5. Mais l'**incertitude contenue** du lot (moyenne de p(1 − p)) vaut 0,0084,
  contre 0,25 pour un lot entièrement indécis : le lot ne contenait que 3 % de l'incertitude maximale et
  ne pouvait presque rien révéler. Le score mesure la prudence sur un cas décidé, pas la calibration.
- Le rappel S1 était affiché et **trois résolutions sur cinq ne le respectent pas**. Les issues n'en sont
  pas changées ici (rien ne s'est produit, sous aucune des deux lectures), mais sur un cas où quelque
  chose arrive, c'est exactement le décalage qui a produit le ×1 628 du Yémen. L'affichage ne suffit
  pas : le contrôle est désormais une étape explicite de la procédure (SKILL.md, étape 6) et du test à
  l'aveugle (`validation.md` §8).
- Apport réel : la première fiche réelle **sans événement** (B4), qui contre le biais du survivant.

---

## Exemple 11 — Politique intérieure française, 19 → 26 octobre 2026 : un bon score qui ne valide rien

**Origine.** Test régressif transmis par l'utilisateur le 2026-10-26 : journée contre la vie chère du 17
octobre (550 000 à 800 000 personnes ; environ 2 400 interpellations), couvre-feux partiels annoncés le
19 (Lille, Douai, Denain, Wattignies, Paris, Lyon), budget 2027 sans majorité, 49.3 « non exclu ».
Faits et sources tels que rapportés, non revérifiés ; **rejeu**, et l'état du 19 a été établi à partir
de pages mises à jour les 23 et 25 octobre (contamination signalée par le testeur).

**Ce que le test a trouvé (moteur 0.4.8).** Lecture : `CONTRAINTE@8[F] + INCERTITUDE@8[f] +
TRACE·MÉMOIRE@9[f]`. Les deux questions scorables (« les couvre-feux sont levés » 0,8 %, « le budget
est tranché » 6,8 %) sont justes, mais l'ablation `--sans-cartes` donne **exactement** les mêmes
probabilités : un modèle « rien ne change » aurait le même score. Le mouvement auto-organisé, moteur de
la situation, n'avait aucune strate où s'ancrer ; « la contrainte s'étend-elle ? » n'était pas posée.

**Ce qui a changé en 0.5.0.**

1. **Strate 13, Politique intérieure** (`strates.md`, `equivalences/strate-13.md`). Recodage :
   `[2026-10-19 | 1 semaine] CONTRAINTE@8[F] + INCERTITUDE@13[f] + ÉMERGENCE@13[f] + TRACE·MÉMOIRE@13[f]`
   — l'incertitude budgétaire est politique (conduites conditionnées : « censure si… »), le mouvement
   s'ancre en ÉMERGENCE@13 (appels décentralisés, blocages repris par imitation), le répertoire de 2018
   en TRACE·MÉMOIRE@13 ; les couvre-feux restent en strate 8 (l'acte juridique).
2. **Comparateur inertiel imprimé et journalisé** (`p_sans_cartes`) :

| Événement | p | sans cartes | Lecture |
|---|---|---|---|
| CONTRAINTE@8 disparaît | 0,8 % | 0,8 % | ne teste que l'inertie |
| INCERTITUDE@13 disparaît | 7 % | 7 % | ne teste que l'inertie |
| SEUIL@13 apparaît (gouvernement renversé, dissolution) | 0,7 % | 0,4 % | les cartes déplacent p de +0,3 point |
| RÉSONANCE@13 apparaît (journées d'action synchronisées) | 0,4 % | 0,4 % | aucune source dans la matrice |

   **Constat de conception, que le test a mis au jour sans le nommer** : sans base de cas, les cartes
   ne modulent que les apparitions ; une persistance ou une disparition ne dépend que de l'inertie
   (`graphe.md` §2.1). Toute question de cette forme a donc un apport des cartes nul, quel que soit son
   score.
3. **« La contrainte s'étend-elle ? » devient exprimable** : `CONTRAINTE@8 s'intensifie` avec une
   résolution chiffrée (grandeur « communes sous couvre-feu », source « communiqués préfectoraux »,
   observations datées au plus tard le 19). Sans fréquence conditionnelle externe, le moteur répond
   **non estimée**, au lieu d'un chiffre inventé.
4. **Droit d'exception** : le testeur proposait un SEUIL@8 « régime d'exception déclaré ». Non retenu
   tel quel : un état d'urgence ou un couvre-feu est réversible, donc CONTRAINTE@8 qui apparaît ou
   s'intensifie ; il n'est SEUIL@8 que par décision définitive ou passage des mesures dans le droit
   commun (`strates.md` §4, `equivalences/strate-08.md`). La bascule politique irréversible (motion de
   censure adoptée, dissolution) est SEUIL@13.

**Ce qui reste.** À une semaine, l'apparition d'une structure non ancrée vaut 0,4 % (fréquence par
défaut ramenée à la fenêtre) : la deuxième journée violente du 24 octobre (1 314 interpellations, selon
une source dont seul le titre a été lu) aurait été une RÉSONANCE@13 ou une CROISSANCE@13 jugée presque
impossible. Ce n'est pas réglable sans données : il faut des fréquences externes (étape 4 de la
feuille de route, sources dans `sources-france.md`) ou des cas homologues. Pour un vrai test à
l'aveugle, figer les questions avant les faits, avec un seuil chiffré : par exemple, pour la
manifestation du 5 novembre, « interpellations selon le ministère de l'Intérieur ≥ 1 000 ».

---

## Exemple 12 — Après les sénatoriales, 28 septembre → 26 octobre 2026 : ce que l'alphabet ne dit pas

**Origine.** Second test régressif sur la politique française, transmis le 2026-10-26 (moteur 0.5.0).
Renouvellement de 178 sièges du Sénat le 27 septembre ; premier groupe RN annoncé ; LFI entre au Sénat ;
mouvement contre la vie chère en extension depuis début septembre. Questions figées et hachées avant
la recherche des issues, mais **trois sur quatre contaminées** : le testeur connaissait déjà la
période du 17 au 25 octobre par le test de l'exemple 11.

**Lecture du testeur.** `[2026-09-28 | 1 semaine] PÉRIODICITÉ@13[F] + SEUIL@13[f] + PROPORTION@13[f] +
ÉMERGENCE@13[f]`.

**Reproduit en 0.5.0 (4 pas).**

| Événement | p | sans cartes | Issue |
|---|---|---|---|
| CROISSANCE@13 apparaît au moins une fois | 2,8 % | 1,6 % | indéterminable : aucune série d'une seule source |
| RÉCIPROCITÉ@13 apparaît au moins une fois | 1,6 % | 1,6 % | non |
| ÉMERGENCE@13 disparaît au moins une fois | 18,4 % | 18,4 % | non |
| POLARITÉ@13 présente au 26 octobre | 1,7 % | 1,4 % | non |

La strate 13 fait son office : le mouvement s'ancre, et les cartes déplacent p sur deux questions sur
quatre (aucune à l'exemple 11).

**Trois défauts, corrigés en 0.5.1.**

1. **Marqueur de SEUIL@13 trop large.** « Résultat électoral proclamé » faisait de tout scrutin un
   seuil, contre la définition de la carte (irréversibilité). Marqueur restreint : résultat qui change
   la majorité ou entraîne une alternance ; un scrutin de continuité n'est pas un seuil. Conséquence
   observée : SEUIL@13 présent, le moteur refusait « SEUIL@13 apparaît » (un mot par carte et par
   strate), donc la question utile (censure, dissolution) devenait impossible. Le message de refus
   l'explique désormais.
2. **Abaisser à f n'est pas une réponse.** Le testeur a gardé SEUIL@13 en f parce que le fait
   remplissait le libellé du marqueur mais pas la définition. Règle ajoutée à A6 : marqueur rempli,
   définition contredite → carte non ancrée, marqueur signalé au journal des lacunes.
3. **Questions nominatives.** Les questions tranchables proprement (qui préside le Sénat, la taille du
   groupe RN, qui préside le groupe RDPI) ne sont pas des événements de cartes. Elles se journalisent
   désormais avec `"origine": "jugement"` et sont scorées à part. Sur les trois jugements du testeur
   (0,80 ; 0,45 ; 0,60 ; issues oui, oui, non), `scorer` donne un Brier de 0,234, contre 0,25 pour une
   réponse indifférente. Les deux erreurs (chiffre annoncé trop décoté, rumeur trop pondérée) sont des
   biais de jugement, que seul ce suivi séparé peut mesurer.

**Règle de méthode.** Enchaîner les rejeux du plus ancien au plus récent (`validation.md` §8) ; toute
question dont l'issue a pu être vue est un rejeu.
