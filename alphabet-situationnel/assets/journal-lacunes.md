# Journal des lacunes

> Entrées **historiques transmises, non revérifiées** (A8, `validation.md` §6). À recopier dans votre propre `journal-lacunes.md`.
> Après vérification des sources, trois entrées indépendantes sur le même motif ouvrent la procédure d'admission d'une carte (A2).

## Lacune 1 — 2026-10-25

Situation : en France, des violences en marge des manifestations du 17 octobre 2026 ont conduit, une
semaine plus tard, à des interdictions de rassemblement, à un parcours modifié et à la fermeture de
stations de métro pour la journée du 24 octobre.
Strate(s) : 5 (Organisations), avec des effets en 8 (Droit : arrêtés préfectoraux).
Motif nommé en clair : **épisode borné et réversible qui modifie durablement les conduites sans
franchir de seuil** — rien d'irréversible le 17, et pourtant une trace qui oriente la suite.
Cartes testées et pourquoi elles ne conviennent pas :
- TRACE·MÉMOIRE décrit bien le **résultat** (un résidu daté qui oriente les conduites), mais aucune carte
  de l'état du 19 octobre n'y mène dans `dynamiques.md` (TRACE n'y est atteinte que depuis SEUIL,
  ÉMERGENCE et TRANSFORMATION) : l'outil ne peut pas proposer son apparition.
- SEUIL : rejeté, aucun passage irréversible (A6 : voisine TRACE · MÉMOIRE `←`).
- POLARITÉ : rejetée au test, une position intermédiaire reste visible et non disqualifiée.
Qualificatifs testés : `{délai}` décrit l'intervalle (17 → 24 octobre) mais suppose une structure déjà
ancrée qui le porte ; aucune ne l'est.
Question ouverte : manque-t-il une **carte** (l'épisode comme structure), ou seulement des **arêtes**
vers TRACE (une contrainte ou une action collective appliquée laisse une trace) ? À trancher avec les
entrées suivantes, pas sur ce seul cas.
Source : test sur cas réel du 2026-10-25 (rapport de l'utilisateur ; faits et sources tels que rapportés).

## Lacune 2 — 2026-10-25

Situation : négociations Ukraine–Russie–États-Unis ; le canal de médiation américain, bilatéral
(neuf rencontres Witkoff–Poutine), devient trilatéral le 23 octobre 2026, sans rupture ni cessez-le-feu.
Strate(s) : 7 (Géopolitique).
Motif nommé en clair : **changement de forme d'une structure persistante** (RÉSEAU@7 garde ses
parties et son objet, change de configuration), que la matrice ne produit pas : TRANSFORMATION n'y est
atteinte que depuis SEUIL, CONTRAINTE, PROPORTION et HIÉRARCHIE.
Cartes testées : TRANSFORMATION décrit le résultat ; RÉSEAU persiste ; aucune carte présente ne mène à
TRANSFORMATION avec une intensité utile (seulement CONTRAINTE@7, faible, ancrée f).
Lien avec la lacune 1 : le test propose d'y voir la même classe (« ce qui se transforme sans rompre »).
Les cartes manquées diffèrent (TRACE·MÉMOIRE, TRANSFORMATION) ; à confirmer par une troisième entrée
indépendante, de préférence issue d'un test à l'aveugle.
Ce qui a été fait en v0.3.0 : l'événement « X@s se transforme » est devenu exprimable ; sa probabilité
reste celle d'une apparition non ancrée (0,4 % sur 6 jours). La lacune porte donc autant sur
l'**absence de fréquence de référence** des changements de forme que sur la matrice.
Source : test régressif du 2026-10-25 (rapport et fiche C-0002-S07 de l'utilisateur ; rejeu).

## Lacune 3 — 2026-10-27 · ancrages des cas réels devenus hors marqueur local (0.6.4) — **close (0.6.8)**

> Close sans recodage : les quatre cas ont été archivés par décision d'auteur (`feuille-de-route.md` §4).
> Le constat reste valable pour tout nouveau codage : un fait qui ne remplit que le marqueur abstrait
> s'ancre en f (A1).

Situation : la strate 7 est passée de 0 à 13 équivalents Documentés (0.6.2 à 0.6.4). Les marqueurs
locaux, alignés sur les sources lues, sont plus étroits qu'avant. Selon A1, un fait qui ne remplit que
le marqueur abstrait de la carte s'ancre par le noyau, et sa force ne dépasse pas f.
Ce n'est pas un motif nouveau mais une **dette de codage** : trois mots des propositions sont à
trancher avant leur activation (`feuille-de-route.md` §4 et §5.1).

| Mot | Fait codé | Marqueur local 0.6.4 | Décision proposée par Claude |
|---|---|---|---|
| C-0002-S07 · INCERTITUDE@7 **F** | Zelensky conditionne des élections à un cessez-le-feu ; Trump suspend des sanctions | « refus déclaré de préciser sa réaction » (ambiguïté stratégique) | **recoder f** : des conditions croisées non remplies laissent l'issue ouverte (marqueur abstrait), mais personne ne refuse de dire comment il réagira. Garantie et option deviennent facultatives. Alternative : trouver un fait d'ambiguïté déclarée dans la fenêtre et garder F |
| C-0003-S07 · CONTRAINTE@7 **F** | suspension des opérations de l'aéroport de Riyad ; avertissement d'évacuation à Sanaa | « option commerciale retirée par une sanction, ou option militaire plafonnée par un traité » | **recoder f** : la contrainte est matérielle (menace de frappe), ce que le noyau couvre et l'équivalent local non. Alternative : ajouter à la strate 7 un second équivalent de CONTRAINTE (« interdiction d'usage imposée par la menace ») — à éviter tant qu'une seule fiche le demande |
| C-0002-S07 · TRANSFORMATION@7 f | le canal de médiation bilatéral devient trilatéral | « alliance qui change de missions et de moyens par étapes » | **conserver f** : un format de négociation n'est pas une alliance, mais le mot est déjà f et s'ancre par le noyau (une entité qui change de forme en gardant ses parties, A1). Aucun changement ; la lacune 2 reste ouverte |

Correction du CHANGELOG 0.6.4 : il comptait trois ancrages « qui ne remplissent plus le marqueur
local » ; deux seulement posent problème (les F). Le troisième, déjà f, est conforme à A1.
Source : audit de la version 0.6.4 (constat O3) et relecture des fiches, 2026-10-27.

## Lacune 4 — 2026-11-03 · CONTRAINTE@7 sans effet sur RÉCIPROCITÉ@7

Situation : test FR-RU (`validation.md` §23), date d'information 2026-06-30. État : CONTRAINTE@7[f] (sanctions de l'UE
contre la Russie en vigueur). Événement : RÉCIPROCITÉ@7 apparaît (expulsions de diplomates en miroir France–Russie).
Constat : la matrice n'a pas d'arête CONTRAINTE → RÉCIPROCITÉ en strate 7 ; produit des λ = 1, p = fréquence par défaut.
Or le marqueur local de RÉCIPROCITÉ@7 inclut les « sanctions en miroir » : une sanction en vigueur est un terrain
de réciprocité, et le moteur ne la voit pas. Nature : **manque de données** plutôt que de vocabulaire ; aucune arête
n'est ajoutée sans cas (P1). À `confronter` dès qu'existeront des cas réels où une contrainte précède, ou non, une
réciprocité. Issue du test : 0 (aucune expulsion), donc aucune indication sur le sens de l'arête.
Source : test régressif du 2026-11-03 (registre de l'utilisateur, ligne P-0001 FR-RU).
