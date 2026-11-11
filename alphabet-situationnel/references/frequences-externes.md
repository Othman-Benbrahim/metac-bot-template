# Alphabet situationnel — Fréquences externes (étape 4)

> Version : 0.7.74

> Comment établir une fréquence de référence que l'on passe à `--references`. Charger ce fichier pour
> constituer ou relire un fichier de références ; il ne sert pas à lire une situation.

---

## 1. Ce qu'est une fréquence de référence

Une fréquence de référence est le taux auquel un événement **défini sans l'alphabet** survient, dans une
population de cas comptés par une source extérieure, sur une fenêtre donnée. Elle n'est ni une
probabilité calibrée pour la question posée, ni un p : elle entre dans f comme référence de la loi Beta
de `graphe.md` §2.2, avec k₀ = 20 pseudo-observations, puis les cartes et les homologues la révisent.
Une référence externe rend la question **ancrée** (accès à ρ3) quel que soit l'effectif de la base ;
ancré ne veut pas dire juste. Elle déplace des p : c'est une donnée, pas une version du skill.

## 2. Les six champs

```json
{"SEU@7 apparait": {
  "frequence": 0.031,
  "source": "nom du jeu de données, version, éditeur, adresse",
  "definition": "nouvel épisode de conflit armé interétatique, au sens de la source",
  "periode": "1990-2020",
  "fenetre": "3 mois",
  "disponible_le": "2026-11-15"}}
```

Les nombres ci-dessus sont **fictifs**. `frequence` : dans ]0 ; 1[, déjà ramenée à la fenêtre ;
`source` : ce qui permet à un tiers de refaire le compte ; `definition` : la classe, dans le vocabulaire
de la source ; `periode` : les années comptées ; `fenetre` : celle de l'état (une référence d'une autre
fenêtre est refusée) ; `disponible_le` : date à laquelle le chiffre était consultable, jamais postérieure
à la date d'information. `moteur.py valider-references F.json` contrôle la forme, refuse la source du
gabarit et la classe tautologique (§5) ; `calculer --references` applique les mêmes refus.

**Champs facultatifs (0.7.10)**, contrôlés s'ils sont présents. `interet` : `aucun`, `declare` (avec
`fourni_par` : qui fournit le taux, et son intérêt) ou `promoteur` — une fréquence fournie par une partie
prenante de l'issue est **refusée** : c'est la « représentation stratégique » de Flyvbjerg (2008), un fait
fabriqué, pas une donnée. `referentiel` : le point à partir duquel le taux est mesuré (pour un dépassement :
décision de construire, signature du contrat…) ; deux taux de référentiels différents ne se comparent pas,
c'est le cœur du désaccord entre Flyvbjerg et Love et Ahiaga-Dagbui (*Transportation Research Part A*,
2018). La méthode de la classe de référence a elle-même un promoteur, auteur de la base la plus citée :
ce n'est pas un motif de refus, c'est une raison de ne pas présenter cette base comme neutre.

## 3. Définir avant de compter

Trois questions, tranchées et écrites **avant** de consulter les chiffres :

1. **Qu'est-ce qu'un cas ?** Un pays, une dyade, une crise, un régime. L'unité de la source fixe la
   population ; changer d'unité change le taux.
2. **Qu'est-ce qu'un événement ?** Le critère de la source (seuil de victimes, niveau d'hostilité,
   adoption d'une sanction), qui doit correspondre au marqueur local de la résolution (S1). Un critère
   voisin se déclare (`ecart_marqueur`), il ne se tait pas.
3. **Quelle unité de comptage ?** Pays-mois, dyade-année, épisode. La fréquence est le nombre
   d'unités où l'événement survient, rapporté au nombre d'unités **exposées** (où il pouvait survenir) :
   une dyade déjà en guerre n'est pas exposée à « une guerre commence ».

## 4. Ramener à la fenêtre

À taux constant, une probabilité p_A d'occurrence sur une durée A devient, sur une fenêtre h :

p_h = 1 − (1 − p_A)^(h / A)

C'est la conversion du moteur pour son défaut (`a_l_echelle`). Diviser par quatre un taux annuel pour
trois mois sous-estime : 20 % par an donnent 1 − 0,8^0,25 = 5,4 % sur trois mois (et non 5 %), 60 % par an
en donnent 20,5 % (et non 15 %). La formule vaut pour « survient au moins une fois ». Pour « présent à
l'échéance », un phénomène qui peut cesser ne se convertit pas ainsi : il faut aussi sa persistance, donc
deux références (`graphe.md` §2.4). Un taux constant est une hypothèse ; une source qui montre une
saison ou un calendrier relève de `temporalite: programmee`.

## 5. Ne pas compter ce que l'alphabet a déjà codé

Une classe de référence ne se définit **jamais** avec le vocabulaire des cartes : compter « les épisodes de
POLARITÉ » revient à compter ses propres codages, ce qui n'est pas une référence externe. Refusé
automatiquement (nom ou abréviation d'une carte dans `definition`).

| Définition fautive | Réécriture |
|---|---|
| « cas où un SEUIL d'escalade est franchi » | « première utilisation de la force entre deux États membres d'une dyade, au sens de la source » |
| « situations de POLARITÉ entre blocs » | « dyades dont les votes à l'Assemblée générale divergent au-delà du seuil de la source, sur l'année » |

## 6. Sources utilisables en strate 7

Description indicative ; couvertures et versions à vérifier à la consultation.

| Source | Unité | Permet de compter | Ne permet pas |
|---|---|---|---|
| UCDP/PRIO, conflits armés | conflit-année, seuil de victimes annuel | apparitions et persistances de conflits armés impliquant un État | les crises sans violence, l'intensité infra-seuil |
| Correlates of War, MID | épisode et dyade, niveaux d'hostilité | menaces, démonstrations et usages de la force entre États | les années récentes au-delà de sa couverture |
| Bases de sanctions (TIES, Global Sanctions Database) | épisode de sanction | menaces et imposition de sanctions, leur levée | l'effet des sanctions sur les options |
| V-Dem, Polity | pays-année | changements de régime, seuils d'indices | les relations entre États |
| Banque mondiale (WDI) | pays-année | grandeurs macroéconomiques | les événements politiques |

## 7. Événements-cibles de la strate 7

État : `à établir` (aucune référence lue), `établie` (référence lue, fichier versé), `impossible` (aucune
source ne compte cette classe). `bilan --references` mesure l'étape 4.

| Événement | Classe candidate | Source pressentie | État |
|---|---|---|---|
| SEU@7 apparait | premier usage de la force dans une dyade, ou conflit armé nouveau | MID, UCDP | à établir |
| POL@7 persiste | dyade rivale qui le reste à l'horizon | listes de rivalités interétatiques, MID | à établir |
| CTR@7 apparait | imposition d'une sanction | TIES, Global Sanctions Database | à établir |
| CTR@7 disparait | levée d'une sanction | idem | à établir |
| RES@7 apparait | entrée en vigueur d'une alliance ou d'un accord de défense | ATOP, COW Alliances | à établir |

## 8. Ce que ce fichier ne fait pas

Il ne certifie pas la vérité des sources, ni que la classe représente la situation étudiée : ce jugement
reste humain et se déclare dans « À vérifier ». Une fréquence non datée, ou disponible après la date
d'information, n'est jamais utilisable. Une référence ne s'emprunte pas à un autre événement, ni à une
autre fenêtre.
