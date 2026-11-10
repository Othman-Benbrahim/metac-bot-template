# Alphabet situationnel — Dynamiques des cartes (couche 4, a priori)

> Version : 0.7.56

> Ce que chaque structure **tend à produire au pas suivant**, proposé comme hypothèse à partir de sa représentation structurelle.
> Ces intensités **modulent** une fréquence de base (T2) : elles ne sont pas des probabilités. Valeurs
> numériques : `protocole.md` §H ; procédure : `graphe.md` §2. La matrice et les inerties de ce fichier
> sont recopiées à l'identique dans `assets/parametres.json`, que lit le moteur ; `moteur.py audit`
> vérifie l'égalité.
>
> **Statut : hypothèses structurelles non calibrées.** Aucun effet inhibiteur n’est estimé dans la
> matrice actuelle ; comparer systématiquement avec la référence sans cartes. Chaque ligne dit une hypothèse de mécanisme associée à la
> carte, avec un mécanisme. Aucune ligne n'est encore vérifiée par la base de cas. La
> couche 6 les corrige (V3) ; une ligne systématiquement démentie est révisée.

---

## 0. Lecture des fiches

- **Inertie** : probabilité a priori que la carte reste ancrée **sur 3 mois** (fenêtre de référence),
  **valeur propre à chaque carte** (§Inerties) ; le moteur la ramène à la fenêtre de l'état. Sa disparition a la probabilité complémentaire.
- **Transitions** : événements que la carte rend **plus probables** au pas suivant, avec une intensité
  (forte F / moyenne M / faible f) traduite en multiplicateur hypothétique λ (§H), et le mécanisme. Sauf mention, l'événement se produit **dans la même
  strate** ; « autre strate » signale une propagation possible (G3, transfert).
- **Indicateurs de bascule** : faits observables qui annoncent la transition. Ils servent à remplir
  le champ « indicateur de bascule » des prévisions (S1).
- **Entrées** : cartes qui mènent le plus souvent à celle-ci (lecture inverse des transitions).
- Les transitions vers « retour à l'état antérieur » ne sont listées que lorsqu'elles sont
  structurellement improbables (SEUIL) ; ailleurs, elles sont couvertes par l'inertie.
- **Paires mutuelles (0.7.56, §33).** La matrice contient dix paires A → B et B → A (20 arêtes sur 66) : SEU↔TRA,
  SEU↔TRC, PER↔SEU, EME↔RES, HIE↔POL, POL↔REC, CTR↔INC, CRO↔EME, CRO↔RES, COM↔REC. Elles se lisent **d'un pas au
  suivant** (A en *t* rend B plus probable en *t+1*, et réciproquement) : le graphe déplié dans le temps est
  acyclique, et le moteur calcule **un pas**, par arêtes directes, sans chaînage. Une boucle **dans un même état**
  (un équilibre où deux structures se tiennent mutuellement) n'est **pas** couverte : si une lecture la suppose, elle
  l'écrit comme une hypothèse d'équilibre, hors du calcul.

---

## SEUIL ⊥
- **Inertie** : 0,97 (forte) — par définition, le retour par le même chemin est fermé.
- **Transitions** :
  - TRACE·MÉMOIRE apparaît — **forte** — le franchissement laisse un résidu qui conditionne la suite
    (inclusion SEUIL ⊂ TRACE).
  - TRANSFORMATION apparaît — **moyenne** — l'entité se réorganise dans le nouveau régime.
  - SEUIL apparaît dans une autre strate — **moyenne** — propagation d'une irréversibilité (défaut
    économique → rupture diplomatique).
  - PÉRIODICITÉ apparaît — **faible** — nouveau régime cyclique après bifurcation.
  - Retour à l'état antérieur par le même chemin — **non documentée** (exclu par la définition).
