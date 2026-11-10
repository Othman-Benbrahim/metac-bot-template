# Alphabet situationnel — Incompatibilités et tensions

> Version : 0.7.59

> **Origine.** Repris de NEXUS-ARCHÊ v0.4.2 (`antagonismes.md`) sans modification des tables.
> Usage dans ce skill : la table du §3 alimente la règle de bonne formation G6 (une paire
> incompatible sur le même objet impose un rejet ; « indépendance » exige deux objets distincts) et la configuration Lacune
> contradictoire (G4). Le §5 hérité (fréquences en tirage aléatoire) ne
> s'applique pas, ce skill n'ayant pas de tirage aléatoire : il est déplacé en annexe. Renvois : R6 → G3 ;
> « Mode 2 » → liaisons d'un état (G3) ; « Mode 3 » → positions *tient / bouge / manque* (G4) ;
> « configuration 3 » → Lacune contradictoire (G4).

> Définit deux relations entre cartes, distinctes de la **confusion** (mesurée par l'accord entre codeurs, A4) :
> l'**incompatibilité** (les deux définitions ne peuvent pas être vraies du même objet au même
> moment) et la **tension documentée** (co-présence fréquente et informative, sans exclusion).
> Seule l'incompatibilité alimente la configuration 3 du Mode 3.

---

## 1. Trois relations à ne pas confondre

| Relation | Porte sur | Exemple | Usage |
|---|---|---|---|
| **Confusion** | le lecteur | PÉRIODICITÉ ↔ RÉCURSIVITÉ | choisir la bonne carte (question discriminante) |
| **Incompatibilité** | les définitions | INCERTITUDE ↮ CONTRAINTE | configuration 3 du Mode 3 |
| **Tension documentée** | les situations | RÉCIPROCITÉ ~ HIÉRARCHIE | énoncé structurel du Mode 2 ou 3 |

**Règle** : ne jamais dériver une incompatibilité du « ou » d'une question discriminante. Ce « ou »
dit quelle carte retenir pour *cette* lecture, pas que les structures s'excluent dans le monde.

---

## 2. Critère d'inscription (durci en v0.4)

Une paire est incompatible si, et seulement si, les deux définitions de `cartes.md` attribuent au
**même objet**, **au même moment**, deux prédicats contradictoires.

Sont donc **exclus** :
- les relations **séquentielles** (l'une avant, l'autre après) ;
- les **aspects** différents d'un même objet (un rapport peut avoir un axe d'obligation et un axe
  de pouvoir) ;
