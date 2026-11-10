# Alphabet situationnel — Les 16 cartes (noyau transversal candidat)

> Version : 0.7.53

> **Statut 0.4.0.** Les rapprochements mathématiques ci-dessous guident la lecture ; ils ne prouvent
> ni universalité ni transfert des probabilités. La bibliographie du noyau ne valide pas les équivalents locaux.
> **Précisé en 0.7.13.** Trois choses distinctes : l'**analogie** mathématique (une forme qui guide la
> lecture), la **définition formelle** (un objet défini sur la situation, avec ses opérations), et
> l'**hypothèse de transfert** (les propriétés de l'objet valent pour la situation). Les fiches donnent la
> première, jamais les deux autres : deux camps ne définissent pas une involution pertinente sur toute
> une situation ; une transformation progressive avec un invariant n'est pas une homotopie formalisée ;
> SEUIL a la forme d'une hystérésis sans que le moteur la représente (`graphe.md` §2.4). Aucune propriété
> d'un objet mathématique ne se transfère à une situation sans démonstration propre.
>
> **Orthogonalité (0.7.17).** Une carte n'est pas une strate de plus : elle traverse les strates sans en
> constituer une, comme les contraintes de réalisabilité de Chandaria et al. (2026) opèrent
> orthogonalement à leur hiérarchie de niveaux sans former un niveau. Le terme dit le rapport ; il ne
> prouve pas que la carte se transporte (P1, T4).
>
> **Gabarit (P, G, I), proposé en 0.7.14** (`apports-theoriques.md` §18). Une carte a trois composants :
> **P**, le *prédicat* (ce qu'un état doit exhiber pour que le mot soit ancré : A6, marqueur local) ;
> **G**, le *générateur* (les transitions que la carte rend plus ou moins probables, avec mécanisme et
> signe : la matrice) ; **I**, l'*invariant* (ce qu'une traduction d'une strate à l'autre doit conserver,
> et que l'homologie doit préserver). L'analogie mathématique n'est aucun des trois. Exemple, SEUIL —
> P : franchissement après lequel le retour par le même chemin est fermé ; G : → TRACE·MÉMOIRE (F),
> → TRANSFORMATION (M), aucun retour ; I : l'aller et le retour ne basculent pas au même point. Critère
> pour une strate : si seul P se traduit, l'équivalent est **descriptif** (aucun λ, aucun emprunt) ; si P et
> G se traduisent sans I, il est **local** (emprunt T4 interdit) ; les trois, il est transversal. Les
> quinze autres fiches sont à écrire (décision d'auteur 11) ; aucune n'est réécrite ici.
> **Origine.** Fiches reprises de NEXUS-ARCHÊ v0.4.2 sans modification de fond ; seuls les renvois
> vers des fichiers absents de ce skill ont été remplacés.
> Ce fichier est la source de vérité du **noyau transversal candidat** des cartes (couche 1) : définition,
> structure mathématique, marqueurs observables abstraits, registre anthropologique, voisines.
>
> **Ce qui s'y ajoute ailleurs** :
> - l'index d'une ligne par carte, à charger en premier → `cartes-index.md` ;
> - la traduction de chaque carte par strate → `equivalences/strate-NN.md` ;
> - ce que chaque structure tend à produire ensuite → `dynamiques.md`.
>
> **Correspondance des renvois.** Les fiches renvoient aux règles courantes (A5, A6, G1…). Pour lire
> un document NEXUS-ARCHÊ : R2 → A5 · R3 → A6 · R4 → A7 · R6 → G3 · R9 → A8 · R13 → G1.
>
> **Registre anthropologique** : ne s'applique qu'aux strates à agents (3 à 10, 12 et 13 ; `strates.md`).
> Dans les strates 1, 2 et 11, seul le noyau mathématique vaut.

---

## SEUIL

**Définition** : franchissement d'une valeur critique après lequel le retour à l'état antérieur est
impossible, ou ne peut plus se faire par le même chemin. Le critère est l'**irréversibilité**, pas la
soudaineté.

**Structure mathématique** : hystérésis (bistabilité : l'aller et le retour basculent à des valeurs
différentes du paramètre) ; état absorbant (chaîne de Markov) ; application non inversible.
*Domaine* : systèmes dynamiques, processus stochastiques.
> Une bifurcation seule n'est **pas** un seuil : une bifurcation supercritique se défait quand le
> paramètre revient. Elle ne devient SEUIL qu'accompagnée d'hystérésis ou d'absorption.

**Marqueurs observables** :
- acte juridique, contractuel ou matériel sans mécanisme de retour (signature, destruction, dépense irrécupérable) ;
- tentative de retour qui échoue, ou qui exige un chemin différent de l'aller ;
- coût du retour sans commune mesure avec le coût de l'aller.

**Registre anthropologique** — *documenté* : « rites of passage ».

**Garantie type** (A6, 0.6.0) — *mécanisme* : un franchissement daté supprime le retour par le même chemin ; *attendu* : aucun retour par le chemin initial ; tout retour passe par un autre chemin, daté ; *contredirait* : un retour documenté par le même chemin.

**À ne pas confondre avec** :
- *TRANSFORMATION* — Les deux cartes coexistent souvent (une métamorphose traverse un seuil).
  Question : *ce qui organise la situation est-il le point au-delà duquel le retour est fermé
  (→ SEUIL) ou le processus de changement de forme et ce qu'il conserve (→ TRANSFORMATION) ?*
- *CONTRAINTE* — Question : *y a-t-il passage effectif vers un nouvel état sans retour (→ SEUIL)
  ou seulement des options retirées sans changement d'état (→ CONTRAINTE) ?*
- *POLARITÉ* — Question : *la dualité est-elle un champ stable à deux pôles (→ POLARITÉ) ou
  l'avant/après d'un passage non réversible (→ SEUIL) ?*
- *TRACE · MÉMOIRE* — **Inclusion mathématique** : l'hystérésis est un cas de dépendance au chemin.
  Les deux cartes coexistent souvent (un seuil franchi laisse une trace). Question : *ce qui organise
  la situation est-il le point au-delà duquel le retour est fermé (→ SEUIL) ou l'effet persistant
  d'un passé qui continue d'agir (→ TRACE) ?*

**Question d'exploration** : qu'est-ce qui ne peut plus être défait — et qu'est-ce qui, de ce fait,
a cessé d'être une option ?

**Signature** : `⊥` LIMITE

---

## RÉCIPROCITÉ

**Définition** : un transfert entre deux parties crée l'obligation d'un contre-transfert entre les
mêmes parties ; la relation se maintient par cette boucle don / retour. La symétrie porte sur
l'**obligation**, pas sur les positions : elle est compatible avec une inégalité de statut.

**Structure mathématique** : jeux répétés et stratégies conditionnelles (donnant-donnant,
Axelrod 1984 ; théorème folk) ; réciprocité directe. *Domaine* : théorie des jeux **non coopératifs**
répétés.

**Marqueurs observables** :
- transferts identifiables dans les deux sens entre les mêmes parties ;
- tenue de compte, explicite ou implicite (rappel d'une dette, « je te dois bien ça ») ;
- refroidissement, rupture ou rétorsion observés après un non-retour.

**Registre anthropologique** — *documenté* : « reciprocal exchanges (of labor, goods, or services) »,
« gift giving », « trade », « reciprocity, negative (revenge, retaliation) ».

**Garantie type** (A6, 0.6.0) — *mécanisme* : un transfert crée une attente de contre-transfert entre les mêmes parties ; *attendu* : un contre-transfert, ou une échéance d'usage, entre les mêmes parties ; *contredirait* : un transfert explicitement sans attente de retour, ou un retour qui passe par un tiers.

**À ne pas confondre avec** :
- *COMMUNAUTÉ* — Question : *la relation est-elle entre deux parties qui se rendent (→ RÉCIPROCITÉ)
  ou entre un collectif et son bien commun (→ COMMUNAUTÉ) ?*
- *RÉSEAU* — Question : *ce qui importe est-il la topologie des liens (→ RÉSEAU) ou l'équilibre de
  ce qui circule dans un lien (→ RÉCIPROCITÉ) ?*
- *RÉSONANCE* — Question : *l'alignement est-il un échange obligé (→ RÉCIPROCITÉ) ou une
  synchronisation de rythmes sans compte (→ RÉSONANCE) ?*
- *HIÉRARCHIE* — Compatibles (relation patron-client : obligation réciproque sous asymétrie de
  statut ; Gouldner 1960, Scott 1972). Question : *ce qui organise le rapport est-il la boucle
  d'obligations (→ RÉCIPROCITÉ) ou l'ordre de préséance (→ HIÉRARCHIE) ?*

**Question d'exploration** : qu'est-ce qui circule ici, dans quel sens — et qui tient le compte ?

**Signature** : `⊗` LIER

---

## PÉRIODICITÉ

**Définition** : retour d'un même état à intervalles réguliers, entretenu par la dynamique du
système ou imposé par un forçage extérieur (calendrier, saison, échéance).

**Structure mathématique** : orbites périodiques, cycles limites, oscillateurs autonomes ou forcés.
*Domaine* : systèmes dynamiques.

**Marqueurs observables** :
- au moins **trois** occurrences datées du même état ou de la même séquence de phases ;
- intervalle approximativement constant ;
- phases du cycle identifiables (on peut dire où l'on en est).

**Registre anthropologique** — *documenté* : « time, cyclicity of », « rituals ».

**Garantie type** (A6, 0.6.0) — *mécanisme* : un état revient à intervalles réguliers, entretenu par le système ou forcé par un calendrier ; *attendu* : au moins deux retours datés à intervalle comparable ; *contredirait* : un épisode unique, ou des retours sans régularité.

**À ne pas confondre avec** :
- *RÉCURSIVITÉ* — Question : *le retour est-il réglé par un rythme ou une échéance (→ PÉRIODICITÉ)
  ou produit par le fait que le système se prend pour objet (→ RÉCURSIVITÉ) ?*
- *TRACE · MÉMOIRE* — Compatibles (un rituel annuel est à la fois un retour et une trace).
  Question : *ce qui agit est-il le retour régulier lui-même (→ PÉRIODICITÉ) ou ce que le passé a
  laissé et qui persiste (→ TRACE) ?*
- *RÉSONANCE* — Question : *s'agit-il du rythme propre d'un système (→ PÉRIODICITÉ) ou de
  l'alignement de plusieurs rythmes par couplage (→ RÉSONANCE) ?*

**Question d'exploration** : à quelle phase du cycle en est-on — et qu'est-ce qui, la dernière fois,
a terminé cette phase ?

**Signature** : `↻` CYCLE

---

## RÉCURSIVITÉ

**Définition** : le système prend sa propre opération ou sa propre représentation pour objet, et
cette prise **modifie** l'opération qu'elle observe. Une seule notion : l'auto-référence opérante.
> Hors carte : la simple rétroaction (une sortie qui influence l'entrée sans représentation de
> soi) et l'auto-similarité. Elles se lisent par les **qualificatifs** `{rétroaction amplifiante}`,
> `{rétroaction stabilisante}` et `{multi-échelle}` posés sur la carte concernée (G1).

**Structure mathématique** : points fixes d'applications auto-référentielles (théorème de
récursion, Kleene 1938) ; réflexivité sociale et prophétie autoréalisatrice (Merton 1948).
*Domaine* : logique et calculabilité ; théorie des systèmes sociaux.

**Marqueurs observables** :
- un discours, une mesure, un modèle ou une analyse **du système sur lui-même** est observable ;
- et ce discours modifie le comportement qu'il décrit (un classement publié change les classés ;
  l'analyse d'un conflit devient un épisode du conflit).

**Registre anthropologique** — *partiel* : « self as subject and object », « self-image, awareness
of (concern for what others think) », « private inner life ». Documenté au niveau individuel ;
l'extension aux collectifs n'est pas couverte par Brown.

**Garantie type** (A6, 0.6.0) — *mécanisme* : le système prend sa propre opération pour objet et cette prise la modifie ; *attendu* : une représentation de soi datée, suivie d'un changement de l'opération représentée ; *contredirait* : une représentation sans effet sur l'opération représentée.

**À ne pas confondre avec** :
- *PÉRIODICITÉ* — voir PÉRIODICITÉ.
- *ÉMERGENCE* — Compatibles (une émergence peut s'appuyer sur des boucles). Question : *ce qui
  organise la situation est-il un ordre collectif apparu sans prescripteur (→ ÉMERGENCE) ou un
  système qui se regarde et se modifie en se regardant (→ RÉCURSIVITÉ) ?*

**Question d'exploration** : quelle représentation de lui-même le système produit-il — et que
change-t-elle dans ce qu'elle représente ?

**Signature** : `↺` RÉFLEXIVITÉ

---

## ÉMERGENCE

**Définition** : une régularité collective (norme, convention, rôle, format, ordre) apparaît des
interactions locales, sans avoir été prescrite par un agent central et sans être présente dans les
composants pris isolément. La rétroaction est compatible et fréquente.

**Structure mathématique** : auto-organisation ; rupture spontanée de symétrie ; criticité
auto-organisée (Bak, Tang & Wiesenfeld 1987). *Méthode* (et non structure) : modèles multi-agents.
*Domaine* : systèmes complexes.

**Marqueurs observables** :
- une régularité collective nommable et datable dans son apparition ;
- l'absence démontrable de prescription (pas de décision, de vote, de consigne qui l'instaure) ;
- son adoption par imitation ou convergence observée.

**Registre anthropologique** — *à établir*. La thèse « les cultures ont émergé » relève de la théorie
de l'ordre spontané (Ferguson 1767, Hayek 1973), pas d'un universel documenté ; la liste de Brown contient
au contraire des institutions délibérées (« government », « leaders », « succession »).

**Garantie type** (A6, 0.6.0) — *mécanisme* : une régularité collective naît d'interactions locales sans prescripteur ; *attendu* : une diffusion de la régularité par imitation ou ajustement local, sans acte d'un centre ; *contredirait* : un acte central (décision, consigne) qui précède et prescrit la régularité.

**À ne pas confondre avec** :
- *TRANSFORMATION* — **Incompatibles sur un même objet** (voir `antagonismes.md`). Question :
  *l'entité observée est-elle apparue (→ ÉMERGENCE) ou existait-elle déjà et change de forme
  (→ TRANSFORMATION) ?*
- *RÉCURSIVITÉ* — voir RÉCURSIVITÉ.
- *CROISSANCE* — Compatibles (le changement d'échelle fait souvent apparaître des propriétés
  nouvelles — Anderson 1972). Question : *ce qui compte est-il l'apparition d'une propriété nouvelle
  (→ ÉMERGENCE) ou l'augmentation d'une grandeur existante (→ CROISSANCE) ?*
- *INCERTITUDE* — Question : *une régularité est-elle apparue (→ ÉMERGENCE) ou les acteurs
  agissent-ils encore sous plusieurs possibles non tranchés (→ INCERTITUDE) ?*

**Question d'exploration** : qu'est-ce qui s'est installé sans que personne ne le décide — et qui
le défend désormais ?

**Signature** : `⊙` SOURCE

---

## HIÉRARCHIE

**Définition** : relation d'ordre entre positions — pour les paires concernées, l'une prime sur
l'autre (autorité, validation, préséance), et l'ordre est au moins partiellement transitif.

**Structure mathématique** : ordres partiels ; arborescences (graphes orientés acycliques enracinés) ;
hiérarchies de dominance et leur linéarité (indice de Landau 1951). *Domaine* : théorie des ordres,
théorie des graphes.
> Les inégalités de **grandeur** (lois de puissance, Pareto) relèvent de PROPORTION ; la
> **centralité** d'un nœud relève de RÉSEAU.

**Marqueurs observables** :
- qui peut valider, bloquer ou annuler la décision de qui ;
- chaînes de validation successives ; préséances observées ;
- organigramme **effectif** (pas seulement affiché).

**Registre anthropologique** — *documenté* : « dominance/submission », « statuses and roles »,
« prestige inequalities », « leaders ».

**Garantie type** (A6, 0.6.0) — *mécanisme* : une position prime sur une autre, selon un ordre au moins partiellement transitif ; *attendu* : un arbitrage ou une validation de l'une sur l'autre, effectivement suivi ; *contredirait* : un arbitrage ignoré sans conséquence, ou un ordre circulaire.

**À ne pas confondre avec** :
- *RÉSEAU* — Une hiérarchie est un graphe particulier : les deux peuvent décrire le même objet.
  Question : *ce qui organise la situation est-il un ordre de préséance (→ HIÉRARCHIE) ou la
  topologie des liens (→ RÉSEAU) ?*
- *CONTRAINTE* — Question : *s'agit-il d'un ordre de positions (→ HIÉRARCHIE) ou d'une règle qui
  retire des options quel que soit qui l'applique (→ CONTRAINTE) ?*
- *PROPORTION* — Question : *s'agit-il d'un rang (→ HIÉRARCHIE) ou d'un rapport de grandeurs
  (→ PROPORTION) ?*
- *RÉCIPROCITÉ* — voir RÉCIPROCITÉ.

**Question d'exploration** : qui peut dire non à qui — et cet ordre tient-il encore là où il est
contesté ?

**Signature** : `✦` AXE

---

## RÉSEAU

**Définition** : topologie des liens — quels éléments sont reliés, par quels chemins un flux peut
passer, où sont les ponts et les trous.

**Structure mathématique** : graphes ; centralités (degré, intermédiarité) ; composantes et ponts ;
trous structuraux (Burt 1992) ; petits mondes (Watts & Strogatz 1998). *Domaine* : théorie des
graphes, analyse de réseaux.

**Marqueurs observables** :
- au moins trois nœuds nommables et leurs liens (présents ou absents) ;
- un chemin de transmission identifiable, ou un pont dont la disparition couperait le graphe.

**Registre anthropologique** — *documenté* : « kin groups », « classification of kin », « kinship
statuses », « coalitions », « triangular awareness (assessing relationships among the self and two
other people) ». Ce cluster est **partagé** avec RÉCIPROCITÉ et COMMUNAUTÉ (confusion fréquente entre ces cartes ; mesurée par l'accord entre codeurs, A4).

**Garantie type** (A6, 0.6.0) — *mécanisme* : la topologie des liens détermine les chemins par lesquels un flux passe ; *attendu* : un flux qui passe par un lien ou un pont nommé, ou qui se bloque quand ce lien manque ; *contredirait* : une circulation indépendante des liens nommés.

**À ne pas confondre avec** :
- *COMMUNAUTÉ* — Question : *ce qui importe est-il la structure des liens (→ RÉSEAU) ou le bien
  commun qui unit (→ COMMUNAUTÉ) ?*
- *HIÉRARCHIE* — voir HIÉRARCHIE.
- *RÉCIPROCITÉ* — voir RÉCIPROCITÉ.

**Question d'exploration** : par où l'information ou la ressource passe-t-elle — et quel lien, s'il
manquait, couperait tout ?

**Signature** : `⊛` NOEUD

---

## POLARITÉ

**Définition** : un champ s'organise autour de deux pôles qui se définissent l'un par l'autre ;
chaque élément est situé par rapport à eux, et passer d'un pôle à l'autre est une inversion.

**Structure mathématique** : involution (groupe Z₂) ; symétrie de réflexion. *Domaine* : algèbre,
théorie des groupes.

**Marqueurs observables** :
- les acteurs se classent eux-mêmes dans deux camps, ou deux termes opposés reviennent dans leur
  propre vocabulaire ;
- les positions intermédiaires sont rares, invisibles ou disqualifiées.

**Registre anthropologique** — *documenté* : « binary cognitive distinctions », « logical notion of
"opposite" », « culture/nature distinction », « in-group distinguished from out-group(s) ».

**Garantie type** (A6, 0.6.0) — *mécanisme* : deux pôles se définissent l'un par l'autre et organisent le champ ; *attendu* : des alignements exclusifs : rejoindre un pôle écarte de l'autre ; *contredirait* : une troisième position stable, ou des alignements croisés durables.

**À ne pas confondre avec** :
- *CONTRAINTE* — Question : *y a-t-il deux pôles qui structurent le champ (→ POLARITÉ) ou une règle
  qui bloque des mouvements (→ CONTRAINTE) ?*
- *SEUIL* — voir SEUIL.

**Question d'exploration** : quels sont les deux pôles — et qui se tient entre eux sans être vu ?

**Signature** : `⥀` INVERSER

---

## INCERTITUDE

**Définition** : pour les **acteurs de la situation**, plusieurs états futurs ou cachés restent
possibles, et cette indétermination **organise leurs conduites** (attente, couverture, recherche
d'information, arrangements provisoires).
> Régime unique : l'incertitude est une propriété de la situation **telle que les acteurs y
> agissent**. L'incertitude de l'analyste — ou une simple déclaration « je ne sais pas » — n'ancre
> pas la carte : il faut une conduite organisée par l'indétermination.

**Structure mathématique** : distribution de probabilité sur un espace d'états non réduit.
*Mesure* : entropie (Shannon 1948). *Méthode de mise à jour* : inférence bayésienne. *Domaine* :
théorie des probabilités et de l'information.

**Marqueurs observables** :
- décision reportée dans l'attente d'une information nommée ;
- scénarios concurrents explicitement tenus ; dispositifs provisoires ;
- ressources dépensées à réduire l'indétermination (enquête, consultation, pronostic, divination).

**Registre anthropologique** — *documenté* : « divination », « magic », « beliefs about fortune and
misfortune », « future, attempts to predict », « anticipation ».

**Garantie type** (A6, 0.6.0) — *mécanisme* : plusieurs états futurs restent possibles et cette indétermination règle les conduites ; *attendu* : des conduites conditionnées à une issue non tranchée (attente, couverture, report) ; *contredirait* : des conduites identiques quelle que soit l'issue, ou une issue déjà connue des acteurs.

**À ne pas confondre avec** :
- *CONTRAINTE* — **Incompatibles sur une même option** (voir `antagonismes.md`). Question :
  *l'option est-elle encore ouverte (→ INCERTITUDE) ou exclue (→ CONTRAINTE) ?*
- *ÉMERGENCE* — voir ÉMERGENCE.

**Question d'exploration** : qu'est-ce que les acteurs attendent de savoir — et que font-ils en
attendant ?

**Signature** : `Ø` VIDE

---

## CONTRAINTE

**Définition** : une règle ou une limite retire des options de l'espace des possibles — formelle
(loi, contrat, règlement), matérielle (budget, capacité, délai) ou sociale (tabou, sanction).

**Structure mathématique** : ensemble admissible et contraintes **actives** (celles qui lient
effectivement la solution ; multiplicateur de Lagrange non nul) ; programmation sous contraintes.
*Domaine* : optimisation.

**Marqueurs observables** :
- règle écrite ou sanction observée ;
- action tentée et bloquée ; option explicitement exclue ;
- la contrainte est **active** : sa levée changerait ce que font les acteurs.

**Registre anthropologique** — *documenté* : « taboos », « tabooed foods », « law (rights and
obligations) », « law (rules of membership) », « sanctions ».

**Garantie type** (A6, 0.6.0) — *mécanisme* : une règle ou une limite retire une option de l'espace des possibles ; *attendu* : une option nommée devenue inaccessible, avec un contournement tenté ou une sanction prévue ; *contredirait* : une option restée accessible, seulement plus coûteuse.

**À ne pas confondre avec** :
- *SEUIL* — voir SEUIL.
- *HIÉRARCHIE* — voir HIÉRARCHIE.
- *POLARITÉ* — voir POLARITÉ.
- *INCERTITUDE* — voir INCERTITUDE.
- *TRACE · MÉMOIRE* — Une règle héritée relève des deux. Question : *ce qui agit est-il
  l'exclusion d'options (→ CONTRAINTE) ou la persistance d'un passé qui ne serait plus choisi
  (→ TRACE) ?*

**Question d'exploration** : quelle contrainte est active — et que feraient les acteurs si elle
tombait ?

**Signature** : `⊘` NÉGATION

---

## PROPORTION

**Définition** : rapport entre les grandeurs des parties d'un ensemble, et sa conservation ou sa
rupture quand l'ensemble change d'échelle.

**Structure mathématique** : ratios ; similitudes et homothéties ; lois d'échelle et allométrie
(y = a·xᵇ, Huxley 1932) ; courbes de concentration (Lorenz) pour décrire des inégalités de grandeur.
*Domaine* : géométrie, analyse dimensionnelle.
> Retiré en v0.4 : la « section dorée ». Son universalité esthétique n'est pas établie
> (Markowsky 1992).

**Marqueurs observables** :
- au moins deux grandeurs mesurables et leur rapport ;
- idéalement le même rapport à deux dates, pour voir s'il se conserve.

**Registre anthropologique** — *partiel* : aucun item de proportion ; items voisins « measuring »,
« numerals (counting) », « aesthetics », « fairness (equity), concept of » (le partage équitable
est un jugement de proportion).

**Garantie type** (A6, 0.6.0) — *mécanisme* : un rapport entre les grandeurs des parties est conservé ou rompu quand l'ensemble change d'échelle ; *attendu* : deux mesures du même rapport, à deux échelles ou à deux dates ; *contredirait* : un rapport non mesuré, ou des grandeurs non comparables.

**À ne pas confondre avec** :
- *HIÉRARCHIE* — voir HIÉRARCHIE.
- *CROISSANCE* — Compatibles (une croissance homothétique conserve les rapports). Question :
  *ce qui compte est-il le rapport entre parties (→ PROPORTION) ou la dynamique d'une grandeur
  (→ CROISSANCE) ?*

**Question d'exploration** : quel rapport a changé — et qu'est-ce qui a grossi sans que le reste
suive ?

**Signature** : `◯` FORME

---

## TRANSFORMATION

**Définition** : une entité **existante** change de forme de façon progressive en conservant au
moins un invariant nommable (identité, mission, membres, fonction).

**Structure mathématique** : déformations continues (homotopies) ; groupes de transformations et
leurs invariants (Klein 1872, programme d'Erlangen). *Domaine* : topologie, géométrie.

**Marqueurs observables** :
- état de départ et état en cours décrits ;
- un invariant explicitement conservé ;
- étapes intermédiaires observées (pas seulement un avant/après).

**Registre anthropologique** — *à établir*. Aucun item de la liste ; « myths » n'est qu'un voisin.

**Garantie type** (A6, 0.6.0) — *mécanisme* : une entité existante change de forme par étapes en conservant un invariant nommé ; *attendu* : au moins deux formes datées et l'invariant conservé entre elles ; *contredirait* : une rupture sans invariant (SEUIL, disparition) ou une entité nouvelle (ÉMERGENCE).

**À ne pas confondre avec** :
- *ÉMERGENCE* — **Incompatibles sur un même objet** (voir ÉMERGENCE).
- *SEUIL* — voir SEUIL.
- *CROISSANCE* — Question : *s'agit-il d'un changement de degré (→ CROISSANCE) ou de forme
  (→ TRANSFORMATION) ?*
- *TRACE · MÉMOIRE* — Relation séquentielle, pas d'exclusion. Question : *est-on dans le
  processus de changement (→ TRANSFORMATION) ou dans ce qu'un changement a laissé (→ TRACE) ?*

**Question d'exploration** : qu'est-ce qui change de forme — et qu'est-ce qui, à travers ce
changement, doit rester pour que ce soit encore la même chose ?

**Signature** : `∿` MOUVEMENT

---

## TRACE · MÉMOIRE

**Définition** : l'état présent dépend du **chemin suivi**, pas seulement des forces actuelles ;
un résidu du passé (enregistrement, habitude, infrastructure, règle héritée, réputation) continue
d'agir.

**Structure mathématique** : dépendance au chemin et rendements croissants (David 1985,
Arthur 1989) ; processus non markoviens (à mémoire). *Domaine* : systèmes dynamiques, processus
stochastiques.
> L'hystérésis, structure de SEUIL, est un **cas particulier** de dépendance au chemin : la relation
> SEUIL / TRACE est une inclusion (`antagonismes.md` §4bis), pas une confusion de définitions.

**Marqueurs observables** :
- un élément présent dont l'origine est datable ;
- qui continue d'orienter les conduites ;
- et qui ne serait pas choisi tel quel si l'on repartait de zéro aujourd'hui (signe que c'est
  l'histoire, et non la situation actuelle, qui le maintient).

**Registre anthropologique** — *documenté* : « memory », « myths », « folklore », « death rituals »,
« mourning », « inheritance rules ».

**Garantie type** (A6, 0.6.0) — *mécanisme* : l'état présent dépend du chemin suivi, pas seulement des forces actuelles ; *attendu* : un trait présent inexplicable par les forces actuelles, expliqué par un événement passé daté ; *contredirait* : un état entièrement expliqué par les forces présentes.

**À ne pas confondre avec** :
- *PÉRIODICITÉ* — voir PÉRIODICITÉ.
- *TRANSFORMATION* — voir TRANSFORMATION.
- *CONTRAINTE* — voir CONTRAINTE.
- *SEUIL* — voir SEUIL.

**Question d'exploration** : qu'est-ce qui reste et agit encore — et qui le porte maintenant ?

**Signature** : `◊` TRACE

---

## CROISSANCE

**Définition** : augmentation d'une grandeur dont le taux dépend de la grandeur elle-même, jusqu'à
une limite de capacité ; inclut les régimes exponentiel, logistique, de saturation et de déclin.

**Structure mathématique** : équations de croissance (exponentielle, logistique de Verhulst 1838,
Gompertz 1825) ; point d'inflexion ; capacité limite. *Domaine* : équations différentielles.

**Marqueurs observables** :
- au moins trois mesures datées d'une même grandeur ;
- un taux estimable ; une limite identifiée ou une saturation visible.

**Registre anthropologique** — *partiel* : documenté pour le cycle de vie des **personnes**
(« age grades », « age statuses », « age terms », « classification of age », « weaning ») ;
**à établir** pour la croissance et le déclin des collectifs.

**Garantie type** (A6, 0.6.0) — *mécanisme* : une grandeur augmente à un taux qui dépend de son propre niveau, jusqu'à une limite ; *attendu* : une série datée, d'une même source, dont l'accroissement suit le niveau atteint ; *contredirait* : une hausse ponctuelle, ou à taux indépendant du niveau.

**À ne pas confondre avec** :
- *TRANSFORMATION* — voir TRANSFORMATION.
- *ÉMERGENCE* — voir ÉMERGENCE.
- *PROPORTION* — voir PROPORTION.

**Question d'exploration** : à quel point de sa courbe est la grandeur — et quelle limite la
freinera ?

**Signature** : `▲` INTENSITÉ

---

## COMMUNAUTÉ

**Définition** : coopération d'un collectif de **plus de deux** membres autour d'un bien ou d'un
projet commun, avec des règles d'appartenance et de contribution, et un problème de passager
clandestin à gérer.

**Structure mathématique** : jeux de biens publics à n joueurs ; jeux coopératifs de coalition
(cœur, valeur de Shapley) ; gouvernance des communs (Ostrom 1990). *Domaine* : théorie des jeux
coopératifs, économie institutionnelle.
> Retiré en v0.4 : le dilemme du prisonnier itéré, jeu bilatéral dont le mécanisme canonique est
> celui de RÉCIPROCITÉ.

**Marqueurs observables** :
- un bien ou un projet commun nommé par les membres eux-mêmes ;
- contributions et règles d'appartenance observables ;
- un dispositif contre le passager clandestin (contrôle, sanction, exclusion, pression).

**Registre anthropologique** — *documenté* : « cooperation », « cooperative labor », « coalitions »,
« group living », « collective identities ».

**Garantie type** (A6, 0.6.0) — *mécanisme* : plus de deux membres coopèrent autour d'un bien commun, avec règles d'appartenance et risque de passager clandestin ; *attendu* : des règles d'appartenance ou de contribution, et un écart de contribution reproché ; *contredirait* : une coopération sans règle, ou à deux parties seulement.

**À ne pas confondre avec** :
- *RÉSEAU* — voir RÉSEAU.
- *RÉCIPROCITÉ* — voir RÉCIPROCITÉ.
- *RÉSONANCE* — Question : *s'agit-il d'une coopération organisée autour d'un bien (→ COMMUNAUTÉ)
  ou d'un alignement de rythmes (→ RÉSONANCE) ?*

**Question d'exploration** : quel bien tient le collectif ensemble — et qui en profite sans
contribuer ?

**Signature** : `⟶` TRANSMETTRE

---

## RÉSONANCE

**Définition** : plusieurs systèmes ayant chacun leur rythme propre se synchronisent par couplage ;
au-delà d'une force de couplage, les rythmes s'alignent.

**Structure mathématique** : oscillateurs couplés ; modèle de Kuramoto ; entraînement (verrouillage
de phase). *Domaine* : physique des systèmes non linéaires.

**Marqueurs observables** :
- au moins deux rythmes propres identifiés ;
- l'observation de leur alignement (simultanéité, cadence commune, gestes synchrones) ;
- un canal de couplage (co-présence, signal partagé, musique, horaire commun).

**Registre anthropologique** — *documenté* : « music », « dance », « rhythm », « music related in part
to dance », « rituals ». L'entraînement lui-même n'est pas un item de Brown ; il est documenté en
biologie et en psychologie expérimentale.

**Garantie type** (A6, 0.6.0) — *mécanisme* : des systèmes à rythmes propres se synchronisent par un couplage ; *attendu* : un rapprochement daté des rythmes après un couplage identifié ; *contredirait* : une synchronie imposée par un calendrier commun (PÉRIODICITÉ), ou sans couplage.

**À ne pas confondre avec** :
- *RÉCIPROCITÉ* — voir RÉCIPROCITÉ.
- *COMMUNAUTÉ* — voir COMMUNAUTÉ.
- *PÉRIODICITÉ* — voir PÉRIODICITÉ.

**Question d'exploration** : qu'est-ce qui s'aligne — et que se passe-t-il quand le couplage
s'interrompt ?

**Signature** : `✶` RÉVÉLER

---

## Références

- Anderson, P. W. (1972). More is different. *Science*, 177.
- Arthur, W. B. (1989). Competing technologies, increasing returns, and lock-in by historical events. *Economic Journal*, 99.
- Axelrod, R. (1984). *The Evolution of Cooperation*. Basic Books.
- Bak, P., Tang, C., & Wiesenfeld, K. (1987). Self-organized criticality. *Physical Review Letters*, 59.
- Brown, D. E. (1991). *Human Universals*. McGraw-Hill (chap. « The Universal People »). Liste citée dans sa compilation reprise par Pinker, S. (2002). *The Blank Slate*. Viking.
- Burt, R. (1992). *Structural Holes*. Harvard University Press.
- David, P. (1985). Clio and the economics of QWERTY. *American Economic Review*, 75.
- Ferguson, A. (1767). *An Essay on the History of Civil Society*.
- Gompertz, B. (1825). On the nature of the function expressive of the law of human mortality. *Philosophical Transactions of the Royal Society*, 115.
- Gouldner, A. (1960). The norm of reciprocity. *American Sociological Review*, 25.
- Hayek, F. A. (1973). *Law, Legislation and Liberty*, vol. 1 : *Rules and Order*. University of Chicago Press.
- Huxley, J. (1932). *Problems of Relative Growth*. Methuen.
- Kleene, S. C. (1938). On notation for ordinal numbers. *Journal of Symbolic Logic*, 3.
- Klein, F. (1872). *Vergleichende Betrachtungen über neuere geometrische Forschungen* (programme d'Erlangen).
- Kuramoto, Y. (1984). *Chemical Oscillations, Waves, and Turbulence*. Springer.
- Landau, H. G. (1951). On dominance relations and the structure of animal societies. *Bulletin of Mathematical Biophysics*, 13.
- Markowsky, G. (1992). Misconceptions about the golden ratio. *College Mathematics Journal*, 23.
- Merton, R. K. (1948). The self-fulfilling prophecy. *Antioch Review*, 8.
- Ostrom, E. (1990). *Governing the Commons*. Cambridge University Press.
- Scott, J. C. (1972). Patron-client politics and political change in Southeast Asia. *American Political Science Review*, 66.
- Shannon, C. E. (1948). A mathematical theory of communication. *Bell System Technical Journal*, 27.
- Verhulst, P.-F. (1838). Notice sur la loi que la population suit dans son accroissement. *Correspondance mathématique et physique*, 10.
- Watts, D., & Strogatz, S. (1998). Collective dynamics of 'small-world' networks. *Nature*, 393.