- **Indicateurs de bascule** (avant franchissement, observés sur les cartes d'entrée) : retour plus
  lent après une perturbation (ralentissement critique), variance et autocorrélation croissantes,
  oscillations entre deux états.
- **Entrées** : CROISSANCE, CONTRAINTE qui se resserre, POLARITÉ en escalade, RÉCURSIVITÉ (panique),
  RÉSEAU (cascade), RÉSONANCE (amplification).

## RÉCIPROCITÉ ⊗
- **Inertie** : 0,65 (moyenne) — la boucle se maintient tant que les retours suivent.
- **Transitions** :
  - POLARITÉ apparaît — **moyenne** — un non-retour déclenche la rétorsion (réciprocité négative,
    donnant-donnant en spirale).
  - HIÉRARCHIE apparaît — **moyenne** — une dette qui ne peut être rendue crée une dépendance
    (relation patron-client).
  - SEUIL apparaît — **faible** — rupture définitive de la relation.
  - COMMUNAUTÉ apparaît — **faible** — élargissement à plus de deux parties.
- **Indicateurs de bascule** : un transfert non rendu à l'échéance d'usage ; rappel explicite d'une
  dette ; retard croissant des contre-transferts.
- **Entrées** : COMMUNAUTÉ qui se fragmente, POLARITÉ en désescalade négociée.

## PÉRIODICITÉ ↻
- **Inertie** : 0,90 (forte) — un cycle limite est stable ; la phase suivante est la transition la plus
  probable.
- **Transitions** :
  - Phase suivante du cycle (même carte, phase avancée) — **forte**.
  - RÉSONANCE apparaît — **moyenne** — couplage avec un autre cycle.
  - SEUIL apparaît — **faible** — un forçage externe brise le cycle.
- **Indicateurs de bascule** : dérive de la période, amplitude croissante, phase manquée.
- **Entrées** : SEUIL (nouveau régime cyclique), CONTRAINTE à échéance fixe, TRACE·MÉMOIRE (rite).

## RÉCURSIVITÉ ↺
- **Inertie** : 0,65 (moyenne) — l'auto-représentation persiste tant qu'elle est diffusée.
- **Transitions** :
  - CROISSANCE {rétroaction amplifiante} apparaît — **moyenne** — prophétie autoréalisatrice.
  - SEUIL apparaît — **moyenne** — une représentation partagée déclenche un basculement (panique,
    retrait massif).
  - CONTRAINTE apparaît — **faible** — l'indicateur détourné est encadré par de nouvelles règles.
  - Disparition — **faible** — prophétie autodestructrice : la prévision publiée annule ce qu'elle
    annonce.
- **Indicateurs de bascule** : publication très diffusée d'une mesure, notation ou prévision ;
  changement de comportement immédiat des acteurs mesurés.
- **Entrées** : HIÉRARCHIE (classements), RÉSEAU (diffusion), INCERTITUDE (recherche de signaux).

## ÉMERGENCE ⊙
- **Inertie** : 0,65 (moyenne) — une régularité naissante reste fragile.
- **Transitions** :
  - TRACE·MÉMOIRE apparaît — **forte** — verrouillage par adoption auto-renforcée.
  - CROISSANCE apparaît — **moyenne** — diffusion par imitation.
  - HIÉRARCHIE ou CONTRAINTE apparaît — **moyenne** — institutionnalisation, codification.
  - Disparition — **faible** — la régularité ne trouve pas d'adoptants.
- **Indicateurs de bascule** : taux d'adoption ; premiers acteurs qui défendent la régularité ;
  première mise par écrit.
- **Entrées** : INCERTITUDE (une forme tranche entre des possibles), RÉSEAU (interactions locales
  denses), CROISSANCE (changement d'échelle).

## HIÉRARCHIE ✦
- **Inertie** : 0,88 (forte) — un ordre de préséance se reproduit.
- **Transitions** :
  - POLARITÉ apparaît — **moyenne** — contestation, surtout au moment d'une succession.
  - TRANSFORMATION apparaît — **faible** — réforme de l'ordre, sommet conservé.
  - SEUIL apparaît — **faible** — renversement.
- **Indicateurs de bascule** : succession ouverte ou incertaine ; perte d'une ressource par le
  sommet ; défections d'échelons intermédiaires.
- **Entrées** : RÉCIPROCITÉ (dette), COMMUNAUTÉ (garant), POLARITÉ (un pôle l'emporte), ÉMERGENCE
  (institutionnalisation).

## RÉSEAU ⊛
- **Inertie** : 0,90 (forte) — une topologie change lentement.
- **Transitions** :
  - PROPORTION apparaît (concentration) — **moyenne** — attachement préférentiel vers les nœuds
    centraux.
  - SEUIL apparaît — **moyenne** — cascade par défaillance d'un nœud central ou perte d'un pont ;
    peut toucher une **autre strate** (chaîne d'approvisionnement → économie).
  - POLARITÉ apparaît — **faible** — fragmentation en deux composantes après perte d'un pont.
- **Indicateurs de bascule** : centralité croissante d'un nœud ; pont unique entre deux groupes ;
  défaillance d'un nœud central.
- **Entrées** : CROISSANCE (expansion), ÉMERGENCE, COMMUNAUTÉ.

## POLARITÉ ⥀
- **Inertie** : 0,85 (forte) — un champ à deux pôles se maintient.
- **Transitions** :
  - CROISSANCE {rétroaction amplifiante} apparaît — **moyenne** — escalade (spirale de rétorsions).
  - SEUIL apparaît — **moyenne** — rupture.
  - HIÉRARCHIE apparaît — **moyenne** — un pôle domine l'autre.
  - RÉCIPROCITÉ apparaît — **faible** — désescalade par échanges conditionnels.
- **Indicateurs de bascule** : rétorsions successives de plus en plus fortes ; disparition des
  intermédiaires ; alignements exclusifs exigés des tiers.
- **Entrées** : RÉCIPROCITÉ (non-retour), RÉSEAU (perte d'un pont), HIÉRARCHIE (contestation).

## INCERTITUDE Ø
- **Inertie** : 0,40 (faible) — les possibles se résolvent avec le temps.
- **Transitions** :
  - ÉMERGENCE apparaît — **moyenne** — une forme tranche entre les possibles.
  - CONTRAINTE apparaît — **moyenne** — une option se ferme (séquentiel, donc compatible avec
    l'incompatibilité sur un même objet *au même moment*).
  - SEUIL apparaît — **faible** — résolution par basculement.
- **Indicateurs de bascule** : échéance de décision ; couvertures qui se défont ; un acteur abandonne
  une option publiquement.
- **Entrées** : CONTRAINTE qui se relâche, RÉSEAU (signaux contradictoires), HIÉRARCHIE (succession
  ouverte).

## CONTRAINTE ⊘
- **Inertie** : 0,90 pour une contrainte formelle, 0,65 pour une contrainte matérielle (option du moteur `--ctr-materielle`) — forte pour une contrainte formelle (loi, traité), moyenne pour une
  contrainte matérielle.
- **Transitions** :
  - RÉSEAU apparaît — **moyenne** — contournement par des canaux parallèles.
  - SEUIL apparaît — **moyenne** — la contrainte se resserre jusqu'à rendre l'état actuel intenable.
  - TRANSFORMATION apparaît — **faible** — adaptation qui conserve l'invariant.
  - Disparition (relâchement) — couverte par l'inertie.
- **Indicateurs de bascule** : coût d'opportunité croissant (ce que la contrainte empêche vaut de plus
  en plus) ; tentatives de contournement documentées ; échéance de révision.
- **Entrées** : CROISSANCE (capacité atteinte), ÉMERGENCE (codification), POLARITÉ (sanctions).

## PROPORTION ◯
- **Inertie** : 0,85 (forte) — tant que l'échelle ne change pas.
- **Transitions** :
  - TRANSFORMATION apparaît — **moyenne** — réorganisation pour restaurer un rapport rompu par un
    changement d'échelle.
  - SEUIL apparaît — **faible** — rupture de proportion non absorbée.
  - POLARITÉ apparaît — **faible** — concentration extrême qui sépare deux groupes.
- **Indicateurs de bascule** : changement d'échelle rapide ; écart croissant à la loi d'échelle
  habituelle.
- **Entrées** : CROISSANCE, RÉSEAU (concentration).

## TRANSFORMATION ∿
- **Inertie** : 0,65 (moyenne) — un processus en cours tend à se poursuivre.
- **Transitions** :
  - TRACE·MÉMOIRE apparaît — **moyenne** — fin du processus, la forme nouvelle se fixe.
  - SEUIL apparaît — **moyenne** — le processus franchit un point de non-retour (tension documentée
    SEUIL ~ TRANSFORMATION).
  - ÉMERGENCE d'une entité nouvelle — **faible** — l'invariant est perdu : ce n'est plus la même
    entité.
- **Indicateurs de bascule** : menace sur l'invariant (mission, membres, identité) ; accélération du
  changement.
- **Entrées** : SEUIL, CONTRAINTE (adaptation), PROPORTION.

## TRACE·MÉMOIRE ◊
- **Inertie** : 0,96 (forte) — par définition, le passé continue d'agir.
- **Transitions** :
  - POLARITÉ apparaît — **faible** — réactivation d'un grief ancien.
  - PÉRIODICITÉ apparaît — **faible** — commémorations, retours rituels.
  - SEUIL apparaît — **faible** — seul un choc rompt un verrouillage.
- **Indicateurs de bascule** : anniversaire d'un événement fondateur ; réactivation publique d'un
  grief ; coût de changement qui chute.
- **Entrées** : SEUIL, ÉMERGENCE (verrouillage), TRANSFORMATION achevée.

## CROISSANCE ▲
- **Inertie** : 0,65 (moyenne) — dépend de la phase (exponentielle, inflexion, saturation).
- **Transitions** :
  - CONTRAINTE apparaît — **forte** — la capacité limite devient active (logistique).
  - SEUIL apparaît — **moyenne** — dépassement de la capacité puis effondrement (bulle).
  - ÉMERGENCE apparaît — **faible** — propriétés nouvelles par changement d'échelle.
  - Peut toucher une **autre strate** : une croissance économique active une contrainte climatique.
- **Indicateurs de bascule** : taux de croissance qui baisse (passage du point d'inflexion) ;
  approche d'une capacité nommée ; financement de la croissance par la croissance elle-même.
- **Entrées** : RÉCURSIVITÉ, ÉMERGENCE (diffusion), RÉSEAU (effets de réseau).

## COMMUNAUTÉ ⟶
- **Inertie** : 0,65 (moyenne) — dépend des sanctions contre les passagers clandestins.
- **Transitions** :
  - SEUIL apparaît (dissolution) — **moyenne** — les passagers clandestins non sanctionnés vident le
    bien commun.
  - HIÉRARCHIE apparaît — **moyenne** — un garant ou une autorité de sanction se met en place.
  - RÉCIPROCITÉ apparaît — **faible** — retour à des échanges bilatéraux.
- **Indicateurs de bascule** : contributions en baisse ; défections sans sanction ; contestation des
  règles d'accès.
- **Entrées** : RÉCIPROCITÉ élargie, ÉMERGENCE, CONTRAINTE commune.

## RÉSONANCE ✶
- **Inertie** : 0,85 (forte) — au-delà du couplage critique, la synchronisation se maintient.
- **Transitions** :
  - CROISSANCE apparaît (amplitude collective) — **moyenne** — des oscillations alignées s'additionnent.
  - SEUIL apparaît — **moyenne** — oscillation synchronisée qui dépasse la tolérance du système ; peut
    toucher une **autre strate**.
  - Disparition (désynchronisation) — couverte par l'inertie, si le couplage faiblit.
- **Indicateurs de bascule** : force de couplage (nombre et intensité des liens) ; alignement de phase
  mesuré ; amplitude commune croissante.
- **Entrées** : PÉRIODICITÉ (cycles couplés), RÉSEAU (couplage).

---

## Barreau des transitions (0.6.0)

Chaque transition porte un barreau de l'échelle de Pearl : **A** association (co-occurrence observée
ou supposée entre cartes), **I** intervention documentée (une action datée produit la carte d'arrivée,
mécanisme établi par une source), **C** contrefactuel documenté. En 0.6.0, **toutes les transitions
sont A** (`barreau` en §H : défaut A, aucune exception). Ce n'est pas un défaut de saisie : c'est la
mesure exacte de ce qui manque au moteur pour répondre à une question causale. Une exception s'inscrit
dans `parametres.json` (`"SRC>CIB": "I"`) seulement avec la source qui documente le mécanisme, et
`audit` refuse toute autre valeur. Conséquence pratique : une transition A ne garantit pas son
transport vers un contexte différent, ce que l'emprunt entre strates (T4, poids 0,5) reconnaissait déjà.

**Ce que la matrice code, et ce qu'elle ne code pas (0.7.18).** Des quatre causes d'Aristote (*Physique*
II.3) — matérielle, formelle, efficiente, finale —, les cartes codent la **formelle** : la forme d'une
situation. La matérielle n'y entre que par les contraintes ; l'efficiente (qui a produit) seulement par
`programmation` ; la finale (en vue de quoi), nulle part. Dans la typologie de Pires (1993, lien matériel ou
d'interprétation × relation événementielle ou structurelle), le skill occupe les cases matérielles ; une
représentation qui consolide une structure, ou une intention qui produit une structure, n'a pas de champ. Les
cartes suffisent-elles à prévoir sans l'agent ? C'est l'hypothèse à éprouver, non un acquis ; une action
volontaire interposée coupe la chaîne pour le sens commun (Hart et Honoré 1959), et le calcul attribue alors
l'effet à l'état antérieur. Une carte « intention » ne comblerait pas ce manque : elle s'appliquerait après
coup à tout événement, sans marqueur qui puisse être absent. Ce qui se code est la **séquence des actes
préparatoires**, datés : 83 attaques ou approches contre des personnalités américaines (Fein et Vossekuil 1998)
ne montrent aucun profil d'auteur, aucune menace directe à la cible chez 43 auteurs d'attaque, mais des propos
sur l'attaque envisagée chez deux tiers des auteurs — un taux P(avoir parlé | être passé à l'acte), non
l'inverse.

**La loi de composition, nommée.** logit p₀ = logit f + Σ ln λ : effets **directs**, multiplicatifs, sans
interaction, monotones (aucun λ < 1), indépendants de l'ordre ; une cause efficiente au niveau de la situation,
jamais finale (Coleman 1990 : le comportement d'un système s'explique par des causes efficientes). Un effet
total de signe opposé à l'effet direct (une politique qui produit l'inverse de ce qu'elle vise) n'est pas
représentable à un pas. Deux cartes qui apparaissent dans le même état n'ont pas d'ordre lisible (causation
contemporaine) ; une transition établit au mieux un ordre de dates, non un ordre causal. Le calcul ne
**compose** pas des événements par produit de marginales : un composé est non estimé, et le noyau joint
(0.7.14) déclare n'estimer aucune dépendance. Un événement collectif qui exige deux volontés de sens opposé
(« démission effective ») se pose comme **un** événement, estimé sur ses homologues ; le décomposer en deux
marginales multipliées surestimerait ou sous-estimerait selon le signe de leur corrélation, inconnu sans la
structure.

**Additif, pas configurationnel (0.7.22).** Le paragraphe précédent nomme la loi ; celui-ci dit ce qu'elle
interdit de lire. Trois couches, trois réponses.

- **(a) Ce que fait le moteur.** L'a priori est une somme en logit : logit p₀ = logit f + Σ ln λ, sans terme
  d'interaction. Deux cartes présentes ensemble ajoutent chacune leur ln λ ; leur présence conjointe
  n'ajoute rien de plus. Aucune carte ne change le poids d'une autre, aucune n'est nécessaire à l'effet
  d'une autre, et aucune combinaison n'a d'effet que ses parties n'auraient pas.
- **(b) Ce que retient l'homologie.** Les cas homologues sont choisis sur la ressemblance de l'état
  (`graphe.md` §3) : H1 exige les mêmes cartes et les mêmes forces, H1.5 un Jaccard pondéré d'au moins 0,7
  sur toutes les cartes ; H2 ne demande plus que les sources de l'événement, H3 les traduit d'une autre
  strate. Le moteur retient le plus strict de ces niveaux qui atteint trois cas. Cette ressemblance porte
  sur des attributs, non sur des relations : les liaisons n'y entrent pas. La fréquence observée chez ces
  homologues révise l'a priori (P = (n_E + 2 p₀)/(n_A + 2), `graphe.md` §4). Quand les homologues sont
  nombreux et semblables à l'état entier (H1, H1.5), cette fréquence peut **refléter** une interaction
  entre cartes, puisqu'elle est comptée sur des états qui les réunissent. Le moteur ne la nomme pas, ne la
  teste pas, et ne la distingue pas du bruit d'un petit effectif.
- **(c) Ce que fournirait la QCA.** La consistance et la couverture d'une règle « configuration → issue »
  (Ragin) restent une proposition en attente de cas réels actifs (`apports-theoriques.md` §16.3), et même
  alors elles seraient des **indicateurs**, jamais des garanties (`apports-theoriques.md` §15). Rien de configurationnel n'est
  calculé aujourd'hui.

**Garde.** Une conjonction de cartes n'est pas une configuration causale : c'est une co-activation. Dans
l'a priori, son effet est additif. Chez les homologues, une fréquence peut porter la trace d'une
interaction, mais ce n'est pas une configuration établie : rien ne l'a nommée ni testée. Un codeur qui écrit
« SEUIL **avec** POLARITÉ produit… » décrit une hypothèse de configuration ; il l'écrit dans la `garantie` ou
au journal des lacunes, et le calcul ne la lit pas. Le mot « configuration » de l'étape 1 du mode CODER
(`base-de-cas.md` §3) désigne la situation à étudier, non une cause conjointe.

**Mesurer la non-additivité (0.7.31).** `attribuer` rend, pour un état donné, l'interaction de chaque paire de mots
en logit (`validation.md` §12). Sur la démonstration, POLARITÉ@7 × CONTRAINTE@6 vaut +1,51 : le choix des homologues y
rend le calcul non additif. C'est une propriété du calcul sur cette base, non une configuration causale établie.

**Une carte est un mécanisme ; une bifurcation n'est pas une carte (0.7.19).** Elster (1998) définit les
mécanismes comme des « structures causales récurrentes et facilement identifiables dont les conditions
d'activation sont inconnues ou les conséquences indéterminées » : c'est le statut des seize cartes. La contingence
y tient à l'irruption d'un mécanisme plutôt que d'un autre, ou à l'effet conjoint de deux mécanismes chacun
déterminé : c'est pourquoi le skill rend une fréquence conditionnelle et non une loi. Grossetti (2004, lu par la
recension de Champenois et Dalla Pria, *Sociologie du travail* 48, 2006) nomme **bifurcation** un enchaînement
d'actions fortement imprévisible qui produit des **irréversibilités** importantes et durables, et distingue trois
échelles de passage du « micro » au « macro » : le temps (du court au long), la masse d'acteurs, la
spécialisation (d'un monde confiné au général). Le skill représente la bifurcation sans carte nouvelle : SEUIL
(un retour qui ne reprend pas le même chemin) et TRACE·MÉMOIRE (dépendance au chemin), dont l'arête est l'une des
trois fortes de la matrice ; il ne la reconnaît qu'à l'issue. De ces trois échelles, il n'en a qu'une, le temps
(la fenêtre, la bande d'horizon) ; les strates sont des domaines, non des masses d'acteurs ni des degrés de
spécialisation. **Tournants de négociation** (Druckman 2020, trente-cinq ans de travaux, 34 cas comparés) : un
tournant se trace en trois temps — précipitant, départ, conséquences pour toutes les parties —, il est abrupt à des
degrés divers, et **un départ proposé puis refusé n'est pas un tournant** : il faut que les parties l'acceptent.
C'est la logique du marqueur de SEUIL@7 (« franchissement reconnu par les parties »), venue d'une autre littérature.
Dans les négociations de sécurité, les précipitants sont plutôt extérieurs (médiation, crise) et les départs
abrupts ; dans les négociations commerciales et politiques, plutôt intérieurs, procéduraux ou substantiels. Une
crise précède souvent un tournant : une escalade est suivie d'une désescalade dans la plupart des cas comparés.

**Le livre de Grossetti, lu (0.7.20).** Le paragraphe précédent s'appuyait sur une recension. Le livre
(*Sociologie de l'imprévisible*, PUF, 2004 ; version auteur de 2004 lue en entier), l'article des *Cahiers
internationaux de sociologie* (2006), la communication de 2003 et « L'espace à trois dimensions des
phénomènes sociaux » (*SociologieS*, 2011) confirment la définition et la précisent sur quatre points.

1. **Imprévisibilité et irréversibilité sont deux axes, non un seul.** Grossetti croise les deux
   (tableau 7 du livre, tableau 2 de 2006) :

   | | Irréversibilités faibles | Irréversibilités fortes |
   |---|---|---|
   | **Imprévisibilité faible** | routine | rituel, changement d'état prévisible ; changement graduel par petites étapes qui se cumulent, puis franchit un seuil |
   | **Imprévisibilité forte** | risque sans conséquence : le couple a failli se séparer, l'accident « évité de justesse » | **bifurcation** |

   Pour le codage, deux conséquences. Un franchissement **prévisible** qui laisse une trace (majorité
   civile, ratification attendue) est SEUIL suivi de TRACE·MÉMOIRE sans être une bifurcation : la
   bifurcation est la seule case où les deux axes sont hauts. Et le **risque sans conséquence** est le
   pendant sociologique du cas sans événement (B4, `base-de-cas.md` §4) : la structure était là, l'issue
   est restée proche du départ ; l'oublier, c'est le biais du survivant. Le changement graduel qui se
   cumule jusqu'à un seuil est ce que Grossetti nomme **sédimentation** ; la fenêtre de 3 mois le voit mal,
   parce que chaque pas y est petit.
2. **La case dépend du niveau choisi.** Les mêmes orientations scolaires sont de la reproduction au
   niveau du système (le système ne change pas) et des bifurcations au niveau d'un parcours de vie (le
   parcours en est changé). Rien n'est bifurcation en soi ; c'est une relation entre un temps court et un
   temps long que l'analyste définit. Pour le skill, c'est l'objet de la question (S1) qui fixe le niveau,
   et deux cas codés à des niveaux différents ne sont pas homologues, même avec les mêmes cartes.
3. **La crise est souvent une contagion entre sphères.** Dans les parcours (2006, d'après Bidart),
   l'instabilité naît du recouvrement de contextes d'ordinaire distincts : travail, famille, santé. Chaque
   contexte pris seul se laisse plus ou moins anticiper ; quand ils se mêlent, les imprévisibilités se
   multiplient (l'équivalent des séries causales indépendantes de Cournot). Dans le skill, le passage à une
   autre strate abaisse d'un cran la source d'une transition, sauf propagation admise ou transfert ancré
   (`graphe.md` §2.1). Grossetti donne à cette convention une raison qualitative ; il ne fournit aucun
   chiffre pour en régler la taille.
4. **La contingence est à mesurer, pas à poser.** « La contingence des situations n'est pas quelque chose
   que l'on doive fixer d'un point de vue théorique mais un paramètre à évaluer empiriquement. » C'est la
   position du skill : une fréquence conditionnelle, estimée sur des cas, et un statut qui dit si elle
   l'est. Grossetti situe aussi les **commencements** (d'une organisation, d'une relation, d'un standard)
   parmi les moments propices aux bifurcations, parce que tout y est encore peu défini. Le skill n'en fait
   pas une règle : c'est une hypothèse sans cas codés.

**Correction de la phrase précédente sur les strates (0.7.20).** On a écrit en 0.7.19 que « les strates
sont des domaines, non des masses d'acteurs ni des degrés de spécialisation ». C'est vrai d'une strate
prise seule. Mais l'article de 2011 définit la troisième échelle, la **généralité**, par la **variété des
contextes** qu'un phénomène implique (travail, famille, santé, science, un territoire), de la
spécialisation (peu de contextes) à la généralité (beaucoup). Le **nombre de strates** qu'un épisode
touche est donc une mesure grossière de cette échelle, et la « montée en généralité » de Grossetti (un
chômage qui entraîne un divorce, puis une dépression) se lit comme une propagation d'une strate à
l'autre. Le skill a ainsi deux des trois échelles, le temps et, en gros, la généralité ; il n'a toujours pas
la masse des acteurs.

**Le tiers (0.7.21, Simmel 1902).** Simmel décrit trois rôles d'un troisième élément face à deux autres
en opposition : le **médiateur**, qui ramène l'antagonisme de la volonté à un désaccord d'idées et rend
l'accord possible ; le ***tertius gaudens***, qui tire profit de la rivalité des deux autres et a intérêt à
ce qu'elle dure ; le *divide et impera*, qui crée ou entretient la division pour dominer. Il montre ces trois
rôles dans la famille, la politique, l'économie et les relations entre États. L'avantage du tiers disparaît
dès que les deux autres s'unissent. Ces rôles éclairent des transitions déjà écrites sans en changer la
force : POLARITÉ → RÉCIPROCITÉ (faible) passe souvent par un médiateur ; POLARITÉ → HIÉRARCHIE (moyenne) peut
être l'œuvre d'un tiers qui divise ; et l'indicateur de bascule de POLARITÉ, « disparition des
intermédiaires ; alignements exclusifs exigés des tiers », est la suppression de la place du tiers. Le
courtier de RÉSEAU (intermédiarité) en est la version mesurée : Burt (2004, *American Journal of Sociology*
110(2), 673 managers d'une seule entreprise) trouve que les idées des managers à réseau peu contraint sont
mieux notées par deux juges qui ignorent leur auteur. C'est un appui pour la structure, pas une fréquence de
transition. Simmel note aussi la fragilité de la **dyade** : le départ d'un seul la détruit, ce qu'une
triade supporte. Rien ici n'est versé au calcul.

## Synthèse : matrice des transitions a priori

Lignes : carte présente. Colonnes : carte qui apparaît (même strate). F = forte, M = moyenne,
f = faible ; vide = non documentée. Les propagations vers une autre strate admises sans abaissement
sont listées dans les fiches (« autre strate ») et dans `assets/parametres.json` (`autre_strate`).

| De \ Vers | SEU | REC | PER | RCS | EME | HIE | RES | POL | INC | CTR | PRO | TRA | TRC | CRO | COM | RSN |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SEUIL | | | f | | | | | | | | | M | F | | | |
| RÉCIPROCITÉ | f | | | | | M | | M | | | | | | | f | |
| PÉRIODICITÉ | f | | | | | | | | | | | | | | | M |
| RÉCURSIVITÉ | M | | | | | | | | | f | | | | M | | |
| ÉMERGENCE | | | | | | M | f | | | M | | | F | M | f | |
| HIÉRARCHIE | f | | | f | | | | M | f | | | f | | | | |
| RÉSEAU | M | | | f | f | | | f | f | | M | | | f | | f |
| POLARITÉ | M | f | | | | M | | | | f | | | | M | | |
| INCERTITUDE | f | | | f | M | | | | | M | | | | | | |
| CONTRAINTE | M | | f | | | | M | | f | | | f | | | f | |
| PROPORTION | f | | | | | | | f | | | | M | | | | |
| TRANSFORMATION | M | | | | f | | | | | | | | M | | | |
| TRACE·MÉMOIRE | f | | f | | | | | f | | | | | | | | |
| CROISSANCE | M | | | | f | | f | | | F | f | | | | | |
| COMMUNAUTÉ | M | f | | | | M | f | | | | | | | | | |
| RÉSONANCE | M | | | | | | | | | | | | | M | | |

## Transitions ajoutées en v0.3.0 : réconciliation des « Entrées »

Les lignes **Entrées** des fiches, écrites dès la v0.1.0, annonçaient 17 transitions absentes de la
matrice. La matrice ne pouvait donc pas produire RÉCURSIVITÉ ni INCERTITUDE (aucun parent), ni faire
apparaître un RÉSEAU autrement que par contournement d'une CONTRAINTE. Ces 17 transitions sont
ajoutées avec l'intensité **faible** (f), la plus basse : elles rétablissent la cohérence du document
avec lui-même, sans prétendre à une force que rien ne mesure. Leur mécanisme est celui que la fiche de
la carte cible donne déjà. `moteur.py audit` vérifie désormais que chaque entrée annoncée est un parent
dans la matrice.

| De → Vers | Mécanisme (repris de la fiche cible) |
|---|---|
| CONTRAINTE → PÉRIODICITÉ | contrainte à échéance fixe |
| HIÉRARCHIE → RÉCURSIVITÉ | classements publiés |
| RÉSEAU → RÉCURSIVITÉ | diffusion d'une représentation du système |
| INCERTITUDE → RÉCURSIVITÉ | recherche de signaux sur soi-même |
| RÉSEAU → ÉMERGENCE | interactions locales denses |
| COMMUNAUTÉ → RÉSEAU | un collectif tisse des liens |
| CROISSANCE → RÉSEAU | expansion |
| ÉMERGENCE → RÉSEAU | une régularité nouvelle crée des liens |
| CONTRAINTE → INCERTITUDE | une contrainte qui se relâche rouvre des possibles |
| RÉSEAU → INCERTITUDE | signaux contradictoires |
| HIÉRARCHIE → INCERTITUDE | succession ouverte |
| POLARITÉ → CONTRAINTE | sanctions |
| CROISSANCE → PROPORTION | changement d'échelle |
| RÉSEAU → CROISSANCE | effets de réseau |
| CONTRAINTE → COMMUNAUTÉ | contrainte commune |
| ÉMERGENCE → COMMUNAUTÉ | une régularité partagée devient un collectif |
| RÉSEAU → RÉSONANCE | couplage |

Ce qui **n'est pas** ajouté : aucune transition vers TRACE·MÉMOIRE ni vers TRANSFORMATION. Leurs fiches
étaient déjà cohérentes avec la matrice, et les deux tests sur cas réel qui les ont manquées étaient des
rejeux (issue connue avant le calcul). Les modifier sur cette base serait ajuster le modèle à l'issue,
ce que V3 interdit ; elles sont au journal des lacunes.

## Inerties

Probabilité a priori de persistance d'une carte ancrée **sur 3 mois**. Pour une fenêtre de d jours,
le moteur utilise inertie^(d / 91,3) : INCERTITUDE, 0,40 sur 3 mois, vaut 0,93 sur 7 jours. Utilisée
seulement quand la base ne fournit pas de fréquence de persistance stable (`graphe.md` §2.3).

| Carte | Inertie | Justification |
|---|---|---|
| SEUIL | 0,97 | état absorbant : une disparition est plus souvent un défaut de codage qu'un retour |
| TRACE·MÉMOIRE | 0,96 | dépendance au chemin |
| PÉRIODICITÉ | 0,90 | cycle limite stable |
| RÉSEAU | 0,90 | une topologie change lentement |
| CONTRAINTE | 0,90 | contrainte formelle (0,65 si matérielle) |
| HIÉRARCHIE | 0,88 | ordre de préséance qui se reproduit |
| POLARITÉ | 0,85 | champ à deux pôles qui se maintient |
| PROPORTION | 0,85 | rapport stable tant que l'échelle ne change pas |
| RÉSONANCE | 0,85 | synchronisation stable au-delà du couplage critique |
| RÉCIPROCITÉ | 0,65 | boucle entretenue seulement si les retours suivent |
| RÉCURSIVITÉ | 0,65 | dure tant que la représentation est diffusée |
| ÉMERGENCE | 0,65 | régularité naissante, fragile |
| TRANSFORMATION | 0,65 | processus en cours |
| COMMUNAUTÉ | 0,65 | dépend des sanctions contre les passagers clandestins |
| CROISSANCE | 0,65 | dépend de la phase de croissance |
| INCERTITUDE | 0,40 | les possibles se résolvent avec le temps |

## Observation pour l'audit

SEUIL est la cible la plus fréquente (14 des 15 autres cartes y mènent ; seule ÉMERGENCE n'y mène pas ;
en v0.3.0, RÉSEAU a 4 parents, INCERTITUDE et RÉCURSIVITÉ 3 chacune). Cela ne découle pas à lui seul de sa définition, mais cela expose l'outil à un biais : sur-prédire des
ruptures. La couche 6 doit surveiller en priorité le score des prévisions « SEUIL apparaît »
(`validation.md` §4).
