# Alphabet situationnel — Apports théoriques et leur traduction en contrôles

> Version : 0.7.75

> Ce que trois analyses du corpus de Carlos E. Perez (*Intuition Machine* : essais 2016-2026 ; livres
> *Artificial Fluency*, 2024, et *Artificial Empathy*, 2023), versées au projet le 27 octobre 2026, ont
> changé dans le skill, ce qui attend et ce qui est refusé. Charger ce fichier pour comprendre **pourquoi**
> une règle de 0.6.0 existe, pas pour lire une situation.

---

## 1. Règle d'importation

> **Un concept n'entre que s'il ajoute un contrôle : un champ qui peut rester vide, un test qui peut
> échouer, une commande. S'il n'ajoute qu'un mot, il appauvrit le skill.**

Le corpus est un **générateur d'hypothèses et un diagnostic de dettes**, pas une autorité : aucun cas
codé, aucune prévision scorée, aucune reprise académique trouvée. Il ne se cite jamais dans une fiche
de cas ni comme référence d'un équivalent (A3).

---

## 2. Le diagnostic retenu

1. **Le moteur répond au barreau 1 et parle au barreau 3** (Pearl). Il compte des associations entre
   cartes ; sa sortie se lit comme une prévision sur un futur non advenu. L'écart n'était pas déclaré.
2. **L'ancrage était une relation à deux termes** (fait → carte). A6 vérifiait que le fait ne relève
   pas des voisines, jamais par quel mécanisme il relève de la carte : il manquait l'interprétant.
3. **Les cartes sont des catégories, pas des règles de transformation.** Une catégorie ne produit pas
   de transition : les 66 arêtes de la matrice sont stipulées, non dérivées.
4. **Le graphe de validation n'a pas d'ancre indépendante** tant que les cas réels ne sont pas actifs :
   « la topologie achète la sophistication, pas la vérité ».
5. **Le système est sous-déterminé** : une centaine de paramètres pour quatre cas réels.

---

## 3. Ce qui est entré en 0.6.0

| Concept | Source | Contrôle ajouté | Où |
|---|---|---|---|
| Barreaux de Pearl | *Artificial Empathy*, ch. 9 | barreau déclaré dans la ligne S5 ; toute transition A tant qu'aucune source ne documente une intervention ; lecture « si le motif observé se répète » | `constitution.md` §3, `dynamiques.md`, `barreau` (§H) |
| Interprétant (Peirce) et clôture sémantique | *Intuition Machine* (étape 4) ; *Artificial Fluency*, ch. 7 | champ `garantie` (mécanisme, attendu, contredirait), requis pour F ; forme type dans chaque fiche | A6, `cartes.md`, `base-de-cas.md` §2 |
| Pertinence (« différence qui fait une différence dans l'action ») | *Artificial Fluency*, ch. 2 et 10 | champ `option` (acteur, avant, après), requis pour F | O1, `base-de-cas.md` §2 |
| Abduction (« une bonne hypothèse rend une question évidente ») | *Artificial Fluency*, ch. 7 ; *Artificial Empathy*, ch. 4 | `questions` au premier état d'un cas réel : chacune départage deux cartes ; question décorative refusée | `grammaire.md` §7, `base-de-cas.md` §2, moteur |
| Journal à deux probabilités | *Artificial Empathy*, ch. 9 (Pearl) | `probabilite_jugement` scellée avant le moteur ; `moteur_contre_jugement` compte améliorations et dégradations | `validation.md` §1, `sceller-jugement` |
| Sous-spécification | *Artificial Empathy*, ch. 4 | bande de sensibilité sur six variantes ; « non identifié » si elle traverse 50 % | `graphe.md` §2.3 |
| Gaming de la métrique | *Artificial Empathy*, ch. 4 | difficulté par question, part des références extrêmes, Brier stratifié | `validation.md` §1, §7 |
| Appariement des boucles (Goodhart) | *Intuition Machine* (Grounded Loop Graph Model) | l'apport des cartes se lit avec la part de ruptures SEUIL | `validation.md` §7 |
| Objets-frontière | *Artificial Fluency*, ch. 12 | Documenté exige un texte de la discipline et un nom local ; `audit` le vérifie | `equivalences.md` §2 |
| Magic rabbits (traceback) | *Artificial Fluency*, ch. 9 | `assets/rabbits.jsonl` ; étape de traceback dans le codage | `base-de-cas.md` §3, `validation.md` §6 |
| Registre des angles morts | *Intuition Machine* (P8 sans instrument) | `angles-morts.md`, entrées réfutables ; ligne obligatoire en sortie LIRE | `simulation.md` §1 |
| Friction cognitive | *Intuition Machine* (essai de mai 2026) | bloc « coût du codage » en sortie | `simulation.md` §1 |

Aucun de ces contrôles ne change un chiffre du moteur, sauf la bande de sensibilité, qui en ajoute.

---

## 4. Ce qui attend, et à quelle condition

| Piste | Pourquoi pas maintenant | Condition | Version |
|---|---|---|---|
| Hors domaine attribué, boucle d'agence | **écarté par la décision 1b** (27 octobre 2026) : les cartes à agents sont universelles ; restent à instruire les anomalies de définition (`equivalences.md` §3) | — | — |
| Échelle de dureté : portes par niveau ρ, date de révision des sources | n'a d'objet qu'avec des cas actifs et des équivalents sourcés | étapes 2 et 3 de la feuille de route | Structurer |
| Séquence (niveau H1.6, motifs ordonnés) | inerte avec quatre cas : aucun homologue | 30 cas actifs dans une strate | Éprouver |
| Cartes comme règles de transformation (condition, opération, invariant, production) ; liaisons comme opérateurs | les 16 règles doivent être écrites **avant** d'être comparées à la matrice, par quelqu'un qui ne l'a pas vue ; écrites par l'auteur du skill, le test perdrait sa valeur | rédacteur indépendant de la matrice | Grammaire |
| Dérivation de l'alphabet (espace ou liste ?) | programme de recherche, hors du skill pour ne pas le contaminer | quatre distinctions préenregistrées, double codage | note de recherche |
| Agapique / anancastique, symétrie brisée, banque de cas adverses | gain local, ou après stabilisation des définitions | après les règles de transformation | Grammaire |

---

## 5. Ce qui est refusé

- **L'ontologie de QPT** (quatre modes « irréductibles ») : thèse d'universalité forte, contraire à
  P1 ; elle rendrait le skill moins réfutable. Utilisable comme générateur d'hypothèses seulement.
- **Le rapprochement des 16 cartes et des 16 espèces d'agence** : coïncidence numérique (9 + 7), objets
  différents (des agents, des situations).
- **La normativité** (« agapique », « sol de qualité ») sans marqueur observable : contraire à A5, P5, P9.
- **La critique bayésienne prise comme verdict** : « une heuristique humaine déguisée en mathématiques »
  est une polémique ; elle oblige à déclarer le barreau et à mesurer la sensibilité, elle ne prouve pas
  que la révision bayésienne est fausse.
- **Le théâtre théorique** : douze cases, neuf boucles, quatre modes n'entrent pas, faute de contrôle.

---

## 6. Ce que le skill faisait déjà mieux que le corpus

Préenregistrement par empreinte, score de Brier, comparateur sans cartes, provenance ρ calculée, refus
de chiffrer l'inconnu, journal non réécrit, audit et autotests, périmètre d'usage borné. Le transfert
est à sens unique : des concepts entrent, aucune autorité.

---

## 7. Deux apports reçus le 27 octobre 2026 (0.6.6)

Deux synthèses versées par l'auteur : *Pistes CIA* (Heuer 1999, Kent 1964, *Tradecraft Primer* 2009,
Gleeson 2023, Schlickenmaier 2026, Mulligan 2026) et *Spiral Semiosis* (deeplearningplaybook.com,
même corpus *Intuition Machine* que les trois premiers rapports). Même règle d'importation (§1).

**Corrections préalables.** Les deux documents décrivent un skill légèrement différent de celui-ci :
16 cartes, pas 36 ; modes LIRE, PRÉVOIR, CODER, SCORER ; barreau, garantie, option, rabbits introduits
en 0.6.0 (le nom local aussi) ; le barreau n'est pas présenté comme une probabilité ; les *rabbits* sont
des constructions ad hoc à résorber, pas des signaux faibles ; garantie et option ne mesurent pas la
qualité d'une source. Les pistes qui reposaient sur ces lectures sont jugées sur le skill réel.

### 7.1 Ce qui entre

| Piste | Source | Contrôle ajouté | Où |
|---|---|---|---|
| Qualité de l'information (*Quality of Information Check*) ; sources fabriquées par IA générative | *Tradecraft Primer* ; Mulligan 2026 | `corroboration` requis pour un mot F de cas réel actif : `independantes` (au moins deux sources nommées) ou `unique` (signalée) ; refus si « indépendantes » ne nomme qu'une source | `base-de-cas.md` §2, `controle_corroboration` |
| Langage probabiliste brouillé | Kent 1964 | aucun mot de probabilité sans son chiffre ; un jugement donné en mots se fait préciser avant scellé, jamais convertir | `simulation.md` §2, `SKILL.md` étape 7 |
| Désinformation cohérente | Mulligan 2026 | angle mort « véracité d'un fait », déclaré délibéré : l'alphabet lit la forme, pas l'authenticité | `angles-morts.md` |

**Le mode « calibrer » proposé (mot → chiffre par la table de Kent) est refusé** pour la raison même
que donne Kent : le même mot (« serious possibility ») était lu de 20 à 80 % par les membres de son
propre comité. Convertir un mot par une table impose au lecteur l'interprétation de la table, pas
celle de l'auteur du jugement. Le contrôle utile est l'inverse : exiger le chiffre.

### 7.2 Ce que le skill fait déjà

| Piste | Déjà couvert par |
|---|---|
| Hypothèses concurrentes (Heuer, ACH) : chercher l'information qui *infirme* | A7 (contre-observation exigée et classée) ; `questions` qui départagent deux cartes, c'est-à-dire la diagnosticité d'ACH |
| *Key Assumptions Check* | `indicateur_bascule` et `refutation` du journal ; ligne A6 (voisines écartées et pourquoi) |
| Confiance dans le modèle, distincte de p | barreau, bande de sensibilité, niveau ρ |
| Transparence face aux LLM ; export lisible par un LLM ; mode « agent » | le skill *est* lu par un modèle de langage ; `--json` ; CODER est déjà l'assistance au codage, la décision restant au codeur |
| « What if we're wrong ? » | A7, angles morts, `moteur_contre_jugement` |
| Interprétants rejetés (Spiral, P1) | `rejets_a7`, ligne A6, bloc « coût du codage » |
| Lectures ouvertes `OPEN` (P4) | statut Spéculatif ; « non identifié » ; questions non tranchées |
| « La différence qui fait une différence » (P10, Bateson) | `option` depuis 0.6.0 (pertinence, *Artificial Fluency*) |
| Clôture conditionnelle (P6) | une case Vide close « ne se rouvre que sur une source nouvelle » (0.6.5) |

### 7.3 Ce qui attend

| Piste | Condition | Version |
|---|---|---|
| Mode « scénarios » à la manière d'ACH (matrice informations × états concurrents, score d'incohérence) | cas actifs : sans eux, la matrice se remplit de jugements que rien ne recoupe | Éprouver |
| Mode sémiotique du fait (règle, occurrence, qualité ; Spiral P8) : CONTRAINTE ancrée sur une occurrence sans règle, PÉRIODICITÉ sur une seule occurrence | 30 cas actifs, pour mesurer si la distinction change un codage | Grammaire |

### 7.4 Ce qui est refusé

- **Tout poids sur les sources** (`fiabilite_source` qui modulerait p, `poids_source` décroissant avec
  la persuasion, `fabrication_risque` qui élargirait la bande) : paramètres non calibrés ajoutés à un
  modèle déjà sous-déterminé. La corroboration se déclare ; elle ne pondère pas.
- **Test de biais par « état inverse »** : inverser des antagonismes ne produit pas une lecture
  plausible ; A7 et les questions qui départagent font le travail sur des faits.
- **Lecture multi-échelle de la bande de sensibilité (Spiral P2)** : la bande mesure les hypothèses du
  modèle, pas l'échelle de lecture ; l'échelle est déjà portée par le qualificatif `multi-échelle`.
- **Phases perceptive à scientifique (P3), quatre stabilités (P5)** : vocabulaire sans marqueur ni
  donnée ; aucun contrôle ne peut échouer.
- **Récursion automatique issue → nouvel état (P7)** : un système qui recode sa propre clôture contamine
  ses cas ; une nouvelle prévision part d'un nouvel état observé, et l'ancienne n'est jamais réécrite.
- **Sceau conditionnel (P6)** : un scellé qui se rouvre ne prouve plus rien ; la révision est une
  nouvelle prévision versionnée.
- **Standard ouvert, API REST** : prématuré avant la 1.0 ; le schéma documenté et validé par `audit`
  tient lieu de contrat.

---

## 8. *Intuition Machine*, site et QPT (0.6.7)

Synthèse versée par l'auteur le 27 octobre 2026 : intuitionmachine.com, Quaternion Process Theory
(3 niveaux × 4 colonnes, 4 lettres, 12 boucles ; « 7 axiomes, 9 théorèmes, 43 vérifications »). Même
auteur et même corpus que le rapport « Intuition Machine » de 0.6.0, dont l'ontologie QPT a été
refusée (§5). Les vérifications « machine-checkable » sont celles du modèle QPT sur lui-même : elles
établissent sa cohérence interne, pas sa correspondance avec des organisations ou des situations.

**Corrections préalables** (comme au §7) : 16 cartes, pas 36 ; modes LIRE, PRÉVOIR, CODER, SCORER ;
`version_regles` ne mesure pas la péremption d'un contexte (c'est la date d'information et
`disponible_le`, B1) ; `option` n'est pas « une rotation au niveau convention sans ancrage » : elle
nomme un acteur et un changement observable.

### 8.1 Ce qui entre

| Piste | Contrôle ajouté | Où |
|---|---|---|
| « Unchecked output » : une sortie de modèle enregistrée comme fait | un cas actif dont le codage a été proposé par un modèle (`codage.recodage`) exige `codage.recodage_confirme` `{par, date}`, signé par un codeur humain nommé ; le modèle ne peut pas se confirmer lui-même. Visait d'abord les quatre propositions, dont Claude avait écrit garanties, options et questions (archivées en 0.6.8) ; vaut pour tout cas que Claude codera | `base-de-cas.md` §2, `feuille-de-route.md` §4 |

### 8.2 Ce que le skill fait déjà

| Piste | Déjà couvert par |
|---|---|
| Système de mots, axiomes (P1) | règles O, A, G, B, T, S, V ; grammaire formelle (`grammaire.md` §2) ; `audit` |
| *Grounding* contre *knowledge* (P2) | garantie et option sont déjà deux champs distincts, aux clés distinctes, contrôlés séparément |
| *Evaluation drift* : comparer à la réalité, pas au rapport précédent (P4) | le Brier se calcule contre une résolution externe figée avant échéance (S1, V1), jamais contre une prévision antérieure |
| *Stale context* (P4) | date d'information, `disponible_le` (B1) : aucune preuve postérieure n'entre dans un calcul |
| Saboteur licencié, remise en cause du graphe (P10) | différé déjà : règles de transformation écrites par un rédacteur indépendant de la matrice, banque de cas adverses (§4) |
| Plafond de procéduralisation (P8) | A4 exige un codeur humain ; CODER assiste, ne décide pas (§7.2) |

### 8.3 Ce qui attend

| Piste | Condition | Version |
|---|---|---|
| Test du témoin, chaîne fait → interprétation → trace → événement (P3, P7) | cas actifs avec `corroboration` : mesurer d'abord combien de mots F reposent sur une source unique, puis décider s'il faut typer la distance à l'événement (document primaire, presse, analyse) | Éprouver |
| Date de révision des règles et paramètres (« orphaned rules », P4, P6) | déjà inscrite dans l'échelle de dureté (§4) | Structurer |

### 8.4 Ce qui est refusé

- **Le sceau conditionnel par propriétaire inactif** (P6) : même motif qu'au §7.4 ; un scellé qui se
  rouvre ne prouve plus rien.
- **Restructurer `audit` en diagnostic à sept couches** (P5), **nommer les contrôles par édit
  pathologique** (P11) : renommage sans contrôle nouveau.
- **Transaction d'apprentissage en sept étapes** (P9) : le cycle état → événement → état est déjà
  tracé par la fiche, le journal et le CHANGELOG ; ajouter sept rubriques à chaque changement d'état
  alourdirait le codage sans qu'aucune puisse échouer.
- **Protocole d'interopérabilité « Common Ground »** (P12) : comme l'API REST au §7.4, prématuré avant 1.0.
- **Opérateur formel `qml_q` comme modèle du moteur** (P1) : « modèle aspiratif » selon le document
  lui-même ; un opérateur sans équivalent dans le calcul n'ajoute pas de contrôle.

---

## 9. Pistes bibliographiques (0.7.0)

Note versée par l'auteur le 27 octobre 2026 : une quarantaine de références (Heuer, Tetlock, Pearl,
Murphy, process tracing, QCA, scénarios, impacts croisés, sensemaking, marchés de prévision). Triée par
la règle d'importation (§1).