- les exclusions obtenues par **stipulation** (définir une carte « sans » la propriété de l'autre).

Chaque ligne cite le texte de `cartes.md` qui la fonde. Toute modification de `cartes.md` impose de
revérifier les citations.

---

## 3. Table des incompatibilités

Deux paires sur 120. Relation symétrique.

| Paire | Fondement (citations de `cartes.md`) | Objet commun requis |
|---|---|---|
| ÉMERGENCE ↮ TRANSFORMATION | ÉMERGENCE : « une régularité collective […] apparaît » ; TRANSFORMATION : « une entité **existante** change de forme ». Une même entité ne peut pas, au même moment, apparaître et préexister. | la même entité (norme, rôle, organisation) |
| INCERTITUDE ↮ CONTRAINTE | INCERTITUDE : « plusieurs états […] restent possibles » ; CONTRAINTE : « retire des options de l'espace des possibles ». Une même option ne peut pas être à la fois ouverte et exclue. | la même option ou le même état futur |

---

## 4. Tensions documentées (anciens antagonismes requalifiés)

Les sept paires suivantes figuraient en v0.3.1 comme antagonismes. Elles ne passent pas le critère
du §2. Elles restent utiles : leur co-présence est fréquente et dit quelque chose de la situation.

| Paire | Pourquoi ce n'est pas une incompatibilité | Ce que la co-présence signale souvent |
|---|---|---|
| ÉMERGENCE ~ CROISSANCE | Aspects compatibles : le changement d'échelle fait apparaître des propriétés nouvelles (Anderson 1972). La v0.3.1 dérivait l'exclusion d'une question discriminante, ce que sa propre règle interdit. | une croissance qui change la nature du collectif |
| ÉMERGENCE ~ RÉCURSIVITÉ | L'exclusion reposait sur la stipulation « émergence sans auto-référence » ; la rétroaction est un mécanisme ordinaire de l'émergence. | un ordre qui se stabilise en se représentant lui-même |
| INCERTITUDE ~ ÉMERGENCE | Relation séquentielle (avant / après). | une forme qui commence à trancher entre des possibles |
| SEUIL ~ TRANSFORMATION | Depuis v0.4, SEUIL est défini par l'irréversibilité et non par la soudaineté : un changement progressif peut franchir un point de non-retour (la métamorphose). | une transformation qui a passé son point de non-retour |
| PÉRIODICITÉ ~ SEUIL | Séquentiel : un système peut basculer irréversiblement puis entrer en régime périodique (cycle limite après bifurcation). | un nouveau régime cyclique après une rupture |
| PÉRIODICITÉ ~ TRACE·MÉMOIRE | Un rituel annuel est un retour régulier **et** une trace ; la mémoire est même la condition d'un cycle (conserver sa phase). | un retour régulier qui transporte un héritage |
| RÉCIPROCITÉ ~ HIÉRARCHIE | Aspects différents d'un même rapport : obligation réciproque sous asymétrie de statut (patron-client ; Gouldner 1960, Scott 1972). | une dépendance entretenue par la dette |

---

## 4bis. Inclusions documentées

Deux cartes peuvent décrire le même objet parce que la structure de l'une est un **cas particulier**
de celle de l'autre. Ce n'est ni une incompatibilité ni une confusion de définitions ; c'est une
relation d'**inclusion** au sens de R6.

| Inclusion | Fondement | Conséquence pour la lecture |
|---|---|---|
| HIÉRARCHIE ⊂ RÉSEAU | une hiérarchie est un graphe orienté acyclique enraciné (`cartes.md`, HIÉRARCHIE) | retenir HIÉRARCHIE quand l'ordre de préséance organise la situation, RÉSEAU quand c'est la topologie |
| SEUIL ⊂ TRACE·MÉMOIRE | l'hystérésis (SEUIL) est un cas de dépendance au chemin (TRACE) | retenir SEUIL quand le point de non-retour est l'objet, TRACE quand c'est l'effet persistant d'un passé ; les deux peuvent être retenues avec des faits distincts |

### Paires examinées et écartées (inchangé depuis v0.3.1)

| Paire | Raison |
|---|---|
| POLARITÉ / RÉSONANCE | Deux oscillateurs peuvent se coupler en opposition de phase. |
| PROPORTION / INCERTITUDE | Un rapport mal connu reste un rapport. L'opposition `◯` / `Ø` n'existe qu'entre glyphes STÈLE. |
| COMMUNAUTÉ / RÉSEAU | Une communauté a une topologie ; un réseau peut porter un projet. |
| HIÉRARCHIE / RÉSEAU | Une hiérarchie est un graphe particulier (inclusion, §4bis). |
| CROISSANCE / CONTRAINTE | La croissance logistique est définie par sa limite. |

---

## 6. La condition du même objet

Une incompatibilité ne devient une contradiction que si les deux cartes portent sur **le même
objet**. INCERTITUDE sur le futur d'un financement et CONTRAINTE sur le périmètre d'action ne se
contredisent pas.

Le signal ouvre donc une question, posée à l'auteur de la situation et non tranchée par le modèle :

> *Ces deux structures portent-elles sur la même chose ?*

Oui → configuration 3 avérée. Non → constellation ordinaire ; noter au journal (§7) un faux positif
de portée.

---

## 7. Journal

*Vide à la publication. Rien dans ce fichier n'est encore validé par l'usage.*

```
## Entrée N — [date]
Signature : [tient / bouge / manque]
Paire signalée : [A ↮ B]
Même objet ? : [oui / non] — [objets visés]
Verdict : [configuration avérée / faux positif de portée]
Observation : [ce que l'entrée apprend sur la table]
```

**Règles d'évolution**
- Trois faux positifs de portée sans aucune configuration avérée → la paire est retirée.
- Une paire n'est ajoutée qu'avec la citation de `cartes.md` qui satisfait le critère du §2.
- Une tension documentée ne devient jamais incompatibilité par accumulation d'usages.

---

## Annexe · Hérité de NEXUS-ARCHÊ, non applicable

### Fréquences en tirage aléatoire uniforme sans remise

560 constellations non ordonnées, 3 360 ordonnées. Calcul : `nexus_tool.py stats`, script de NEXUS-ARCHÊ, absent de ce skill.

| Configuration | v0.3.1 (9 paires) | v0.4 (2 paires) |
|---|---|---|
| 3 — *tient* et *manque* incompatibles | 252 / 3 360 = 7,5 % | **56 / 3 360 = 1,67 %** |
| ancienne 4 — au moins deux paires incompatibles | 10 / 560 = 1,8 % | **0 / 560** — supprimée |

La configuration 4 est **supprimée** : avec deux paires disjointes, aucune constellation ne peut
contenir deux paires incompatibles. Elle mesurait surtout, en v0.3.1, la présence d'ÉMERGENCE avec
l'un de ses quatre antagonistes, dont trois étaient contestables.

Ces taux n'ont de sens qu'en tirage aléatoire. En tirage délibératif, l'analyste ne tire pas au hasard.