**Entré.** Les tests de process tracing (Van Evera 1997 ; Collier 2011, *PS* 44(4), 823-830, lu) donnent
au choix F/f un critère de preuve : F exige un fait suffisant (`test` : pistolet ou double), un fait qui
remplit seulement le marqueur est un cerceau et donne f (`protocole.md` A6). La décomposition de Murphy
(1973) sépare, dans le Brier, la fiabilité, la résolution et l'incertitude (`validation.md` §5).

**Retenu pour plus tard.** Un marché de prévision (Metaculus, Polymarket) comme comparateur externe au
même horizon, plus exigeant que l'inertie, si sa probabilité peut être figée à la date de la prévision
(0.8, étape 4). Les *Cross-Impact Balances* (Weimer-Jehle 2006) pour le mode « scénarios » (0.9).
L'agrégation de codeurs par calibration passée (Cooke 1991), au second codeur (étape 5).

**Déjà présent.** ACH (A7, questions qui départagent) ; barreau de Pearl ; Tetlock (scellé, comparateur,
Brier par épisode) ; boîte morphologique (l'alphabet lui-même, cartes × strates, paires incompatibles).

**Non retenu.** Sensemaking, apprentissage en double boucle, niveaux logiques, autopoïèse, perspectives
T/O/P : vocabulaire sans contrôle. QCA et ensembles flous pour F/f : la force est une qualité de preuve,
pas un degré d'appartenance. La note contenait des correspondances inexactes (numéros et noms de strates,
règles) et une référence introuvable (« EL-DRUIN », arXiv 2604.10087), non citée ici.

---

## 10. Cinq apports reçus le 27 octobre 2026 (0.7.2)

Cinq analyses versées par l'auteur, toutes rédigées sur la 0.7.1 (commit `0d92b34`) : *Inquisitive
Semantics* (Ciardelli, Groenendijk et Roelofsen, Oxford UP, 2019, ch. 2, 5 et 9) ; VECTOR (Nour et al.,
arXiv 2509.14455) ; les travaux de Rulin Shao (OpenScholar, ReasonIR, Context Language Models,
DR Tulu, *Spurious Rewards*) ; ceux de Hao Zhang (spécifications, LLM-as-a-judge, ReFoRCE, Certaindex,
GameArena, LongPack) ; ceux d'Alex L. Zhang (*Recursive Language Models*, généralisation
compositionnelle, *Language-Guided World Models*, KernelBench). Même règle d'importation (§1). Les
cinq décrivent correctement le skill ; elles convergent sur un point : **le skill déclare beaucoup et
éprouve peu ses propres étapes** (source → fait → marqueur → carte → question), et l'évaluation risque
de mesurer la forme ou le style plutôt que la lecture.

Un sixième fichier versé le même jour, `apports-intuition-machine.md`, est la synthèse QPT déjà triée
au §8 (0.6.7), mêmes pistes P1–P12 et mêmes inexactitudes (36 cartes, modes SIMULER et VALIDER) :
aucun apport nouveau.

### 10.1 Ce qui entre

| Piste | Source | Contrôle ajouté | Où |
|---|---|---|---|
| Conditions de résolution d'une question ; « non A » ne vaut pas « B » | *Inquisitive Semantics*, ch. 2, §2.3–2.5 | pour un cas réel, chaque question porte `resolution` ; une question de discrimination porte `justification` {oui, non}, une par branche menant à une carte ; une branche peut mener à `indetermine` (les deux, refusé). L'exemple du schéma (« pas de troisième groupe → POLARITÉ ») commettait l'erreur : corrigé | `grammaire.md` §7, `base-de-cas.md` §2, `controle_questions` |
| Toutes les questions utiles ne départagent pas | *Inquisitive Semantics*, ch. 5, §5.4 et ch. 9, §9.2 | `type: "documentation"` (`carte`, `manque`) ; ne remplace pas la question qui départage, exigée au premier état | idem |
| Questions qui restent ouvertes, levées ou invalidées | *Inquisitive Semantics* ; GameArena (Hao Zhang) | `statut` (ouverte, partielle, resolue avec `reponse`, presuppose_invalide), chacun avec sa `preuve` | idem |
| Contrôle affirmation–passage | OpenScholar (Shao) ; spécifications (Hao Zhang) | `passage` {localisation, relation} requis pour F de cas actif ; F exige `soutient`, `partiel` donne f, `contredit` renvoie à A7, `insuffisant` n'ancre rien (scindé en 0.7.11, §15) ; « independantes » exige deux passages | `protocole.md` A6, `controle_passage` |
| Annonce ≠ réalisation | VECTOR ; OpenScholar | A5 : une possibilité, une condition, une décision non entrée en vigueur ne sont pas une réalisation | `protocole.md` A5 |
| Requêtes qui ne présupposent pas la lecture ; contradictions conservées | ReasonIR (Shao) | trois familles de requêtes (observation, discrimination, contradiction), jamais sur le nom de la carte | `protocole.md` A7, `sources-france.md` §1 |
| Arrêt sur contrôles faits, pas sur sentiment de certitude | Certaindex, DeepConf (Hao Zhang) | budget épuisé = dossier incomplet ; la convergence de réponses n'est pas une corroboration | `protocole.md` A7 |
| Sens d'une série avant usage | ReFoRCE, Arctic-Text2SQL (Hao Zhang) | liste : objet compté, unité, période, périmètre, manquants, agrégation, révisions | `sources-france.md` §5 |
| Conservation de l'information après résumé | Context Language Models (Shao) ; RLM (Alex Zhang) | contenu minimal de l'état de travail ; pièces, état révisable et prévisions scellées séparés | `simulation.md` §7 |
| Évaluer la représentation, pas seulement le résultat ; juge biaisé ; gain mal attribué | VECTOR ; LLM-as-a-judge, Chatbot Arena (Hao Zhang) ; *Spurious Rewards*, DR Tulu (Shao) ; généralisation compositionnelle, KernelBench (Alex Zhang) | banc d'essai : trois résultats séparés, épreuves de stabilité et de réexamen, corrigé indépendant, une variante à la fois, sorties anonymisées, lots séparés par épisode ; une règle constitutive ne se retire pas faute d'échec | `validation.md` §9 |

**Règle d'importation, complétée.** Depuis 0.7.2, un contrôle nouveau entre avec son épreuve : le
défaut qu'il doit détecter, construit au banc (`validation.md` §9). Les contrôles ci-dessus ont leurs
autotests (forme) ; leur utilité (lecture) reste à mesurer au banc sur des dossiers qu'ils n'ont pas
inspirés.

### 10.2 Ce que le skill fait déjà

| Piste | Déjà couvert par |
|---|---|
| Hypothèses concurrentes, critères de résolution externes, refus de chiffrer sans données | A7, S1, « non estimé » |
| Incertitude de l'analyste distincte de celle des acteurs | carte INCERTITUDE (`cartes.md`) |
| Trois chronologies (ordre du récit, date des faits, date de disponibilité) | `date`, `disponible_le`, date d'information (B1) ; l'ordre du récit n'entre dans aucun calcul |
| Plusieurs appels au même modèle ne sont pas plusieurs sources | `corroboration`, codeurs `{id, role}`, `recodage_confirme` |
| Comparer à une référence sans le mécanisme proposé | `--sans-cartes`, `p_sans_cartes`, `moteur_contre_jugement` |
| Chargement sélectif du contexte | table « Ce qu'il faut charger » de `SKILL.md` |
| Critères figés avant l'issue | scellés, résolution figée, journal non réécrit |
| Rattachement d'un attribut au bon acteur (*Language-Guided World Models*) | `option` (acteur nommé) et `objet` ; renforcé par `passage` |

### 10.3 Ce qui attend

| Piste | Condition | Version |
|---|---|---|
| Registre de dépendances : une source corrigée signale les mots, états et prévisions qui en dépendent (Alex Zhang) | un premier cas réel où une source est corrigée ; sans lui, le registre serait une documentation de plus | Éprouver |
| Dossier externe et sous-tâches bornées (*Recursive Language Models*) | dossiers réels assez longs pour que le banc montre une perte de pièces ; comparer d'abord un simple index à la décomposition, coût compris | Éprouver |
| Comparaison de trajectoires datées, contre l'état courant seul (VECTOR) | avec H1.6, 30 cas actifs dans une strate | Éprouver |
| Aide apprise proposant des marqueurs ou des cas voisins (VECTOR, ReasonIR) | corpus annoté, séparé par épisode et par date ; la proposition reste vérifiée par le codeur | après 1.0 |
| Corpus documentaire figé et son manifeste (MassiveDS, DataComp-LM) | premières comparaisons de recherche au banc | Éprouver |

### 10.4 Ce qui est refusé

- **Distances vectorielles converties en probabilités**, déplacement dans un espace de textes lu comme
  TRANSFORMATION, sortie de classifieur sommée à 100 % entre cartes : ces grandeurs ne mesurent pas
  l'objet du moteur, et plusieurs cartes coexistent.
- **Cartes ordonnées en étapes** : les cartes ne forment pas une succession unique.
- **Indices de confiance internes** (tokens, stabilité de réponse) comme force F/f ou comme
  probabilité : une erreur peut être stable.
- **Consensus de modèles ou de générations** comme corroboration ; **architecture multi-agent** ou
  récursion par principe : à comparer d'abord à une procédure simple, mêmes sources et budget.
- **Retirer une règle parce qu'aucune sortie ne l'enfreint** (rubriques sans variance de DR Tulu) :
  valable pour un signal d'entraînement, pas pour une règle constitutive.
- **Écarter les observations difficiles** (filtrage de données d'Arctic) : un résultat nul ou une
  abstention sont des observations.
- **« Indéterminé » comme troisième issue probabilisée** : c'est un état de l'information.
- **Nouvelles cartes « contexte », « recherche », « récompense »** : elles décrivent l'outil, pas une
  structure observée. Aucun de ces travaux ne justifie les 16 cartes, les 13 strates, la matrice ou
  les multiplicateurs.
- **Usage individuel ou clinique** des trajectoires de pensée (VECTOR) : hors périmètre (`constitution.md` §6).

---

## 11. « Ce qu'il manque à l'Alphabet situationnel » (0.7.5)

Note versée par l'auteur le 30 octobre 2026, rédigée sur la 0.7.4 : de Finetti (1937), David et
Michaud (1989), Goldfarb et Pardoux (2011), Vidal (2004), Diebold et Mariano (1995), Gneiting et Raftery
(2007), Carletta (1996), Reidsma et Carletta (2008), Gruber (1995), Gómez-Pérez et al. (2004), Bartlett
(1932), Weidmann. Chaque chiffre a été **recalculé** sur le dépôt avant intégration. La note est
juste sur l'essentiel — la matrice n'était jamais confrontée aux observations, les écarts de score
n'étaient jamais testés, les jalons n'avaient pas de calcul de puissance — et se trompe sur sept points,
dont trois de conception.

### 11.1 Vérifié et retenu

| Point | Vérification | Contrôle ajouté | Où |
|---|---|---|---|
| Matrice jamais confrontée aux observations (§2.1) | exact ; mesure **corrigée** (11.2) | `confronter` : chaque apparition classée par la règle du moteur | `graphe.md` §2.4, `SKILL.md` |
| Écarts de score publiés sans test (§2.10) | exact : `apport_cartes` concluait sur une moyenne. Table du test du signe exacte (0,101 ; 0,033 ; 0,008 ; 0,001) | différentiel par épisode, σ(d), autocorrélation d'ordre 1, tests exacts du signe et de Wilcoxon ; lecture tirée du test | `validation.md` §5 |
| Résidus non testés (§2.8) | exact ; fondu dans le point précédent, comme la note le propose | autocorrélation des d d'épisodes, descriptive | idem |
| Précision de f (§2.6) | chiffres exacts (6,9 points, 138 %, 60 % de zéro succès sur 10) ; critère proposé corrigé (11.2) | intervalle de la loi de f, part de la référence, « ancré » qualifié | `graphe.md` §2.2 |
| Poids des deux a priori (§2.5) | exact (k₀ = 20, k = 2 sont des pseudo-observations) ; lecture corrigée (11.2) | deux poids dans la trace | `graphe.md` §4 |
| Seuil κ sans source (§2.3) | citations conformes ; repères d'α repris pour κ, déclaré | `kappa_min` 0,67, `kappa_rapportable` 0,80, réservés ; forme des désaccords | A4, `base-de-cas.md` §6 |
| Puissance des jalons (§2.9) | direction juste, chiffres **faux** (11.2) | table de puissance recalculée | `feuille-de-route.md` §1 |
| Classe de source (§2.4) | pertinent ; réalisable à coût nul tant qu'aucun cas n'est actif | `classe_source` requis pour un cas réel actif et un dossier | `base-de-cas.md` §2 |
| Fenêtre sans lien à la durée (§2.2) | chiffres exacts (96,75 / 86,62 / 65,00 / 42,25 %) ; option A retenue, option B refusée (elle mêlerait la question au modèle) | `duree_caracteristique_jours` sourcée, refus avec temporalité générique sous la moitié de la fenêtre | `graphe.md` §2.4 |
| Intervalle dit « approximatif » (§4.1) | la forme Beta-binomiale est exacte ; « intervalle exact » est **trop fort** (11.2) | libellé corrigé dans le moteur, `graphe.md`, `SKILL.md`, glossaire | `graphe.md` §4 |
| Taux constant (§2.7) | table d'âge reproduite (80/68, 45/40, 12/10) ; interprétation corrigée (11.2) | hypothèse déclarée ; mesure par `confronter` | `graphe.md` §2.4 |
| `p_sans_cartes` = f (§4.5) | vérifié à l'égalité exacte | identité écrite, décomposition p − f | `graphe.md` §3.3 |
| Score logarithmique (§4.3) | pertes vérifiées (0,9025 / 3,00 ; 0,9801 / 4,61 ; 0,998 / 6,91) | `log`, `log_sans_cartes`, `log_infini` | `validation.md` §5 |
| Cohérence au sens de de Finetti (§4.6) | exact : partitions sommant à 1 | limite écrite | `SKILL.md` Limites |
| Épreuve bien déterminée (§3.3) | principe juste, contrôle proposé **faux** (11.2) | une révision garde l'épreuve | `valider_journal` |

### 11.2 Corrigé avant intégration

1. **Mesure de la matrice.** Sur `cas-reels.jsonl`, la note compte 1 apparition non atteignable sur 3
   (TRACE·MÉMOIRE@5) ; il y en a **2** : CONTRAINTE@8 depuis RÉSEAU@5 n'est atteignable par aucune arête
   (RÉSEAU n'en a aucune vers CONTRAINTE). Sur la base d'exemple, l'unique cas signalé part de l'état
   nul, qui n'est pas une divergence de matrice ; une autre apparition n'est atteignable que par une
   arête inter-strates abaissée. Ces quatre cas sont des archives exclues : la mesure illustre le
   contrôle, elle ne confronte la matrice à rien.
2. **Puissance de κ.** La note traite κ comme une proportion (erreur-type √(κ(1 − κ)/n)). L'erreur-type
   de κ dépend de l'accord attendu par hasard pₑ et vaut environ √(pₒ(1 − pₒ)/n) / (1 − pₑ) (Cohen
   1960), nettement plus grande : pour distinguer 0,80 de 0,60, environ 83 unités et non 33 (pₑ = 0,5).
   La conclusion de la note est renforcée, ses chiffres sont faux. Et l'unité est la décision codée,
   pas le cas.
3. **Puissance de V4.** La colonne « 2,5 points » de la note est calculée pour 2 points : 49 épisodes
   pour σ(d) = 0,05 au lieu de 32 (les colonnes 5 et 10 points sont justes). Le seuil de suffisance de
   50 épisodes est σ(d) ≲ 0,063, non 0,05. L'exemple de modèle informé (Brier 0,0446) n'est pas
   reproductible : calibré sur une fréquence de 5 %, il donne 0,0465.
4. **Taux constant et hystérésis.** La note écrit que le modèle « nie la mémoire » de SEUIL et de
   TRACE·MÉMOIRE. C'est confondre la dépendance au chemin de la **situation** — portée par l'état, son
   inertie et ses arêtes — avec la dépendance à l'**âge** d'un mot, seule absente. Une chaîne de Markov
   représente l'hystérésis : c'est l'inertie de 0,97. *[Corrigé en 0.7.13, §17 : l'inertie représente une
   persistance, non une hystérésis ; la note avait raison sur ce point.]*
5. **Ce que teste le placebo.** La note en fait le test de l'échangeabilité de la classe. Il teste
   l'inverse : que la classe **diffère** du reste de la strate. Un apport nul est ce que prédirait une
   strate entièrement échangeable ; l'échangeabilité interne à la classe reste postulée (`graphe.md`
   §3.3).
6. **Épreuve commune.** Imposer le même critère à toutes les lignes d'un même `evenement` refuserait
   SEUIL@7 sur deux objets différents. Le phénomène est déjà fixé par le marqueur local, contrôlé ;
   l'épreuve (source, critère, seuil, objet) est propre à une question. Le contrôle retenu : une
   révision — même épisode, même événement, même échéance — garde son épreuve.
7. **Lectures trop fortes.** « Intervalle exact » : exact pour une vraisemblance pondérée, approché pour
   ce qu'il vise. « Dix fois plus de confiance dans le défaut que dans les homologues » : k₀ et k
   portent sur deux quantités différentes. « Refuser “ancré” tant que l'intervalle de f contient 0 » :
   l'intervalle d'une loi Beta lissée ne contient jamais 0. « 30 est la borne du théorème central
   limite » : c'est une règle d'usage, et ρ0 ne repose sur aucune approximation normale. Le dépôt ne
   citait ni CAMEO ni Weidmann, contrairement à ce que dit la note ; ρ4 est calculé. La perte
   quadratique comme critère de la prévision est développée surtout dans des textes postérieurs de de
   Finetti (années 1960 et 1970) ; le texte de 1937 fonde la cohérence sur le pari.

### 11.3 Ce qui attend, et ce qui est refusé

**Attend** (`feuille-de-route.md` §1) : seuil d'ancrage, atténuation par corroboration et passage,
loi de Weibull, idéologie sémiotique à l'étape 5, contrôle de circularité de la garantie, test de
représentativité (sans population de référence, il reste vide), évaluation des 208 cases contre les
critères de Gruber (clarté, cohérence, extensibilité, biais d'encodage minimal, engagement ontologique
minimal). La distinction vérification / validation de Gómez-Pérez est celle que le dépôt écrit déjà
(« l'audit vérifie la forme, pas la vérité ») ; elle est désormais attribuée. Que les trois arêtes fortes
soient « dérivables des définitions » n'est pas établi et n'est pas repris.

**Refusé**, avec la note elle-même : statistique de Diebold-Mariano asymptotique comme premier outil,
appareil ARIMA, indices de prix, lois de distribution, tests de comparaison de moyennes, p-value comme
critère de décision, ontologie greimassienne, dix-septième carte, mode d'abduction, aspectualité à la
place de `temporalite`. Renommer le champ `frequence_de_base` casserait le schéma du journal : le champ
garde son nom, `graphe.md` §2.2 dit ce qu'il est (une moyenne a posteriori, non une fréquence observée).

---

## 12. « Capacité et généralisation » et « Réponses à la feuille de route » (0.7.6)

Deux notes versées par l'auteur le 30 octobre 2026. La première lit Dreyfus et al. (2008), *Apprentissage
statistique*, ch. 1 et 2, pour la méthodologie d'évaluation seulement ; la seconde répond aux décisions
ouvertes de `feuille-de-route.md` §1. Chiffres recalculés avant intégration.

### 12.1 Vérifié et retenu

| Point | Vérification | Ajout | Où |
|---|---|---|---|
| Variable sonde sur les paramètres | reproduite : matrice réelle au 99ᵉ centile des arêtes aléatoires (la note : 97ᵉ, autres tirages), au 83ᵉ des intensités permutées (la note : 71ᵉ) ; inerties sans effet sur une apparition à un pas | `moteur.py sonde`, avec la référence « cas seuls » qui manquait | `graphe.md` §3.4 |
| `n_min_frequence` ne change pas p | exact : p = 22,04 % de n_min = 3 à 76 ; la feuille de route 0.7.5 se trompait | ligne corrigée ; effet réel écrit (comparateur V4, ρ3) | `feuille-de-route.md` §1 |
| Concentration des poids (Kish) | exact : 9,34 pour 10 cas, cas le plus lourd 15,5 % | `n_eff_kish`, `part_cas_le_plus_lourd` dans la trace | `graphe.md` §3.2 |
| Variante corroboration / passage avant la décision 5 | orthogonale à F/f, sans effet sur p | sondes `effet_attenuation` (force ; corroboration et passage avec un dossier) | `feuille-de-route.md` §1 |
| Circularité de la garantie : signaler, ne pas refuser | juste : faux signalements inconnus | signalement dans le dossier | idem |
| Champ d'idéologie écrit avant l'étape 5 | juste : une déclaration rétrospective ne prouve rien | `signe_suffisant`, `declare_le` ≤ `codage.debut` | `base-de-cas.md` §2 |
| Critère du premier cas | juste, et la mise en garde contre le tri sur l'informativité aussi | critère écrit | `feuille-de-route.md` §4 |
| Étape 3 possible avant l'étape 2 | exact ; RÉSONANCE@7 a 2 recherches sur 3 | écrit | idem |
| Capacité relative aux exemples | juste dans sa direction | mesure arête par arête (`couverture_aretes`), P8 complété | `graphe.md` §3.4 |

### 12.2 Corrigé

1. **Ce que reproduit le hasard.** La note conclut que « 68 % de l'apport revendiqué est reproduit par une
   matrice aléatoire », artefact de la densité du graphe. Sa médiane aléatoire (18,87 %) est **exactement**
   le p obtenu sans aucun multiplicateur : ce que le hasard « reproduit » est la révision par les cas,
   présente quelle que soit la matrice. Avec la bonne référence, une matrice aléatoire médiane apporte
   +0,0 point, la vraie +3,2. La densité explique qu'un tirage sur trois environ déclenche un multiplicateur,
   pas que l'apport soit un artefact.
2. **Parcimonie.** La note lit la règle de niveau comme « le niveau qui offre le plus de cas, donc le plus
   complexe ». C'est l'inverse : la règle retient le niveau le plus **spécifique** (H1, le plus complexe)
   dès 3 cas, et ne regroupe qu'en dessous ; la parcimonie de Dreyfus et al. favoriserait le regroupement,
   et elle suppose des scores de validation qui n'existent pas. L'« option 2 » de la note est la règle
   actuelle. Le choix est écrit comme compromis biais-variance (`graphe.md` §3.2).
3. **« Proposé clos ».** Refusé : il compterait comme traitée une correspondance qu'aucun texte ne
   soutient. La règle existante suffit si elle est appliquée : non soutenu à la lecture → Vide, puis clos.
4. **Richardson pour CROISSANCE.** Ne convient pas : taux fonction du niveau adverse, terme propre
   d'amortissement, pas de capacité limite. **Modelski et Thompson pour PÉRIODICITÉ** : à vérifier contre
   la règle de la strate 12. **« `p_sans_cartes` n'est publié que si la question est ancrée »** : faux ; il
   l'est toujours ; c'est `frequence_de_base`, comparateur de V4, qui dépend de l'ancrage.
5. **Comptes.** 121 paramètres « libres » mêle paramètres de modèle et seuils d'affichage ou de
   validation ; « de l'ordre de 120 cas pour 121 paramètres » n'est pas une règle, et la dimension de
   Vapnik-Chervonenkis n'est pas le nombre de paramètres en général. Les 28 cas d'exemple sont fictifs :
   le rapport utile est zéro. La mesure qui convient est la couverture des arêtes.
6. **Validation croisée.** Le partage apprentissage / test du dépôt ne sert pas à sélectionner un modèle
   (rien n'est ajusté) ; l'épreuve de généralisation est le journal prospectif. La validation croisée est
   différée, avec la réserve de la note sur les cas dépendants.

### 12.3 Refusé ou différé

Réseaux, SVM, cartes topologiques, régularisation, arrêt anticipé, bornes numériques de
Vapnik-Chervonenkis : refusés avec la note. Weibull : différé, le diagnostic d'âge existe depuis 0.7.5
(`confronter`). Seuil d'ancrage dédoublé, rétrogradation de CROISSANCE@7, troisième recherche de
RÉSONANCE@7, lecture d'un texte pour PÉRIODICITÉ@7 : décisions et travaux de l'auteur
(`feuille-de-route.md` §1 et §4).

---

## 13. Accord sous faible prévalence, rejets, concessions (0.7.9)

Document versé par l'auteur le 30 octobre 2026. Il signale que la nécessité de ces contrôles a été
constatée en examinant un projet public de skills sous licence CC-BY-NC 4.0 ; **aucun texte, tableau,
gabarit ni code de ce projet n'est repris**, et seules les sources primaires sont citées : Cohen (1960) ;
Feinstein et Cicchetti (1990, « High agreement but low kappa: I ») ; Cicchetti et Feinstein (1990,
« … II. Resolving the paradoxes », accords spécifiques positif et négatif) ; Byrt, Bishop et Carlin
(1993) ; Krippendorff (1980) via Carletta (1996) ; Reidsma et Carletta (2008). Les formules sont celles de
ces articles ; la rédaction est propre au dépôt.

### 13.1 Retenu

| Point | Vérification | Contrôle ajouté | Où |
|---|---|---|---|
| κ s'effondre sous faible prévalence | juste ; κ = −0,009 pour 116 accords sur 118 reproduit | table 2×2, κ indéfini déclaré, PABAK, accords spécifiques | `moteur.py accord`, `base-de-cas.md` §6, A4 |
| PABAK seul ne voit pas un codeur qui n'ancre jamais | juste : 0,908 contre κ = 0 | verdict sous plafond des taux de manque (`fnr_max` 0,20) | idem |
| Erreurs directionnelles | juste dans l'idée ; corrigé (13.2) | **deux** taux de manque | idem |
| Les rejets ne sont relus par rien | juste | `rejets` : feuille aveugle, tirage fixé par le sceau, contrôle de l'audit | `validation.md` §6 |
| Révision sous insistance | juste ; déjà en partie couvert par A7 et A5 | journal des concessions, contrôles de cohérence | `validation.md` §6 |

### 13.2 Corrigé

1. **Prévalence mesurée.** La note compte 87 ancrages sur 1 888 décisions (4,6 %) ; il y en a 205 (10,9 %)
   — elle comptait les seuls mots documentés à leur apparition, pas leur présence dans chaque état. Les huit
   cartes jamais présentes sont exactes ; la conclusion tient, moins fortement.
2. **Tables de κ.** La ligne « 0 ancrage » (pₒ 0,983, PABAK 0,966) est impossible : sans ancrage, pₒ = 1 et
   PABAK = 1. « Un désaccord → κ 0,496 » ne se reproduit pas : un désaccord donne κ = 0 (un seul ancrage, non
   partagé) ou 0,663 (un ancrage commun, un en plus) ; 0,491 correspond à deux désaccords.
3. **FNR et FPR prennent le premier codeur pour référence.** A4 n'en reconnaît aucune. Les deux taux de
   manque se publient ; c/(c+d), voisin de zéro sous faible prévalence, n'informe pas.
4. **Le seuil de 15 % de prévalence** pour passer de κ à PABAK n'est dans aucune des sources citées : non
   repris. PABAK sous plafond des taux de manque porte le verdict à toute prévalence ; κ est toujours publié.
5. **Les « 95 % de rejets ».** Les 1 888 décisions comptent toutes les cartes de tous les états ; un rejet
   au sens du dossier est une candidate écartée avec motif, soit quelques-unes par dossier. Les cartes
   jamais candidates ne sont pas relues. Le **rejet « near-miss »** (tous les marqueurs présents dans les
   faits) n'est pas calculable par machine : un marqueur est une phrase, pas un champ ; non repris, la
   liste ne pourrait pas être « recalculée ».
6. **Numéro.** 0.7.9, la 0.8 restant réservée aux étapes 2 et 3.

### 13.3 Refusé

Les mécanismes que la note écarte elle-même (§5 : déjà présents, souvent mieux ancrés) ; un barème
d'accord concurrent ; tout texte du projet examiné.


---

## 14. Six notes et un audit des rivaux (0.7.10)

Versés par l'auteur le 30 octobre 2026 : notes sur Green et Armstrong (analogies structurées), sur les
profils apparentés à Perez, sur Toulmin (lu par Plantin), sur MACTOR (Godet), sur la recension de *Noise*
par Sood et Gelman, et sur trois rivaux (Wardley, Cynefin, Bueno de Mesquita) ; puis un complément et un
audit de ces notes. Lus sur le code de la 0.7.9, pas sur les notes seules. **Aucune probabilité ne
change** (144 calculs de démonstration identiques ; `scorer` ne diffère que par des clés ajoutées).

### 14.1 Retenu

| Point | Vérification | Contrôle ajouté | Où |
|---|---|---|---|
| Le mécanisme n'a pas de répondant (*backing*, Toulmin 1958, ch. III) | juste : `garantie` couvre loi de passage et réfutation, pas le support | `garantie.support` {type, reference, disponible_le} ; `argument` refusé ; prospectif | protocole A6 « Support », `base-de-cas.md` §2 |
| Une réfutation qui n'annule rien n'est pas une réfutation | juste ; aucun contrôle ne le voyait | `contredirait` ≠ `attendu` (refus) ; `contredirait` qui nomme la carte (signalé) | idem, `moteur.py dossier` |
| F occupe la place du modalisateur de Toulmin sans en être un | juste ; le texte le laissait entendre | écrit : F n'est pas un « probablement », la force d'une conclusion est p et ρ | protocole A6 |
| Bruit d'occasion (répétabilité) non mesuré | juste ; la source est la métrologie, et pour des codes catégoriels l'**analyse d'accord par attributs**, pas Gage R&R | `accord --repetabilite --ecart-jours`, `repetabilite_ecart_min_jours` 30 | A4, `base-de-cas.md` §6 |
| Représentation stratégique (Flyvbjerg 2008) | juste ; mais Flyvbjerg est contesté sur le référentiel (Love et Ahiaga-Dagbui 2018 ; réponse Flyvbjerg et al. 2018) | `interet` (promoteur refusé), `fourni_par`, `referentiel`, facultatifs | `frequences-externes.md` §2 |
| « Jugement » sans procédure | juste : la condition la moins bien mesurée ; un étalon public existe (modèle de compromis, Thomson et al. 2006) | `procedure` requise à compter de `jugement_procedure_depuis` ; Brier par procédure | `validation.md` §1 |
| Le bras externe le plus exigeant est le modèle sans le skill | juste ; le dispositif existait (0.7.8), pas la consigne | méthode recommandée du comparateur externe | `validation.md` §1 |

### 14.2 Corrigé dans les notes

1. **« Le moteur retient un homologue unique, régime à 38 % » (note Toulmin §5) : faux.** Le moteur compte
   **tous** les cas de la base au niveau d'homologie retenu (H1, H1.5, H2), pondérés ; il publie `c_A`,
   `n_eff_kish`, `nb_cas_par_niveau`, la fragilité de niveau et un placebo d'homologie (`graphe.md` §3).
   La contrainte d'ordre de Green et Armstrong (lister avant de noter) est satisfaite **par construction**
   pour le moteur : la sélection est une règle fixée d'avance, appliquée à toute la base, sans arrêt à la
   première analogie — c'est exactement la « règle qui bat la synthèse de l'expert ». Le champ
   `homologues_listes` proposé n'entre donc pas. Le risque d'arrêt prématuré se déplace vers la
   **composition de la base** (quels cas on code) : il relève de B5 (registre daté du partage avant
   codage) et du test à l'aveugle, pas d'un champ du dossier.
2. **De même, la question critique de Walton** (« un autre cas semblable a-t-il une issue contraire ? »)
   est déjà dans le calcul : les homologues à issue contraire comptent dans n_A − n_E. Le
   « contre-homologue » proposé par le complément n'entre pas.
3. **« Pluralité forcée mesurée trois fois par des équipes différentes » (note des rivaux §6) : faux.**
   Green 2002, Green 2005 et Green et Armstrong 2007 sont d'un même laboratoire. La seule réplication
   indépendante trouvée (Nikolopoulos et al. 2015, *J. Business Research* 68(8)) donne un gain **faible**
   des analogies structurées (+5 à 8 %, deux versions du résumé) et un gain fort des groupes qui mettent en
   commun leurs analogies : le « travail individuel vaut mieux » ne se généralise pas, et l'expérience y
   améliore la justesse. Le refus des architectures multi-agents **comme corroboration** (§10.4) tient, par
   la dépendance des sources ; il ne s'appuie plus sur Green et Armstrong.
4. **Green 2005** : publié (*IJF* 21(3), 463-472) ; la note citait le document de travail, et ses chiffres
   (31 % contre 32 %) au lieu de ceux de l'article (31 % contre 31 %).
5. **Bueno de Mesquita** : l'étalon n'est ni Feder ni le jeu de rôle, mais le modèle de compromis, testé
   avec le modèle de défi sur les décisions de l'UE (Thomson, Stokman, Achen et König 2006 ; Achen, ch. 10).
6. **« Les deux concurrents oubliés »** (complément) : le modèle nul existe depuis 0.5 (`--sans-cartes`,
   `p_sans_cartes`, V4 lu contre l'inertie), le bras externe depuis 0.7.8. Ce qui manquait était la
   consigne de jouer **le modèle seul** comme bras externe.
7. **Gage R&R** (note *Noise*) : outil des grandeurs continues ; pour des cartes, l'analyse d'accord par
   attributs. Recension : *CHANCE* 37(3), 70-72. Théorème des piranhas : *Notices of the AMS* 72(1),
   15-25 (2025), six auteurs.

### 14.3 Ce qui attend

| Apport | Condition | Note |
|---|---|---|
| Analyse CIB (Weimer-Jehle 2006, *TFSC* 73(4) ; ScenarioWizard) : sonde de **cohérence** de la configuration des cartes ancrées | une matrice d'impacts entre **états** publiée et datée, distincte des 66 arêtes | plus proche de la « proxémie » que MICMAC ; sujette à l'erreur de spécification, comme les arêtes |
| MICMAC : invariant ΣI = ΣD et quadrants influence × dépendance comme sonde | décision d'auteur sur le sort d'une arête non structurante | arithmétique incompatible avec les λ : sonde, jamais multiplicateur |
| Couverture de l'alphabet (TRIZ : une matrice tirée d'un corpus daté perd de la couverture ; ~40 % contre ~80 % pour une matrice reconstruite, doi:10.1007/s10845-010-0466-4) | premiers cas actifs (étape 2) | part des faits d'un dossier récent exprimés sans « non classé », par strate et période ; **indicateur d'usure, jamais garantie de lecture** (§15 : un taux agrégé monte quand on lit plus, pas quand on lit juste) |
| Typologie des contraintes de Cynefin (contrainte **habilitante**) | décision d'auteur : touche A1 | CONTRAINTE n'a qu'un type, qui retire des options |
| Marqueurs de maturité de Wardley (types de publications) | décision d'auteur : marqueur nouveau | candidat pour CROISSANCE et TRANSFORMATION |
| Épreuves des rivaux : Cynefin (accord **à structure égale**, ≥ 30 situations), Wardley (persistance d'un composant sous la règle de décomposition), SenseMaker (signification par les acteurs contre codeur extérieur) | lots du banc d'essai (`validation.md` §9) | un κ sur cinq domaines exclusifs ne se compare pas à un κ sur ensembles de cartes |
| Théorème des piranhas comme borne des λ | cas réels actifs | argument externe, analogie de forme : pas de calcul transposable |

### 14.4 Refusé

Les doctrines et prescriptions des rivaux (40 principes de Wardley, « probe-sense-respond », phase 5 de
MACTOR, 40 principes de TRIZ) : `constitution.md` §5. Les chiffres des rivaux et de *Noise* comme
fréquences externes. Le seuil « ≥ 2 analogies et expérience directe » (sous-groupe post-hoc de 23
prévisions) comme filtre. Un champ nommé `qualifier` ou `qualificatif` (collision avec G1). Toute
conversion de F en force modale. La collaboration entre codeurs comme corroboration.

---

## 15. *open-ontologies* : un régime de preuve, pas un rival (0.7.11)

Note versée par l'auteur le 30 octobre 2026 sur le dépôt `fabio-rovai/open-ontologies` (MIT), à partir de
son README, de sa décision 0007 et du résumé de CIVeX (arXiv:2605.09168) ; ni code lu ni outil exécuté.
Tout ce qu'elle rapporte de ce dépôt est donc affirmé par lui, non vérifié ici. Le dépôt ne dispute pas
l'objet de l'alphabet ; il dit comment rendre une dérivation re-vérifiable par un tiers. **Aucune
probabilité ne change, et c'est désormais établi par clôture** : 2 790 conséquences sur les 111 états de la
base d'exemple, empreinte identique pour la 0.7.9, la 0.7.10 et la 0.7.11
(`b1a592c8184d505becf216d07b83a2b5545e08527c4c67f2311b20b5530fdade`).

### 15.1 Ce que le skill fait déjà

Six règles du dépôt coïncident avec des règles du skill, trouvées séparément dans une discipline sans
rapport (ingénierie d'ontologies) : aucun chiffre sans producteur ; vocabulaires séparés et non
permutables ; l'incertitude portée par l'artefact, pas par une note ; sceller avant l'issue et ne jamais
réécrire ; un contrôle non exécuté ne s'affiche pas comme un contrôle réussi ; la partie stipulée se
déclare. C'est une corroboration **de méthode**, venue d'une source qui ignore l'alphabet — pas un
apport, et pas une preuve que la lecture est juste. Les deux systèmes prouvent ce qui est en aval de leur
partie stipulée et laissent celle-ci en prose : ici, les 66 arêtes et le barreau déclaré.

### 15.2 Retenu

| Point | Vérification | Contrôle ajouté | Où |
|---|---|---|---|
| `insuffisant` confond une lecture trop étroite et un fait sans source, aux remèdes opposés | juste : le message disait « corriger le fait, chercher une autre pièce, ou ne pas ancrer », trois remèdes pour deux causes | `absent_de_la_piece` (élargir) et `non_soutenu` (retirer) ; `insuffisant` refusé | protocole A6, `controle_passage` |
| « La couverture est mesurée » nomme un proxy qui monte quand on lit plus, pas quand on lit juste | juste ; l'intention (profondeur plutôt qu'étendue) était bonne, le mot mauvais | écrit : chaque ancrage se mesure, un par un ; la couverture TRIZ (§14.3) reste un indicateur d'usure, jamais une garantie | `SKILL.md`, §14.3 |
| « independantes » ne dit pas ce qui rend les pièces indépendantes | juste : deux identifiants peuvent partager une origine ; l'accord ne protège alors que des erreurs de transcription | `independance` {critere : origine, producteur, transmission ; motif}, prospectif | protocole A6, `controle_corroboration` |
| « Aucune probabilité ne change » vérifié par témoins, pas par conservativité | juste ; le vocabulaire est fini, la clôture calculable | `conservativite` : clôture complète, empreinte, comparaison ; désarmés comptés | `validation.md` §9 |
| Le refus du barreau 2 | juste : CIVeX montre qu'une intervention exige l'identifiabilité, donc un graphe causal engagé | rédaction : conséquence de P1, non prudence | `SKILL.md`, Limites |

### 15.3 Refusé

Le vérificateur formel (Lean) : un mécanisme est une phrase, on ne vérifie pas une phrase par machine,
et le vouloir serait le théâtre théorique (§5). Les certificats de dérivation comme format de fiche : une
dérivation qui citerait une arête postulée certifierait une pétition de principe ; le dépôt lui-même
change le mot du verdict dans ce cas. Aucune sortie du skill ne doit dire qu'une issue « découle » ou est
« impliquée » par les cartes. CIVeX comme outil : il agit sur des actions d'agent dans un environnement
instrumenté ; une lecture n'a ni action ni graphe engagé. Les ontologies du marché, les plongements et le
vocabulaire de production (« blast radius », « drift », « rollback ») : hors périmètre.

---

## 16. Audit V34 de la 0.7.11 (0.7.12)

Audit versé par l'auteur le 31 octobre 2026 : lecture de la documentation, exécution du moteur (`audit`,
`autotest`, `bilan`, calcul de démonstration), comparaison avec des théories rivales. Son verdict :
**l'instrument est terminé, la mesure n'a pas commencé** (0 cas actif, 0 Attesté, 13 Documentés sur 208).
Chaque point a été revérifié sur le code avant tri. **Aucune probabilité ne change** : clôture identique à
celle de la 0.7.9 (2 790 conséquences, empreinte `b1a592c8…`).

### 16.1 Vérifié et retenu

| Défaut | Vérification | Ajouté | Où |
|---|---|---|---|
| D5 · le placebo ne commande rien | juste : démonstration p 22 %, placebo 20 %, plage à 90 % 10–34 %, apport +1,8 point, ρ1 maintenu | `homologie_discernable` et drapeau « indiscernable du hasard » ; ρ inchangé (16.2) | `simulation.md` §1 |
| D6 · l'horizon, levier le plus fort, hors de la sortie | juste ; sur la démonstration : 22 % à un pas, 52 % à trois, 76 % à six | `bande_horizon` (1, 3, 6 fenêtres, avec et sans cartes) | idem |
| D7 · un paramètre non estimable (P8) déplace p, et p vient en tête | juste : 12 % → 22 % par des arêtes jamais éprouvées | sans cas réel actif, `resultat_principal` = paire (sans cartes, avec cartes), imprimée avant le reste ; aucun calcul changé | idem, `SKILL.md` étape 7 |
| D4 · tests exacts à effectif fixe sur un journal croissant | juste : relire le test à 50, 80, 120 épisodes gonfle α | `e_processus` dans chaque différentiel ; `v4.sequentiel` à côté du statut | `validation.md` §5 |
| D3 · retraits de marqueurs jamais agrégés | juste : 6 cartes sur 13 en strate 7 promues après modification | compte publié ; règle proposée, non appliquée | `equivalences.md` §4, `validation.md` §9 |
| L1 · le test qui change le statut n'est pas planifié | juste | test à trois bras écrit et placé dans la feuille de route | `validation.md` §8 |

### 16.2 Corrigé dans l'audit

1. **D5, ρ1 conditionné au placebo.** L'audit propose de refuser ρ1 quand p est dans la plage placebo.
   C'est changer le sens de ρ : ρ dit **d'où vient** le chiffre (trois homologues et plus), pas s'il est
   bon — l'audit lui-même compte cette distinction parmi les forces du skill (son §2.3). Le constat est
   retenu comme drapeau ; changer ρ reste une décision d'auteur.
2. **D3, « 46 % ».** Exact en nombre de cartes modifiées, mais trois seulement perdent deux éléments ou plus,
   et la règle proposée (≥ 2 éléments dans ≥ 2 strates) ne peut pas mordre avec une seule strate
   documentée. Un retrait peut aussi préciser un marqueur trop large ; la règle vise la répétition.
3. **CIB « gratuit » depuis `antagonismes.md` (§4.3).** Inexact : les antagonismes sont des
   **incompatibilités** binaires, déjà appliquées par G6, qui refuse un état incohérent. Une consistance à
   la CIB demande des impacts **signés et gradués** entre états ; aucun fichier ne les contient. Reste en
   §14.3.
4. **D8, « coder --rapide ».** Le chemin léger existe : une fiche `statut_donnees: proposition` n'exige ni
   corroboration ni passage, et n'entre pas dans les estimations. Un mode qui mettrait des champs à `null`
   dans une fiche active affaiblirait A6 sans gain : refusé.
5. **§4.4, chiffres d'o3.** L'évaluation sur 464 questions Metaculus existe (Lu 2025, arXiv:2507.04562 :
   modèles devant la foule, nettement derrière un groupe d'experts) ; les valeurs citées (0,1352 contre
   0,0225 en médiane) ne sont pas vérifiées ici et ne sont pas reprises.
6. **§6, « excès de prudence ».** La description du skill garde « aucune performance prédictive n'est
   acquise » : c'est vrai, et c'est la ligne qu'un modèle lit pour décider de charger le skill. Les forces
   se revendiquent ailleurs (16.4), sans retirer un avertissement exact.

### 16.3 Ce qui attend

| Proposition | Condition | Note |
|---|---|---|
| D1 · dériver ou calibrer λ | rédacteur indépendant (1.0) ou cas réels | l'audit mesure le déséquilibre : abaisser toutes les forces F à f déplace p de +0,7 point sur la démonstration |
| D2 · statut d'arête « Éprouvée » (n occasions, k transitions) | décision d'auteur ; premiers cas réels | `confronter` calcule déjà les occasions ; « Attesté » reste indexé sur la case |
| Dynamics of Contention (McAdam, Tarrow, Tilly 2001) : table 16 cartes ↔ mécanismes (courtage, diffusion, attribution de menace…) | une heure de lecture, texte en main | soit l'alphabet est une redescription, soit il ajoute la dimension de strate ; déjà signalé dans les notes de profils (MTT), jamais instruit |
| QCA (Ragin) : consistance et couverture d'une règle configuration → issue | cas réels actifs | indicateurs, jamais garanties (§15) |
| Gentner (structure-mapping) : H1.5 est une similarité d'**attributs** (Jaccard pondéré sur les cartes), pas de relations | décision d'auteur | les liaisons G3 n'entrent pas dans l'homologie ; l'écart entre le mot « structurale » et la mesure est à écrire |
| L7 · réduire la boîte (une strate entièrement sourcée d'abord) | décision d'auteur | compatible avec P1 : l'universalité est une hypothèse |
| Suspendre la 0.8 jusqu'au test à trois bras | décision d'auteur | `feuille-de-route.md` §1 |

### 16.4 Ce que l'alphabet fait que ses rivaux ne font pas

Trois revendications, chacune vérifiable dans le paquet et chacune réfutable :

- **Décomposabilité** (contre la panarchie, Holling et Gunderson ; Sundstrom et Allen 2019, *Ecological
  Complexity* 39, posent eux-mêmes la question « plus qu'une métaphore ? ») : une carte peut être Vide ou
  close dans une strate sans que les quinze autres soient touchées ; un cycle adaptatif échoue ou réussit
  en bloc.
- **Marqueur indépendant du modèle** (contre la théorie des catastrophes en sciences sociales, Zeeman ;
  critique de Sussmann et Zahler 1978) : SEUIL a la même forme que la fronce (hystérésis), mais un fait ne
  l'ancre que par un marqueur local mesuré hors du modèle (« franchissement reconnu par les parties »), ce
  qui empêche l'ajustement après coup à toute discontinuité. Réfutable : un dossier qui ancre SEUIL sans
  marqueur rempli serait un contre-exemple.
- **Provenance ρ** : une échelle qui dit d'où vient le chiffre, distincte de sa fiabilité.

Et une comparaison de statut, pas de théorie : la cliodynamique (Turchin, lettre à *Nature*, 2010) a une
prédiction datée et publique ; l'alphabet n'en a aucune. Le test à trois bras (`validation.md` §8) est ce
qui changerait cela.

---

## 17. Audit comparatif avec cinq projets open source (0.7.13)

Audit versé par l'auteur le 31 octobre 2026, lu sur le commit `3acde1d` (0.7.12), comparant le skill à
PyCIB (analyse d'impacts croisés), FCMpy (cartes cognitives floues), pgmpy (modèles graphiques
probabilistes), EMA Workbench (exploration sous incertitude profonde) et Metaculus `forecasting-tools`.
Sa thèse : le mode LIRE est défendable comme méthode qualitative ; PRÉVOIR exploite une version appauvrie
de la lecture, et ses justifications mathématiques sont à corriger. Chaque point revérifié sur le code.
**Aucune probabilité ne change** (clôture identique à la 0.7.9).

### 17.1 Vérifié et retenu

| Point | Vérification | Ajouté ou corrigé | Où |
|---|---|---|---|
| F et f ont le même effet numérique | juste : sans base, 10,2079 % dans les deux cas | `variantes_codage` : p si chaque mot f, puis tous, étaient absents (exploration de codages plausibles, à la manière d'EMA Workbench, plutôt qu'un poids arbitraire) ; sur la démonstration, 6 à 22 % | `simulation.md` §1, `SKILL.md` |
| Trajectoires et événements isolés ne viennent pas d'un même modèle | juste : deux événements à 50 % reçoivent 37,5 % chacun, le statu quo 25 % | `ecart_marginales_pas1` et drapeau ; écrit : deux modèles | `simulation.md` §3, `SKILL.md` Limites |
| de Finetti ne donne pas la forme Beta-binomiale | juste : mélange de Bernoulli ; la bêta est un choix de modélisation | corrigé | `graphe.md` §3.3 |
| f et la révision utilisent les mêmes transitions | juste | écrit : lissage bayésien empirique en deux étapes ; intervalle trop étroit, surtout sur une strate pauvre | `graphe.md` §4 |
| Une inertie de 0,97 n'est pas une hystérésis | juste ; la 0.7.5 avait corrigé à tort la note qui le disait (§11.2, point 4) | corrigé : persistance, pas hystérésis ; le paramètre de contrôle n'est pas dans l'état | `graphe.md` §2.4, §11.2 |
| La matrice ne peut qu'augmenter une apparition | juste : λ = 3, 1,8, 1,2, tous > 1 | écrit en limite ; inhibitions en décision d'auteur | `SKILL.md` Limites |
| Analogie mathématique, définition formelle et transfert sont confondus | juste dans les fiches (involution, homotopie) | les trois séparées en tête des cartes | `cartes.md` |
| La décision 1b se lit comme un résultat | juste | reformulée en politique de recherche sous P1 ; deux voies exigées | `equivalences.md` §3 |

### 17.2 Ce qui attend (décisions d'auteur, `feuille-de-route.md` §1)

| Proposition | Pourquoi pas dans cette version |
|---|---|
| Distribution jointe sur quelques événements liés (pgmpy, extension probabiliste de PyCIB) | change le modèle des trajectoires et demande des dépendances que rien ne fournit encore |
| Influences défavorables (impacts négatifs de CIB, poids négatifs des cartes cognitives floues) | changerait des p : version séparée (règle de l'auteur, 0.7.3) ; et il faudrait des arêtes inhibitrices sourcées, pas inventées (`graphe.md` §2.1) |
| Similarité relationnelle (objets, rôles, liaisons typées) | même point que Gentner (§16.3) ; change la sélection des homologues, donc des p |
| Définition abstraite commune par carte, et conservation par traduction | travail de fond carte par carte ; c'est la condition de toute promotion d'une case Vide d'une strate sans agents |

### 17.3 Nuancé

Les comparateurs ne sont pas des concurrents au même titre que Wardley ou Cynefin : ce sont des
**cadres de calcul** qui ne disent rien de la vérité des modèles construits avec eux, l'audit le note
lui-même. Leur apport est de rendre les hypothèses et leurs conséquences explicites, ce qui est l'objet du
§17.1. La comparaison confirme aussi que le vocabulaire commun est à la fois l'apport propre de l'alphabet
et sa charge : CIB et les cartes cognitives choisissent leurs variables par domaine, l'alphabet doit
prouver ce qu'une carte conserve d'un domaine à l'autre. Les dépôts cités sont nommés par l'audit ; leur
contenu n'a pas été relu ici, sauf l'existence de PyCIB.

---

## 18. Unifier représentation, inférence et dynamique (0.7.14)

Note de conception versée par l'auteur le 31 octobre 2026, mesurée sur la 0.7.13. Elle propose un objet
unique — un **générateur markovien sur un espace d'états déclaré** — dont la représentation fixe le
support, l'inférence lit une marginale, et la dynamique déroule la loi ; et un ordre en quatre temps
(Déclarer, Joindre, Signer, Structurer), contraint par la règle de l'auteur : une version qui change un p
est une version séparée. Ses mesures ont été refaites : réciprocité de la matrice 12 / 8 / 46 sur 66 ;
identité logistique (p₀ = 10,2079 %) ; masse simultanée au premier pas 37,5 % ; liaisons lues : trois
types sur neuf. Toutes exactes. **Aucune probabilité ne change** (clôture identique à la 0.7.9).

### 18.1 Ce qui est souhaitable, et pourquoi

L'objet proposé est le bon pour ce projet, pour une raison que la note donne et qui tranche : **la
matrice est asymétrique par thèse** (le retour d'un SEUIL est fermé). Un champ d'équilibre exigerait de la
symétriser ; un générateur hors équilibre la garde. Le temps, levier le plus fort du calcul, y devient un
paramètre. Les comparateurs de l'audit précédent ne conviennent pas comme cadre : un réseau bayésien exige
l'acyclicité (or les rétroactions sont l'objet de l'alphabet), une carte cognitive floue ne produit pas de
probabilités. Le chantier est donc retenu **comme direction**, et réalisé ici dans sa seule partie qui ne
change aucun nombre.

### 18.2 Appliqué

| Proposition | Ce qui est fait | Où |
|---|---|---|
| Nommer l'objet, l'estimande et le quotient (§5.1) | bloc `modele` dans `calculer --json` ; drapeau pour toute liaison sans effet | `moteur.py`, `graphe.md` §2.1 |
| Table « lu / non lu » (§5.3) | publiée, dans les termes du skill | `graphe.md` §2.1 |
| Lecture en pseudo-vraisemblance ; ne pas symétriser (§2.2, §3.2) | écrite, avec l'identité logistique vérifiée | `graphe.md` §2.1 |
| Deux estimandes (§2.4, §6.3) | le noyau de `trajectoires` nommé (« premier changement ») ; `masse_simultanee_pas1` | `simulation.md` §3 |
| Noyau joint d'un pas (§6.1) | **ajouté à côté**, pas à la place : `moteur.py noyau`, frontière de 2 à 10 événements, marginales = `calculer` à 10⁻¹², exclusions déclarées par IPF, `p_horizon` et `p_premier` | `simulation.md` §3 |
| Gabarit (P, G, I) (§4) | défini, avec le critère descriptif / local / transversal, et SEUIL en exemple | `cartes.md` |

### 18.3 Corrigé ou nuancé

1. **Numéro.** La note place « Déclarer » en 0.8.0. La feuille de route réserve 0.8 aux étapes 2 et 3, et
   l'audit V34 recommandait de ne pas l'ouvrir avant le test à trois bras : 0.7.14.
2. **« Le noyau double chaque probabilité. »** À préciser : il double à peu près la masse des états **à un
   seul changement** (72,9 % contre 35,4 %), parce qu'il y reporte la masse simultanée ; la probabilité de
   chaque événement y est au contraire **plus basse** que dans `calculer` (6,0 % contre 10,2 % pour
   SEUIL@7). Les deux constats sont justes ; ils ne disent pas la même chose.
3. **Remplacer le noyau de `trajectoires`** et ne plus écrire `f` sur un mot simulé (§5.4) changent les
   probabilités des trajectoires : différé, décision d'auteur (« Joindre »). En attendant, les deux
   noyaux coexistent et la sortie dit lequel répond à quoi.
4. **Le diagnostic « champ moyen »** (§5.2) n'est pas assez spécifié pour être publié (sur quels nœuds,
   avec quelles bₖ hors de la frontière ?) : non ajouté. Le noyau joint en tient lieu sur la frontière.
5. **Invariance au découpage** (§2.5, §6.4) : la limite est déjà écrite (`graphe.md` §2.3, 10,2 % contre
   10,4 %) ; le pont exact par générateurs à deux états la lèverait, il entre avec « Joindre ».

### 18.4 Ce qui attend (feuille de route, chantier formel)

Signer (θ < 0, `manque` et `conflit` lus) ; Structurer (objet dans le mot, H1.7 par raffinage de couleurs,
Weisfeiler et Leman 1968, condition nécessaire et non suffisante d'isomorphisme) ; Mélange (codage latent,
poids mesurés par `accord`) ; hystérésis représentée (variable de contrôle mesurée, deux seuils, un sens),
seulement là où une grandeur de contrôle est sourcée ; Estimer (régression autologistique, matrice en a
priori). Les cinq critères de réfutation de la note (§13) se reprennent tels quels : un écart sous 1 point,
une masse simultanée sous `seuil_affichage`, des θ tous compatibles avec zéro, une H1.7 qui ne change
aucune classe ou des estimandes indiscernables diraient que l'étape correspondante est inutile — et
chacun se calcule déjà, ou se calculera avec les instruments de la 0.7.14.

---

## 19. Sémantique du futur : Copley (2009) et le critère de rétrospection en français (0.7.16)

Deux documents versés par l'auteur le 31 octobre 2026 : une note de lecture de B. Copley, *The Semantics
of the Future*, Routledge, 2009 (ISBN 978-0-415-97116-4, vérifié), lue intégralement sauf le chapitre 4,
survolé ; et un document de méthode qui en transpose au français le critère dit *fate-in-hindsight*. Le
livre est de sémantique formelle : il établit ce qu'**engage** une phrase sur le futur, par jugements
d'acceptabilité, sans mesure ni chiffre. Il ne dit rien de ce qui va arriver. **Aucune probabilité ne
change** (clôture identique à la 0.7.9).

### 19.1 Retenu

| Point | Vérification | Ajouté | Où |
|---|---|---|---|
| Le futur générique au passé entraîne la réalisation ; une pièce peut raconter l'issue au lieu de la précéder | juste chez Copley (p. 87-88, d'après Binnick 1971), régularité forte et non loi (sa note 23) ; en français, le conditionnel est d'abord une **reprise**, d'où deux contrôles et non un | `passage.forme` ; F refusé sur pièce rétrospective, attribuée ou non datable, avec trois motifs distincts | protocole A6, `controle_passage` |
| Un événement programmé présuppose un directeur et affirme son engagement | juste (ch. 2 : « # It rains tomorrow » est inacceptable faute de directeur, non faute de probabilité) | `programmation` {qui, engagement} exigé au dossier pour `programmee` | `simulation.md` §4, `dossier_valider` |
| `programmee` / `generique` ↔ futurate / futur générique inertiel | juste terme à terme ; `duree_de_vie` sans correspondant | correspondance écrite, avec le trou | `simulation.md` §4 |
| Les trois sémantiques temporelles suivent la propriété de sous-intervalle | juste comme correspondance | écrite en `graphe.md` §2.4 | `graphe.md` §2.4 |
| La confiance dans le futur n'est pas portée par l'ancrage | juste ; appuie la règle de 0.7.10 | une phrase à F/f | protocole A6 |
| « Inertie » : même mot, deux objets | juste | entrée de glossaire | `glossaire.md` |
| Le critère doit être éprouvé avant usage | juste, et dit par la note elle-même | épreuve d'accord sur 30 phrases au banc | `validation.md` §9 |

### 19.2 Corrigé

1. **« Copley explique pourquoi c'est la seule combinaison possible » (§5.2 de la note).** Trop fort : le
   moteur admet `presence` et `au-moins-une-fois` pour une apparition, `presence` et `continue` pour une
   persistance. La propriété de sous-intervalle **justifie les défauts**, elle ne les rend pas uniques.
2. **Règle de comparabilité « `semantique` constante dans une classe d'homologues » : refusée.** Les cas
   codés ne portent aucune sémantique (aucun champ `semantique` dans le schéma de fiche) : ce sont des
   transitions d'un pas, et la sémantique ne s'applique qu'à la composition sur l'horizon, après la
   sélection des homologues. La règle porte sur un objet qui n'existe pas.
3. **Le tiers exclu.** Il vaut pour le *futurate* (direction présupposée), non pour tout énoncé de futur :
   les futurs génériques admettent le milieu. Il appuie donc l'exigence d'une résolution tranchée pour un
   événement **programmé**, pas pour tout événement ; l'exigence générale reste justifiée par la
   décidabilité du score (S1).
4. **Pièce rétrospective ≠ pièce postérieure.** En mode CODER, les sources sont souvent postérieures à
   l'issue (historiens) : refuser F sur toute pièce postérieure fermerait le codage historique. Le refus
   porte sur la pièce qui décrit le fait **à travers son issue** ; une pièce postérieure qui le décrit sans
   la présupposer reste `prospective` (tardive). Les champs `antecedente` et `ecart_jours` proposés ne sont
   pas ajoutés : la date de la pièce est déjà contrôlée (`disponible_le`, B1).
5. **Facultatif, pas obligatoire.** La note demande `antecedente` obligatoire ; le critère n'a ni accord
   mesuré ni exemples relus par des locuteurs natifs, et l'imparfait narratif comme `devait` + infinitif
   sont indiscernables par la forme. Champ facultatif tant que l'épreuve du §9 n'est pas faite.
6. **Liens.** La note renvoie à `analyse-alphabet-situationnel.md` et `concurrents-directs.md`, absents du
   dossier versé.

### 19.3 Refusé

Les futurs ramifiés de Thomason et l'opérateur de quantification sur les mondes d'engagement dans le
moteur : quantifier sur des mondes est une opération sémantique, p est une fréquence sur des cas ; les
confondre serait l'erreur déjà refusée pour λ. Un champ `directeur` dans l'état : c'est ce que la phrase
présuppose, pas ce que la situation contient — d'où un champ de l'**événement déclaré**. Une quatrième
valeur de `temporalite` pour la rétrospection : elle décrit la pièce, non l'événement. Le chapitre 4
(conditionnels) : non lu, et le skill n'a pas de liaisons conditionnelles.

---

## 20. Évaluer une propriété sans étalon : le Digital Consciousness Model et Chandaria et al. (0.7.17)

Note versée par l'auteur le 31 octobre 2026 sur deux textes de 2026 qui évaluent probabilistiquement la
conscience des systèmes d'IA : Shiller, Duffy, Muñoz Morán, Moret, Percy et Clatterbuck, *Initial results
of the Digital Consciousness Model* (arXiv:2601.17060) ; Chandaria, Muñoz Morán, Rosas, Seth, Shevlin et
al., *From cacophony to hierarchy: a principled framework for assessing AI consciousness*
(arXiv:2609.35618). Les deux références existent (vérifié le 31 octobre) ; la note dit avoir lu le premier
jusqu'à sa section 4 et du second le résumé, la section 1 et le plan. Ce ne sont pas des concurrents : ils
ne prévoient rien. Leur intérêt est **structurel** — agréger des indicateurs dont la valeur probante
dépend de théories que personne ne tranche, sans vérité terrain. **Aucune probabilité ne change**
(clôture identique à la 0.7.9).

### 20.1 Retenu

| Point | Vérification | Ajouté | Où |
|---|---|---|---|
| Un indicateur a un support **et** une exigence | juste : définitions du DCM vérifiées sur le texte (support = sensibilité / (1 − spécificité) ; exigence = spécificité / (1 − spécificité)) | distinction écrite ; règle de mesure par arête **fixée avant les cas** | `graphe.md` §2.1 |
| Le DCM met à jour sur les **absences** | juste (vérifié : « the model updates on indicators or features that are observed to be absent ») ; le moteur ne le fait jamais | écrit en limite | `graphe.md` §2.1, `SKILL.md` |
| Un modèle de langage est anthropomimétique | juste comme argument de mécanisme (Chandaria et al., §1.4) | raison de l'exigence d'un codeur humain (A4) ; bras « modèle seul » comparateur, jamais juge | protocole A4, `validation.md` §1 |
| Problème de spécificité (Shevlin 2021, *Mind & Language*, vérifié) | juste : c'est la question du statut Proposé | nommé | `equivalences.md` §2 |
| Contraintes orthogonales à une hiérarchie | juste comme terme | note terminologique | `cartes.md` |
| Agnosticisme structuré | juste comme description ; le placebo d'homologie va plus loin que les deux textes | écrit, sans valeur de preuve | `constitution.md` §1 |

### 20.2 Corrigé dans la note

1. **La formule de mesure de l'exigence est fausse.** La note propose « p(événement | carte absente) /
   p(événement | carte présente) ». C'est une inversion du risque relatif, donc une mesure du **support**,
   pas de l'exigence. L'exigence porte sur l'indicateur quand la propriété est absente :
   P(i absent | j n'apparaît pas) / P(i présent | j n'apparaît pas). La règle écrite en `graphe.md` §2.1
   suit les définitions du DCM.
2. **« Sans exigence, une arête ne peut pas être défavorable » : non.** Un rapport de vraisemblance
   inférieur à 1 s'écrit avec un seul paramètre — le DCM a des rapports de 0,04 à 1. Ce qui interdit
   l'inhibition ici, c'est la grille λ ≥ 1 (déjà en limite depuis 0.7.13, décision d'auteur 9) ; ce qui
   manque en propre, c'est la mise à jour sur l'absence d'une carte.
3. **« Les marqueurs ne sont ni nécessaires ni suffisants (A5) : identique. »** Inexact : les tests de preuve
   (0.7.0) distinguent le cerceau (nécessaire) et le pistolet (suffisant). Le skill admet des preuves
   nécessaires ou suffisantes, à condition de les déclarer ; le DCM n'en admet aucune.
4. **« Un κ élevé entre un humain et un modèle ne mesure pas la fiabilité » :** juste, à une nuance près —
   il mesure un accord, qui n'est pas rien ; ce qu'il ne prouve pas, c'est que la lecture a eu lieu. D'où
   « se publie à part », et non « ne compte pas ».
5. **Liens.** La note renvoie à `analyse-alphabet-situationnel.md` et `concurrents-directs.md`, absents du
   dossier versé.

### 20.3 Refusé

Décomposer λ en deux paramètres dans le moteur : changerait tous les p (version séparée, et seulement
une fois l'exigence mesurée sur cas réels). Des indicateurs nombreux par propriété (206 pour une
propriété dans le DCM) : aggraverait le déséquilibre que l'audit V34 reproche déjà. Un prior uniforme
commun à toutes les questions : le skill a une fréquence de base par événement. La plage 0,01–0,8 des
deux textes comme résultat : leurs auteurs la donnent pour une sensibilité aux hypothèses, non pour une
fourchette empirique.

## 21. Les mathématiques expérimentales : quatre sortes d'expériences (0.7.18)

**Source.** Borwein, J. M., Bailey, D. H., Calkin, N. J., Girgensohn, R., Luke, D. R., Moll, V. H. (2007),
*Experimental Mathematics in Action*, Wellesley (MA), A K Peters ; référence vérifiée. La note de lecture
a lu le chapitre 1 (p. 1-26) et une partie du chapitre 6 (p. 142-150).

### 21.1 Retenu

| Point de la note | Vérification | Versé | Où |
|---|---|---|---|
| Quatre formes d'expérience (Medawar, cité p. 5-6) ; seule la galiléenne, qui peut conclure non, rend la démarche sérieuse | juste comme cadre ; « peut conclure non » est le critère de la note | classement des instruments, corrigé (§21.2) | `validation.md` §9 |
| « Étaler ses cartes sur la table » (p. 24) | juste ; c'est ce que font le dossier scellé, les sources du calcul, `garantie.support`, « non estimé » | une phrase | `constitution.md` §1 |
| Aucun des rôles du calcul liés à la visualisation n'est exercé | juste : aucune figure | sortie de données pour figures, moteur sans dépendance | `feuille-de-route.md` §7 |
| Le nombre de tests survécus est une donnée (p. 13) | juste ; rejoint la lecture séquentielle (0.7.12) | une phrase | `validation.md` §9 |
| La certitude des mathématiques expérimentales ne se transpose pas : l'arithmétique est un oracle, la prévision n'en a pas | juste | phrase de frontière | `constitution.md` §1 |

### 21.2 Corrigé dans la note

1. **« Aucune expérience critique ne porte sur la lecture ; le second codeur et κ n'existent pas. »** Faux
   sur le code : `accord` (0.7.9), `--repetabilite` (0.7.10), `rejets` (0.7.9), le banc d'essai
   (`validation.md` §9) et le test à trois bras (0.7.12) sont des expériences galiléennes sur la lecture.
   Le constat juste est plus dur : celles qui portent sur l'appareil ont été jouées, parce qu'elles
   n'exigent aucun humain ; aucune de celles qui portent sur la lecture ne l'a été.
2. **`conservativite` n'est pas une expérience** : c'est un contrôle de non-régression, comme `audit`.
3. **« Les fréquences de base sont estimées sur des cas filtrés par homologie. »** Faux :
   `frequence_de_base` porte sur toutes les transitions de la strate et de la fenêtre ; seule la révision
   utilise les homologues ; `p_sans_cartes` vaut exactement f.
4. **« L'apport des cartes est l'effet du conditionnement par homologie ; +0,7 point. »** Faux deux fois :
   l'apport des cartes vaut +10,0 points sur la démonstration, décomposé en +1,8 (sélection des homologues,
   p − p_placebo) et +8,2 (multiplicateurs et cas de la strate, p_placebo − p_sans_cartes) ; +0,7 est l'effet
   de l'abaissement F → f. La leçon du chapitre 6 — conditionner change la population — est ce que mesure le
   placebo (0.7.4).
5. **Renvois.** Au moment du tri, la note citait des documents absents du dossier versé
   (`modifications-substantielles.md`, `analyse-alphabet-situationnel.md`) ; ils sont versés depuis et triés
   au §22.

### 21.3 Refusé

Revendiquer une certitude pratique : sans oracle, le skill garde ses intervalles. Un outil de visualisation
dans le moteur : une sortie de données suffit.

## 22. Dix notes de méthode : López de Prado, stumpy, Johnson, Hardt et Recht, Galaxy Zoo, Gelman et al., Chan, un cas agricole (0.7.18)

**Sources des notes.** *Modifications substantielles* (López de Prado 2018, *Advances in Financial Machine
Learning*, ch. 4, 7, 11, 12) ; *Le gabarit de formulation* ; *Lire le langage, prévoir l'événement*
(révision 0.7.17) ; *Les concurrents directs* (révision 0.7.17) ; *Comprendre l'Alphabet situationnel*
(vulgarisation) ; *Ce que les outils d'évaluation apportent* (stumpy, tsfresh, river, alibi-detect,
giskard, promptfoo, RobustBench, ART ; Johnson 2002 ; `physics.data-an` ; Hardt et Recht 2022, ch. 8 ;
Lintott et al. 2008 ; Gelman et al., *Bayesian Data Analysis*, 3ᵉ éd., ch. 6, 8, 9 ; Chan 2026, ch. 6, 8, 9 ;
Patterson) ; *Un cas d'école mesuré : la production agricole indienne* ; et de nouvelles copies des notes
Copley, rétrospection et DCM, qui reprennent les corrections des §19.2 et §20.2 sans apport nouveau.
Chaque point a été vérifié sur le code avant d'être versé ; **aucune probabilité ne change**.

### 22.1 Retenu et versé

| Point | Vérification | Versé | Où |
|---|---|---|---|
| La base a-t-elle des répétitions ? (stumpy, matrice de profil) | **mesuré** avec la similarité du moteur, correspondances triviales exclues : 69/78 jumeaux H1, médiane 1,000, 73/78 au-dessus de 0,7 — reproduit exactement les chiffres de la note | `moteur.py voisins`, test | `graphe.md` §3.4, `SKILL.md` |
| Unicité moyenne ū (López de Prado, ch. 4) | **mesuré** : 0,705, médiane 0,5, minimum 0,25, 42/78 transitions, concurrence maximale 4 — identique à la note | publié par `voisins`, hors du calcul | `graphe.md` §3.4 |
| Le placebo rend un tricolore là où la sonde rend un centile | **constaté** : `sonde_matrice` publie `centile_reel`, `placebo_homologie` non, avec les mêmes 200 tirages | `centile_placebo`, nullité nommée ; 0,63 sur la démonstration | `graphe.md` §3.4 |
| Le centile est une p-value prédictive (BDA3 §6.3) et se lit sous une nullité nommée | juste : même formule ; un centile vers 0,5 dit que l'instrument ne trouve rien | une phrase | `graphe.md` §3.4 |
| L'empreinte de clôture publiée ne se reproduit pas (`b8d346ea…` contre `b1a592c8…`) | **non reproduit** sous Linux, Python 3.8, 3.12, 3.13, 3.14 : `b1a592c8…` partout ; la note l'obtient sous Windows, Python 3.14.3. Cause non établie (bibliothèque mathématique probable) ; la note se trompait en l'imputant au journal, qui est juste sur la plateforme de référence | empreinte **portable** ajoutée, empreinte stricte inchangée | `validation.md` §9 |
| Fiabilité n'est pas validité (Hardt et Recht) | juste : tous les instruments mesurent fiabilité, sensibilité ou intégrité | écrit | `validation.md` §10 |
| Deux sens de « reproductible » ; banc d'essai déjà résolu (Johnson 2002) | juste | écrit | `validation.md` §10 |
| Troncature et ignorabilité (BDA3 §8) | juste : l'inclusion dépend de l'issue | écrit ; compteur différé | `validation.md` §10, `feuille-de-route.md` §7 |
| Deux multiplicités ; k déclaré ; ajuster les décisions, pas les lectures (López de Prado ch. 11 ; tsfresh : BY ; Gelman) | juste ; BY retenu parce que les variantes partagent λ, inerties et demi-vie | écrit, avec le seuil pour k = 12 | `validation.md` §10 |
| Ordres de grandeur de résolution (Hardt et Recht ; Chan) | calculs refaits : √(log 12 / 10) ≈ 0,50 | écrit comme ordre de grandeur | `validation.md` §10 |
| κ à 20 cas : les deux repères ne se distinguent pas (Chan) | calcul refait : SE 0,134 à κ = 0,80, pₑ = 0,5 | écrit | `protocole.md` A4 |
| Effet Hawthorne sur la répétabilité ; refus de pondérer les codeurs par l'accord (Galaxy Zoo, +37 %) | juste, chiffres de la source | écrit | `protocole.md` A4 |
| p est l'estimateur sous perte quadratique ; pas de fonction d'utilité | juste | écrit | `validation.md` §10 |
| Contrôle positif manquant ; transformation neutre et mutation (Galaxy Zoo) | juste | écrit ; base plantée différée | `validation.md` §10, `feuille-de-route.md` §7 |
| Décroissance chronologique déconseillée par la source (López de Prado §4.7) | juste ; `demi_vie_ans` est chronologique | écrite comme choix assumé, non changée | `graphe.md` §3.4, commentaire du moteur |
| Produit des λ : pseudo-vraisemblance, non champ moyen ; pièges de l'estimation | juste | écrit | `graphe.md` §3.4, `feuille-de-route.md` §1 |
| Lu 2025 : médiane contre moyenne | **vérifié sur le texte** (v2) : o3 0,1352 / 0,1362, experts 0,0225 / 0,1573 | précision ajoutée, sans retirer la phrase du §8 | `validation.md` §8 |
| Gabarit de formulation en six questions | déduit des règles existantes (A5–A7, `temporalite`, `semantique`, `questions`, `passage.forme`) ; non éprouvé | liste facultative avant le mode PRÉVOIR | `SKILL.md` |
| Différés : poids par unicité, purge, CPCV, verdict à quatre états, codeur disqualifié, compteur des cas non résolus, fiche de base, bootstrap par cas, résultats persistants, priorisation par dispersion | chacun attend des cas réels ou change p | lignes de feuille de route | `feuille-de-route.md` §7 |

### 22.2 Corrigé dans les notes

1. **« Inverser la séquence du journal et recalculer : le geste le plus rentable. »** Pas ici : les
   probabilités sont scellées avant l'issue, et le gain moyen, le test du signe et la valeur finale de
   l'e-processus (un produit) sont invariants par permutation des épisodes ; seuls le maximum et l'épisode
   de franchissement changent. Recalculer les prévisions dans l'ordre inverse ferait entrer des cas
   postérieurs. La critique du test en marche avant est écrite (`validation.md` §10) ; le test d'inversion
   ne l'est pas.
2. **« L'inertie est un paramètre, pas un concurrent évalué » (cas agricole).** Inexact : `p_sans_cartes`
   est le comparateur inertiel, publié à chaque calcul et au journal ; c'est précisément le statu quo que
   la note demande.
3. **Décalage des notes et du code.** La note principale annonce « 151 autotests » et « 149 tests » à deux
   endroits, la sonde au 98ᵉ centile quand `graphe.md` §3.4 dit 99ᵉ : chiffres d'exécutions différentes, à
   relire sur la sortie du moteur.
4. **« Exclure les homologues triviaux dans `valider_base`. »** Sans objet pour le calcul : les homologues
   d'un état sont tirés de la base à la date d'information, l'état interrogé n'en fait pas partie, et deux
   transitions d'un même cas ne se recoupent pas. L'exclusion vaut pour le diagnostic de la base, où elle est
   appliquée (`voisins`).
5. **La note DCM, nouvelle copie.** Son §7 et son §10 maintiennent encore que l'absence d'exigence explique
   l'absence d'inhibition, corrigé au §20.2 (point 2) ; la correction est déjà versée.

### 22.3 Refusé

Embargo (López de Prado ch. 7) : inutile pour un journal chronologique. Décroissance par unicité cumulée :
changerait la sémantique de `demi_vie_ans` et toutes les probabilités. Seuil de Jaccard adaptatif :
change la classe, donc p (version séparée). MPdist sur les états : l'objet est catégoriel. Pondération des
codeurs par leur accord (Galaxy Zoo) : mesurée défavorable par la source même. Un σ tiré d'un pourcentage
d'accord : il ne tient que sous une nullité implicite. Mesures par gradient (ART) : le moteur n'a pas de
gradient. Bootstrap naïf sur les transitions : 42 des 78 partagent leurs mois. Remplacer l'intervalle bêta
par un bootstrap : ses quantiles sont exacts. Un instrument de validité : il n'existe pas de critère formel
simple ; la validité s'écrit. Le vulgarisé *Comprendre l'Alphabet situationnel* : sans règle nouvelle.

## 23. Causalité, lecture des causes et accord : dix notes du second lot (0.7.18)

**Notes triées.** *L'accord entre codeurs* (Krippendorff 2011 ; Artstein et Poesio 2008 ; Bayerl et Paul 2011 ;
Willett et al. 2013) ; *Les lois de la dynamique causale* (Coleman 1990, Ylikoski 2021, Bhaskar 1975) ; *La
causalité humaine* (Aristote, Mackie 1965, Hart et Honoré 1959, Weber 1906 ; Fein et Vossekuil 1998 ; Grabo 2002) ;
*Lire une causalité dans un texte* (Wüest 2023) ; *Le lien d'interprétation et le topos local* (Pires 1993, Mellet
2003) ; *Mesurer un construit* (Croutsche 2002) ; *Le diagnostic du flou* (Verleyen et Swiggers 2006) ; *La fausse
évidence du collectif* (Boudon 1963) ; *Causalité, causativité, transitivité* (Desclés et Guentchéva 1998) ; *L'échelle
se monte par hypothèses* (Runge et al. 2023). Vérifiés sur le code ; **aucune probabilité ne change** (clôture
identique, l'emprunt n'est pas touché).

### 23.1 Retenu et versé

| Point | Vérification | Versé | Où |
|---|---|---|---|
| PABAK n'est pas sûr sous forte prévalence | **reproduit** : `accord --a 90 --b 5 --c 5 --d 0` rendait « rapportable » avec κ = −0,053 | contrôle des absences quand la carte est la valeur fréquente ; test | `moteur.py accord`, `protocole.md` A4 |
| Publier aussi le coefficient à marges regroupées ; α de Krippendorff | exemple Meg et Owen reproduit (α = 0,095 pour 60 % d'accord brut) | π de Scott et α nominal publiés, hors verdict | `accord`, A4 |
| 0,80 est un seuil de publication ; but de la mesure à déclarer ; liste en huit points | chiffres de la méta-analyse | écrit | A4 |
| Pondération plafonnée (Galaxy Zoo 2) | juste : corrige le défaut mesuré au §22 | refus du §22 nuancé, non retiré | A4 |
| Répartition des cas par strate (Boudon) | **mesurée** : la démonstration couvre 2 strates sur 13, 40 cas chacune | `voisins` par strate | `graphe.md` §5 |
| `w_emprunt` : un poids unique pour toute distance (Coleman, Bhaskar, Boudon) | **constaté** : même poids pour toute strate source | écrit comme convention de repli ; poids par distance différé (change p) | `graphe.md` §5, `feuille-de-route.md` §7 |
| Les cartes codent la cause formelle ; typologie de Pires ; pas de carte « intention » | juste ; `dynamiques.md` dit déjà que toutes les transitions sont au barreau A | écrit | `dynamiques.md` |
| Loi de composition nommée : effets directs, monotones, sans interaction ; causation contemporaine | juste sur le code (logit additif, λ ≥ 1) | écrit | `dynamiques.md` |
| Lire un « parce que » : affirmer n'est pas établir ; contenu, épistémique, acte de parole ; parataxe et topos ; pas de biunivocité mot → carte | juste ; `passage.relation` et `passage.forme` ne disent pas le type de rapport | règles de lecture en A5 ; champs différés | `protocole.md` A5, feuille de route |
| Voulu, contrôlé, effectué (Desclés et Guentchéva, corrigeant Wüest) | juste : la paire volitif / non-volitif confond deux paramètres | écrit | A5 |
| L'échelle se monte par hypothèses ; question sans estimand refusée ; sept défis | juste | écrit | `validation.md` §10 |
| Contraintes contre sélection ; incomplétude ; régime formatif ; indicateur contre indication ; réflexivité | justes | écrits | `validation.md` §10 |

### 23.2 Corrigé dans les notes

1. **« Seize strates » (`nombre_strates` = 16)**, dans quatre notes : faux, il y en a **13** (`parametres.json`).
   Le calcul de Boudon qui en découle (« 111 états sur 16 strates, environ 7 par strate ») ne vaut donc pas ; la
   répartition réelle, mesurée, est pire : 2 strates couvertes sur 13.
2. **« L1 multiplie les marginales ; elle surestime de 62 % la démission effective. »** Le calcul ne compose pas
   des événements par produit : un composé est non estimé (« aucun produit de marginales »), et le noyau joint
   n'estime aucune dépendance. L'arithmétique de la note est juste (0,170 contre 0,275) ; elle vaut contre une
   décomposition que le skill ne fait pas. La leçon retenue : un événement à deux volontés se pose comme un
   événement (`dynamiques.md`).
3. **« Le dépôt renvoie toujours un p. »** Faux : état nul, composé, Hors domaine, calcul désarmé, abstention.
   Ce qui manque est le refus d'une question de barreau I ou C ; il est écrit.
4. **« Refuser PABAK dès que pₑ > 0,90. »** Briserait la faible prévalence, cas pour lequel PABAK a été retenu
   (0.7.9) ; le contrôle retenu porte sur la valeur rare, quelle qu'elle soit.
5. **« Une carte contestée pèse 1,5 fois plus » (`multiplicateur_bouge`).** Exact pour λ ; l'inertie de la cible
   en position `bouge` est élevée à la puissance 1,5, elle n'est pas multipliée.
6. **« 2/3 des auteurs avaient parlé de l'attaque »** est P(avoir parlé | avoir agi) ; la note le dit
   elle-même ; aucun taux d'auteurs politiques n'en découle.

### 23.3 Refusé

Une carte INTENTION, MOBILE ou DUPLICITÉ : infalsifiable ou, pour les deux dernières, à arbitrer sur cas réels
(l'accord baisse avec le nombre de catégories). Coder un acteur par ses attributs : aucun profil (Fein et
Vossekuil). Les équations structurelles et les liens bidirectionnels : la base ne les estime pas. Une théorie
du choix pour résoudre la sélection : un second dispositif. Détecter la parataxe par règles : le codeur reste
l'instrument. Les méthodes de séries temporelles de Runge et al. (PCMCI, CCM) : elles supposent des variables
continues et beaucoup d'observations.

## 24. Causes des effets, rigueur et langage estimatif : dix notes du troisième lot (0.7.18)

**Notes triées.** *Une recension et le livre qu'elle signale* (Couture 2007 sur McFalls 2006) ; *Un seul niveau de
causes* (Rama 2025, Mayr 1961) ; *La causalité en médecine* (Académie des sciences 2017 : Hill, Koch, Mayr) ; *Ce qui a
l'air rigoureux* (Zelik et al. 2007, Marrin 2013) ; *Des experts pas meilleurs qu'un modèle simple* (Salganik 2023 sur
Grossmann et al.) ; *Le langage estimatif* (Van Puyvelde 2015, ODNI 203 ; Wong 2014) ; *La méthodologie de l'analyste*
(synthèse de douze travaux, dont Ross et Tecuci et al.) ; *Le banc d'essai pour l'intuition* (Davies et al. 2021) ;
*Les effets des causes et les causes des effets* (Musio et Dawid 2025 ; Schubert 2022 sur Seifert et al.) ; *Quatre
hypothèses* (Gao et al. 2022). Vérifiés sur le code ; **aucune probabilité ne change**.

### 24.1 Retenu et versé

| Point | Vérification | Versé | Où |
|---|---|---|---|
| Confondant entre cartes : la co-occurrence n'était pas mesurée (demandée trois fois) | **mesurée** : 111 états, aucune paire toujours ensemble, CTR@6 et POL@7 au plus haut (Jaccard 0,44) | `voisins` publie la co-occurrence ; test | `validation.md` §10 |
| Une bande verbale, pas seulement un point (ODNI 203) | la sortie texte donne p à une décimale, le JSON en flottant | `bande_verbale` (colonne « probabilité »), ligne en sortie ; test | `validation.md` §10 |
| Effets des causes contre causes des effets ; bornes plutôt qu'un nombre ; médiateur contre confondant | juste ; la sortie dit déjà « ni effet d'une intervention ni ce qui se serait passé » | écrit ; bornes différées | `validation.md` §10 |
| Quatre relations compatibles avec un λ ; régime observationnel ; trois obstacles | juste | écrit ; une ligne par arête différée | `validation.md` §10, feuille de route |
| Hill comme guide de lecture, Koch comme critère du barreau I | juste | écrit | `validation.md` §10 |
| Rigueur perçue contre justesse ; aucune preuve que l'appareil améliore les réponses | juste : V4, comparateur externe et test à trois bras jamais joués | écrit | `validation.md` §10 |
| Banc d'essai pour l'intuition ; attribution ; contre-exemple construit | juste | écrit ; contre-exemples par arête différés | `validation.md` §10, feuille de route |
| Postulats d'arrière-plan, présomption ; « 0 = absence de preuve » | « présomption » absent des références, vérifié ; l'inertie en est une | écrit | `validation.md` §10 |
| McFalls (2006), seul titre sur la causalité en science politique | une recension seule | lecture à faire | `feuille-de-route.md` §7 |

### 24.2 Corrigé dans les notes

1. **« Publier une version simple à côté de la version complète » ; « un comparateur naïf manque ».** Le modèle
   simple existe : `p_sans_cartes` (la fréquence seule) est publié à chaque calcul et au journal, et le placebo
   tire des cas au hasard. Ce qui manque est de les avoir joués sur des questions résolues.
2. **« La démonstration D6 (22 %, 52 %, 76 %) converge avec Grossmann : l'horizon long est plus exact. »** Non : la
   bande d'horizon montre que p **monte** avec l'horizon (l'événement a plus de temps pour arriver) ; Grossmann
   mesure une **erreur** qui baisse. Deux grandeurs ; aucune convergence.
3. **« Le modèle de Toulmin : quatre termes sur cinq, le support (*backing*) est `attendu`, le qualificateur
   manque. »** Le support est un champ depuis 0.7.10 (`garantie.support`) ; la question du qualificateur a été
   tranchée alors : F n'est pas un modalisateur, la force de la conclusion est p et ρ (§14).
4. **« Le dépôt publie trois décimales. »** La sortie texte donne une décimale de pourcentage ; le JSON garde le
   flottant. La critique de la fausse précision vaut pour les écarts dérivés (§22).
5. **Contradiction ouverte, non tranchée.** Bhaskar (deux niveaux, contrôle dual) et Rama (un seul niveau de
   causes, deux types d'explication) sont incompatibles ; le skill ne choisit pas, il le déclare : les strates
   distinguent au moins des **questions** ; qu'elles distinguent des **causes** n'est pas établi. Chez Mayr, la
   distinction proximal / ultime est hiérarchisée, non neutre.

### 24.3 Refusé

Un score composite des critères de Hill. Une « probabilité de causation » comme nombre. « X a causé Y » dans une
sortie. Générer des états synthétiques pour élargir la base (ils testeraient le générateur). Ajouter des paramètres
pour améliorer la prévision (les modèles simples gagnent les tournois). Les techniques structurées promues comme
méthode, ou la formation des codeurs présentée comme gage de justesse (elle produit de l'usage). PCMCI, CCM,
Granger : variables continues et séries longues. Tirer un apport de la recension de McFalls.

## 25. Horizon, prévision politique et validation par des experts : trois notes du quatrième lot (0.7.18)

**Notes triées.** *L'horizon décide de la causalité* (Bruneau et Nicolaï 1994 ; recension de Michotte 1946) ; *Un
prédicteur qui survit sur douze* (Mendenhall et Ingber 2024 ; Rosenfeld et Kraus 2018) ; *Combien de voix valident un
vocabulaire ?* (Rindermann et al. ; Smith et Fieldsend 2021). Vérifiées sur le code ; **aucune probabilité ne change**.

### 25.1 Retenu et versé

| Point | Vérification | Versé | Où |
|---|---|---|---|
| Arêtes à un pas ; multi-pas mono-carte, contexte figé ; liens indirects sans chemin | **vérifié** : `transitions` (paires consécutives), `horizon_result` et `cumul` (récurrence sur la seule cible) ; le drapeau « sources et probabilités supposées fixes » existait déjà | écrit ; test du relais différé | `graphe.md` §2.4, `feuille-de-route.md` §7 |
| La causalité perçue dépend de la présentation (Michotte, par recension) | juste comme avertissement ; recension seule | rejoint A5 (topos, parataxe) | — |
| p prédit l'événement rapporté ; un prédicteur plausible sur douze survit | juste | écrit | `validation.md` §10 |
| Modèle généralisé (pas d'attribut d'acteur dans λ) ; la règle de l'acteur plutôt que sa décision | **vérifié** : λ vient de la matrice seule | écrit | `validation.md` §10 |
| 57 % comme ordre de grandeur sur la tâche la plus favorable ; « prédire jamais » | juste, tâches non comparables | écrit comme repère, non comme seuil | `validation.md` §10 |
| Un panel porte sa composition ; reconnaissabilité ≠ justesse ; double herméneutique ; huit cas idiographiques | juste ; r = 0,55 sur un objet très politisé, non transposable tel quel | écrit | `protocole.md` A4 |

### 25.2 Corrigé dans les notes

1. **« Le taux de base de chaque carte doit être en tête de sortie ; il manque. »** Il y est : `p_sans_cartes` vaut
   la fréquence de base et s'imprime d'abord (« À lire d'abord : sans cartes → avec cartes », 0.7.12) tant qu'aucun
   cas réel n'est actif.
2. **« Comparer au hasard, une phrase par sortie. »** Le placebo est ce comparateur et s'imprime avec sa plage et,
   depuis 0.7.18, son centile.
3. **« Trois décimales », « seize cartes et 111 états », « la variante à une carte ».** Une décimale en sortie texte ;
   seize cartes mais treize strates ; la variante la plus simple est `p_sans_cartes`, toujours publiée.
4. **Michotte « n'a pas été lu »** : la note le dit ; rien n'est versé qui repose sur un chiffre de Michotte.

### 25.3 Refusé

Modéliser pleinement l'acteur : il faudrait beaucoup de données par acteur. Un consensus d'experts comme preuve.
Agréger des lectures idiographiques en probabilité. Ajouter des pas à `transitions` sans instrument : rien de plus
ne serait mesuré.

### 25.4 Bilan des quatre lots

Trente-trois notes versées le 1er novembre 2026 ont été triées (§22 à §25), plus le tri des mathématiques
expérimentales (§21). Ce qu'elles ont changé dans le moteur, sans effet sur p : `voisins` (meilleur voisin, unicité,
répartition par strate, co-occurrence), centile du placebo, empreinte de clôture portable, contrôle des absences et
coefficients π et α dans `accord`, bande verbale. Ce qu'elles ont écrit : `validation.md` §10 (ce que la validation
mesure et ne mesure pas), A4 et A5, `dynamiques.md`, `graphe.md` §2.4, §3.4 et §5. Ce qu'elles ont différé : une
vingtaine de lignes de `feuille-de-route.md` §7, dont trois changeraient p (poids par unicité, poids d'emprunt par
distance, combinaison crédibilité × pertinence). La conclusion commune des quatre lots est celle du skill depuis
0.7.7 : l'instrument est construit, la mesure n'a pas commencé ; les notes l'ont rendu plus exact sur ce qu'il
mesure, non plus informé sur le monde.

## 26. Contingence et tournants : Grossetti, Elster, Druckman (0.7.19)

**Documents reçus.** La recension par Claire Champenois et Yan Dalla Pria de Michel Grossetti, *Sociologie de
l'imprévisible. Dynamiques de l'activité et des formes sociales* (PUF, 2004), dans *Sociologie du travail* 48(1), 2006,
p. 114-116, qui cite Elster (1998) ; Daniel Druckman, « Thirty-Five Years of Research on Turning Points: Insights Gained
and Gaps to be Filled », *Negotiation Journal* 36(2), 2020, p. 91-106 ; Andrew Hadfield, « Turning point: or, the wheel
has come full circle », *Textual Practice* 28(1), 2014. Lus intégralement. Le livre de Grossetti n'a pas été lu, ni
Abbott (1997), suggéré par une note extérieure d'un autre modèle, dont le reste a été jugé en majorité déjà couvert.
**Aucune probabilité ne change.**

### 26.1 Retenu et versé

| Point | Vérification | Versé | Où |
|---|---|---|---|
| Une carte est un mécanisme au sens d'Elster (conditions d'activation inconnues) ; la contingence est l'irruption d'un mécanisme plutôt qu'un autre | juste ; c'est le statut de « structures transversales candidates » (P1) | écrit | `dynamiques.md` |
| Bifurcation : enchaînement imprévisible qui produit des irréversibilités durables (Grossetti, par recension) | juste comme définition ; SEUIL et TRACE·MÉMOIRE la portent, SEUIL → TRACE est une arête forte | écrit, sans carte nouvelle | `dynamiques.md` |
| Trois échelles de passage micro → macro (temps, masse, spécialisation) | le skill n'a que le temps (fenêtre, bande d'horizon) | écrit comme limite | `dynamiques.md` |
| Tournant : précipitant, départ, conséquences ; un départ refusé n'est pas un tournant | converge avec le marqueur de SEUIL@7 (« reconnu par les parties ») | écrit ; référence d'appui, statut inchangé | `dynamiques.md` |
| 34 négociations tracées (Druckman 2001), codes de processus à fidélité inter-codeurs « acceptable » | une base de cas réels candidate pour la strate 7, la première du dossier | ligne de feuille de route ; à recoder | `feuille-de-route.md` §7 |

### 26.2 Corrigé dans la note extérieure

1. **« Ajouter une strate ou des cartes de bifurcation. »** Refusé : SEUIL et TRACE·MÉMOIRE portent la bifurcation,
   et l'accord entre codeurs baisse avec le nombre de catégories (§23).
2. **« Cartes à agents universelles » lu comme une agentivité structurelle.** Contresens : la décision 1b porte sur
   l'application aux strates sans agents des cartes qui supposent des agents.
3. **« Ajouter un champ mécanisme causal par carte ».** Il existe : `garantie` (`mecanisme`, `attendu`, `contredirait`,
   `support`).
4. **Modèle Bayo-ACE.** Non trouvé ; rien n'est versé sans source.

### 26.3 Refusé

Hadfield (2014) : un essai sur les études littéraires (Eagleton, Leavis) dont seul le titre parle de tournant ; sans
objet. Une carte « bifurcation » ou « contingence » : elle ne serait reconnue qu'après coup. Les cartes cognitives
floues et le modèle de la fronce par ensembles flous : déjà comparés et écartés (§17 ; `concurrents`, théorie des
catastrophes).

## 27. Grossetti lu dans le texte : formes de l'imprévisibilité, irréversibilités, échelles (0.7.20)

**Documents reçus.** Michel Grossetti, *Sociologie de l'imprévisible. Dynamiques de l'activité et des formes
sociales*, PUF, 2004 (version auteur déposée sur HAL, halshs-00715823, environ 71 000 mots, lue pour les
chapitres 1, 2 et 4 et le début du chapitre 3) ; « L'imprévisibilité dans les parcours sociaux », *Cahiers
internationaux de sociologie* 120, 2006, p. 5-28 ; « Éléments de discussion pour une sociologie des
bifurcations », communication au colloque « Anticipation », 2003 ; « L'espace à trois dimensions des phénomènes
sociaux. Échelles d'action et d'analyse », *SociologieS*, 2011 ; Yann Bérard, « Quand l'événement structure »,
recension de Bessin, Bidart et Grossetti (dir.), *Bifurcations*, La Découverte, 2010. Le fichier de l'article
de 2006 porte en page de garde la notice HAL d'un autre texte (halshs-00476374, « Lien social et réseaux
économiques chez les migrants internationaux ») : le contenu est bien celui des *Cahiers*. Le §26 avait été
écrit sur une recension ; ce paragraphe ne le retire pas, il le complète et le corrige sur un point.
**Aucune probabilité ne change.**

### 27.1 Retenu et versé

| Point | Vérification | Versé | Où |
|---|---|---|---|
| Moment prévu ou non × issues délimitées ou non : carrefour, transition programmée, risque anticipé, crise | juste ; la numérotation des cases diffère entre 2004 et 2006, on les cite par leur nom | correspondance avec `temporalite` et l'événement déclaré ; la crise n'a pas d'estimande | `simulation.md` §4 |
| Risque anticipé : imprévisible pour la personne, routinier au niveau agrégé | juste ; c'est le niveau de la fréquence d'homologues | écrit ; raison de plus de ne rien décider sur une personne | `simulation.md` §4 |
| Une crise se resserre souvent en carrefour ; une situation change de case | juste | moment où une prévision devient rédigeable ; indicateur de bascule | `simulation.md` §4 |
| Imprévisibilité × irréversibilité : routine, risque sans conséquence, rituel, bifurcation | juste ; distingue SEUIL prévisible et bifurcation | écrit | `dynamiques.md` |
| Risque sans conséquence (« évité de justesse ») | pendant du cas sans événement ; `sans_evenement: true` reste plus strict | écrit | `base-de-cas.md` §4 |
| Le niveau choisi fixe la case (reproduction du système, bifurcation du parcours) | juste ; S1 fixe le niveau | deux niveaux ne sont pas homologues | `dynamiques.md` |
| Crise par recouvrement de contextes (travail, famille, santé), à la Cournot | qualitatif ; appuie l'abaissement entre strates sans en régler la taille | écrit | `dynamiques.md` |
| Généralité = variété des contextes impliqués (2011) | corrige la phrase de 0.7.19 : le nombre de strates touchées en est une mesure grossière | correction ajoutée à côté du texte de 0.7.19 | `dynamiques.md` |
| Alternatives non réalisées, rationalisation des témoignages, point d'arrêt de la remontée, ralenti, continuité | juste ; le ralenti est incompatible avec les fenêtres égales (B1) | quatre précautions de codage | `base-de-cas.md` §3 |

### 27.2 Corrigé dans le texte du skill

1. **« Le skill n'a que le temps » (0.7.19).** Trop fort : il a aussi, en gros, la généralité, par le
   nombre de strates qu'un épisode touche. Il n'a pas la masse des acteurs.
2. **« Le livre de Grossetti n'a pas été lu » (§26).** Vrai en 0.7.19 ; il l'est en 0.7.20, en version
   auteur. La ligne de lecture de la feuille de route est complétée, pas effacée.

### 27.3 Refusé ou différé

- **Une case « forme d'imprévisibilité » dans la fiche ou le journal.** Utile pour comparer plus tard les
  scores par forme ; mais c'est un champ nouveau, que personne n'a encore codé à deux. Différé à la feuille de
  route (§7), comme les autres champs sans accord mesuré.
- **Les commencements comme règle** (une transition plus probable au début d'une entité). Hypothèse de
  Grossetti, illustrée, non chiffrée ; la règle changerait p. Différé.
- **Les opérateurs d'échelle comme sous-commandes** (reproduction, agrégation, sédimentation, montée en
  généralité). Ce sont des descriptions de la forme d'un changement, pas des estimateurs ; le skill n'a pas
  de cas pour les distinguer. Écrit comme vocabulaire de lecture seulement.
- **Encastrement et découplage** (chapitre 3, Polanyi et Granovetter). Lus en partie ; ils décrivent le
  rapport entre sphères d'activité, que la grille porte déjà par la strate et les liaisons. Rien de
  vérifiable à verser sans lecture complète du chapitre.
- **Recension de *Bifurcations*** (Bérard) : trois réserves (statut de l'entretien rétrospectif, absence de
  l'événement médiatique, diagnostic de « société de bifurcation » non tranché). La première est déjà
  couverte par `classe_source: memoire` ; les deux autres sont hors du domaine du skill.

## 28. Simmel, Durkheim et Ramos : formes, objection, événements critiques (0.7.21)

**Documents.** Déjà reçus : Howard Ramos, « Sociology in Existential Times », *Society* 62, 2025, p. 809-820 ;
Isaac E. Catt, « Unsuspected Realms of the Stranger in Semiotics, Semiosis, and Communication », *Semiotics*
2001. Trouvés et lus : Georg Simmel, « The Number of Members as Determining the Sociological Form of the
Group », *American Journal of Sociology* 8, 1902, parties I et II (Mead Project, Brock University ; la fin de
la partie I n'a pas été lue) ; Émile Durkheim, « La sociologie et son domaine scientifique » (1900), dans la
traduction espagnole de *Sociológica* 17(50), 2002 ; Howard Ramos, « Opportunity for Whom? Political
Opportunity and Critical Events in Canadian Aboriginal Mobilization, 1951-2000 », *Social Forces* 87(2), 2008 ;
Ronald S. Burt, « Structural Holes and Good Ideas », *American Journal of Sociology* 110(2), 2004 (lu en
partie). L'article de Cantó-Milà (2018) sur les formes chez Simmel, cité par Ramos, n'a pas pu être ouvert
(accès refusé). **Aucune probabilité ne change.**

### 28.1 Retenu et versé

| Point | Vérification | Versé | Où |
|---|---|---|---|
| Une même forme dans des contenus différents (Simmel 1902) | juste ; c'est l'hypothèse P1 des cartes transversales | écrit comme filiation | `protocole.md`, A2 |
| Les quatre objections de Durkheim : séparation non prouvée, niveau de coupe arbitraire, exemples au hasard, preuve par exemples | juste ; elles valent pour les seize cartes de départ, qui n'ont pas suivi A2 | objection écrite comme ouverte, réponse par la mesure | `protocole.md`, A2 |
| Le tiers : médiateur, *tertius gaudens*, *divide et impera* ; avantage perdu quand les deux s'unissent | juste ; lit des transitions et un indicateur de POLARITÉ déjà écrits | écrit, sans changer de force | `dynamiques.md` |
| Courtage mesuré (Burt 2004) | une entreprise, 673 managers ; appui de structure pour RÉSEAU, pas une fréquence | écrit comme appui | `dynamiques.md` |
| Événements critiques (Ramos 2008) : trois années (1969, 1982, 1990) choisies par l'auteur ; effets « modestement soutenus », non robustes selon la spécification ; une seule source de presse | confirme deux règles du skill : pas de carte « bifurcation » reconnue après coup (§26), et la sélection par la presse (`classe_source`, Weidmann 2016) | écrit ici, sans règle nouvelle | §28 |

### 28.2 Corrigé dans la lecture de Ramos (2025)

1. **« Les menaces existentielles sont des tournants. »** Ramos l'affirme sans le montrer : son article
   est un essai sur la discipline. Pour le skill, qu'un problème soit **cadré** comme menace existentielle est
   un fait sur le discours (A5), non un fait sur le monde, ni un tournant.
2. **Les cinq « lentilles » de la sociologie** (formes, processus, mécanismes, distributions, acteurs). Le
   skill les a toutes, à des degrés inégaux : cartes (formes), transitions (processus), `garantie.mecanisme`,
   fréquences (distributions), `option.acteur` (acteurs, le plus faible). Rien à ajouter.

### 28.3 Refusé

- **Catt (2001).** Sémiotique de l'« étranger » appliquée au profilage racial ; la figure de l'étranger de
  Simmel y est mentionnée de loin. Hors du domaine du skill, qui ne décide rien sur une personne
  (`constitution.md` §6).
- **Une carte « tiers » ou « dyade ».** La triade se lit avec POLARITÉ, RÉSEAU et HIÉRARCHIE ; une carte de
  plus baisserait l'accord entre codeurs (§23) et n'a ni lacune au journal ni passage par A2.
- **Le seuil du nombre** (le passage de deux à trois change tout, au-delà moins). Juste chez Simmel, mais le
  skill ne compte pas les acteurs (§27 : pas d'échelle des masses).

## 29. Deux relectures du protocole de validation (0.7.23)

**Documents.** Un audit par une IA de recherche scientifique (amass), sur extraits du dépôt, puis sa relecture de
`validation.md` §8 et §10 et de A4 ; une seconde relecture, par un autre modèle, qui a tiré le dépôt au commit
`5835739` et vérifié le code. **Aucune probabilité ne change.**

### 29.1 Retenu et versé

| Point | Vérification | Versé | Où |
|---|---|---|---|
| Personne n'est désigné pour coder les états de V4 | confirmé (§8, étape 2) | un humain, sur dossier scellé, aveugle à p | `validation.md` §11 |
| La répétabilité est conçue pour un humain | confirmé ; `variantes_codage` ne mesure pas le bruit | `accord --llm` ; protocole k exécutions, paraphrases, versions | `moteur.py accord`, §11 |
| `p_sans_cartes` garde la cible et l'état codé | confirmé dans `apriori` | bras « dossier neutre » ; deux niveaux, interne et externe | §11 |
| Le placebo n'est pas un bras scoré | confirmé (pas de `brier_placebo`) | placebo listé comme bras | §11 |
| Les abstentions sont retirées avant le score | confirmé (`score_result`) | `couverture` : repli sur la fréquence de base, taux de repli, Brier avec repli | `moteur.py scorer`, §11 |
| Pas de critère primaire, pas de marge d'équivalence | confirmé | e-processus pour le gain, TOST à δ = 0,025 pour l'absence d'apport ; test du signe descriptif | `v4.decision`, §11 |
| Autocorrélation sans règle | confirmé | barrière ρ̂₁ > 0,3 | `v4.decision`, §11 |
| PABAK sans intervalle | confirmé | `pabak_intervalle_95_approche` ; « non évaluable » sous 82 décisions | `moteur.py accord`, §11 |
| Pas de test de leurres | confirmé | protocole en quatre points | §11 |
| Exécution par des tiers | absente pour V4 | exigée, ou publication « exécuté par l'auteur » | §11 |

### 29.2 Corrigé dans les relectures

1. **Seuil d'échec du codage à 0,40** (proposition faite ici même, avant la seconde relecture). Retiré au profit
   de la règle existante (verdict au moins `provisoire`, 0,67) : 0,40 aurait admis en V4 un codage qu'`accord`
   refuse.
2. **Effectif d'équivalence** calculé avec z = 2,80 dans la seconde relecture : la formule du TOST demande
   z₁₋α + z₁₋β/₂ = 2,93 ; à σ(d) = 0,10, 138 épisodes et non 125.
3. **Comparer à DIAMONDS** (premier audit) : refusé. DIAMONDS décrit la perception individuelle d'une situation
   et ne produit ni transition ni probabilité ; il n'a rien à scorer sur une question de prévision. Le comparateur
   parcimonieux est l'inertie.

### 29.3 Ce qui reste hors du moteur

Le bras dossier neutre, la dispersion de p entre exécutions d'un modèle, le test de leurres et la confirmation
humaine d'un état proposé par un modèle sur un dossier : des règles écrites, non calculées.

### 29.4 Troisième relecture (0.7.24)

amass, sans avoir pu lire le §11, a listé dix endroits où une décision pouvait se prendre après coup. Tous sont
fermés au §11.8 ; deux ont demandé du code (`v4_effectif_equivalence`, fixé une fois ; issues de `v4.decision`
complétées : contradiction, plancher de `v4_n` épisodes). **Corrigé dans le texte envoyé à amass** : le chiffre de
125 épisodes venait de la seconde relecture, par un autre modèle, non d'amass ; le §29.2 l'attribue bien à la
seconde relecture. **Constat** : aucune carte n'a d'accord mesuré, donc V4 ne peut pas commencer.

### 29.5 Quatrième relecture (0.7.25)

amass, sur le §11 complet : huit marges, toutes retenues et fermées au §11.9. Le contraste confirmatoire devient
conjoint (dossier neutre, inertie, placebo, test d'intersection-union) ; les bras d'un modèle de langage sont
figés ; les leurres viennent du même dossier, cartes permutées ; les conclusions nomment H0 et le seuil ; hors
liste et abstention reçoivent le même repli, et le d̄ primaire est celui avec repli (`couverture.v4_avec_repli`) ;
une fiche d'étude horodatée porte les valeurs absentes ; le tiers exécute le score et les leurres et recode 20 %
des états ; plafond de 300 épisodes. **Corrigé chez amass** : l'e-processus teste déjà H0 « gain < 2,5 points »
(§5), il ne pouvait pas le voir sans ce paragraphe ; le libellé, en revanche, était à reprendre. **Corrigé chez
nous** : l'exemple de la marge de 1 point (862 contre 138).

### 29.6 Cinquième relecture (0.7.26)

amass, sur le §11.9 : sept marges, toutes retenues et fermées au §11.10 (ordre des opérations horodaté, le tiers
calcule p ; accord prospectif groupé ; puissance conjointe à 93 % par contraste, 192 épisodes ; équivalence
nommée ; cas mixtes ; même réécriture pour la lecture réelle et le leurre ; graine publique ; dilution et taux
d'abstention maximal ; plafond limité à l'équivalence ; justification de l'écrêtage). **Corrigé chez nous, en
vérifiant sa question sur le placebo** : `p_placebo` ne permute pas les cartes, il tire des cas au hasard à la place
des homologues ; la conjonction tient, sa justification du §11.9 était fausse.

### 29.7 Sixième relecture (0.7.27)

amass, sur le §11.10 : six marges, retenues au §11.11. La plus lourde est juste : les trois p sont emboîtés
(inertie ⊂ placebo ⊂ alphabet). L'ancienne conjonction exigeait que le seul choix des homologues apporte 2,5
points. **Remplacée** : contrastes confirmatoires alphabet − inertie (effet total des cartes) et alphabet −
dossier neutre ; décomposition par le placebo, descriptive ; 171 épisodes à σ = 0,10. Aussi : équivalence exigée
sur l'ensemble avec repli et sur les seules codées ; critère par carte et bootstrap sur les états pour l'accord
prospectif ; seul le tiers s'abstient ; carte hors liste retirée de l'état plutôt que convertie en abstention ;
modèle à poids ouverts hébergé par le tiers ; réécriture aveugle et contrôle positif des juges.

### 29.8 Septième relecture (0.7.28)

amass, sur le §11.11 : six marges, retenues au §11.12. La première est juste dans sa conséquence et a demandé du
code : un quatrième p, l'**inertie de strate** (mêmes tirages que le placebo, p₀ = f, sans λ), qui donne la vraie
ablation des cartes à base de cas égale. **Corrigé chez amass** : f n'est pas une référence extérieure à la base,
c'est la fréquence de la strate contractée avec k₀ = 20 ; l'écart vient de k et du tirage, non de l'absence de base.
**Mesuré** sur la démonstration : 5,5 des 9,9 points d'écart alphabet − f viennent du tirage, sans carte. Aussi :
courbe de puissance du gain publiée (zone grise de 2 à 4,5 points) ; conclusion négative sur un contraste désigné ;
fréquences données au dossier neutre et modèle nommé ; taux de manque par bootstrap ; barème des abstentions ;
indépendance du tiers déclarée.

### 29.9 Huitième relecture (0.7.29)

amass, sur le §11.12 : aucune décision ouverte après coup, cinq marges de lecture, retenues au §11.13. Deux énoncés
séparés (cartes, appareil) avec la table des quatre issues, au lieu d'une conjonction qui contredisait le §11.12 ;
l'énoncé négatif devient une non-supériorité unilatérale, plus un énoncé de nuisance (`v4.decision`) ; puissance par
énoncé, σ par contraste ; ce que « pas d'apport > 2,5 » n'exclut pas, et la raison du seuil ; troncature différentielle.
amass recommande d'arrêter la boucle avec lui seul : retenu, une relecture par un méthodologue extérieur et par le tiers
devient une condition de l'épisode 1.

### 29.10 Neuvième relecture (0.7.30)

amass, sur le §11.13 : aucune marge de décision, deux précisions de formulation, versées au §11.14 (le paramètre
`v4_effectif_equivalence` fixe le point de lecture d'une non-supériorité ; erreur contrôlée par énoncé, énoncés publiés
ensemble). La boucle de relecture s'arrête là, comme le §11.13 le prévoit.

## 30. Attribution contrefactuelle dans un évaluateur déterministe : *Agent-Causality* (0.7.31)

**Document.** V. K. Mogia, « Agent-Causality: Declared Dependency Tracing and Counterfactual Sensitivity Analysis for
Multi-Agent Systems », Psionics, 2026 ; lu en entier. Préprint d'ingénierie ; preuves faibles, déclarées par l'auteur.
**Aucune probabilité ne change.**

| Point | Vérification | Versé | Où |
|---|---|---|---|
| Rejouer un évaluateur déterministe en remplaçant ses entrées ; Shapley et interaction par paire | transposable : le moteur est déterministe, un état a peu de mots | `attribuer` (2ⁿ calculs, n ≤ 8) | `moteur.py`, `validation.md` §12 |
| L'interaction mesure une sensibilité conjointe, pas une causalité | même discipline que le skill | écrit | §12 |
| Quatre formes (seule, l'une ou l'autre, conjointe, dépendante) | lues comme formes du calcul | écrit | §12 |
| Ascendance structurelle ≠ influence ; lien exact ou grossier quand une valeur passe par un modèle | déjà présents en substance (`liaisons` et preuves ; codeur `modele` à confirmer) | rien de nouveau | — |

**Refusé** : la capture d'événements, les adaptateurs et l'étude de l'incident Replit, propres aux pipelines d'agents ;
le découpage minimal par *delta debugging*, sans objet sur des états de quelques mots.

## 31. Audit pratique de DeepSeek V4 (0.7.32)

**Document.** Audit de la 0.7.31 sur clone, contrôles exécutés. Treize pistes, classées P0 à P3. **Aucune probabilité ne
change.**

| Piste | Vérification | Décision |
|---|---|---|
| P0.1 `recolter` | manquait | versé (carnet, brouillon de dossier) |
| P0.2 grille A–F × 1–6 | `classe_source` et `independance` existaient, pas la grille | versée, facultative, contrôlée pour F |
| P0.3 saisie des cas réels, fichier Druckman pré-rempli | impossible sans lire et coder les sources | différé |
| P1.4 `depouiller` | A4 le disait différé | versé |
| P1.5 rapport Markdown | utile, non bloquant | différé |
| P1.6 registre des sceaux chaîné | `partage.jsonl` et sceaux existent, pas de chaînage | différé |
| P1.7 sceau d'adjudication | la règle est déjà scellée dans le dossier | contenu exigé écrit (`validation.md` §13) |
| P2.8 provenance des sorties | **déjà présente** (`contexte.empreintes`) | rien |
| P2.9 test cp1252 de tous les glyphes | correction déjà générale, test limité | test étendu à `accord` |
| P2.10 rapport d'écarts | `confronter` le contient en partie | différé |
| P3.11 table ACH | questions discriminantes existantes | différé |
| P3.12 import de fréquences CSV | méthodologie prête, outil absent | différé |
| P3.13 pas de web, d'API ni de modèle branché | conforme à la posture | retenu comme règle |

## 32. Druckman (2001) lu : le corpus des 34 négociations (0.7.33)

**Document.** Daniel Druckman, « Turning Points in International Negotiation: A Comparative Analysis », *Journal of
Conflict Resolution* 45(4), 2001, p. 519-544 ; numérisation sans couche texte, lue par reconnaissance de caractères.
**Aucune probabilité ne change.**

**Ce que l'article contient.** 34 cas : 13 de sécurité, 11 politiques (environnement compris), 10 commerciaux ; 30 tirés
des *Pew Case Studies in International Affairs* (1999) par un tirage stratifié par région et par type, **avec
remplacement** quand un cas manquait de détail chronologique ; 2 des *Foreign Relations of the United States* (1942,
1946) ; 2 d'études antérieures de l'auteur. Environ 110 tournants codés en trois temps (précipitant procédural,
substantiel ou extérieur ; départ abrupt ou non ; conséquence escalatoire ou désescalatoire). **L'unité d'analyse est
le cas, non le tournant**, parce que les tournants d'un même cas ne sont pas indépendants : c'est la règle du skill
(`graphe.md` §3.1, un cas pèse au plus une observation).

**Correction du §26 (0.7.19).** Le tableau du §26 attribuait aux codes de ce corpus une « fidélité inter-codeurs
acceptable ». L'article ne le dit pas. Les 34 cas internationaux ont été codés par des étudiants (deux cas chacun),
revus par l'auteur et son assistant, qui ont confirmé ou réduit les séquences, puis fixés **par consensus** (à la façon
d'un panel Delphi). Aucune mesure d'accord indépendant n'est publiée. Seuls les 11 cas de négociations sociales du
transport aérien, en fin d'article, ont été codés par deux analystes indépendants, sans statistique rapportée. Les codes
de Druckman ne peuvent donc servir ni de second codeur (B3) ni de faits : ce sont des lectures consensuelles.

**Ce qui se transpose, et à quelle condition.**

| Point | Lecture | Versé |
|---|---|---|
| Cadre d'échantillonnage : 34 cas, trois types, sources nommées | une liste tirée selon une règle publiée avant codage, au sens du §11.8 ; mais **les faits sont dans les études Pew**, non dans l'article, qui ne donne que six cas en annexe, sans dates ni sources assez détaillées | feuille de route : obtenir les études Pew avant toute saisie |
| Sécurité : 12 cas sur 13 à précipitant surtout extérieur ; commerce et politique, surtout intérieur (χ² = 15,36, ddl 2, C = 0,67) | converge avec SEUIL@7 et la propagation depuis une autre strate ; un constat sur 34 cas, non une fréquence par fenêtre | écrit ici |
| 75 % des conséquences sont désescalatoires ; une escalade est suivie d'une désescalade dans 20 séquences sur 25 (17 cas) | fréquences **par tournant**, non par fenêtre de 3 mois : unités incompatibles avec `calculer` (`frequences-externes.md`) ; corpus biaisé vers les négociations documentées, souvent conclues (médiation : 6 accords sur 9) | référence d'appui seulement, aucun chiffre versé |
| Négociations sociales aériennes : escalades répétées avant accord, que l'auteur attribue au cadre légal américain | même forme de tournant, dynamique opposée selon le cadre institutionnel : un argument pour des fréquences par strate et pour l'abaissement entre strates | écrit ici |
| L'auteur lui-même : la population des cas ne se définit que par les cas documentés, et l'on manque les cas non documentés ou classifiés (le « tiroir », Rosenthal 1984) | c'est le biais de troncature déclaré au §10 de `validation.md` | écrit ici |

## 33. Audit Open Science de la 0.7.33 (0.7.34)

**Verdict de l'audit.** Ingénierie et discipline remarquables, programme de recherche non testé ; un appareil statistique
qui paraît plus scientifique que ses preuves. **Retenu** : l'affichage honnête des probabilités, le périmètre réduit à la
strate 7, la docstring et son contrôle, et le gel (`validation.md` §14). **Corrigé chez l'audit** : les équivalents de la
strate 1 (physique) ne sont pas des métaphores ; la strate 7 cite ses références. **Déjà reconnu par le skill** : base
empirique nulle (`bilan`), paramètres posés à la main (`graphe.md` §2.1, « hypothèses de travail »). **Non retenu
maintenant** : découper `moteur.py` en paquet ; le fichier unique sans dépendance est un choix de distribution du skill, et
le découpage serait encore du travail sans mesure.

## 34. Vue extérieure et contrôle prédictif a priori (0.7.35)

Demande de l'auteur, sur deux sources connues : Tetlock et Gardner (2015), la « vue extérieure d'abord » ; McElreath
(2020), le contrôle prédictif a priori. **Retenu**, comme champ requis du dossier (`vue_exterieure`) et comme refus de
chiffrer quand p₀ s'écarte de plus d'un facteur 10 en cotes du taux de base déclaré (`validation.md` §15). **Limite
déclarée** : sans loi sur les paramètres, le contrôle est ponctuel, non une simulation. **Aucune probabilité ne change**
sur la clôture, qui n'utilise pas de dossier ; un calcul avec dossier peut désormais rendre « non estimé ».
