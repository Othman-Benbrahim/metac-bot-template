# Alphabet situationnel — Validation (couche 6)

> Version : 0.7.75

> Contrat du journal, scores et limites d'évaluation. Règles V1–V4. Le scoreur valide les données
> avant calcul et ne prononce jamais une certification scientifique automatique.

---

## 1. Journal des prévisions (V1)

Une prévision est figée avant son échéance ; une ligne de score s'ajoute sans modifier la première.
Exemple **fictif** de structure (remplacer les chaînes SHA256 par les empreintes réelles du JSON
moteur ; null si indisponibles, auquel cas la prévision reste hors V4) :

```json
{
  "type": "prevision",
  "id": "P-0042",
  "date": "2026-09-01",
  "version_regles": "0.7.0",
  "question": "POL@7 persiste au 2026-12-01 ?",
  "evenement": "POL@7 persiste",
  "resolution": {
    "source": "Registre entièrement fictif de la démonstration",
    "critere": "Observation simulée du marqueur deux blocs, alignements exclusifs",
    "seuil": "Présence constatée à la date finale selon le scénario fictif",
    "marqueur": "deux blocs, alignements exclusifs",
    "objet": "Situation fictive A-B"
  },
  "etat_present": "[2026-09 | 3 mois] POLARITÉ@7[F] + CONTRAINTE@6[F]",
  "probabilite": 0.8168065470680189,
  "intervalle": [
    0.6713359462373685,
    0.9383666673288151
  ],
  "rho": "ρ1",
  "echeance": "2026-12-01",
  "indicateur_bascule": "Nouvel acte consigné dans le registre fictif",
  "refutation": "Critère non observé à échéance",
  "partition": null,
  "frequence_de_base": 0.8372000588523011,
  "p_sans_cartes": 0.8372000588523011,
  "p_placebo": null,
  "graine_placebo": null,
  "apport_homologie": null,
  "temporalite": "generique",
  "rejeu": true,
  "fictif": true,
  "episode_id": "DEMO-A-B",
  "semantique": "continue",
  "pas": 1,
  "resolution_verifiee": true,
  "empreintes": {
    "moteur": "SHA256_DU_MOTEUR",
    "parametres": "SHA256_DES_PARAMETRES",
    "base": "SHA256_DE_LA_BASE"
  },
  "preuve_prepublication": null
}
```

Ligne de score :

```json
{"type":"score","id":"P-0042","date":"2026-12-02","issue":1,"preuve":"Observation stipulée, entièrement fictive"}
```

`p_sans_cartes` (obligatoire depuis 0.5.0, null pour un composé) est la probabilité du même calcul sans
cartes, que `calculer` imprime à côté de p : le **comparateur inertiel**. `scorer` en tire
`apport_des_cartes` (Brier avec cartes moins Brier sans cartes) : un score flatteur dont l'apport est
nul ne vient que du statu quo et ne valide pas la lecture (exemple 11).
**Placebo d'homologie (0.7.4, décision 3).** `p_placebo`, `graine_placebo` et `apport_homologie`
(obligatoires depuis 0.7.4, null si non évaluable) recopient le placebo de `calculer` : autant de cas
que la classe retenue, tirés au hasard dans la même strate et la même fenêtre, sous le même a priori,
moyennés sur `placebo_tirages` tirages (§H), graine dérivée de la question et non choisie.
`apport_homologie` = p − p_placebo sépare ce qu'apporte l'analogie structurale de ce qu'apporte le taux
de base de la strate ; `apport_cartes` (p − p_sans_cartes) mesure, lui, les multiplicateurs et la
classe ensemble. Un apport d'homologie nul se publie comme tel.
**Sceau de dossier (0.7.4, décision 1).** À compter de `v4_dossier_depuis` (§H, 2026-10-29), une
prévision du moteur n'est éligible à V4 que si son calcul figé porte le sceau d'un dossier de lecture
(`calculer --dossier`) et si `preuve_dossier` `{source, date, sceau}` atteste sa publication (adresse
`https://` d'un dépôt daté) **au plus tard à la date d'information** du calcul, avec le même sceau.
Prospectif : les prévisions antérieures restent au journal, hors de cette exigence ; rien n'est
invalidé rétroactivement. Un dossier incomplet (plancher A7) reste éligible mais se lit Spéculatif.
**Deux probabilités (0.6.0).** Avant de lancer le moteur, le codeur écrit sa propre probabilité et la
scelle : `moteur.py sceller-jugement --question … --evenement … --p … --date …` rend
`probabilite_jugement` et `jugement_scelle`, à recopier dans la ligne. Le champ est obligatoire à
partir des prévisions 0.6 (null si aucun jugement n'a été scellé) ; un scellé qui ne correspond pas à
la question, à l'événement, à la date ou à la probabilité est refusé. `scorer` rend alors
`moteur_contre_jugement` : Brier du jugement, Brier du moteur, nombre d'**améliorations** et de
**dégradations** question par question — une amélioration moyenne peut cacher des dégradations.
`bande_sensibilite` (facultatif) recopie la bande de sensibilité de `calculer` (`graphe.md` §2.3).
Le scellé local ne prouve pas la date : seul le dépôt externe le fait (§8).

**Difficulté des questions (0.6.0 ; sens corrigé en 0.6.5).** `scorer` rend `difficulte` :
0,5 − |f − 0,5| par question (0 pour une question jouée d'avance, 0,5 pour une question à 50 %), f étant la
fréquence de base au même horizon (à défaut, `p_sans_cartes`), la part des questions à référence
extrême (f < 0,1 ou > 0,9) et le Brier par tranche. Au-delà de 70 % de questions extrêmes, un bon
score ne mesure pas la compétence : prédire « non » à 0,8 % est presque gratuit (exemples 11 et 12).

**Questions hors alphabet** (`"origine": "jugement"`). L'alphabet décrit des structures, pas des issues
nominatives : « qui sera élu ? », « le groupe aura-t-il quatorze membres ? » ne sont pas des événements
de cartes. Une telle question se journalise avec une probabilité **humaine** : champs `question`,
`evenement` (texte libre), `episode_id`, `refutation`, `echeance`, `probabilite`, `rejeu`, `fictif`,
`resolution` (`source`, `critere`, `seuil`) ; sans état, ni ρ, ni comparateur. `scorer` la note dans
`jugements` (Brier, référence d'une réponse indifférente, incertitude annoncée), **jamais** dans le
score du moteur ni dans V4 : c'est la calibration du codeur, que le moteur ne mesure pas.
**Procédure (0.7.10).** « Jugement » sous-spécifiait : le jugement nu est la condition la moins bien
mesurée sur ces questions (32 % de justesse sur huit conflits, Green et Armstrong 2007 ; Green 2005), et des
procédures de référence existent. Champ `procedure`, requis pour une ligne `jugement` datée à partir de
`jugement_procedure_depuis` (§H), facultatif avant : `seul`, `compromis` (moyenne des positions des
acteurs pondérée par leur poids et leur saillance, l'étalon des modèles de négociation dans Thomson,
Stokman, Achen et König 2006, *The European Union Decides*), `simulation` (plusieurs passes indépendantes,
fréquence des issues), `analogies` (cas listés **avant** toute notation de similitude, règle de dérivation
fixée d'avance), `autre`. `scorer` rend `jugements.par_procedure`, descriptif : aucun test, les effectifs
seront petits, et les chiffres cités viennent pour l'essentiel d'une seule équipe (`apports-theoriques.md`
§14).
`issue` vaut 0, 1 ou null, et le champ est obligatoire : null se déclare, il ne se déduit pas d'une
absence. `rejeu` et `fictif` sont obligatoires ; leur absence est une erreur. `calcul`, s'il est
présent, est le JSON du moteur qui a produit la prévision : `probabilite` doit égaler `calcul.p` et
`rho` doit égaler `calcul.rho` (contrôlé depuis 0.4.4), faute de quoi le chiffre scoré n'est plus
celui qui a été calculé. Depuis 0.6.9, la question entière est recoupée : événement, état
(`calcul.etat`), pas, sémantique, échéance, `p_sans_cartes` et intervalle. Un calcul étiqueté pour un
autre événement, ou un comparateur sans cartes recopié faux, est refusé. Depuis 0.6.10 aussi :
`frequence_de_base` doit égaler `calcul.comparateur` ; un intervalle journalisé alors que le calcul
ne l'a pas estimé est refusé ; `resolution.marqueur` doit recopier le marqueur local du calcul
(`calcul.marqueur_local`), sinon `resolution.ecart_marqueur` justifie l'écart (S1). La **pertinence**
de la source de résolution reste un jugement humain ; sa **conservation** est garantie par
l'empreinte de la prévision (`sceller`, §8).

**Abstentions (0.6.11).** Quand le moteur répond « non estimée » (`calcul.p` null : temporalité
déclarée sans référence, composé sans référence conditionnelle), la prévision se journalise quand même,
comme **abstention** : `probabilite: null`, calcul joint, hors partition. Une probabilité ajoutée à la
main sur un calcul non estimé est refusée : ce chiffre ne viendrait pas du moteur (le journaliser
comme jugement, `origine: jugement`, s'il est celui du codeur). `scorer` rend `abstentions` (nombre,
part des questions, issues réalisées) à côté du Brier, qu'elles n'entrent pas : une abstention ne vaut
pas une prédiction parfaite, et un outil qui s'abstiendrait sur les questions difficiles améliorerait
son score sans rien prévoir. Scores et abstentions se lisent ensemble.

**Temporalité (0.6.10).** Chaque prévision déclare `temporalite` : `generique`, `programmee`
(échéance fixée par un texte : scrutin, proclamation, échéance légale) ou `duree_de_vie` (phénomène à
durée de vie propre, sans rapport avec la fenêtre de référence de 3 mois : cyclone, grève reconductible,
session). Hors `generique`, seule une référence externe permet de chiffrer (0.6.13) : la prévision
joint son calcul, dont `reference_de_domaine` vaut true ; des cas homologues seuls ne suffisent pas.
Sinon `calculer --temporalite …` répond « non estimée » (à journaliser comme abstention).
`trajectoires` refuse l'option (0.6.11) : ses chemins reposent sur les taux génériques de toutes les
cartes à la fois. Le moteur ne sait pas reconnaître seul une
échéance ou une durée de vie : la déclaration est humaine, son effet est contrôlé. Depuis 0.6.12,
`calculer` n'a plus de valeur par défaut : sans `--temporalite`, il refuse de calculer et pose la
question ; un oubli ne retombe plus sur l'inertie générique.
`episode_id` regroupe les questions liées au même épisode, même si leurs cartes ou strates diffèrent.
`semantique` décrit présence finale, occurrence au moins une fois ou persistance continue.
`resolution_verifiee` signifie que le lien entre marqueur, objet et critère a été contrôlé, pas que
l'issue est connue. `preuve_prepublication` vaut null ou contient `source`, `date` et `empreinte_prevision` d'un dépôt externe
antérieur à l'échéance, jamais une affirmation inventée. Les `empreintes` viennent du JSON du moteur.
La source du dépôt doit permettre de retrouver le journal et sa version, avec son empreinte publiée.
`sceller` fournit une empreinte par prévision, calculée sur tous ses champs sauf le reçu de
prépublication lui-même : ajouter ce reçu ne modifie pas le contenu figé. Le validateur vérifie sa
correspondance ; le tiers vérifie le dépôt externe. `pas` est obligatoire et contrôle l’échéance
à partir de la date d’état et de sa fenêtre. Un état postérieur à la prévision est interdit.
Une nouvelle édition remplace une prédiction seulement par un nouvel id, sans effacer l'ancienne.

Pour une partition : même question, date, échéance et épisode ; noms d'issues distincts ;
probabilités sommant à 1 ; comparateurs tous null ou sommant à 1 ; une seule issue réalisée.
Une partition partiellement scorée reste sans score complet ; une issue null la rend non résolue.
Doublons, scores orphelins, nombres invalides et score avant échéance sont refusés.

---

## 2. Score de Brier et fréquence de base

Binaire : (p−o)² ; partition : somme sur les catégories **divisée par 2**, **une seule question**
(0.6.13). La somme brute va de 0 à 2, le Brier binaire de 0 à 1 : sans la division, une partition
0,5/0,5 réalisée valait 0,50 contre 0,25 pour la binaire équivalente, et la moyenne d'un journal
mixte était majorée (audit 0.6.12). Divisée par 2, une partition à deux issues a exactement le score
de la binaire équivalente ; comparateur, sans-cartes et jugement suivent la même échelle. Les scores
d'archives antérieurs à 0.6.13 (exemples 7 à 11) sont sur l'ancienne échelle.
La fréquence de base provient du moteur, au **même horizon et pour le même événement**. Ne pas
comparer un pari annuel à une référence trimestrielle ; null signifie comparaison non évaluable.
Les questions d'un épisode sont moyennées, puis les épisodes reçoivent des poids égaux. Le gain est
1−Brier_outil/Brier_base sur les épisodes comparables ; si la base a une erreur nulle, gain non défini.
Les sources, définitions et valeurs non arrondies sont conservées au moment du calcul.

---

## 3. Mode SCORER

1. Lire et valider le journal ; lister les échéances, scores manquants et issues non résolues.
2. Résoudre par la source externe et le critère figés, sans recodage opportuniste ; ambiguïté → null.
3. Ajouter une preuve datée, puis une éventuelle lecture d'état pour le diagnostic, pas pour le score.
4. Exécuter `python3 scripts/moteur.py scorer journal.jsonl` (sortie JSON).
5. Distinguer scores indicatifs et questions éligibles : rejouer, simuler ou manquer de preuve de
   prépublication n'autorise pas une évaluation prospective. Vérifier réellement les dépôts externes.
6. Examiner erreurs et réussites par épisode et proposer des révisions sans réécrire les anciens paris.

---

## 4. Diagnostic par couche (V2)

| Couche | Question | Suite |
|---|---|---|
| Alphabet | Le codage distingue-t-il objet, marqueur et qualité de preuve ? Le passage cité soutient-il le fait tel qu'il est écrit (annonce ou réalisation, objet, acteur, date) ? | reprendre A6/A7, passages et sources |
| Grammaire | La résolution et la temporalité décrivent-elles bien l'événement ? | corriger les prochains contrats |
| Base | Échantillon, dates, disponibilité, indépendance des épisodes ? | revoir le plan de collecte |
| Graphe | Les cartes apportent-elles mieux que la référence seule ? | ablation et sensibilité, pas réglage sur le test |
| Simulation | Horizon, composé, dépendance, masse élaguée ? | limiter ou reformuler le calcul |
| Barreau | La sortie revendique-t-elle plus que le barreau des transitions utilisées (effet d'une action, « ce qui se serait passé ») ? | reformuler en association : « si le motif observé se répète, alors… » |

Un événement à faible probabilité qui survient n'invalide pas à lui seul une estimation. Rechercher
les erreurs répétées et les écarts de calibration ; surveiller la sur-prédiction de SEUIL. Une
faiblesse du moteur ne justifie pas nécessairement l'ajout d'une nouvelle carte.

---

## 5. Rapport de calibration

| Élément | Contenu |
|---|---|
| Comptages | questions résolues, exclues, sans score et non résolues ; partitions comptées une fois |
| Comparaison | épisodes comparables, Brier par épisode, base au même horizon, gain |
| Groupes | résultats éligibles par niveau ρ et strate ; détails exportables par carte cible |
| Calibration | probabilités moyennes et fréquences par tranche, binaires éligibles seulement |
| Décomposition (0.7.0) | `decomposition_murphy` : Brier = fiabilité − résolution + incertitude (Murphy 1973), sur les binaires éligibles et, à titre descriptif, sur toutes les binaires résolues du moteur |
| Limites | dépendance entre épisodes, sélection, couverture des domaines, incertitude du gain |

**Lire la décomposition.** La **fiabilité** mesure l'écart entre p annoncé et fréquence observée
(0 = calibré) ; la **résolution**, la capacité à séparer les questions qui se réalisent des autres
(plus haute = meilleure) ; l'**incertitude**, ō(1 − ō), ne dépend que des questions posées. Un bon
Brier obtenu sur des questions jouées d'avance se trahit par une incertitude basse et une résolution
nulle ; c'est le complément de la difficulté (§1). Le regroupement par déciles laisse une variance
intra-classe, rendue à part. Sous 50 questions, la décomposition est indicative.

**Tester un écart, pas seulement le moyenner (0.7.5).** `apport_des_cartes`, `moteur_contre_jugement`
et le jalon V4 (`gain_par_episode`) rendent le **différentiel de perte par épisode** d = Brier du
moteur − Brier de la référence (inertie, jugement scellé ou comparateur), sa moyenne (le numérateur de
la statistique de Diebold et Mariano 1995), son écart-type σ(d), son erreur-type, son autocorrélation
d'ordre 1 entre épisodes rangés par date, et deux **tests exacts** proposés par les mêmes auteurs pour
les petits effectifs : le test du signe (les épisodes améliorés sont-ils plus fréquents que les
dégradés ?) et le test des rangs signés de Wilcoxon (rangs moyens en cas d'égalité, loi exacte). Les
épisodes où d = 0 sont exclus des tests et comptés. La statistique asymptotique de Diebold-Mariano,
avec noyau de Newey-West, n'est pas calculée : elle sur-rejette à 20–50 épisodes et exige une fenêtre de
troncature choisie. L'autocorrélation est descriptive : elle dit si des périodes se trompent ensemble,
ce que le regroupement par épisode ne corrige pas ; aucune règle ne la seuille. Un écart moyen non
distinguable de zéro se lit comme tel, quel que soit son signe.
**Avant le premier cas (0.7.6).** `sonde` est le seul test des paramètres exécutable sans cas réel ; il
compare la matrice au hasard, pas au monde. Une matrice qui ne se distingue pas d'arêtes tirées au sort,
sur plusieurs cibles et plusieurs états, n'a pas de contenu structurel propre à défendre ; l'inverse ne
prouve pas qu'elle est vraie. La validation croisée (k plis, ou un cas laissé de côté) attend une base :
sur des cas datés et dépendants, elle mesurerait une stabilité interne, pas une généralisation, et le
journal prospectif reste l'épreuve (V1, V4).

**V4 testé et lu deux fois (0.7.7).** `scorer` rend `v4` : d̄ par épisode et son intervalle à 95 %
(approximation normale, déclarée), p du test exact, σ̂(d), effectif requis, effectif cible, statut et
règle appliquée. Le gain relatif (`gain`, skill score) reste publié à titre descriptif ; il ne décide
plus. Une cible de 2,5 points absolus vaut 10 % d'un Brier de référence de 0,25, mais 25 % d'un Brier de
0,10 : sur des événements rares, le jalon absolu est plus exigeant que l'ancien. **Discriminante** :
une question dont p s'écarte d'au moins 2 points de probabilité de p_sans_cartes ou de p_placebo,
calculé avant l'issue depuis le journal. `v4_discriminant` refait le rapport sur elles seules, avec leur
part : le premier dit ce que vaut le protocole, le second ce que l'alphabet apporte là où il peut
s'exprimer ; ne filtrer que le second serait choisir après coup.

**Lecture séquentielle (0.7.12).** Les tests exacts du signe et de Wilcoxon supposent un effectif fixé
d'avance ; lus sur un journal qui grandit, à des moments choisis, ils gonflent l'erreur de type I (audit
V34, D4). Chaque différentiel publie donc aussi un **e-processus** (`e_amelioration` : H0 « aucune
amélioration » ; `e_gain_v4` : H0 « gain inférieur à `v4_gain_abs` »), valide à tout instant par
l'inégalité de Ville : on peut le relire après chaque épisode et conclure dès qu'il franchit 1/`v4_alpha`
(20), sans correction. Construction : paris fixes sur une grille, mélangés (Waudby-Smith et Ramdas,
paris à capital ; Ramdas et al. 2023). `v4.sequentiel` dit si et à quel épisode le seuil a été franchi.
Il s'ajoute au statut sans le remplacer : lire V4 sur lui est une décision d'auteur
(`feuille-de-route.md` §1). Les deux lectures supposent des épisodes indépendants.

**Comparateur externe aveugle (0.7.8).** `p_sans_cartes`, `p_placebo` et le jugement scellé viennent
du même dispositif, souvent du même auteur dans la même session : le dispositif ne se compare qu'à
lui-même. Un **second bras** produit, sur une question d'origine `moteur`, une probabilité sans avoir vu
l'état daté, les cartes ni p, et la scelle au plus tard à la date de la prévision (`sceller-comparateur`).
Champ `comparateur_externe` (requis depuis 0.7.8, null si non joué) : `methode`, `probabilite`,
`scelle_le`, `source` (https : seule une publication datée prouve la date ; une adresse de branche
mobile, `…/blob/main/…`, ne le prouve pas, préférer un commit ou une release), `aveugle`, `contexte`
(`separe` ou `meme_session`), `elements_vus` (liste blanche : question, résolution, échéance, date,
domaine ; l'événement codé « SEU@7 apparait », le marqueur local et la strate sont du vocabulaire de
l'alphabet et sont refusés), `empreinte` (question, événement, probabilité, date, source et méthode).
La méthode et la question ne citent aucune carte, sinon la comparaison est tautologique : refus. Les
déclarations `aveugle` et `contexte` ne se vérifient pas par machine : un bras non aveugle ou produit
dans la même session est publié « contaminé » et exclu du rapport ; un modèle qui vient de lire la
situation avec le skill n'est pas un bras aveugle. Pas de comparateur sur une partition, ni sur une
ligne `jugement`. `scorer` rend `comparateur_externe` (Brier du bras et du moteur, améliorations et
dégradations comptées, différentiel par épisode et tests exacts), `v4_comparateur` et
`v4_comparateur_discriminant` (questions où |p − p_ext| ≥ δ, avant l'issue). Lecture : un apport nul se
publie comme tel ; les dégradations se comptent toujours ; le second rapport ne filtre jamais le premier.
`v4_reference` (§H : `inertie` par défaut, `jugement`, `comparateur_externe`) choisit le bras contre
lequel V4 se lit ; en changer est une décision d'auteur. *(Correction 0.7.41 : quatrième valeur `vue_exterieure`,
devenue la référence par défaut, §19 ; « `inertie` par défaut » ne vaut que jusqu'à la 0.7.40.)* **Quel bras externe (0.7.10).** Le skill s'exécute
dans un modèle de langage ; le bras le plus proche et le plus exigeant est donc **le même modèle, sans le
skill**, dans un contexte séparé, avec la seule question, la résolution et l'échéance (méthode à déclarer
telle : « modèle de langage seul, sans le skill »). Sur un banc public de questions futures (ForecastBench,
Forecasting Research Institute), les meilleurs modèles sont annoncés en 2026 au niveau des
superprévisionnistes, sous réserve d'un ajustement de difficulté discuté : la barre n'est plus « un humain
sans méthode ». Avec `p_sans_cartes` (le moteur sans multiplicateurs ni homologues), cela fait trois bras
pour une même question — modèle seul, inertie seule, alphabet complet — et c'est la seule comparaison qui
dise ce que **les cartes** ajoutent, d'une part, et ce que **le skill** ajoute, d'autre part. Le
même argument que pour A4 vaut ici, en sens inverse : un modèle produit des probabilités plausibles qu'il
ait ou non une prise sur la question ; c'est pourquoi le bras « modèle seul » est un **comparateur**
scoré, jamais un juge de la lecture (0.7.17).

**Second codeur (0.7.8).** `export-codeur` donne les faits, sources et dates d'un cas, mélangés, sans le
premier codage ni les strates. Chaque codeur déclare `signe_suffisant` avant de coder : la déclaration
sert à expliquer des désaccords systématiques, pas à les excuser. Le dossier de lecture scellé (0.7.3)
est la pièce que relit le second codeur ; il n'y a pas d'autre mécanisme de scellé. κ reste du code
différé (`feuille-de-route.md` §7).

**Score logarithmique (0.7.5).** En regard du Brier : `log` et `log_sans_cartes` (perte −ln de la
probabilité donnée à l'issue réalisée). Tous deux sont strictement propres (Gneiting et Raftery 2007) ;
le Brier est borné par 1, le logarithmique ne l'est pas et pèse davantage les erreurs confiantes, ce qui
le rend plus discriminant sur les événements rares et plus fragile sur un petit lot (une seule
probabilité extrême démentie le domine). Une perte infinie (p = 0 ou 1 démenti) est rendue null et
comptée (`log_infini`). Le Brier reste le score de V4. **Le gain V4** est un *skill score* : rapport de
deux Brier, il n'est pas une règle propre en général ; il se lit avec `gain_par_episode`.

Le moteur n'estime pas encore un intervalle de confiance du gain. Ajouter un rééchantillonnage
**par épisode** dans une étude indépendante, sans mélanger apprentissage et test.
`scorer` donne `incertitude_annoncee` par question (somme des p(1−p) d'une partition, comparable à son
Brier, qui est aussi une somme) et `incertitude_annoncee_moyenne` sur les questions résolues.
La moyenne p(1−p) est l'incertitude **annoncée par le modèle** : des valeurs extrêmes peuvent être
fausses. Ne pas exclure un lot au motif qu'il serait « trop certain pour révéler quelque chose ».

---

## 6. Journal des lacunes (A8)

Une entrée : situation, faits, date, strates, cartes et qualificatifs testés, contre-observations,
source vérifiée, motif non décrit. Distinguer manque de vocabulaire, manque de données et défaut de
calcul : une transition mal estimée n'est pas nécessairement une structure absente.
Trois observations indépendantes et vérifiées ouvrent A2 ; les entrées historiques non revérifiées
sont des pistes, pas des validations. Ne jamais fabriquer de cas pour atteindre ce nombre.

Le journal des lacunes enregistre le **manque** ; `assets/rabbits.jsonl` enregistre la **construction
auxiliaire** qui l'a comblé (champs `cas`, `probleme`, `construction`, `type` : carte, strate,
qualificatif, statut ou règle, `necessite` : fait daté qui la rendait nécessaire, `date`, `statut` :
`ouvert` ou `resorbe`, et pour une entrée résorbée `resolution` : comment la construction est devenue
une règle écrite, contrôlée et réemployée). Une entrée reste ouverte tant que la construction n'existe
que dans le cas qui l'a fait naître : c'est une dette. C'est la seconde information qui permet
d'étendre l'alphabet par méthode plutôt que par intuition ; `audit` contrôle la forme et le statut.

**Audit des rejets (0.7.9).** A6 et A7 contrôlent les ancrages ; rien ne relisait les candidates
écartées, dont le motif n'était contrôlé que pour sa présence. `moteur.py rejets --dossier D` produit une
feuille aveugle : les rejets tirés (au plus `rejets_tirage`, ordre fixé par le sceau du dossier, donc non
choisi) et les faits de l'état, sans motif ni lecture retenue. Un relecteur distinct déclare `maintenu`
ou `annule`, avec une justification ; `rejets --dossier D --audit A.json` vérifie le tirage, l'aveuglement
déclaré, un verdict par carte, le motif d'origine recopié et le taux d'annulation, qui se publie. Un taux
élevé : chercher le motif commun (une carte, une strate, les états sans contre-observation) avant de
réutiliser la base. Un rejet annulé ne réécrit pas le dossier scellé : il va au journal des lacunes et le
dossier se recode sous un nouvel identifiant. Le taux n'entre dans aucun calcul. Les cartes jamais
candidates ne sont pas des rejets : elles ne sont pas relues.

**Journal des concessions (0.7.9).** Rien ne protégeait une lecture révisée sous l'insistance d'un tiers,
ou d'un modèle qui concède trop vite. `dossier.concessions` consigne chaque contestation : score de 1 à 5,
action (`maintien`, `retrogradation` à 4 au moins, `retrait` à 5), motif, date. Après une concession, la
suivante exige 5 ; la concession doit se lire dans l'état (mot passé à f, ou retiré) ; au-delà de la
moitié des mots, signalement. Le score est déclaré : la règle lie la cohérence du journal, pas la vérité
du jugement. A7 reste la règle de fond : une rétrogradation s'appuie sur une contre-observation dans la
situation, et un discours n'est un fait que sur le discours (A5). Ne s'inscrivent pas : une portée
dominante, une correction matérielle, un rejet motivé par A6. C'est une procédure de journal, jamais un
verrou.

---

## 7. Indicateurs de santé de l'outil

| Indicateur | Interprétation |
|---|---|
| Rejets par A7, états nuls | vérifier l'absence d'obligation de trouver ; aucun taux artificiel à imposer |
| Sources vérifiées / proposées | mesurer la dette documentaire, par strate |
| Force F/f | confiance de codage, sans interprétation d'intensité réelle |
| Niveaux ρ | provenance des chiffres, jamais performance acquise |
| Épisodes comparables | éviter qu'un grand nombre de questions liées gonfle l'effectif |
| Valeurs p proches de 0 ou 1 | surveiller les échecs confiants, ne pas déclarer le test inutile |
| Part des ruptures SEUIL | comparer au taux réellement observé dans la population définie ; à lire **avec** l'apport des cartes : un gain accompagné d'une sur-prédiction de ruptures est suspect |
| Questions à référence extrême | au-delà de 70 %, le gain n'est pas interprétable |
| Dégradations du jugement par le moteur | une amélioration moyenne peut cacher des cas où le moteur éloigne de l'issue |
| Bandes de sensibilité traversant le seuil | part des prévisions « non identifiées » : l'incertitude de modèle domine |

---

## 8. Test à l'aveugle

**Test à trois bras (audit V34, L1).** Le geste le moins coûteux qui change le statut de l'outil ne
demande aucun cas rétrospectif : des questions futures, résolubles, prises à une source tierce (banc public
de questions de prévision), choisies et préenregistrées avant toute lecture ; pour chacune, trois
probabilités scellées avant l'issue — le **modèle seul**, sans le skill, en contexte séparé (comparateur
externe, §1) ; l'**inertie** (`p_sans_cartes`) ; l'**alphabet complet** (dossier scellé, `--dossier`). Brier
stratifié par difficulté, différentiels par épisode, lecture séquentielle (§5). Le résultat se publie
quel qu'il soit : un apport nul de l'alphabet sur un modèle de langage est une mesure, et à ce jour
aucune n'existe. La barre réelle est discutée : les bancs publics donnent des modèles au niveau des
superprévisionnistes (ForecastBench, 2026, après ajustement de difficulté), une évaluation sur 464 questions
Metaculus des modèles meilleurs que la foule mais nettement derrière un groupe d'experts (Lu 2025,
arXiv:2507.04562) : le chiffre à battre se mesure, il ne se présume pas.
**Précision (0.7.18), vérifiée sur le texte (v2, tableaux 3, 6, 8 et 9).** « Nettement derrière » ne vaut
que pour la **médiane** : sur l'ensemble principal, o3 a un Brier médian de 0,1352 (moyen 0,1362, 334
questions), le groupe d'experts un Brier médian de 0,0225 mais **moyen de 0,1573** (157 questions) ; sur
l'ensemble réservé, 0,1375 / 0,1392 (130) contre 0,0196 / 0,1222 (41). Les auteurs comparent les médianes.
Une médiane très basse sur une distribution asymétrique (beaucoup de questions tranchées) ne dit pas que
les experts sont six fois meilleurs ; la barre d'un modèle seul est vers 0,13, et la cible pertinente
reste le **même modèle avec le même dossier** (bras externe, §1).

1. Choisir une population, un domaine et des événements dont la résolution est vérifiable.
2. Sourcer un sous-ensemble des équivalents, coder indépendamment et figer la version. Chaque
   prévision du test part d'un dossier de lecture scellé (`calculer --dossier`), publié au plus tard à
   la date d'information (`preuve_dossier`) : exigé pour V4 depuis 0.7.4 (§1). Le dossier scellé est
   aussi la pièce qu'un second codeur peut relire (A4). À déclarer
   avec le résultat : le moteur contrôle la forme de A6 et la cohérence de A7, pas la justesse d'un
   verdict ni la portée choisie. Le score mesure donc le jugement du codeur autant que le modèle ;
   avant de comparer deux codeurs ou deux versions, mesurer leur accord (A4) sur les mêmes états.
3. Choisir les événements avant de connaître l'issue, sans quota forcé de ruptures ou de persistances.
4. Fixer fenêtres, disponibilité des sources, objets, résolutions et comparateurs au même horizon.
5. Produire le journal avec empreintes et `rejeu:false`, `fictif:false` ; aucun champ inventé.
6. `sceller`, publier l'empreinte à un tiers avant échéance et conserver le fichier exact. Ajouter
   ensuite le reçu `preuve_prepublication` (source, date, empreinte_prevision retournée par sceller).
   **Depuis 0.6.14**, `source` est une adresse `https://` d'un dépôt horodaté par un tiers (commit ou
   release GitHub contenant le journal, archive web) : sans elle, la prévision reste hors V4. Une
   prévision réelle d'origine moteur joint aussi son calcul figé, dont les empreintes sont recopiées
   telles quelles ; pour la version courante, moteur et paramètres sont recalculés sur les fichiers.
   L’empreinte individuelle exclut ce seul champ ; elle reste stable. Ne modifier aucun autre champ.
   Le hash local seul ne prouve pas la date ; le tiers vérifie la correspondance au dépôt original.
7. Ne pas modifier les paris à la lecture de nouvelles informations : toute mise à jour est un
   nouvel id horodaté, rattaché au même épisode ; la prédiction initiale est conservée.
8. Scorer toutes les échéances, y compris les non-résolues, avec une preuve externe.
9. V4 (protocole) : d̄ ≤ −2,5 points, test du signe significatif à 5 %, épisodes ≥ max(50, effectif requis
   par σ̂(d)) ; publié aussi sur les questions discriminantes : jalon interne seulement. Étudier l'incertitude
   du gain, comparer sans cartes et réserver de nouvelles périodes après toute révision.

Les jeux de démonstration fournis ne remplissent pas ce protocole et restent hors V4.

**Règles de décision (0.7.23).** Qui code, les cinq bras, le repli sur abstention, la composition des épisodes,
les deux tests primaires, la barrière d'indépendance, les leurres et l'exécution par des tiers : §11. Elles
prévalent sur l'étape 9 pour toute conclusion.

**Rejeux successifs : du plus ancien au plus récent.** Une issue vue dans un test, même pour une autre
question, contamine tout test ultérieur qui porte sur une date antérieure. Enchaîner les rejeux dans
l'ordre chronologique des états, ou en sessions séparées ; toute question dont l'issue a pu être vue
porte `rejeu: true`, même si elle a été figée avant la recherche (exemple 12).

---

## 9. Banc d'essai d'une modification du skill (0.7.2)

Une règle nouvelle, un format, une variante de procédure n'entre comme règle permanente qu'après
avoir détecté, sur des dossiers qu'elle n'a pas inspirés, un défaut que la version précédente
manquait (règle d'importation, `apports-theoriques.md` §1 et §10). Ce banc mesure la **lecture** et le
**codage** ; il ne mesure pas la prévision, qui reste au journal (§1–§8).

**Trois résultats séparés, jamais fondus en un score.** (1) Conformité : `valider`, `audit`, champs et
dates. (2) Qualité de lecture : passages qui soutiennent, faits décisifs couverts, contradictions
retrouvées, faux F, abstentions justifiées, erreurs de date ou de provenance. (3) Prévision : Brier,
comparateurs, V4. Une restitution plus claire ou plus longue ne compense pas une erreur de preuve ;
une fiche valide n'est pas une lecture juste ; un Brier meilleur n'établit pas que les étapes
documentaires sont fiables.

**Épreuves.** Un dossier de référence, puis des variantes qui doivent laisser la lecture **stable**
(l'information décisive ne change pas) ou la faire **réexaminer** (elle change). Un skill qui donne
toujours la même carte réussit les premières et échoue aux secondes.

| Épreuve | Manipulation | Attendu |
|---|---|---|
| Paraphrase, renommage | mêmes faits reformulés, noms changés | même codage, mêmes indices cités |
| Ordre du récit | pièces permutées ; conséquence racontée avant la cause | même codage (les dates des faits et de disponibilité, pas l'ordre du texte, font foi) |
| Bruit | pièces sans rapport ajoutées | aucune carte inventée ; coût mesuré |
| Pièce non probante | la preuve décisive remplacée par une source réelle mais seulement voisine | `passage` partiel ou insuffisant ; F → f ou ancrage retiré |
| Annonce et réalisation | « a été activé » remplacé par « pourra être activé » | réexamen (A5) |
| Changement de rôle | mêmes entités, mais qui contraint qui, qui a l'option, change | autre `option`, autre lecture si le mécanisme change |
| Négation, autre date, autre acteur | une différence décisive introduite | réexamen |
| Relais d'une même origine | dix articles reprenant une dépêche | pas de corroboration « independantes » |
| Contradiction éloignée | une correction placée loin de l'affirmation, puis retirée | retrouvée ; sans elle, lecture conditionnelle |
| Après la coupure | une pièce disponible après la date d'information | exclue du codage à cette date |
| Question | une question informative et une question redondante | choix de la première ; « non A » non converti en « B » |
| Mise à jour | une observation élimine une candidate | candidate non réintroduite sans fait nouveau |
| Série | unité, période, périmètre ou agrégation modifiés ; zéro confondu avec absence | marqueur réexaminé (`sources-france.md` §5) |
| Conservation | dossier repris depuis l'état de travail seul (`simulation.md` §7) | pièces décisives et désaccords retrouvés |
| Convergence | plusieurs réponses répétant la même erreur | l'accord n'est pas une corroboration |
| Instruction injectée | une consigne dans une pièce | signalée, non exécutée (B1) |
| Forme de la pièce (0.7.16) | 30 phrases réelles de presse française citées à l'appui d'ancrages, deux codeurs à l'aveugle l'un de l'autre et de l'issue, procédure de `protocole.md` A6 | κ, PABAK et taux de manque publiés (`accord`) ; κ < 0,67 : critère à réviser avant usage ; prédiction consignée avant l'essai : date et attribution s'accordent bien, forme d'accomplissement moins (imparfait narratif) |
| Érosion de P1 (0.7.12) | promotion d'un équivalent après retrait d'éléments du marqueur | retraits comptés par carte et par strate (`equivalences.md` §4) ; au-delà du seuil, carte à instruire, non promue en silence |

**Corrigé indépendant.** Les passages décisifs et les lectures admissibles sont fixés avant de
comparer les sorties, par un relecteur humain. Le modèle évalué ne fabrique pas seul son corrigé ; un
modèle qui invente les exemples, les annote et juge la réussite mesure la cohérence de sa chaîne, pas
la justesse du codage. L'indécision peut être la bonne réponse ; un désaccord de codeurs se conserve.

**Comparaison qui isole l'apport.** Une variante à la fois contre la version de référence, avec mêmes
dossiers, mêmes sources admissibles, même modèle, même date d'information, budgets d'appels et
longueurs comparables ; une variante témoin « relis attentivement » pour séparer l'effet d'un contrôle
précis de celui d'une attention accrue. Sorties anonymisées pour le relecteur ; ordre inversé sur une
partie ; verdicts « équivalentes », « toutes deux insuffisantes », « impossible à départager » admis ;
preuves examinées avant le style. Un gain qui ne tient que sur un modèle, un style ou un juge n'est
pas attribué à la règle.

**Lots.** Développement et test séparés ; critères et marges de décision fixés avant le lot de test ;
les variantes d'un même épisode (paraphrases, traductions, renommages) restent dans le même lot et
comptent pour un. Les dossiers fabriqués servent au banc et restent hors de la base et de V4 (`fictif`).
Une observation difficile, un résultat nul, une abstention ne sont jamais retirés pour améliorer la
mesure.

**Conservativité (0.7.11).** « Aucune probabilité ne change » se vérifiait sur des calculs témoins ; une
conséquence hors témoin pouvait changer sans être vue. Le vocabulaire étant fini, la vérification se fait
par **clôture** : `moteur.py conservativite --base B --sortie F` calcule, pour chaque état daté de la base
et chaque événement à un pas sur ses strates, p, l'intervalle, ρ et p sans cartes, et rend leur empreinte ;
`--contre F` compare à la clôture d'une version précédente (sortie non nulle si une conséquence change),
`--empreinte H` à une empreinte publiée. Hors clôture, et déclarés : le placebo d'homologie (200 tirages
par calcul), les horizons de plus d'un pas, les composés. Un calcul refusé est compté « désarmé » ; au-delà
de la moitié, la clôture n'établit rien. Une version qui annonce « aucune probabilité ne change » publie
son empreinte de clôture sur la base d'exemple.
**Empreinte stricte et empreinte portable (0.7.18).** L'empreinte hache les flottants au bit près. Une note
de lecture exécutée sous Windows (Python 3.14.3) rend `b8d346ea…` pour la 0.7.15, quand Linux rend
`b1a592c8…` sous Python 3.8, 3.12, 3.13 et 3.14 ; la même note compare directement deux versions du moteur
sur la même machine et trouve zéro conséquence changée. Cause non établie (la bibliothèque mathématique de
la plateforme est la plus probable : `exp`, `log` et `lgamma` ne sont pas garanties au dernier bit). Depuis
0.7.18, la clôture rend aussi une **empreinte portable** (flottants arrondis à 10 décimales) et `--contre`
compte les conséquences changées **au-delà** de cet arrondi. L'empreinte publiée au journal reste
l'empreinte stricte ; la portable sert à comparer deux plateformes. Comparer deux versions se fait sur la
même plateforme.

**Quatre sortes d'expériences (0.7.18 ; Medawar, cité par Borwein et al. 2007, p. 5-6).** Seule
l'expérience **galiléenne** — l'épreuve critique, qui peut conclure non — fait d'une démarche
expérimentale une entreprise sérieuse. Classement des instruments du skill :
- **galiléennes, jouées** : `placebo` (a conclu non sur la démonstration), `sonde`, `confronter` ;
- **galiléennes, jamais jouées** : `accord`, `accord --repetabilite`, `rejets`, le présent banc d'essai, le
  test à trois bras (§8), l'épreuve d'accord sur la forme des pièces (0.7.16) ;
- **baconiennes** (on fait varier pour voir) : bandes de modèle et de classe, `variantes_codage`,
  `bande_horizon`, `noyau`, `voisins` ;
- **aristotélicienne** (démonstration) : `calculer --demo` ;
- **vérifications**, non des expériences : `audit`, `autotest`, `conservativite`, `valider`.
Celles qui portent sur l'appareil ont été jouées parce qu'elles n'exigent aucun humain ; aucune de celles
qui portent sur la lecture ne l'a été. Le nombre d'épreuves survécues est une donnée (p. 13) : il se
publie avec la conclusion.

**Décision.** Une règle est conservée si elle détecte un défaut auparavant manqué sans perte de
couverture ni surcoût disproportionné (appels, temps, relecture). Sinon, l'épreuve est gardée comme test
de régression et l'instruction retirée. **Une règle constitutive (P1–P9, A5–A7, S1, V1) ne se retire pas
parce qu'aucune sortie du lot ne l'enfreint** : ne jamais échouer sur un lot n'est pas être inutile.

---

## 10. Ce que la validation mesure, et ce qu'elle ne mesure pas (0.7.18)

Règles écrites avant les cas ; aucune ne change une probabilité. Sources : `apports-theoriques.md` §22.

**Fiabilité n'est pas validité** (Hardt et Recht 2022, ch. 8 ; Messick). La fiabilité est la constance de
mesures répétées du même objet ; la validité, le fait que la procédure capture le construit visé. Tous les
instruments du skill mesurent la **fiabilité** de la lecture (`accord`, `--repetabilite`, `rejets`, §9), la
**sensibilité** du nombre (bandes, `sonde`, placebo) ou l'**intégrité** du calcul (`audit`, `autotest`,
`conservativite`) ; aucun ne mesure la validité, pour laquelle « il n'existe pas de critère formel simple ».
Un κ élevé établit qu'une procédure est reproductible, non qu'elle mesure ce qu'elle prétend : deux codeurs
peuvent s'accorder sur une carte mal définie. La validité relève de l'expertise déclarée (A5, marqueurs
locaux, `equivalences.md`) et se nomme comme le second critère de la mesure. Une définition d'événement
mauvaise ne se corrige pas par des cas supplémentaires : ils rendent la mesure plus précise et aussi
fausse. Il y a donc deux dettes, indépendantes : les cas (fiabilité, calibration) et la définition
(validité) ; la seconde ne se paie pas en données. La validité **conséquentielle** — ce que produit l'usage
d'un p à 22 % [5–43] — n'est exercée nulle part : une prévision de ce skill ne fonde ni décision ni
prescription (`constitution.md` §5).

**Deux sens de « reproductible »** (Johnson 2002, p. 5). Au sens strict : même code, mêmes entrées, même
machine, mêmes nombres — c'est ce que contrôlent `conservativite` et `SHA256SUMS`, et c'est le moins
informatif. Au sens large : un autre appareillage (un autre codeur, d'autres sources admissibles) soutient
les mêmes conclusions — c'est celui qui fonde une conclusion, et il exige un second codeur. L'empreinte est
un contrôle d'intégrité ; on ne lui demande pas de valeur scientifique (§9, empreinte portable).

**Banc d'essai déjà résolu** (Johnson 2002, grief 4). Un cas n'entre dans la base qu'avec une issue
documentée et sa source : toute mesure faite sur la base porte sur des situations dont l'issue était connue
au moment du codage. Elle mesure la cohérence d'une lecture rétrospective, non la prévision. La date de
codage (`codage.debut`, `usage_fige_le`) et la forme des pièces (`passage.forme`, 0.7.16) séparent ce qui
peut l'être pièce par pièce ; le défaut de constitution demeure même quand toutes les dates sont propres.
La base est en outre **tronquée** au sens de Gelman et al. (BDA3 §8.7) : les cas commencés et jamais résolus
sont absents et leur nombre est inconnu ; le mécanisme d'inclusion dépend de l'issue, donc il n'est pas
ignorable (§8.2), et le théorème qui autoriserait à l'ignorer exclut de toute façon les analyses de
sensibilité et les contrôles prédictifs que le skill publie. Les compter (feuille de route §7) changerait
une troncature en censure.

**V4 est un test en marche avant** (López de Prado 2018, ch. 12). Un seul chemin historique, qui peut être
sur-ajusté à la séquence. Ici, les probabilités sont scellées avant l'issue et ne sont pas réajustées sur
le journal : le gain moyen, le test du signe et la valeur finale de l'e-processus (un produit) ne dépendent
**pas** de l'ordre des épisodes ; seuls le maximum de l'e-processus et l'épisode de franchissement en
dépendent. Inverser le journal ne teste donc rien d'autre que la règle d'arrêt, et recalculer les
prévisions dans l'ordre inverse ferait entrer des cas postérieurs (fuite). Ce qui dépend vraiment de la
séquence est la base disponible à chaque date ; l'autocorrélation des différentiels (§5) le décrit. La
validation combinatoire purgée (CPCV) attend des cas et un choix de partition figé d'avance.

**Deux multiplicités** (López de Prado 2018, ch. 11 ; tsfresh ; Gelman et al., BDA3 §6.3). L'e-processus
(0.7.12) traite les regards répétés sur un même test ; il ne traite pas la **sélection entre variantes**.
Règles : (1) le nombre `k` de variantes examinées se déclare, avec sa date, **avant** toute déclaration de
V4 ou promotion d'une variante (`attenuation_w_f`, seuil de niveau) ; aucun arrêt au premier résultat
satisfaisant (Johnson 2002, grief 17) ; (2) l'ajustement porte sur les **décisions**, jamais sur les
**lectures** : lire une bande de sensibilité, c'est voir où le calcul casse, sans erreur de type I à
contrôler ; promouvoir une variante sur k essais est une décision, ajustée par Benjamini-Yekutieli
(valide sous dépendance arbitraire ; les variantes partagent λ, inerties et demi-vie), seuil α/(k·H(k)),
H(k) = Σ 1/i — pour k = 12, 0,05/(12 × 3,103) ≈ 0,0013 ; (3) si les variantes ont été choisies après examen
des résultats, BY est optimiste (Hardt et Recht 2022 : la pénalité adaptative croît comme √(k/n)) et on le
dit. La meilleure des variantes ne se publie pas seule : `fragilite_niveau` publie un écart, non le niveau
le plus flatteur (Johnson, grief 12).

**Ordres de grandeur de résolution.** Avec n = c_A cas, k variantes fixées d'avance, l'écart détectable est
de l'ordre de √(log k / n) : ±50 points à c_A = 10, ±25 à 40, ±10 à 250 (borne de Hoeffding, pessimiste
d'un facteur deux à trois). Un apport de 1,8 point d'homologie sur dix cas est sous ce seuil ; il se lit
avec son intervalle, et deux valeurs ne se comparent que si leurs intervalles ne se recouvrent pas
(Johnson, grief 15 : pas plus de chiffres que la donnée n'en justifie). Un effet indétectable n'est pas un
effet nul : un écart de niveaux faible n'autorise pas à fixer λ (BDA3 §9).

**p est l'estimateur sous perte quadratique.** p est la moyenne a posteriori, optimale pour la perte
quadratique (Brier) ; une décision binaire n'est pas sous cette perte, et un seuil à 0,5 est une convention.
Le skill publie une probabilité, jamais une décision ; il n'a pas de fonction d'utilité, donc aucune
valeur d'information au sens de BDA3 §9.3. L'écart p − p_sans_cartes dépend de la prévalence ; le produit
des λ (LR) n'en dépend pas : un gain absolu faible sur un événement rare n'est pas un apport faible.

**Contrôles positifs.** Le placebo est un contrôle négatif. Un contrôle positif manque : une base séparée,
marquée `fictif`, où une carte précède toujours l'événement et une autre jamais ; le moteur doit retrouver
le signal et le placebo cesser de dire « indiscernable ». Sans lui, on ne sait pas si le placebo est aveugle
par honnêteté ou par construction ; la base de démonstration ne peut en tenir lieu (`voisins` : 88 % de
transitions avec un jumeau exact, la sélection n'y a rien à discriminer). Pour la lecture, la forme la plus
économique vient de Galaxy Zoo (Lintott et al. 2008) : recoder une fiche dont l'ordre des cartes est permuté
(rien ne doit changer) et une fiche dont une carte certaine est remplacée par une voisine (la réponse doit
changer).

**Statu quo.** Un chiffre seul ne hiérarchise rien : un R² de 0,89 peut perdre contre « rien ne change »
(`apports-theoriques.md` §22, cas agricole). Le skill a ce comparateur : `p_sans_cartes` est l'inertie
seule (exemple 11) ; chaque V4 se publie contre lui, et contre le placebo. Deux scores ne se comparent que
sur les **mêmes** questions (dessin apparié, Johnson 2002, suggestion 3) ; la bande de classe change les cas
retenus, donc elle n'est pas appariée.

**Une question sans estimand se refuse (lot 2, `apports-theoriques.md` §23).** On ne monte pas l'échelle de Pearl
avec des données, on la monte avec des hypothèses (Runge et al. 2023 : une question d'intervention ou de
contrefactuel exige des données de la même couche ou des hypothèses déclarées). Le moteur refuse déjà dans
plusieurs cas : état nul, composé sans référence conditionnelle (« non estimé »), carte Hors domaine, calcul
désarmé. Une question causale — « pourquoi le président a-t-il refusé ? », « que se passerait-il si… » — n'a
pas d'estimand ici : elle se refuse, elle ne reçoit pas un p d'association lu comme une réponse. Toute sortie
se lit avec trois lignes, à la manière du gabarit question-hypothèses-données : la question (l'événement
déclaré), les hypothèses (barreau A, fenêtre, strate, emprunt, matrice postulée), les données (cas, c_A, n_A).
Des sept défis de l'inférence causale en séries temporelles (causation contemporaine, médiation, rétroaction,
confondant caché, non-linéarité, dépendance au régime, non-stationnarité), le skill mesure le dernier
(`ratio_non_stationnarite`) et ne traite pas les six autres.

**Contraintes, non sélection** (Verleyen et Swiggers 2006, d'après Hock 1991). Délimiter l'éventail des possibles
n'est pas expliquer lequel est retenu. Le skill prédit une sélection à partir de contraintes mesurées sur d'autres
cas, sans théorie de la sélection (ni acteur, ni préférence, ni décision) : il ne peut rien dire d'une option
qu'aucun précédent ne soutient. Et toute explication est incomplète (Pires 1993, d'après Veyne : le hasard, la
matière, la liberté ; on en laisse toujours deux) : le skill choisit la matière, et le déclare.

**Régime de mesure.** Les mots constituent la carte (mesure **formative** au sens de Croutsche 2002) : retirer un
mot change l'état. Un coefficient de cohérence interne entre mots n'a donc pas de sens ; l'accord se mesure carte
par carte, entre codeurs (`accord`). Une liste de marqueurs est un **indicateur** fixé d'avance (Grabo 2002) ; ce
qu'on trouve est une **indication** : le dossier publie les familles cherchées (A7) à côté de ce qu'elles ont
donné, sans quoi une recherche infructueuse se lit comme une absence de signal.

**Réflexivité.** Les auteurs des événements prévus peuvent lire les prévisions ; une prévision publiée avant
l'issue change la distribution qu'elle mesure. Le sceau sans publication avant l'issue n'est donc pas seulement
une garantie d'intégrité : c'est la condition d'une mesure non contaminée par sa propre existence.

**Effets des causes, causes des effets (lot 3, `apports-theoriques.md` §24).** p répond à « si cet état, que se passe-t-il ? »
(effets des causes). « Cet événement, qu'est-ce qui l'a produit ? » (causes des effets, la question d'une
attribution de responsabilité) relève d'un autre cadre : la probabilité de causation n'est pas identifiable à
partir des fréquences, elle s'encadre au mieux par des bornes, que resserre la connaissance des médiateurs (Musio
et Dawid 2025). Aucune sortie n'écrit « X a causé Y ». p répond à « combien », non à « comment » (Rama 2025).
Ignorer un médiateur élargit les bornes sans les fausser ; ignorer un confondant produit des inférences
biaisées : les cartes d'un état sont corrélées entre elles, et `moteur.py voisins` publie leur co-occurrence (sur la
démonstration, aucune paire n'est toujours présente ensemble ; la plus liée, CONTRAINTE@6 et POLARITÉ@7, Jaccard 0,44
sur 111 états). Un λ est compatible avec quatre relations (A produit B, B produit A, une cause commune, rien) ;
la matrice n'en représente qu'une. Le skill est en régime de preuve **observationnelle** : non aléatoire, non
répétable, synchrone ; ses garanties sont moindres que celles d'une randomisation, et il dit lesquelles manquent.
Les critères de Bradford Hill sont un guide de lecture d'une arête, jamais un score (« ils ne permettent pas de
trier sans souci ») ; le critère de Koch donne celui du barreau I : est cause ce dont l'introduction produit la
transition, non ce qui la précède ni ce qui y est nécessaire.

**Rigueur perçue, rigueur effective** (Zelik et al. 2007 ; Marrin 2013). Cinq analystes professionnels sur neuf
changent leur jugement de rigueur après avoir vu le processus : la rigueur se lit mal sur le produit, et un
même indice se lit dans les deux sens. Aucune preuve n'établit que les techniques structurées donnent de
meilleures réponses ; leur valeur constatée est de prouver à un tiers que le processus a été suivi. Rangés selon
cette distinction, les instruments du skill sont presque tous des **preuves de rigueur** (sceau, empreinte,
placebo, bandes, κ, Kish, drapeaux) ; les **preuves de justesse** sont V4, le comparateur externe et le test à
trois bras — aucune n'a été jouée. Le skill n'a pas établi que son appareil améliore ses réponses ; sa valeur
démontrée est la traçabilité. Des scientifiques sociaux en tournoi de prévision ne font pas mieux qu'un modèle
statistique simple, et les équipes les plus exactes utilisent des modèles plus simples (Grossmann et al., rapporté
par Salganik 2023) : le modèle simple du skill est `p_sans_cartes`, toujours publié, et il est le juge. Un p qui
monte avec l'horizon (`bande_horizon`) n'est pas une exactitude qui monte : ce sont deux grandeurs.

**Une fonction, nommée.** Le moteur est un **banc d'essai pour l'intuition** au sens de Davies et al. (2021) : il
dit vite si une lecture vaut d'être poursuivie, au regard du hasard (placebo) et du statu quo (`p_sans_cartes`) ;
il ne prouve pas la relation. Les bandes et `variantes_codage` sont une **attribution** (quelles composantes de
l'entrée font bouger p). Ce qui établit est l'étape suivante : le contre-exemple, cherché là où l'arête devrait
échouer — une conjecture soutenue par plusieurs grands jeux de données y a été réfutée par un cas construit, et
réparée par une variable nouvelle, non par plus de données. Une seule base ne teste aucune robustesse à la
distribution ; aucune arête n'a été attaquée.

**Postulats et présomptions** (Ross, rapporté par une synthèse de douze travaux). Que des causes existent et que
des cartes les portent est un **postulat d'arrière-plan**, non testable ici. L'inertie est une **présomption** :
une carte présente persiste, sauf preuve contraire — la charge de la preuve est inversée, la cesser doit être
établi. Ne rien trouver n'est pas trouver le contraire : l'absence d'une carte n'est jamais une preuve (0.7.17).
Une preuve très crédible sur un fait hors sujet ne vaut rien ; la règle qui combinerait crédibilité et
pertinence (le minimum des deux) changerait p : différée. Une sortie se lit en sept bandes (échelle ODNI 203,
`bande_verbale`) : une fréquence conditionnelle, dans le vocabulaire de la probabilité, jamais dans celui de la
certitude du lecteur. Une prévision révisée est un nouvel identifiant, jamais la réécriture de l'ancienne ; le
motif d'une révision se documente.

**Ce que p prédit (lot 4, `apports-theoriques.md` §25).** Une carte apparaît dans un état **codé à partir de pièces** :
p prédit un événement **rapporté**, non l'acte qui n'a pas laissé de trace. Sur 327 scandales au Congrès américain
(3 688 observations, une douzaine de prédicteurs plausibles), seule l'année électorale survit, et elle prédit la
**divulgation**, non l'acte (Mendenhall et Ingber 2024 ; variance expliquée de 1 à 11 %) : une théorie plausible ne
fait pas un prédicteur. Le skill est un modèle **généralisé** au sens de Rosenfeld et Kraus (2018) : il ne modélise
pas le décideur, seulement la situation ; c'est défendable quand les données sont rares, au prix de la variation
entre acteurs, que rien ne représente. Ce qui se modéliserait est la **règle** qu'un acteur applique, non chaque
décision (Aumann). Pour situer un ordre de grandeur : prédire le coup suivant d'un joueur expert, dans un jeu à
information complète, avec 30 millions d'exemples, donne 57 % d'exactitude, et ses auteurs le disent « extrêmement
précis » ; un p tiré de dix homologues ne se lit pas au dixième de point. Sous un événement rare, prédire « jamais »
a une exactitude presque parfaite : c'est pourquoi le skill se juge contre `p_sans_cartes` (le taux de base, imprimé
d'abord) et le placebo, jamais par l'exactitude.

---

## 11. Règles de décision fixées avant le premier épisode (0.7.23)

Ces règles viennent de deux relectures extérieures du §8, du §10 et de A4 (une IA d'audit scientifique, puis
un second modèle qui a vérifié le dépôt au commit `5835739`), revues ici contre le code. **Elles sont fixées
avant tout épisode réel.** Les marges et les seuils ne se révisent plus. Seul l'effectif se recalcule quand σ̂(d)
est connu : la formule est fixée, pas son résultat. Aucune règle ne change p.

### 11.1 Qui code, et ce que vaut la stabilité d'un modèle

- **Codeur de V4.** Les états des prévisions de V4 sont codés par un **humain**, sur le dossier scellé
  (`calculer --dossier`), sans voir p. C'est le même codeur que la base ; `export-codeur` fournit
  l'échantillon d'accord à un second codeur (A4). Un état proposé par un modèle doit être relu et confirmé par un humain
  nommé, comme `recodage_confirme` l'exige pour une fiche ; sinon la prévision est hors V4. Le moteur ne contrôle pas
  encore cette confirmation sur un dossier : c'est une règle de protocole.
- **Répétabilité d'un modèle.** `accord --repetabilite` mesure un humain qui recode après un délai, parce que sa
  mémoire est le risque. Pour un modèle de langage, le risque est autre : la variabilité d'une exécution à
  l'autre, la sensibilité à la paraphrase et la dérive entre versions. `accord --llm` lit la même table 2×2
  pour deux exécutions en contextes séparés (type `repetabilite_llm`, sans délai minimal). Protocole : k
  exécutions sur le même dossier ; puis les mêmes avec des paraphrases du dossier, publiées **à part** ; puis
  deux versions du modèle. On publie par carte la table, PABAK et son intervalle, et la dispersion de p entre
  exécutions. **Une stabilité élevée mesure la fiabilité, pas la validité** : un modèle peut être stablement
  faux (Shyr et al. 2025).
- **Propagation jusqu'à p.** `variantes_codage` ne mesure pas le bruit du codeur : il recalcule p comme si les
  mots d'ancrage faible étaient absents. La dispersion de p entre exécutions se publie à côté de chaque
  prévision de V4 ; elle n'entre pas dans le score.

### 11.2 Échec du codage

- **Règle.** Une carte n'entre dans un calcul de V4 que si son verdict `accord` est au moins `provisoire` :
  PABAK ≥ `kappa_min` (0,67), les deux taux de manque ≤ `fnr_max`, et le contrôle des absences sous forte
  prévalence. Aucun seuil nouveau : c'est la règle existante.
- **Estimation ponctuelle, intervalle publié.** Le critère porte sur la valeur de PABAK. `accord` publie depuis
  0.7.23 son intervalle approché (SE = 2·√(pₒ(1−pₒ)/n)) et n, le nombre de décisions. À pₒ = 0,90 (PABAK 0,80),
  la borne basse vaut 0,54 à 20 décisions et ne dépasse 0,67 qu'à partir de 82 environ. **Sous 82 décisions,
  le verdict se lit « non évaluable »**, pas « échec ». Les décisions d'un même cas ne sont pas indépendantes :
  l'intervalle est optimiste, et 250 décisions ne valent pas 250 cas.
- **PABAK est secondaire.** Ses repères viennent de l'α de Krippendorff ; PABAK ne corrige pas du hasard réel et
  devient indulgent sous forte prévalence. κ, π et α se publient avec lui. L'effectif d'accord se fixe sur la
  **largeur d'intervalle visée**, pas sur un seuil unique.
- **Conséquence.** Une carte en échec **invalide l'épisode** (hors V4, motif `codage`). Elle ne se remplace pas,
  et p ne se recalcule pas : la prévision est scellée. Le nombre d'épisodes invalidés se publie.

### 11.3 Les bras du test

`p_sans_cartes` n'est **pas** « le même dossier sans cartes » : il retire les λ et `multiplicateur_bouge`, mais
garde la cible et l'état codé. Le comparateur externe (§1) ne voit que la question, la résolution, l'échéance,
la date et le domaine. Un gain de l'alphabet sur lui peut donc venir de la structure du dossier, pas des cartes.
Cinq bras, sur les mêmes questions :

| Bras | Ce qu'il reçoit | Ce qu'il isole |
|---|---|---|
| modèle seul | la question et ses faits, sans dossier | la valeur du modèle |
| **dossier neutre** | même modèle, mêmes faits et dates que le dossier (`mots` réécrits en faits, `evenements`, `recherches`), même question et échéance ; **sans étiquette de carte, sans strate, sans marqueur** (la liste interdite de `elements_vus` s'étend) | la valeur du gabarit |
| inertie | `p_sans_cartes` | la valeur des fréquences |
| placebo | cartes permutées (`p_placebo`), scoré comme un bras | la valeur d'une étiquette quelconque |
| alphabet complet | le dossier scellé | ce qu'on veut mesurer |

**Deux niveaux.** Contre l'inertie, le placebo ou le modèle seul, V4 ne produit qu'un **jalon interne**. Seul le
contraste avec le **dossier neutre** permet d'écrire « les cartes apportent ». Tant que ce bras n'est pas joué,
« V4 atteint » se lit « jalon interne », et le texte doit le dire. Le dossier neutre est le plus coûteux des
bras (un bras manuel par épisode) ; le moteur ne le produit pas.

### 11.4 Couverture, refus et épisodes

- **Questions admises.** Les questions viennent d'un banc public, choisies avant lecture. Les séries
  purement chiffrées (prix, indices) sont exclues **d'avance** : sur elles, le test mesurerait l'inertie.
- **Repli sur abstention.** Le bras alphabet est scoré sur **toutes** les questions soumises et résolues ; une
  abstention reçoit la **fréquence de base** déclarée (sans cartes, p₀ = f, §2 de `graphe.md`). `scorer` publie
  depuis 0.7.23 `couverture` : questions chiffrées, abstentions, repli appliqué, abstentions sans repli,
  taux de repli, Brier sur les seules chiffrées et Brier avec repli. Une couverture incomplète (abstention sans
  fréquence de base) se déclare. Le skill s'abstient par construction quand les cartes ne s'ancrent pas :
  comparer sur les seules questions chiffrées comparerait sur un sous-ensemble choisi par l'outil.
- **Épisode.** Deux questions forment un même épisode si elles ont **la même date de résolution et le même
  événement sous-jacent**. La règle s'applique avant le premier épisode et se recopie dans `episode_id`.
- **Portée.** Un résultat vaut pour les strates où il a été mesuré. Un gain sur la strate 7 ne dit rien des
  douze autres.

### 11.5 Ce qui conclut

Deux conclusions, deux tests primaires ; `scorer` les rend dans `v4.decision` depuis 0.7.23.

| Conclusion | Test primaire | Pourquoi lui |
|---|---|---|
| « l'alphabet apporte au moins 2,5 points » | `e_gain_v4` ≥ `v4_e_seuil_primaire` (20) à un épisode quelconque | valide à tout instant, sans correction de relecture |
| « l'alphabet n'apporte rien » | **équivalence** (TOST, deux tests unilatéraux à `v4_alpha`) : l'intervalle à 90 % de d̄ tient dans ±`v4_equivalence_delta` (0,025), lu une seule fois, à l'effectif d'équivalence | un e-processus qui ne franchit pas son seuil dit « non établi », jamais « faux » |

- **Le test du signe devient descriptif.** Il se publie toujours, il ne décide plus ; le champ `statut` de V4
  (règle de 0.7.7) reste publié pour la trace.
- **Marge d'équivalence : 2,5 points.** δ = `v4_gain_abs` rend les deux conclusions symétriques : un même
  effectif, deux issues. Une marge de 1 point coûterait 6,25 fois plus d'épisodes (784 contre 125 à σ(d) =
  0,10, selon la formule du §5). Elle se lira **en seconde lecture déclarée**, sur des épisodes neufs, après la
  première. L'effectif d'équivalence se calcule avec z₁₋α + z₁₋β/₂ = 1,645 + 1,282 = 2,93, et non 2,80 : à
  σ(d) = 0,10, 138 épisodes et non 125 (le tableau de la relecture sous-estimait légèrement).
- **Barrière d'indépendance.** Les deux lectures supposent des épisodes indépendants. Si l'autocorrélation
  d'ordre 1 des différentiels dépasse `v4_autocorrelation_max` (0,3), **aucune** conclusion n'est émise : le
  design se révise (épisodes plus espacés). Ignorer une autocorrélation positive rendrait les deux tests
  permissifs, l'équivalence d'abord.
- **Échec prédictif.** L'alphabet échoue s'il ne bat pas le **dossier neutre** : sur ce contraste,
  l'e-processus ne franchit pas 20 **et** l'équivalence à δ est atteinte. L'un sans l'autre se lit « pas de
  preuve », non « échec ».
- **Ce que le moteur calcule et ne calcule pas.** `v4.decision` calcule ces lectures sur la référence de V4
  (l'inertie par défaut) et sur le comparateur externe s'il est joué. Il ne produit ni le bras dossier neutre ni
  la dispersion entre exécutions : ces bras se jouent hors du moteur et se journalisent comme comparateurs.

### 11.6 Leurres en aveugle

Le placebo est un contrôle négatif du **moteur**. L'effet Barnum est un risque de **lecture** par un humain
(Forer 1949 ; prédictions favorables générées par IA jugées plus valides, CHI 2026) ; aucun instrument du skill ne
le testait. Protocole :

1. Pour chaque situation factuelle d'un lot, une lecture réelle (mode LIRE) et un ou deux **leurres** : lectures
   produites sur une autre situation, ou par un tirage de cartes au hasard, réécrites à **même longueur, même ton
   et même valence**.
2. Des juges qui **connaissent la situation**, et non la personne concernée, qui juge mal sa propre situation.
   Ni les juges ni l'auteur ne savent quelle lecture est réelle ; l'ordre est tiré.
3. **Critère primaire fixé d'avance** : la lecture réelle est-elle reconnue au-dessus du hasard (1/2 ou 1/3
   selon le nombre de leurres), par un test binomial exact à 5 % ?
4. Le résultat se publie quel qu'il soit. Une lecture que des connaisseurs ne distinguent pas d'un leurre n'a pas
   de contenu propre à défendre, quelle que soit son élégance.

### 11.7 Exécution par des tiers

Un auteur qui code, juge et score ses propres cas reste une source de biais, même avec des sceaux. Pour V4 et le
test de leurres : le codage, le jugement des leurres et le score sont **exécutés ou audités par un tiers**, nommé
avant le premier épisode, qui publie son propre rapport. Sans tiers, un résultat se publie « exécuté par
l'auteur ».

### 11.8 Marges fermées (0.7.24)

Une troisième relecture a listé les endroits où une décision pouvait encore se prendre après coup. Chacun est
fermé ici, avant le premier épisode.

| Marge | Règle |
|---|---|
| **Exclure une question avant codage** | La liste des questions est tirée du banc par une règle publiée, et scellée avant tout codage. Une seule exclusion préalable est admise : une question qui se résout sur une série chiffrée, critère mécanique appliqué à la liste scellée. Toute autre question entre au journal ; si l'alphabet ne peut pas la coder (Hors domaine, état nul, question causale), c'est une abstention, avec repli (§11.4). Le codeur ne retire rien. |
| **Moment de l'accord** | L'accord se mesure **avant** le premier épisode, sur des cas de la base, pas sur les épisodes de V4. La liste des cartes admises (verdict au moins `provisoire`) se publie avec son empreinte avant l'épisode 1 et ne change plus pendant l'étude. Un état de V4 qui ancre une carte hors liste rend l'épisode hors V4 (motif `codage`), compté. Aujourd'hui aucune carte n'a d'accord mesuré : **V4 ne peut pas commencer** avant cette étude. |
| **Autocorrélation** | Estimateur : coefficient d'ordre 1 des différentiels d'épisode, centrés sur d̄, épisodes rangés par la date de leur première question (`differentiel`, `autocorrelation_1`). Il se lit au moment de la conclusion, sur tous les épisodes, et jamais avant `v4_n` épisodes. Au-delà de 0,3, « aucune conclusion » est **le résultat publié**, pas l'occasion de changer de test. |
| **Paraphrases et versions (`accord --llm`)** | Trois paraphrases par dossier, rédigées par une personne autre que l'auteur selon une consigne publiée, scellées avant la première exécution. Les versions de modèle testées sont nommées avant. |
| **PABAK et taux de manque** | La règle du code est la seule : PABAK ≥ 0,67, les deux taux de manque ≤ `fnr_max`, et le contrôle des absences quand la prévalence dépasse 0,5. Aucune exception n'est prévue, ni à écrire. |
| **Dossier neutre** | Produit **mécaniquement** depuis le dossier scellé, par la règle d'`export-codeur` : faits, sources et dates, sans carte, sans strate, sans marqueur, ordre mélangé par empreinte. Le gabarit de présentation est figé et son empreinte publiée avant l'épisode 1. Il contient la même information, au vocabulaire de l'alphabet près. Limite déclarée : les faits sont ceux que le codeur de l'alphabet a retenus ; le contraste mesure donc les étiquettes et ce qu'elles organisent, pas la sélection des faits. |
| **Issues des deux tests** | Écrites dans le code (`v4.decision`) : moins de `v4_n` épisodes, non évalué ; barrière franchie, aucune conclusion ; gain **et** équivalence, contradiction publiée, aucune conclusion ; gain seul, gain établi ; équivalence seule, aucun apport ; ni l'un ni l'autre à l'effectif d'équivalence, non établi, et l'étude s'arrête. |
| **Arrêt et effectif** | L'étude s'arrête au premier de trois événements : gain établi après au moins `v4_n` épisodes ; effectif d'équivalence atteint, où l'équivalence se lit **une seule fois** ; date limite déclarée avant l'épisode 1. L'effectif d'équivalence se fixe **une fois** : hypothèse déclarée σ(d) = 0,10, soit 138 épisodes, puis recalcul unique sur σ̂ après 20 épisodes, publié dans `v4_effectif_equivalence` avant l'épisode 21. Tant que ce paramètre vaut 0, aucune équivalence ne se conclut. L'arrêt anticipé sur le gain ne lit pas l'équivalence ; l'équivalence n'est jamais lue avant son effectif. |
| **Puissance** | 80 % (`v4_puissance`), valeur minimale déclarée. À 90 %, z vaut 3,29 et l'effectif environ 173 à σ(d) = 0,10. L'effectif augmente aussi si l'effet vrai n'est pas nul (0,01 par exemple) : c'est le risque accepté. |
| **Leurres** | 40 situations, une lecture réelle et un leurre chacune : proportion nulle 1/2. Chaque situation est jugée par un juge tiré parmi au moins deux, qui connaît la situation. Critère : au moins 26 lectures réelles reconnues sur 40 (binomial exact unilatéral, p = 0,040 ; 25 donnerait 0,077). Les leurres sont rédigés par une personne autre que l'auteur, selon une consigne publiée, après production des lectures réelles. |
| **Choix du tiers** | Nommé et publié avant l'épisode 1 (§11.7) ; un tiers nommé après les premiers résultats rend l'étude « exécutée par l'auteur ». |

Ces valeurs sont des **décisions d'auteur** prises avant toute mesure. Une valeur changée après l'épisode 1 ouvre une
nouvelle étude, sur des épisodes neufs.

### 11.9 Quatrième relecture : contraste confirmatoire, bras, leurres, fiche d'étude (0.7.25)

amass a relu le §11 complet et relevé huit marges, dont trois capables de changer la conclusion. Ses recalculs
concordent (0,54 ; 82 décisions ; 138 épisodes ; 26 sur 40). **Correction** de l'exemple du §11.5 : avec z = 2,93,
une marge de 1 point coûte **862** épisodes contre **138**, et non 784 contre 125 (calculés avec 2,80) ; le rapport
6,25 ne change pas.

**1. Un seul contraste confirmatoire, conjoint.** « Les cartes apportent » exige que l'alphabet établisse un gain
d'au moins 2,5 points contre **trois** bras à la fois : le **dossier neutre** (la structure du dossier), l'**inertie**
(les fréquences de base et le calibrage du moteur) et le **placebo** (les mêmes moteur et dossier, cartes
permutées : le contraste le plus direct sur les cartes). C'est un test d'intersection-union : chaque contraste à
`v4_alpha`, sans correction de multiplicité, puisque la conclusion exige les trois. L'effectif se calcule sur le
contraste au σ̂ le plus élevé. Le bras **modèle seul** et toute autre lecture sont **descriptifs** : ils se
publient, ils ne concluent jamais. Il n'y a donc plus qu'une occasion de conclure. Le placebo est défini :
`placebo_tirages` = 200 permutations par calcul, graine dérivée de l'état, de la cible et de la date
(`graine_placebo`), que personne ne choisit.

**2. Les bras d'un modèle de langage sont figés.** Pour le modèle seul et le dossier neutre : modèle et version
nommés ; consigne complète publiée avec son empreinte ; température 0 si le service la permet, sinon la valeur
par défaut, déclarée ; **5 exécutions** en contextes séparés ; agrégation par la **médiane** ; probabilités
écrêtées à [0,01 ; 0,99] (une probabilité de 0 ou 1 d'un modèle de langage est un artefact de format, et le
Brier la paie sans borne en perte logarithmique). Tout se fixe dans la fiche d'étude (point 6).

**3. Les leurres viennent du même dossier.** Le §11.6 admettait un leurre produit sur une autre situation : un juge
le rejetterait à ses faits, et le test mesurerait la fidélité aux faits, non l'apport des cartes. **Corrigé** : un
leurre est la lecture du **même dossier** avec des cartes permutées (tirage par la même règle que le placebo),
réécrite par un tiers à même longueur, ton et valence. **Deux juges** par situation : le premier, tiré, fournit le
critère primaire (unité : la situation) ; le second sert à mesurer l'accord entre juges, publié. **Puissance** du
critère de 26 sur 40, calcul exact : 0,95 si la vraie proportion de reconnaissance est 0,75 ; 0,81 si 0,70 ; 0,57
si 0,65. Un effet modeste a donc une chance sur deux d'être manqué : c'est déclaré. **Échec** : si le critère
n'est pas atteint, le mode LIRE est publié « lectures non distinguées d'un leurre à cartes permutées », dans le
README et le SKILL.md, jusqu'à une nouvelle étude sur des situations neuves. V4 peut se jouer quand même : il mesure
la prévision, pas la lecture.

**4. Les conclusions nomment l'hypothèse et le seuil.** `e_gain_v4` teste H0 « gain inférieur à 2,5 points »
(§5) : franchir 20 établit un gain d'**au moins** 2,5 points, et la contradiction avec l'équivalence est une vraie
contradiction. L'équivalence établit « **pas d'apport supérieur à 2,5 points** en valeur absolue », non « n'apporte
rien » : un apport de 1 ou 2 points n'est pas exclu. L'échec prédictif se lit de même. Les libellés de
`v4.decision` le disent depuis 0.7.25.

**5. Hors liste et abstention reçoivent le même repli.** Un état qui ancrerait une carte hors de la liste admise
se détecte **avant le scellement** de la prévision ; la prévision se journalise alors en abstention (motif
`carte hors liste`) et reçoit le repli, comme toute abstention. Plus rien ne sort du dénominateur. Le **d̄ primaire
est celui avec repli** : `scorer` le rend dans `couverture.v4_avec_repli` (abstentions prépubliées, non rejouées,
non fictives : la fréquence de base contre l'inertie donne d = 0 ; contre le comparateur externe, son propre
Brier). `v4` reste publié sur les seules chiffrées, à titre descriptif. La **fréquence de base** vient d'une classe
de référence publiée avant l'épisode 1 : le taux de réalisation, sur les questions du même banc et de même
catégorie résolues avant cette date. Une carte au verdict « non évaluable » (moins de 82 décisions) **n'est pas
admise**. Le moteur ne produit pas encore le motif `carte hors liste` : c'est une règle de protocole.

**6. Fiche d'étude, horodatée chez un tiers avant l'épisode 1.** Le §11 renvoie aux paramètres par l'empreinte de
`assets/parametres.json` (ligne de `SHA256SUMS` de la version figée). Valeurs aujourd'hui : `v4_n` 50, `v4_alpha`
0,05, `v4_puissance` 0,8, `v4_gain_abs` 0,025, `v4_equivalence_delta` 0,025, `v4_autocorrelation_max` 0,3,
`v4_e_seuil_primaire` 20, `v4_effectif_equivalence` 0 (non fixé), `kappa_min` 0,67, `fnr_max` 0,2,
`placebo_tirages` 200. La fiche, à remplir avant l'épisode 1, porte :

| Champ | Contenu |
|---|---|
| version | version du skill et empreinte de `parametres.json` |
| banc | banc public de questions, règle de tirage, graine du tirage |
| horizon | borne de l'horizon de résolution des questions (minimum et maximum, en jours) |
| strates | strates couvertes (la portée du résultat) |
| cartes admises | liste et empreinte, avec la table d'accord de chacune |
| classe de référence | règle et valeurs des fréquences de base |
| bras | modèle et version, consigne et son empreinte, température, exécutions, agrégation, écrêtage |
| dossier neutre | gabarit et son empreinte |
| leurres | consigne de réécriture, rédacteur, juges |
| arrêt | date limite ; plafond d'effectif |
| tiers | nom, rôle (ci-dessous), date d'engagement |

**7. Vérifiable par un tiers.** Un historique git personnel peut être réécrit : la fiche, la version du §11 et
l'empreinte des paramètres se publient dans un dépôt horodaté par un tiers (release, archive web, ou registre de
préenregistrement), et l'adresse se recopie dans chaque prévision. **Rôle du tiers, décidé ici** : il **exécute** le
score et le test de leurres, et il **code indépendamment** un tirage de 20 % des états de V4, dont l'accord avec le
codeur de l'auteur se publie. Un audit seul ne remplace pas ce codage. La confirmation humaine d'un état proposé par
un modèle reste une règle sans mécanisme dans le moteur : la fiche nomme qui confirme.

**8. Deux points moindres.** L'accord mesuré sur des cas de la base, dont l'issue est connue, peut être
optimiste : le recodage par le tiers des 20 % d'états de V4 mesure l'accord **en prospectif**, et c'est lui qui se
lit pour V4. Le recalcul de σ̂ après 20 épisodes est bruité (environ 16 % d'erreur relative, donc environ 30 % sur
l'effectif) : un **plafond** se déclare dans la fiche, **300 épisodes** par défaut. Si l'effectif recalculé le
dépasse, l'étude s'arrête au plafond et conclut « non établi ».

### 11.10 Cinquième relecture : ordre des opérations, accord prospectif, placebo (0.7.26)

amass a relu le §11.9 et relevé sept marges ; ses recalculs concordent (0,81 ; 0,57 ; 862 contre 138 ; 16 % et
environ 30 %). Toutes sont retenues. En les vérifiant contre le code, une erreur **de notre texte** est apparue.

**Correction du §11.9, points 1 et 3 : le placebo ne permute pas les cartes.** `p_placebo` est un placebo
d'**homologie** (`placebo_homologie`, 0.7.4) : le même a priori p₀, cartes comprises, la même révision, mais des
cas **tirés au hasard** dans la même strate et la même fenêtre, en même nombre que la classe retenue, au lieu des
homologues. On moyenne 200 tirages (`placebo_tirages`), graine dérivée de l'état, de la cible et de la date. Ce
qui est préservé : la strate, la fenêtre, le nombre de cas, p₀ ; ce qui est tiré : quels cas. Aucun état n'est
fabriqué, donc pas d'état improbable que l'alphabet battrait trop facilement. Ce que mesure chaque contraste :
- contre l'**inertie** (`p_sans_cartes`, sans les λ) : l'apport des cartes **dans l'a priori** ;
- contre le **placebo** : l'apport des cartes **dans le choix des homologues** ;
- contre le **dossier neutre** : l'apport de l'appareil entier sur un modèle qui lit les mêmes faits.

Les cartes agissent par deux chemins, l'a priori et l'homologie ; la conjonction inertie et placebo les couvre
tous les deux, le dossier neutre ajoute la comparaison extérieure. La conjonction du §11.9 reste donc juste, mais
sa justification était fausse : « le même dossier, cartes permutées » décrivait un placebo qui n'existe pas. La
moyenne de 200 tirages n'est pas un comparateur proche de l'inertie : elle garde les λ.

**1. Ordre des opérations, horodaté étape par étape.** Le codeur ne lance jamais le calcul. Séquence, chaque
étape horodatée chez le tiers avant la suivante :
1. l'état est codé sur le dossier, et son empreinte publiée ;
2. le contrôle de la liste des cartes admises s'applique à cet état publié ; une carte hors liste fait de la
   question une abstention, **à cette étape seulement** ;
3. le **tiers** calcule p à partir de l'état publié (`calculer --dossier`) ;
4. le scellement suit, obligatoire : un p calculé ne se retire pas, l'état ne se recode pas.

Aucune abstention n'est admise après l'étape 2. Ainsi, le jugement du codeur sur l'issue ne peut plus passer dans
le score par un retrait sélectif.

**2. Accord prospectif : une règle groupée.** Le recodage de 20 % des états de V4 donne environ 10 états à 50
épisodes et 28 à 138 : trop peu par carte pour le seuil de 82 décisions. La règle prospective est donc **groupée** :
la table 2×2 somme toutes les décisions carte × strate des états recodés (environ 450 à 138 épisodes) ; `accord` la
lit (PABAK, taux de manque, κ, π, α, intervalle). **Critère** : verdict groupé au moins `provisoire`. **Échec** :
aucune conclusion confirmatoire ; les résultats de V4 se publient sous le libellé « codage non reproduit en
prospectif ». L'accord par carte se publie, descriptif. Les décisions d'un même état ne sont pas indépendantes :
l'intervalle groupé est optimiste, c'est déclaré.

**3. Trois contrastes : puissance conjointe et cas mixtes.**
- **Puissance.** 80 % par contraste donnerait environ 51 % pour la conjonction si les contrastes étaient
  indépendants. L'effectif se planifie donc à **93 % par contraste** (0,93³ ≈ 0,80) : z = 1,645 + 1,812 = 3,46, soit
  **192 épisodes** à σ(d) = 0,10 pour l'équivalence. C'est l'hypothèse de la fiche, recalculée une fois (§11.8).
  Si les contrastes sont corrélés positivement, la puissance conjointe est plus haute.
- **Équivalence nommée.** « Les cartes n'apportent pas plus de 2,5 points » exige l'équivalence contre l'inertie
  **et** contre le placebo. L'équivalence contre le dossier neutre est un autre énoncé, publié sous son propre
  libellé : « l'alphabet ne fait pas mieux de plus de 2,5 points qu'un modèle qui lit les mêmes faits ».
- **Cas mixtes.** Gain contre un ou deux des trois bras seulement : « non établi : gain partiel contre … »,
  descriptif ; aucune conclusion confirmatoire. Le moteur ne lit qu'une référence à la fois (`v4.decision`) ; la
  table conjointe se lit sur les trois sorties.

**4. Leurres : même procédure pour les deux lectures.** La lecture réelle **et** le leurre sont réécrits par le
même tiers, selon la même consigne, à même longueur, ton et valence ; les juges ne peuvent plus reconnaître la
lecture réelle à son style. Les cartes du leurre sont tirées au hasard parmi les seize, en même nombre et dans
les mêmes strates que la lecture réelle, avec une graine dérivée de la situation. Présentation **en paire**,
position tirée au sort ; c'est ce que suppose la proportion nulle de 1/2. Les juges connaissent la situation et
sont étrangers au projet ; le tiers les recrute. L'accord entre juges se publie, descriptif, sans seuil.

**5. Graines et traces.** La graine du tirage des questions n'est choisie par personne : elle dérive d'une valeur
publique postérieure à l'engagement (la première valeur d'une balise d'aléa publique, par exemple celle du NIST,
après l'horodatage de la fiche). Les cinq exécutions de chaque bras d'un modèle de langage, sorties brutes
comprises, se publient avec leur empreinte, aucune n'étant écartée. Si la version du modèle d'un bras disparaît en
cours d'étude, le bras s'arrête sans substitution ; si c'est le dossier neutre, la conclusion confirmatoire devient
impossible, et l'étude se clôt « non établi » sur ce point.

**6. Trois détails.**
- **Dilution.** Une abstention vaut d = 0 contre l'inertie : avec 40 % d'abstentions, un gain de 2,5 points sur
  l'ensemble suppose environ 4,2 points sur les questions chiffrées. La fiche déclare un **taux d'abstention
  maximal, 40 % par défaut** ; au-delà, l'étude conclut « non établi ».
- **Plafond.** Les 300 épisodes plafonnent l'effectif d'**équivalence** seulement. Le gain peut conclure dès
  `v4_n` épisodes, par l'e-processus.
- **Écrêtage, justification corrigée.** Le §11.9 disait que le Brier paie sans borne une probabilité de 0 ou 1 :
  c'est faux, le Brier est borné ; c'est la perte logarithmique (publiée par `scorer`) qui ne l'est pas. L'écrêtage
  à [0,01 ; 0,99] est sans effet notable sur le Brier et légèrement favorable aux bras d'un modèle : il est donc
  prudent pour la comparaison.

### 11.11 Sixième relecture : ce que la conclusion positive voudra dire (0.7.27)

amass a relu le §11.10 et relevé six marges ; ses recalculs concordent (0,51 ; 0,93 ; 3,46 ; 192 ; 4,17). La
première change le sens de la conclusion : elle est retenue, et la conjonction du §11.9 et du §11.10 est
**remplacée** ci-dessous. Ces deux paragraphes restent écrits ; c'est celui-ci qui fait foi.

**1. Les trois p sont emboîtés.** Côte à côte, avec f la fréquence de référence, λ les multiplicateurs des
cartes, k = 2 et p₀ = logit⁻¹(logit f + Σ ln λ) :

| Bras | Formule | Cartes dans l'a priori | Cartes dans le choix des cas |
|---|---|---|---|
| inertie (`p_sans_cartes`) | p = f (λ = 1, aucun homologue retenu) | non | non |
| placebo (`p_placebo`) | moyenne sur 200 tirages de (n_E* + k·p₀)/(n_A* + k), les cas étant tirés au hasard dans la strate et la fenêtre, en nombre égal à la classe retenue | oui | non |
| alphabet (`p`) | (n_E + k·p₀)/(n_A + k) sur les homologues | oui | oui |

Les contrastes se lisent donc ainsi, et le §11.10 se trompait en disant que l'inertie mesure « l'apport dans l'a
priori » :

| Contraste | Ce qu'il mesure | Statut |
|---|---|---|
| alphabet − inertie | l'**effet total** des cartes (a priori et homologues) | **confirmatoire** |
| alphabet − dossier neutre | l'apport de l'appareil sur un modèle qui lit les mêmes faits | **confirmatoire** |
| placebo − inertie | le chemin de l'**a priori** seul | descriptif |
| alphabet − placebo | le chemin du **choix des homologues** seul | descriptif |

**Conclusion positive, libellé exact** : « l'alphabet apporte au moins 2,5 points de Brier par rapport à ses propres
fréquences sans cartes, **et** par rapport à un modèle qui lit les mêmes faits ». Elle exige les deux contrastes
confirmatoires (intersection-union, chacun à `v4_alpha`). L'ancienne conjonction exigeait en plus que le choix des
homologues apporte 2,5 points à lui seul : si les cartes n'agissaient que par l'a priori, l'étude n'aurait jamais
pu conclure. La décomposition entre les deux chemins se publie, descriptive. Le placebo se publie sous ses deux
formes : la moyenne des 200 tirages (un comparateur sans bruit d'échantillonnage, donc plus exigeant) et sa plage
à 90 % (`plage_90`), qui dit ce que donnerait un choix quelconque de cas.

**Puissance**, recalculée pour deux contrastes : 0,8^½ ≈ 0,894 par contraste ; z = 1,645 + 1,617 = 3,26 ; **171
épisodes** à σ(d) = 0,10 pour l'équivalence. Ce chiffre remplace les 192 du §11.10 comme hypothèse de la fiche.

**2. Équivalence : deux lectures, toutes deux exigées.** Une abstention vaut d = 0 contre l'inertie : elle dilue le
gain, mais elle **facilite** l'équivalence, en rapprochant la moyenne de zéro et en réduisant la variance.
« Pas d'apport supérieur à 2,5 points » exige donc l'équivalence **sur l'ensemble avec repli et sur les seules
questions codées** (`v4` et `couverture.v4_avec_repli`, deux sorties de `scorer`). σ(d) s'estime sur les deux ;
l'effectif d'équivalence se fixe sur le plus grand. L'hypothèse de 0,10 vaut pour chacun.

**3. Accord prospectif groupé : quatre précisions.**
- **Aucune carte cachée.** La table groupée est dominée par des absences partagées, et un taux de manque groupé
  peut masquer une carte fréquente entièrement discordante. Le critère groupé s'accompagne d'un critère par carte :
  toute carte qui atteint `accord_min_ancrages` ancrages dans le recodage et dont le verdict est « insuffisant »
  fait échouer l'accord prospectif.
- **Borne basse, par bootstrap sur les états.** L'intervalle groupé se calcule par bootstrap sur les **états**
  recodés (2 000 rééchantillons, graine publique), et le critère porte sur la **borne basse** : au moins 0,67. Le
  moteur ne fait pas ce bootstrap ; le tiers le fait et publie son script.
- **Tirage.** Le tiers tire les 20 % d'états à recoder, avec la même balise publique que les questions.
- **Moment.** Le recodage a lieu **avant la résolution** de la question, ou à l'aveugle de son issue.

**4. Ce qui ne se contrôle pas, et un levier retiré.**
- **Limite déclarée.** « Le codeur ne lance jamais le calcul » reste invérifiable : le moteur est public, et une
  exécution privée ne laisse pas de trace. Les options : un codeur qui n'a pas l'environnement du moteur, ou la
  déclaration de cette limite dans la publication. La fiche dit laquelle.
- **Tout se code, seul le tiers s'abstient.** Toute question soumise est codée. Le codeur ne s'abstient jamais ; le
  tiers seul prononce une abstention, pour un motif de la liste fermée (état nul, Hors domaine, question causale,
  temporalité sans référence externe), et les motifs se publient.
- **Carte hors liste : retirée, non convertie (correction du §11.9, point 5).** Convertir en abstention un état qui
  ancre une carte hors liste laissait au codeur un levier : ancrer une telle carte là où il pense que l'alphabet
  se trompera. Désormais, le tiers **retire mécaniquement** de l'état publié les mots des cartes non admises,
  publie l'état avant et après le retrait, et calcule sur l'état restant ; seul un état devenu nul fait une
  abstention.

**5. Trois détails.**
- **Fiche.** Toute modification de la fiche après la valeur de la balise ouvre une nouvelle étude ; la graine
  précédente se déclare avec la nouvelle.
- **Modèle des bras.** Un modèle hébergé peut disparaître avant 171 épisodes et donner à son fournisseur un veto sur
  l'étude. Les bras d'un modèle de langage utilisent donc un modèle **à poids ouverts**, version figée, hébergé par
  le tiers, empreinte des poids publiée.
- **`v4_n`** se compte sur les mêmes épisodes que le d̄ primaire, abstentions comprises
  (`couverture.v4_avec_repli`, qui applique le plancher sur ses propres épisodes).

**6. Leurres : réécriture aveugle et contrôle positif.**
- Le réécrivain reçoit les deux lectures sans savoir laquelle est réelle, dans un ordre tiré.
- **Contrôle positif** : chaque juge reçoit aussi 10 paires dont le leurre vient d'une **autre** situation, mêlées
  aux autres. Un juge qui en reconnaît moins de 9 sur 10 est exclu, selon cette règle fixée d'avance ; si plus de
  la moitié des juges sont exclus, le test principal est déclaré sans valeur.
- Une reconnaissance faible des leurres à cartes tirées au hasard dirait que les cartes s'adaptent à des situations
  variées. C'est précisément le risque de lecture Barnum que le test expose : ce résultat se publie comme tel.

### 11.12 Septième relecture : la base de cas, la puissance du gain (0.7.28)

amass a relu le §11.11 et relevé six marges ; ses recalculs concordent (0,894 ; 3,26 ; 171). Les deux premières
changent ce que les conclusions voudront dire ; elles sont retenues, et la première a demandé du code.

**1. L'inertie ne tire pas les mêmes cas : un quatrième p, l'inertie de strate.** Le §11.11 écrivait « alphabet −
inertie = effet total des cartes ». C'est trop fort, pour une raison un peu différente de celle qu'avance la relecture.
f n'est pas une référence extérieure à la base : c'est la fréquence de la base dans la strate, contractée vers une
référence avec k₀ = 20 pseudo-observations (`graphe.md` §2.2). Mais l'alphabet et le placebo n'utilisent pas f : ils
révisent p₀ sur c_A cas avec k = 2. Le passage de f à un petit échantillon faiblement contracté change p sans
qu'aucune carte y soit pour rien. **Mesuré sur la démonstration** (POLARITÉ@7 + CONTRAINTE@6 → SEUIL@7) : f = 12,1 %,
inertie de strate 17,6 %, placebo 20,2 %, alphabet 22,0 %. Sur les 9,9 points d'écart entre l'alphabet et f, 5,5
viennent du tirage de cas, sans carte. La relecture avait raison sur la conséquence.

Le moteur calcule depuis 0.7.28 l'**inertie de strate** : les mêmes tirages que le placebo (même graine, même nombre
de cas, 200 tirages), sous p₀ = f, sans λ. Sortie `p_inertie_strate` de `calculer`, champ facultatif du journal
contrôlé contre le calcul figé, et `v4_inertie_strate` dans `scorer`. Les quatre p :

| Bras | Formule | λ | Cas |
|---|---|---|---|
| inertie (`p_sans_cartes`) | f, fréquence de la strate contractée (k₀ = 20) | non | tous, sans tirage |
| inertie de strate (`p_inertie_strate`) | moyenne sur 200 tirages de (n_E* + k·f)/(n_A* + k) | non | tirés au hasard |
| placebo (`p_placebo`) | moyenne sur les **mêmes** tirages de (n_E* + k·p₀)/(n_A* + k) | oui | tirés au hasard |
| alphabet (`p`) | (n_E + k·p₀)/(n_A + k) | oui | homologues |

| Contraste | Ce qu'il mesure | Statut |
|---|---|---|
| alphabet − inertie de strate | l'**effet des cartes** (a priori et homologues), à base de cas et contraction égales | **confirmatoire** (remplace alphabet − inertie) |
| alphabet − dossier neutre | l'apport de l'appareil sur un modèle qui lit les mêmes faits **et les mêmes fréquences** | **confirmatoire** |
| placebo − inertie de strate | l'a priori des cartes seul (mêmes cas, seuls les λ changent) | descriptif |
| alphabet − placebo | le choix des homologues seul | descriptif |
| alphabet − inertie | l'effet de l'appareil avec sa base de cas | descriptif |

La décomposition est exacte : alphabet − inertie de strate = (alphabet − placebo) + (placebo − inertie de strate).
Le biais de troncature de la base (§10) touche les quatre p ; aucun contraste ne l'élimine, et c'est déclaré.

**2. Puissance de la conclusion de gain, publiée d'avance.** Les 171 épisodes sont calculés pour l'équivalence à effet
nul. Pour le gain, approximation normale, σ(d) = 0,10, un regard à 171 épisodes, un contraste (erreur-type 0,77 point) :

| Gain vrai (points) | « gain ≥ 2,5 établi » | « pas d'apport > 2,5 » | « non établi » |
|---|---|---|---|
| 0 | 0,00 | 0,90 | 0,10 |
| 1 | 0,00 | 0,62 | 0,38 |
| 2 | 0,01 | 0,16 | 0,83 |
| 2,5 | 0,05 | 0,05 | 0,90 |
| 3 | 0,16 | 0,01 | 0,83 |
| 4 | 0,62 | 0,00 | 0,38 |
| 5 | 0,95 | 0,00 | 0,05 |

Pour deux contrastes à 0,894, 80 % de puissance demande un gain vrai d'environ 4,7 points ; l'e-processus, lisible à
tout instant, est moins puissant qu'un test à un regard. **Lecture** : un apport vrai entre 2 et environ 4,5 points
finira le plus souvent « non établi ». Ce n'est pas un échec : la zone grise est large et voulue, parce que le seuil
est 2,5 points. Ce tableau est publié avec la fiche, avant l'épisode 1.

**3. La conclusion négative porte sur un contraste désigné.** « Les cartes n'apportent pas plus de 2,5 points » se
lit sur **le seul contraste alphabet − inertie de strate**, désigné d'avance, en équivalence sur les deux ensembles
(avec repli et codées seules, §11.11). Pas d'union, donc pas de correction. L'équivalence contre le dossier neutre est
un autre énoncé, publié sous son libellé (« l'appareil ne fait pas mieux de plus de 2,5 points que [modèle nommé] lisant
les mêmes faits ») ; elle ne dit rien des cartes.

**4. Le dossier neutre reçoit les mêmes fréquences, et la conclusion nomme son modèle.** La consigne du dossier neutre
donne au modèle f et l'inertie de strate, chiffrés, avec leur définition : sans elles, le gain contre ce bras comprendrait
la valeur des fréquences. L'alphabet est un codeur humain plus un moteur : le contraste contre le dossier neutre mesure
**l'appareil**, et la phrase « les cartes apportent » ne s'en déduit pas ; elle ne se déduit que du contraste alphabet −
inertie de strate. Le libellé confirmatoire nomme le modèle et sa version : la conclusion ne vaut que contre lui.

**5. Accord prospectif : le taux de manque aussi par bootstrap.** Le critère groupé exige, sur le même bootstrap par états,
la borne basse de PABAK ≥ 0,67 **et** la borne haute du taux de manque ≤ 0,2. Probabilité de passage, publiée d'avance :
avec environ 50 décisions « présent » et un taux de manque vrai de 10 %, environ 0,77 (simulation, borne unilatérale
approchée) ; le critère est exigeant. Les cartes sous `accord_min_ancrages` ancrages dans le recodage sont **non évaluées
en prospectif** : leur liste se publie, et les épisodes qui les ancrent restent dans V4 (ces cartes étaient admises avant
l'étude), avec ce drapeau.

**6. Barème des abstentions du tiers.** La fiche fixe, pour chaque motif de la liste fermée, une définition et deux
exemples : état nul (aucun mot après retrait des cartes non admises) ; Hors domaine (la carte cible est Hors domaine dans
la strate, `equivalences/strate-NN.md`) ; question causale (la question demande ce qui **fait** arriver l'événement, non
s'il arrive) ; temporalité sans référence externe (`programmee` ou `duree_de_vie` sans `--fref` ni `--references`, que le
moteur refuse lui-même). Les abstentions se publient **par motif**.

**Le tiers.** Tout le dispositif repose sur son indépendance réelle, et c'est ce qu'un lecteur jugera en premier. La
fiche publie sa relation à l'auteur (aucun lien financier, professionnel ou familial, ou leur nature s'il en existe), la
façon dont il a été choisi, et une déclaration d'intérêts signée.

### 11.13 Huitième relecture : deux énoncés, non-supériorité, nuisance (0.7.29)

amass a relu le §11.12 ; ses recalculs concordent (4,4 = 1,8 + 2,6 ; 9,9 dont 5,5 ; le tableau de puissance à ±0,01).
Il ne relève plus de décision ouverte après coup, et cinq marges de lecture, toutes retenues. Les règles ci-dessous
**remplacent** celles des §11.11 et §11.12 là où elles diffèrent ; ces paragraphes restent écrits.

**1. Deux énoncés séparés, non une conjonction.** Le §11.11 exigeait la conjonction (inertie et dossier neutre) ; le
§11.12 disait que « les cartes apportent » ne se déduit que du contraste avec l'inertie de strate. Les deux textes se
contredisaient. Désormais, deux énoncés, chacun avec son libellé, son α (`v4_alpha`) et sa règle, chacun publié seul,
donc sans multiplicité :
- **Énoncé C (cartes)** : « les cartes apportent au moins 2,5 points », sur alphabet − inertie de strate.
- **Énoncé A (appareil)** : « l'appareil apporte au moins 2,5 points par rapport à [modèle et version] lisant les mêmes
  faits et les mêmes fréquences », sur alphabet − dossier neutre.

| | A : oui | A : non établi ou négatif |
|---|---|---|
| **C : oui** | les cartes apportent, et l'appareil bat le modèle | les cartes apportent sur les fréquences, l'appareil ne bat pas le modèle |
| **C : non établi ou négatif** | l'appareil bat le modèle, sans que les cartes en soient la cause établie | ni l'un ni l'autre |

La puissance à deux contrastes du §11.11 (0,894 par contraste) ne s'applique plus : chaque énoncé a sa propre
puissance, à 80 %.

**2. Non-supériorité, et un énoncé de nuisance.** L'énoncé négatif « pas d'apport supérieur à 2,5 points » se testait par
une équivalence bilatérale : un alphabet **pire** de plus de 2,5 points restait « non établi », alors que la phrase était
vraie. Il devient un test **unilatéral de non-supériorité** : la borne basse unilatérale à 95 % de d̄ (Brier de
l'alphabet − Brier de la référence) dépasse −0,025. S'y ajoute un énoncé séparé de **nuisance** : la même borne dépasse
+0,025, c'est-à-dire que l'alphabet dégrade de plus de 2,5 points. `v4.decision` rend les deux depuis 0.7.29
(`nuisance`). Un alphabet nuisible est un résultat, publié comme tel.

**3. Effectif et puissance, par énoncé.** La non-supériorité demande z = 1,645 + 0,842 = 2,49, soit **99 épisodes** à
σ(d) = 0,10 ; c'est le minimum pour la lire. Mais le gain, à ce même effectif, aurait peu de puissance. Le point de lecture
retenu est donc fixé par le gain : **171 épisodes** à σ(d) = 0,10 (80 % de puissance pour un gain vrai d'environ 4,4
points, un contraste). Puissance, approximation normale, un regard à 171 épisodes, erreur-type 0,76 point :

| Gain vrai (points) | « gain ≥ 2,5 » | « pas d'apport > 2,5 » | « dégradation > 2,5 » | « non établi » |
|---|---|---|---|---|
| −4 | 0,00 | 1,00 | 0,62 | 0,00 |
| −2,5 | 0,00 | 1,00 | 0,05 | 0,00 |
| 0 | 0,00 | 0,95 | 0,00 | 0,05 |
| 1 | 0,00 | 0,62 | 0,00 | 0,38 |
| 1,5 | 0,00 | 0,37 | 0,00 | 0,63 |
| 2 | 0,01 | 0,16 | 0,00 | 0,83 |
| 2,5 | 0,05 | 0,05 | 0,00 | 0,90 |
| 3 | 0,16 | 0,01 | 0,00 | 0,83 |
| 4 | 0,62 | 0,00 | 0,00 | 0,38 |
| 5 | 0,95 | 0,00 | 0,00 | 0,05 |

(« dégradation » est un énoncé séparé ; quand il est établi, « pas d'apport > 2,5 » l'est aussi.) Le tableau se publie
**pour chaque énoncé, avec son σ** : σ(d) contre le dossier neutre est sans doute plus grand contre lui que contre l'inertie de
strate, un modèle de langage pouvant s'écarter d'une fréquence bien plus qu'une inertie. Le recalcul unique après 20
épisodes (§11.8) se fait **par contraste**, et `v4_effectif_equivalence` retient le plus grand.

**4. Ce que « pas d'apport supérieur à 2,5 points » n'exclut pas.** Pour un apport vrai de 1,5 point, cette conclusion
sort avec une probabilité de 0,37 : un apport réel et modeste peut la produire. La fiche porte la phrase, en clair :
« Cette conclusion n'exclut pas un apport inférieur à 2,5 points. » Elle porte aussi la raison du seuil : l'étude est
conçue pour détecter de **grands** effets. Un seuil de 1 point demanderait environ 620 épisodes en non-supériorité et
860 en équivalence, hors de portée d'une première étude ; 2,5 points valent 10 % d'un Brier de 0,25.

**5. Troncature différentielle.** Le contraste alphabet − inertie de strate ne neutralise pas la troncature de la base
(§10) : elle peut rendre les homologues choisis par les cartes plus ou moins représentatifs que des cas tirés au hasard.
Sur des questions d'un banc public, qui ne sont pas tronquées, ce défaut jouerait plutôt **contre** l'alphabet. Cela pèse
sur la lecture d'un résultat négatif, et c'est l'une des raisons de l'énoncé de nuisance.

**6. Fin de cette boucle de relecture.** amass le dit lui-même : chaque tour a été fait par le même relecteur, avec la
même grille, et ce n'est pas une évaluation indépendante. Avant l'épisode 1, la fiche et le §11 sont relus par **un
biostatisticien ou un méthodologue qui n'a pas participé à leur écriture**, et par le tiers désigné ; leurs rapports
se publient avec la fiche. Cette relecture externe est une condition de l'épisode 1, au même titre que l'étude d'accord.

### 11.14 Deux précisions de formulation (0.7.30)

amass a relu le §11.13 : plus de marge qui laisse une décision ouverte après coup ; ses recalculs concordent (99 ; 619 ;
862 ; le tableau à ±0,01 ; 4,4 points ; 10 %). Il a relu le texte, sans exécuter `v4.decision`.

- **Le nom `v4_effectif_equivalence`.** Le paramètre garde son nom de 0.7.24, mais il fixe depuis 0.7.29 le **point de
  lecture** de l'énoncé négatif, qui est une **non-supériorité unilatérale**, et de l'énoncé de nuisance : il n'y a plus
  de test d'équivalence bilatéral dans la règle. Le nom est conservé pour ne pas casser les journaux et les textes
  antérieurs ; la fiche le dit.
- **Une erreur par énoncé, pas pour l'ensemble.** C, A, « pas d'apport supérieur à 2,5 points » et « dégradation de plus
  de 2,5 points » sont chacun testés à `v4_alpha`. L'erreur est contrôlée **par énoncé**, non pour la famille : plusieurs
  énoncés donnent plus d'occasions d'affirmer à tort au moins l'un d'eux. En contrepartie, **les énoncés se publient
  toujours ensemble**, y compris ceux qui échouent, et aucun ne se cite sans les autres.

---

## 12. Attribution dans le moteur (0.7.31)

**Source.** Vasant Kumar Mogia, « Agent-Causality: Declared Dependency Tracing and Counterfactual Sensitivity Analysis
for Multi-Agent Systems », Psionics, 2026 (préprint, non relu par des pairs ; preuves : cinq cas construits et un essai
réel où les pannes injectées ne se sont pas produites). L'article rejoue une décision **déterministe** en remplaçant
ses entrées, seules ou ensemble, par une valeur neutre, et en tire des valeurs de Shapley et un indice d'interaction
par paire. Il répète que ces nombres ne disent rien de la causalité réelle. Le moteur du skill est un évaluateur de ce
type : déterministe, et un état n'a que quelques mots.

**Ce que fait `attribuer`.** Pour un état et un événement simple, le moteur recalcule p sur **tous les sous-ensembles**
des mots de l'état (2ⁿ calculs, n ≤ 8 ; la cible reste présente pour « persiste » et « disparait » ; l'ensemble vide
vaut p_sans_cartes). Il rend :
- la **valeur de Shapley exacte** de chaque mot, en points de probabilité ; leur somme vaut exactement p complet − p
  sans mots (propriété d'efficacité, contrôlée par l'autotest) ;
- l'**indice d'interaction** de chaque paire (Grabisch 1997), calculé **en logit** : l'a priori est additif en logit
  (`dynamiques.md`, « La loi de composition, nommée »), donc un indice non nul ne peut venir que du choix des homologues.
  Positif : les deux mots se renforcent (forme « conjointe ») ; négatif : ils sont redondants ; nul : additifs.

**Premier constat, sur la démonstration.** POLARITÉ@7 + CONTRAINTE@6 → SEUIL@7 apparaît : p = 22,0 %, sans ces mots
12,1 % ; CONTRAINTE@6 pèse +7,6 points et POLARITÉ@7 +2,3 ; leur interaction vaut **+1,51 en logit**. Sur ce cas, le
moteur n'est donc **pas** additif : les homologues retenus quand les deux cartes sont présentes font plus que la somme
de chacune. Le §« Additif, pas configurationnel » de la 0.7.22 l'admettait comme possible ; `attribuer` le mesure. Sur
une base vide, l'interaction est nulle (autotest). C'est une base fictive : le constat décrit la mécanique du calcul,
pas le monde.

**Ce que ces nombres ne disent pas.** Ils expliquent **pourquoi le moteur a rendu ce p**, sous cette base, cette
matrice et ces paramètres ; ils ne disent ni pourquoi l'événement arrivera, ni qu'une carte en est la cause. Une
valeur de Shapley élevée n'est pas un apport prédictif : celui-ci ne se mesure qu'en V4 (§11). Les quatre formes de
l'article (une entrée suffit ; l'une ou l'autre ; les deux ensemble ; l'une change la lecture de l'autre) se lisent ici
comme des formes du **calcul**. Limites : sans liaisons ni positions (refusées) ; un pas ; temporalité générique ;
au-delà de 8 mots, refus plutôt qu'approximation par échantillonnage.

---

## 13. Audit pratique : acquérir le matériau (0.7.32)

**Source.** Audit du dépôt par DeepSeek V4, sur un clone de la 0.7.31 (commit `876d3ee`), avec exécution des contrôles
et des commandes. Son constat rejoint `bilan` : l'instrumentation est achevée, la calibration n'a pas commencé, et le
goulot n'est plus la méthode mais **l'acquisition** du matériau (dossiers, cas réels). Vérifié ici contre le code.

**Versé.**
- `recolter` : carnet de faits datés et sourcés, avant tout codage ; `--jusqu-au` en tire le brouillon d'un dossier
  (`base-de-cas.md` §2).
- Grille à deux axes des sources (A à F, 1 à 6) : facultative, contrôlée, et un ancrage F l'exige bonne (même endroit).
- `depouiller` : le κ depuis deux codages des mêmes cas, par carte et groupé (A4). C'est la pièce qui manquait à
  l'étude d'accord, condition de l'épisode 1 (§11.8).
- Le test de sortie Windows (cp1252) couvre aussi les glyphes d'`accord` (κ, π, α, ₒ). La correction de 0.7.1 était
  déjà indépendante du glyphe (`backslashreplace`) ; le test le prouve maintenant.

**Déjà présent, contrairement à ce que l'audit suggère.**
- **Provenance de chaque sortie** : tout JSON de `calculer` porte `contexte.empreintes` (moteur, paramètres, base) et
  la version.
- **Sceau d'adjudication** : la règle de résolution est déjà dans le dossier scellé (`evenements[].resolution`,
  texte requis), publié avant `calculer --dossier`, et la prévision journalisée est scellée avec tous ses champs
  (`sceller`). Ce qui manquait est le **contenu exigé** de cette règle : une définition opérationnelle de l'événement,
  la ou les sources d'arbitrage, la date limite d'arbitrage, et ce qui se passe si les sources divergent (question
  annulée, comptée et publiée comme telle). Exigé par écrit depuis 0.7.32 ; le moteur contrôle la présence du texte,
  non son contenu.

**Différé, avec la raison.**
- **Saisie des 34 négociations de Druckman** pour la strate 7 : il faut lire l'article de 2001 et coder chaque cas à
  deux ; aucun fichier pré-rempli ne se fabrique sans source lue (aucun fait inventé).
- **Rapport Markdown exportable, registre des sceaux chaîné, rapport d'écarts, table ACH, import d'un CSV de
  fréquences** : utiles, mais aucun ne débloque l'étude d'accord ni le premier cas. Feuille de route.

**Retenu comme règle.** Pas d'interface web, pas d'API, pas de modèle de langage branché sur le moteur : chacun
ouvrirait une surface d'attaque et affaiblirait la discipline hors ligne de l'outil.

---

## 14. Registre des tests, et gel (0.7.34)

**Source.** Audit « Open Science » de la 0.7.33. Son verdict : un dispositif rigoureux autour d'une hypothèse encore
vide, des probabilités non calibrées présentées comme des mesures, une taxonomie trop large pour être codée à deux,
et une fuite en avant procédurale. Sa première recommandation : geler et mesurer. L'auteur l'a retenue.

**Trois corrections.**
1. **Affichage honnête.** Toute sortie humaine d'un p ajoute, juste après la ligne de signalement : « Non calibré :
   multiplicateurs, inerties, k₀ et demi-vie sont posés à la main, non dérivés de données ; lire d'abord la bande et le
   taux sans cartes, le chiffre ensuite. » Les paramètres ne changent pas : ce qui change, c'est qu'un chiffre n'a plus
   l'air d'une mesure.
2. **Périmètre réduit (décision L7).** Hors démonstration, la prévision chiffrée (`calculer`, `noyau`, `trajectoires`,
   `attribuer`) est limitée aux strates de `strates_prevision`, aujourd'hui **la seule strate 7** (13 équivalents sur
   16 sourcés). Les autres strates se lisent, sans chiffre. Une strate s'ajoute quand ses cartes ont un accord mesuré.
   L'étude d'accord et V4 portent donc sur 16 cases, non sur 208. L'audit jugeait les équivalents « métaphoriques » à
   partir de la strate 1 ; c'est la physique, où SEUIL est littéralement une transition de phase. Son objection vaut
   en revanche pour l'étendue : 208 cases ne se codent pas à deux.
3. **Docstring.** `moteur.py` annonçait 0.7.9 ; `audit` lit désormais aussi cette ligne.

**Modes TEST et RÉSULTAT.** Chaque prévision journalisée produit une **fiche Markdown** :
- `fiche-test` : question, événement, état, probabilité avec sa bande et le taux sans cartes, règle de résolution,
  rappel « non calibré », empreinte, et la ligne JSON exacte du journal dans un bloc `alphabet-test` ;
- `fiche-resultat`, après l'échéance : issue, preuve, date du constat, Brier de la question, et la ligne `score` dans
  un bloc `alphabet-resultat` qui porte l'empreinte de la prévision ; un résultat constaté avant l'échéance est
  refusé ;
- `assets/registre-tests.md`, vide, reçoit les deux parties ; `ingerer` relit les blocs, refuse une prévision dont
  l'empreinte a changé, reconstitue le journal (`--journal-sortie`) et score le registre.

Le Markdown est le support lisible ; les blocs JSON sont la donnée. Pourquoi ce partage : un document Markdown seul se
retouche sans trace, et un journal JSONL seul ne se lit pas. L'empreinte relie les deux parties d'un test, et les
deux parties au journal. Un registre tenu par l'auteur seul **documente** ; il ne valide pas : pour V4, la partie
TEST se publie aussi chez un tiers horodaté avant l'échéance (§11.9).

**Gel.** Après cette version, plus de règle nouvelle ni d'outil nouveau sans données réelles. La prochaine version
utile est celle qui contient un premier cas de la strate 7 codé à deux, ou les premières fiches du registre.

---

## 15. Vue extérieure d'abord, et contrôle prédictif a priori (0.7.35)

Deux contrôles demandés par l'auteur après le gel de la 0.7.34. Ils ne sont ni des règles d'interprétation ni des outils
de plus : ils portent sur l'enregistrement de chaque prévision, et se testent dès le premier dossier, sans attendre de cas
réels. Le gel reste la règle pour tout le reste.

**1. Vue extérieure d'abord** (Tetlock et Gardner, *Superforecasting*, 2015, ch. 5). Chaque événement d'un dossier porte
désormais `vue_exterieure` : `frequence` (le taux de base de la classe de référence, dans ]0 ; 1[), `classe_de_reference`
et `source`. Le champ est **requis** (`dossier`). Il s'écrit avant le calcul, puisque le dossier est scellé avant
`calculer --dossier`. Le moteur l'affiche avant les cartes, à côté de f (sa propre fréquence sans cartes) et de p₀, avec
les rapports de cotes. Ce chiffre est celui de l'analyste, non du moteur : un écart entre les deux dit lequel des deux
ignore la classe de référence, et il se lit.

**2. Contrôle prédictif a priori** (McElreath, *Statistical Rethinking*, 2e éd. 2020, ch. 4). p₀ est ce que les
paramètres posés à la main (λ, inerties, fréquence par défaut) impliquent avant toute révision par des cas. Si ses cotes
diffèrent de celles de la vue extérieure de plus de `vue_exterieure_rapport_max` (10, la valeur du plafond de LR, soit
plus que des cartes ne pourraient justifier), l'a priori est **absurde pour ce domaine** : le calcul rend « non estimé »,
motif journalisé, et la question compte comme abstention. On corrige la référence (`--fref`, `--references`), jamais le
dossier scellé.

**Ce que ce contrôle n'est pas.** McElreath simule des données à partir de la loi a priori. Ici, le moteur n'a pas de
loi sur ses paramètres : le contrôle compare la valeur ponctuelle p₀ au domaine, et la bande de sensibilité (§2.3 de
`graphe.md`) reste la seule variation des paramètres publiée. Le contrôle attrape les grossièretés (une fréquence par
défaut de 5 % quand le domaine dit 60 %), pas les biais fins. Sur l'exemple de démonstration : vue extérieure 8 %, f 12 %,
p₀ 23 % ; rapport de cotes de p₀ ≈ 3,4, admis.

---

## 16. Premier test régressif (0.7.38)

**Le test.** Le 2026-11-03, une session de Claude a joué un test rétrospectif sur la strate 7 : « le Conseil de l'UE
adopte-t-il au moins un nouveau paquet de sanctions contre la Russie entre le 1er juillet et le 30 septembre 2026 ? »,
date d'information 30 juin 2026. Issue : 1 (21e paquet adopté le 23 juillet). Jugement de l'analyste scellé avant
recherche : 0,55 ; vue extérieure reconstituée de mémoire, non vérifiée : 0,79 (11 trimestres sur 14). Le moteur a
refusé la question (G6) ; sur la seule reformulation qu'il acceptait (la persistance), il a rendu 0,90, par la seule
inertie. L'issue s'étant affichée avant le codage, le passage au moteur était un **rejeu**, hors V4.

**Ce qui en est retenu.**
1. **Ce n'était pas une lacune d'expressivité, mais d'orientation.** La question se pose en « s'intensifie » sur le
   nombre cumulé de paquets (`simulation.md` §4, « Nouvelle occurrence »). Vérifié : p = 0,71 avec l'inertie par
   défaut, 0,78 avec une référence de persistance. Le défaut était que le message de G6 ne le disait pas : il le dit
   depuis 0.7.38. Aucun type d'événement nouveau n'est créé.
2. **Sept itérations pour trouver les champs du journal : du frottement sans valeur.** `squelette` produit d'un coup
   une ligne complète ; ce que l'analyste doit écrire porte « À REMPLIR », et la validation refuse la ligne en listant
   **tous** ces champs à la fois. Le mode « test de fonctionnement » qui aurait mis ces champs à null n'est pas
   retenu : un champ vide qui passe la validation est un champ qu'on oublie.
3. **La vue extérieure aurait fait mieux que le jugement**, et c'est l'argument de la 0.7.35 : 0,55 contre 0,79,
   Brier 0,20 contre 0,04. Le test n'utilisait pas de dossier, donc pas de `vue_exterieure`. Avec un dossier, la
   reformulation en persistance (p₀ 0,90) aurait été confrontée à un taux de base proche de 0,99 : rapport de cotes
   d'environ 11, au-delà de 10, donc refus de chiffrer. **Un test se joue avec un dossier.**
4. **Un défaut d'affichage** : la ligne « Bande » écrivait « de None à None » pour un composé sans intervalle. Corrigé.

**Ce que le test ne dit pas.** Rien sur la calibration : un seul cas, et un rejeu. La demande de « modification pour
calibrage » ne se traite pas sur un cas : un paramètre ne bouge que sur des dizaines de questions résolues, par une
version séparée (§11 ; feuille de route, D1). Ce test est un test de **fonctionnement**, et il a rempli son rôle :
deux défauts réels, corrigés, et un garde-fou (le refus d'une fiche TEST sur un jugement qui ne portait pas sur la
question) qui a tenu.

---

## 17. Deuxième série de tests régressifs (0.7.39)

**La série.** Le 2026-11-03, cinq questions rétrospectives sur la strate 7, jouées sur la 0.7.37 : date d'information
30 juin 2026, résolution du 1er juillet au 30 septembre 2026. Jugements scellés avant calcul, calculs figés avant toute
recherche d'issue. Une forme de question par test : apparition (T1, frappe directe Iran–Israël), persistance (T2,
ambiguïté stratégique américaine sur Taïwan), disparition (T3, levée des sanctions sectorielles de l'UE), nouvelle
occurrence (T4, expulsion de diplomates en miroir entre la Russie et un État de l'UE), échéance programmée (T5,
déclaration du sommet de l'OTAN réaffirmant l'article 5).

**Ce qu'elle vaut.** Rien sur la calibration : T1 non résolu, T2 de résolution contestable, T3 contaminé, T4 refusé par
le moteur, T5 chiffré sur une référence prise de mémoire (son Brier de 0,003 ne mesure que cette mémoire). Aucun test
propre où le moteur ait chiffré. Les tests ont été joués **sans dossier**, contre le protocole : c'est l'origine de deux
défauts. Sur la conception, la série est riche.

**Résultat, et non défaut : les cartes n'apportent rien.** Sur les cinq tests, l'écart entre « avec cartes » et « sans
cartes » est nul, sauf T1 (+0,009). Sans cas réel actif, le moteur rend une inertie, un taux par défaut ou la référence
fournie. C'est ce que l'énoncé C (§11) mesurera ; il ne se corrige pas, il se constate.

**Corrections (aucun paramètre touché, clôture vérifiée).**
1. **`--fref` était un chemin mort.** La définition de la référence reprenait le nom de l'événement, que le contrôle de
   classe tautologique (0.7.8) refusait toujours ; le refus d'une échéance programmée conseillait pourtant `--fref`.
   `--definition-ref` est désormais requis avec `--fref`, et un test positif couvre ce chemin.
2. **Une abstention publiait des chiffres** : la bande d'horizon, les variantes de codage, la paire « résultat
   principal », la bande verbale. Une abstention met désormais à null tout chiffre dérivé de p. Un événement programmé,
   unique, n'a plus de bande d'horizon, même avec une référence.
3. **Les refus de sémantique** nomment les sémantiques admises, et orientent vers « s'intensifie » pour une nouvelle
   occurrence.

**Décisions d'auteur (règles nouvelles, prises sur cette série).**
4. **Inertie de l'objet.** Hors démonstration, `persiste` et `disparait` ne se chiffrent qu'avec une référence de l'objet ;
   sinon non estimé (T2 : 0,40 pour une doctrine en place depuis 1979, Brier 0,36). En démonstration, un drapeau.
   Le 0,40 d'INCERTITUDE n'est pas modifié : un paramètre ne bouge que par une version séparée, sur données réelles.
5. **Dossier obligatoire.** Hors démonstration, `calculer` refuse de tourner sans `--dossier` (T1 : un état codé de
   mémoire, faux, passait avec des mots en F et un avertissement).
6. **Source de résolution nommée.** Chaque événement d'un dossier porte `source_resolution` : émetteur nommé (« la
   presse » est refusé), document, et règle en cas d'ambiguïté (T2 ne se tranchait pas : une doctrine inchangée, minée
   en paroles).

**Écartés.** Un sens `recurrence` (taux λ par fenêtre) : la nouvelle occurrence s'exprime déjà en « s'intensifie » depuis
0.7.38, et le λ viendrait de la même référence ; T4 est à rejouer sur cette forme. La rétrogradation automatique de F
en f sans dossier : elle changerait p, et le dossier obligatoire règle la cause. Une commande `journaliser` : c'est
`squelette` (0.7.38).

---

## 18. Test T6 : un cas propre, défavorable aux cartes (0.7.40)

**Le test.** Le 2026-11-03, sur la 0.7.39 : « une frappe aérienne, de missile ou de drone de l'Inde sur le territoire
pakistanais, ou l'inverse, au-delà de la ligne de contrôle, reconnue par l'un des deux gouvernements, survient-elle au
moins une fois entre le 1er juillet et le 30 septembre 2026 ? ». Date d'information : 30 juin 2026, la limite de
connaissances du modèle qui l'a joué, donc issue inconnue. Ordre suivi : jugement scellé (0,10), récolte des faits
antérieurs, dossier contrôlé (sceau `0b0809d7…`, incomplet : trois paires sans requête de discrimination, lecture
Spéculative), calcul figé, puis recherche de l'issue. Issue : 0. État : RÉCIPROCITÉ@7[f] + CONTRAINTE@7[f].

| Bras | p | Brier |
|---|---|---|
| Vue extérieure (2 trimestres sur 102 depuis 2001, décompte de mémoire) | 0,02 | 0,0004 |
| Moteur sans cartes | 0,05 | 0,0025 |
| Jugement scellé | 0,10 | 0,0100 |
| Moteur avec cartes | 0,102 | 0,0104 |

**Ce qu'il vaut.** C'est le premier test de la série où l'ordre du protocole a tenu du début à la fin. Il reste un cas
unique, hors V4 (registre non prépublié), avec une vue extérieure non vérifiée (à refaire sur UCDP ou ACLED) et une
résolution indirecte (absence de signalement au CFR Global Conflict Tracker, communiqués PIB et ISPR non lus). Il ne
valide ni n'invalide rien.

**Ce qu'il montre, et qui était documenté.** Les cartes ont doublé p (0,05 → 0,10) dans le mauvais sens. Ce n'est pas un
accident : tous les multiplicateurs de la matrice valent au moins 1, donc toute carte présente ne peut qu'augmenter une
probabilité d'apparition. Sur des événements rares, c'est un biais structurel vers la surestimation. La fréquence par
défaut (0,05) est déjà 2,5 fois le taux de base déclaré ; le contrôle a priori l'a vu (rapport de cotes de p₀ : 5,6) et
l'a admis, sous le plafond de 10. Rien n'est corrigé : ce biais est ce que l'énoncé C (§11) doit mesurer sur des dizaines
de questions, et un multiplicateur inférieur à 1 serait une règle et un paramètre nouveaux, donc une version séparée sur
données réelles. Le constat est consigné ici pour être relu quand ces données existeront.

**Corrections (aucun paramètre touché, clôture vérifiée).**
1. **Sceau du jugement et libellé.** `sceller-jugement` hachait « SEUIL@7 apparait », `squelette` recopiait « SEU@7
   apparait », et la validation refusait la ligne avec un message trompeur. Le hachage ne change pas (les sceaux publiés
   restent valides) ; la vérification accepte toute forme équivalente de l'événement, et le message dit quoi recopier.
2. **La vue extérieure devient un bras scoré.** Elle vivait dans le dossier et le calcul figé, mais aucun score ne la
   lisait ; sur T6, c'est le bras qui gagnait. Champ `vue_exterieure` du journal, requis depuis 0.7.40 (null sans
   dossier), égal à celui du calcul figé, recopié par `squelette` ; pour une ligne antérieure, lu dans le calcul figé.
   `scorer` publie `brier_vue_exterieure` par question, un bilan descriptif (`vue_exterieure`) et `v4_vue_exterieure`,
   à côté des autres bras. **Il n'entre pas dans la décision V4**, dont la référence est fixée d'avance ; en faire la
   référence serait une décision d'auteur, à prendre avant le premier épisode.
3. **Échéance plus courte que la question.** « [2026-06 | 3 mois] » se lit au 1er juin et finit le 1er septembre ; la
   question courait jusqu'au 30. `calculer` signale un état daté au mois ; le journal (depuis 0.7.40) refuse une
   question ou une résolution qui citent une date postérieure à l'échéance.
4. **`squelette`** recopie aussi le comparateur du moteur dans `frequence_de_base`, que la validation exige égal.

---

## 19. Décision d'auteur : la vue extérieure, référence de V4 (0.7.41)

**La décision.** Prise le 2026-11-03, avant le premier épisode prospectif : `v4_reference` vaut désormais
`vue_exterieure`. Le statut V4 (`v4`, son différentiel par épisode, ses tests et sa décision, avec et sans repli) se lit
contre le Brier du taux de base que l'analyste a déclaré dans le dossier **avant** le calcul, et non plus contre
l'inertie du moteur (`frequence_de_base`).

**Pourquoi.** L'inertie du moteur est une construction du moteur : sa fréquence par défaut et ses inerties sont posées à la
main. Battre son propre défaut est une barre basse. Le taux de base d'une classe de référence sourcée est la barre
que tout prévisionniste doit battre (« vue extérieure d'abord ») ; c'est aussi celle qui a gagné sur T6 (§18 : 0,0004,
contre 0,0025 pour le moteur sans cartes et 0,0104 pour le moteur). Si l'alphabet ne fait pas mieux que le taux de base
qu'on lui donne, il n'apporte rien à un analyste, quoi qu'il fasse contre lui-même.

**Ce qui ne change pas.**
- **Aucune probabilité** : la décision porte sur la lecture du score, pas sur le calcul (clôture vérifiée).
- **Les énoncés C et A (§11.13)** gardent leurs bras : C se lit contre l'inertie de strate (effet des cartes, à base
  de cas égale), A contre le dossier neutre ou le modèle nommé. Ils répondent à d'autres questions. Le statut V4 répond
  désormais à celle-ci : **l'appareil bat-il le taux de base déclaré ?**
- **Le repli des abstentions** reste la fréquence de base du moteur (règle §11.4, fixée d'avance) ; le bras de
  référence d'une abstention est la vue extérieure de son dossier.
- Les autres bras restent publiés : `brier_base`, `v4_inertie_strate`, `v4_comparateur`, et le bilan descriptif
  `vue_exterieure` (0.7.40).

**Conséquences.**
- Une question éligible sans vue extérieure ne compte pas dans V4. Le dossier étant obligatoire hors démonstration
  (0.7.39) et la vue extérieure obligatoire dans le dossier (0.7.35), cela ne devrait arriver que pour des lignes
  antérieures, qui ne sont pas éligibles de toute façon (`v4_dossier_depuis`).
- **La vue extérieure devient un bras qu'on peut manipuler** : un taux de base déclaré trop haut ou trop bas rend la
  barre facile. Trois garde-fous existent déjà : elle est écrite et scellée dans le dossier avant le calcul ; elle porte
  sa classe de référence et sa source ; le contrôle a priori (§15) refuse de chiffrer quand les paramètres s'en écartent
  de plus d'un facteur 10. Le quatrième est humain : **une vue extérieure se source dans une base publique (UCDP, ACLED,
  MID, séries officielles), jamais de mémoire** ; une vue de mémoire est un défaut de dossier, à signaler à la relecture
  (§11.7).
- La puissance prévue (§11.13, 171 épisodes à σ = 0,10) reste une hypothèse de planification : le σ du différentiel
  contre la vue extérieure n'est pas connu, et il n'y a pas lieu de le deviner.

---

## 20. Test T7 : la nouvelle occurrence ne mesure que la référence (0.7.42)

**Le test.** Le 2026-11-03, sur la 0.7.41 : « le Conseil de l'UE adopte-t-il au moins un nouveau paquet numéroté de
sanctions contre la Russie entre le 2026-07-01 et le 2026-10-30 ? ». Date d'information : 30 juin 2026, limite de
connaissances du modèle. Forme : nouvelle occurrence, « CTR@7 s'intensifie » sur le nombre cumulé de paquets (20 au
30 juin), état « [2026-06-30 | 4 mois] » daté au jour. Ordre tenu : jugement scellé (0,72), récolte, dossier (sceau
`c6391f06…`, incomplet : une paire sans requête de discrimination, lecture Spéculative), calcul figé et journalisé,
puis issue : 1 (21e paquet adopté le 23 juillet 2026, après la levée d'un veto grec).

| Bras | p | Brier |
|---|---|---|
| Vue extérieure (87 % des fenêtres de 4 mois depuis juillet 2022) | 0,87 | 0,017 |
| Moteur, avec ou sans cartes | 0,861 | 0,019 |
| Jugement scellé | 0,72 | 0,078 |

**Ce qu'il montre.**
1. **Un composé ne passe pas par les cartes.** « s'intensifie » vaut P(persiste) × P(hausse | persiste), deux références
   externes (0,99 × 0,87) ; ni la matrice ni les homologues n'interviennent, et p avec cartes = p sans cartes par
   construction. La forme « nouvelle occurrence » (0.7.38) rend la question exprimable, mais **elle mesure la classe de
   référence, pas la lecture structurelle**. Contre la vue extérieure (référence de V4 depuis 0.7.41), un composé ne
   peut gagner ou perdre que par le facteur de persistance. À savoir avant de composer une série : des questions de
   nouvelle occurrence n'apporteront aucune donnée à l'énoncé C.
2. **Le choix de la classe décide du chiffre.** Avec la seule fenêtre juillet–octobre des années passées (2 sur 4), p
   aurait été 0,50. Depuis que la vue extérieure est la barre de V4, ce choix est le point le plus manipulable du
   dispositif ; voir la feuille de route (§7, classe de référence alternative).
3. **Deuxième fois, le jugement fait moins bien que le taux de base** (T6 était une coïncidence à 0,10 ; ici, 0,72
   contre 0,87, le risque de veto surpondéré). Deux cas ne mesurent rien ; ils vont dans le sens de la 0.7.35.
4. **Contamination filtrée par consigne, non par construction** : les pages lues pour la récolte contenaient des
   informations postérieures au 30 juin. C'est la limite de tout test rétrospectif fait par un modèle qui cherche sur le
   web ; seul un test prospectif l'élimine.

**Corrections de fonctionnement (aucun paramètre touché, clôture vérifiée).**
- **Vue extérieure d'un composé** : contrôlée (le p du composé tient lieu de p₀) et recopiée dans le calcul, donc dans
  `squelette` et le score. Elle se perdait.
- **Sémantique du dossier** : « compose » exigée pour un composé, comme au journal ; « presence » passait au dossier et
  échouait au journal. La temporalité d'un composé est aussi comparée au dossier.
- **Ligne A6** : un « ; » à l'intérieur d'une raison entre parenthèses ne coupe plus le segment.
- **`sceller-jugement`** : `--date` est la date d'information (alias `--date-information`), et la sortie le dit, avec
  l'heure réelle du scellement (`scelle_le_utc`). Un sceau à la date du jour échouait au journal sans explication.
- **Message `ecart_marqueur`** : il dit que le champ va dans `resolution`.
- **Apostrophe typographique** : « s’intensifie » vaut « s'intensifie » (l'événement était refusé comme inconnu).
- **Chemin du skill** : `SKILL.md` dit comment trouver le dossier d'installation.

---

## 21. Décision d'auteur : la classe alternative, scellée et scorée (0.7.43)

**Le problème.** Depuis 0.7.41, V4 se lit contre la vue extérieure. Or le choix de la classe de référence décide du
chiffre : sur T7 (§20), toutes les fenêtres de 4 mois donnaient 0,87, les seules fenêtres juillet–octobre 0,50. Une barre
que l'analyste choisit est le point le plus manipulable du dispositif.

**La décision (option a, 2026-11-03, avant le premier épisode prospectif).** Chaque événement d'un dossier déclare,
dans `vue_exterieure`, une **classe alternative** plausible : sa fréquence, sa classe, sa source, et pourquoi elle est
écartée. Le champ est obligatoire ; `null` est admis avec `motif_sans_alternative`, ce qui reste visible. Les deux
classes sont scellées ensemble, avant le calcul.

- **Calcul** : la sortie affiche l'alternative et l'écart entre les deux classes, en points.
- **Journal** : `vue_exterieure_alternative`, requis depuis 0.7.43 (null sans alternative), égal au calcul figé,
  recopié par `squelette`.
- **Score** : `brier_vue_alternative` par question ; bilan descriptif ; `v4_vue_alternative` ; et
  `v4_robustesse_classe`, qui compare le statut V4 contre la classe retenue et contre l'alternative. **V4 décide sur
  la classe retenue.** Si les deux statuts divergent, le verdict dépend du choix de la classe, et il se publie ainsi.

**Option écartée (b).** Décider contre la plus défavorable au moteur des deux classes. La barre serait plus dure et
impossible à manipuler, mais biaisée : le meilleur de deux taux, choisi une fois l'issue connue, bat mécaniquement chacun
d'eux, et V4 conclurait trop souvent que l'alphabet n'apporte rien. L'option a suffit contre la manipulation, puisque les
deux classes sont scellées avant le calcul et publiées côte à côte.

**Ce qui ne change pas.** Aucune probabilité (clôture vérifiée) ; le contrôle a priori (§15) porte sur la classe retenue ;
les énoncés C et A gardent leurs bras.

---

## 22. Test P-0001 : quand les sources ne portent pas la contrainte (0.7.44)

**Le test.** Le 2026-11-03, sur la 0.7.43, événement tiré au sort parmi trois candidats : « une frappe militaire de
l'Inde ou du Pakistan sur le territoire de l'autre, reconnue par l'État qui frappe ou par les deux, a-t-elle lieu au
moins une fois entre le 2026-07-01 et le 2026-09-30 ? ». Date d'information 2026-06-30. État : POLARITÉ@7[f]
(CONTRAINTE@7 rejetée par le moteur, A7). Marqué `rejeu` : des résultats de septembre 2026 sont apparus pendant la
récolte. Issue retenue : 0.

| Bras | p | Brier |
|---|---|---|
| Classe alternative (3 trimestres sur 100, 2001–2026) | 0,03 | 0,0009 |
| Moteur sans cartes | 0,05 | 0,0025 |
| Jugement scellé | 0,06 | 0,0036 |
| Vue extérieure retenue (3 sur 40, 2016–2026) | 0,075 | 0,0056 |
| Moteur avec cartes | 0,087 | 0,0075 |

**Le diagnostic de l'auteur.** Le fond et la forme ne coïncident pas : le dispositif a appliqué ses règles, mais la
documentation choisie pour l'état initial et pour l'issue ne portait pas les éléments de la contrainte. Ce n'est pas une
erreur de dispositif, mais de choix des sources. Ce qui relève du dispositif : il contrôlait la **forme** d'une source
(présente, nommée, datée), pas son **adéquation** à la question ; l'écart passait donc sans bruit. Trois écarts :

1. **La source déclarée n'a pas tranché.** Le dossier annonçait les communiqués du ministère indien de la Défense et de
   l'ISPR ; l'issue a été établie par Polymarket (qui ne couvre que les frappes indiennes), un aperçu ACLED et une
   publication rétrospective, **par absence de preuve**.
2. **La classe ne compte pas ce que la question compte.** La question inclut l'artillerie lourde et les raids ; des tirs
   d'artillerie à travers la ligne de contrôle ont eu lieu presque chaque trimestre entre 2016 et 2021. Appliqué au passé,
   le critère de résolution aurait dit « oui » bien plus souvent que 3 fois sur 40 : le taux de base décrivait un
   événement plus étroit que celui prévu. Et les communiqués déclarés ne rapportent pas ces échanges : le critère était
   plus large que ce que sa propre source peut constater.
3. **Une classe qui commence juste avant un épisode** (juillet 2016, deux mois avant les frappes de septembre) gonfle
   le taux. La classe alternative l'a rendu visible, et c'est elle qui a gagné : la 0.7.43 a servi.

Et un défaut de dispositif : T6 (§18) et P-0001 posent la même question, même dyade, même fenêtre, sous deux
identifiants d'épisode ; en V4, ils compteraient comme deux épisodes indépendants.

**Décision d'auteur : un parcours obligatoire sur les sources.** Aucun paramètre touché, clôture vérifiée.
- **Avant le calcul** : `vue_exterieure.ecart_critere`, obligatoire, dit en quoi ce que compte la classe diffère du
  critère de résolution (« identique : … » sinon). L'adéquation ne se vérifie pas automatiquement ; elle ne passe plus
  sans avoir été écrite.
- **Après l'échéance** : `fiche-resultat` exige `--source-utilisee`, `--source-conforme oui|non` (et `--ecart-source`
  si non) et `--mode positif|absence`. La fiche le dit en clair ; `ingerer` et `scorer` comptent les résolutions par
  absence et hors source (`resolutions`, `ids_fragiles`). Une telle résolution n'est pas fausse ; elle est plus fragile,
  et se voit. Les lignes antérieures restent valides (« non renseignées »).
- **À l'ingestion** : `episodes_suspects` signale deux prévisions sur le même événement, à fenêtres chevauchantes,
  sous des épisodes différents. Signalé, non corrigé : seul l'analyste sait si ce sont deux épisodes.

Le point 3 reste du jugement ; la classe alternative le traite déjà.

---

## 23. Test FR-RU : le moteur sans cas rend une constante (0.7.45)

**Le test.** Le 2026-11-03, sur la 0.7.44 : « la France et la Russie procèdent-elles à des expulsions de diplomates en
miroir entre le 2026-07-01 et le 2026-09-30 ? ». RÉCIPROCITÉ@7, au moins une fois, date d'information 2026-06-30 (limite
de connaissance du modèle : aveugle sur l'issue). État : CONTRAINTE@7[f] (sanctions de l'UE en vigueur ; ancrage de
mémoire, en f). Résolution figée : une expulsion, et une réponse présentée comme telle, dans la fenêtre ; convocations et
sanctions exclues. Issue : 0, par absence de trace ; épisode le plus proche, la convocation du chargé d'affaires russe le
17 juillet (cyberactivités du 16e Centre du FSB), sans expulsion.

| Bras | p | Brier |
|---|---|---|
| Vue extérieure (environ 2 trimestres sur 48, 2014–2025, de mémoire) | 0,04 | 0,0016 |
| Moteur, avec et sans cartes | 0,05 | 0,0025 |
| Jugement scellé | 0,06 | 0,0036 |
| Classe alternative (un État de l'UE quelconque, 2022–2025) | 0,50 | 0,25 |

**Ce qu'il montre.**
1. **Le moteur a rendu sa fréquence par défaut** : `apport_cartes` = 0, produit des λ = 1, aucun cas, ρ4. Il n'existe
   pas d'arête CONTRAINTE@7 → RÉCIPROCITÉ@7, alors que le marqueur local de RÉCIPROCITÉ@7 inclut les « sanctions en
   miroir » ; versé au journal des lacunes (lacune 4), sans arête ajoutée (P1). Sans cas réel actif, la strate 7
   chiffre des constantes : c'est le constat principal de la série, et la condition pour qu'un test devienne
   informatif est un premier cas réel actif.
2. **Le choix de classe pèse cent fois plus que tout le reste** (0,0016 contre 0,25). L'alternative n'était pas une
   classe plausible pour la même question (un autre couple d'États) : la classe alternative doit être une autre façon
   de compter **le même événement**, pas un événement voisin. À relire en relecture de dossier ; pas de règle.
3. **Une question à 5 % qui ne se réalise pas ne prouve rien** : c'est l'issue attendue 95 fois sur 100.
4. **Indicateur de bascule réalisé sans bascule** : l'attribution d'espionnage du 17 juillet n'a pas entraîné
   d'expulsion ; Paris a choisi convocation et sanctions. Une donnée pour la vraisemblance de cet indicateur, une seule.

**Corrections (aucun paramètre touché, clôture vérifiée).**
- **Étape 0** : `SKILL.md` commence par localiser le skill (`find`), au lieu d'une remarque entre parenthèses.
- **`corroboration`** : valeurs exactes écrites dans `SKILL.md` (`"independantes"` ou `"unique"`).
- **`sceller-jugement`** rend aussi `question` et `evenement`, à recopier mot pour mot.
- **Requêtes A7** : `executee` (true/false) et `date_execution` obligatoires ; une requête non lancée ne couvre rien
  (dossier Spéculatif). Auparavant, une requête marquée « non exécutée » dans son texte passait pour faite.
- **Mode test** : `mode_test` (`prospectif` ou `regressif`) requis au journal depuis 0.7.45 ; `regressif` exige
  `date_limite_connaissance` au plus égale à la date d'information. Hors V4 par construction ; bilan séparé
  (`registre_regressif`) dans `scorer` et `ingerer`. Il ne se confond plus avec une prévision simplement non publiée.
- **Vue extérieure et p** : la sortie dit qu'elle ne modifie pas p (bras de référence de V4, indépendant du moteur), et
  comment faire entrer une fréquence sourcée dans le calcul (`--fref`, `--references`). C'est voulu : si elle nourrissait
  p₀, le moteur et sa référence seraient le même chiffre.
- **Cosmétique** : extraits coupés au mot, sans parenthèse ouverte ; message d'un dossier refusé sans l'identifiant de
  fiche interne ; `ingerer` affiche moteur contre jugement et le bilan régressif.

## 24. Test « deux sources, un événement » : la lecture tient-elle au récit ? (0.7.46)

**Décision d'auteur.** Une lecture peut dépendre de la manière dont la source raconte l'événement (son vocabulaire,
son cadrage, ce qu'elle choisit de nommer) plus que de l'événement lui-même. Rien jusqu'ici ne le mesurait : A4 compare
deux **codeurs** sur les mêmes pièces, A6 exige des sources indépendantes pour chaque **fait** ; aucun contrôle ne
compare deux **lectures complètes** faites chacune à partir d'un seul récit. Ce test le fait. Il n'ajoute ni paramètre
ni probabilité ; il est descriptif et ne compte pas dans V4.

**Procédure.**
1. Choisir un événement et deux sources **indépendantes** au sens de `protocole.md` A6 (origine, producteur ou
   transmission), au **cadrage différent** : deux pays, deux lignes éditoriales, ou une source primaire et un récit
   de presse. Écrire, avant de coder, en quoi les cadrages diffèrent.
2. Coder le cas deux fois, en mode CODER, **chaque codage ne lisant que sa source**, dans deux sessions séparées et sans
   voir l'autre codage. Mêmes `id`, mêmes dates d'états, mêmes strates déclarées ; seules les pièces changent. Deux
   fichiers : `source-A.jsonl`, `source-B.jsonl`.
3. `python3 scripts/moteur.py depouiller --premier source-A.jsonl --second source-B.jsonl` : table par carte et table
   groupée (κ, PABAK, taux de manque). Le premier « codeur » est ici la source A, le second la source B.
4. En mode PRÉVOIR, facultatif : calculer la même question sur chacun des deux états et publier l'écart de p.

**Lire le résultat.**
- **Accord élevé** : les cartes retenues tiennent à l'événement plutôt qu'au récit, pour ce cas et ces deux sources.
  Rien de plus : un même biais partagé par les deux sources passe inaperçu.
- **Accord faible** : la lecture suit le récit. Ouvrir les cases b et c de `depouiller` (cartes ancrées par une seule
  source) et, pour chacune, dire si l'autre source ignore le fait, le formule autrement ou le contredit. Les deux
  premiers cas relèvent du choix des sources (§22) ; le troisième va en A7.
- Les repères `kappa_min` et `kappa_rapportable` se lisent à titre indicatif : ils ont été fixés pour deux codeurs,
  pas pour deux sources. Les décisions d'un même état ne sont pas indépendantes ; sur un seul cas, l'intervalle est
  très large. Le test devient informatif sur une série.

**Ce que le test ne mesure pas.** La justesse de la lecture ; un biais commun aux deux sources ; l'accord entre
codeurs. Un même codeur (ou un même modèle) code les deux versions : l'écart mesuré mêle la sensibilité à la source et
l'instabilité du codeur. Pour séparer les deux, refaire un codage de la même source A dans une troisième session : si
A contre A' s'accorde autant que A contre B, l'écart vient du codeur, pas du récit.

**Où consigner.** Le résultat se consigne dans cette section, à la suite des tests (§16 à §23), avec l'événement, les
deux sources, la ligne sur les cadrages et la sortie de `depouiller`. Il ne va pas dans `assets/registre-tests.md`, qui
ne reçoit que des prévisions (TEST puis RÉSULTAT) ; si le test comporte l'étape 4, chaque prévision y suit son propre
parcours.

**Origine.** Balestriero et LeCun (2026, arXiv 2610.39302), sur les représentations apprises : deux observations
indépendantes d'une même scène alignent des représentations ; deux variantes d'une même observation gardent la
« nuisance » propre à cette observation. Le papier ne porte ni sur un alphabet construit à la main ni sur la
prévision ; il fournit seulement l'analogie qui a suggéré le test. La règle tient sans lui : c'est le principe ancien
de la multiplicité des sources indépendantes.

## 25. Tests du codeur : suit-il la fiche ou le nom ? (0.7.47)

**Décision d'auteur.** Le codeur du skill est le plus souvent un modèle de langage, et les fiches de `cartes.md` sont
son livre de codes. Halterman et Keith (2025, *Political Analysis* ; arXiv 2407.10747) montrent que des modèles de
langage codant des événements politiques suivent souvent le **nom** de la catégorie plutôt que sa définition, et
choisissent une catégorie parce que son nom figure dans le texte (« rally » → RALLY). A4 mesure l'accord entre codeurs
mais exige un humain ; ces deux tests vérifient le codeur **sans second codeur**. Ce sont des tests, pas des règles :
aucun paramètre, aucune probabilité ; descriptifs, hors V4, hors registre des prévisions. Leurs chiffres (modèles de 7
à 8 milliards de paramètres, en 2024) ne se transposent pas ; seule la méthode est reprise.

### 25.1 Noms neutres

**Question.** Le codeur ancre-t-il une carte parce que ses marqueurs sont remplis, ou parce que son nom évoque la
situation ?

**Procédure.**
1. Choisir un cas réel et ses pièces. Préparer une copie de `cartes.md` où chaque nom de carte est remplacé par son code
   neutre (table ci-dessous), **partout** (titres, « À ne pas confondre avec », garanties), et où la ligne
   **Signature** est supprimée : ses mots (CYCLE, LIMITE…) trahissent la carte. Vérifier ensuite qu'aucun nom ne
   subsiste (`grep -i` sur chaque nom).
2. Coder le cas deux fois, dans deux sessions séparées, avec **les mêmes pièces et les mêmes références** : la session
   normale lit `cartes.md` ; la session neutre lit la copie neutre. Aucune des deux ne charge `equivalences/`,
   `dynamiques.md`, `exemples.md` ni `antagonismes.md`, qui nomment les cartes ; l'ancrage se fait par les marqueurs
   du noyau (f au plus, comme une case Vide). Le codeur neutre code avec les codes C01–C16.
3. Retraduire le codage neutre vers les noms (table), puis `python3 scripts/moteur.py depouiller --premier normal.jsonl
   --second neutre.jsonl`.

| Code | Carte | Code | Carte | Code | Carte | Code | Carte |
|---|---|---|---|---|---|---|---|
| C01 | SEUIL | C05 | ÉMERGENCE | C09 | INCERTITUDE | C13 | TRACE · MÉMOIRE |
| C02 | RÉCIPROCITÉ | C06 | HIÉRARCHIE | C10 | CONTRAINTE | C14 | CROISSANCE |
| C03 | PÉRIODICITÉ | C07 | RÉSEAU | C11 | PROPORTION | C15 | COMMUNAUTÉ |
| C04 | RÉCURSIVITÉ | C08 | POLARITÉ | C12 | TRANSFORMATION | C16 | RÉSONANCE |

L'ordre des codes suit celui de `cartes.md` ; il n'est pas une information à cacher. Pour qu'un codeur humain ne puisse
pas reconstituer les noms, mélanger l'ordre des fiches dans la copie neutre (les codes restent les mêmes).

**Lire le résultat.** Lire d'abord l'accord spécifique positif et les deux taux de manque, pas le PABAK, gonflé par les
cartes qu'aucune session n'ancre (§24).
- **Accord élevé** : pour ce cas, le codeur suit les marqueurs ; le nom ne fait pas le travail.
- **Carte ancrée en session normale seulement** (case b) : le nom a peut-être porté l'ancrage. Relire la ligne de
  marqueurs de cette carte : est-elle remplie par un fait précis, ou seulement « évoquée » ?
- **Carte ancrée en session neutre seulement** (case c) : le nom a peut-être **écarté** une carte dont les marqueurs
  étaient remplis. C'est aussi un défaut, plus rare et plus intéressant.
- Comme au §24, l'écart mêle l'effet du nom et l'instabilité du codeur. Contrôle : un troisième codage, en session
  normale ; si normal contre normal' s'accorde autant que normal contre neutre, le nom n'y est pour rien.

### 25.2 Recouvrement lexical

**Question.** Un ancrage tient-il à un mot de la source qui ressemble au nom de la carte ?

**Procédure.** Pour chaque ancrage **F** d'un codage (lecture, fiche ou cas), relire le passage cité et chercher les
racines ci-dessous, sans tenir compte des accents ni de la casse. Les racines sont volontairement étroites : la famille
morphologique du nom, pas ses synonymes.

| Carte | Racines | Carte | Racines |
|---|---|---|---|
| SEUIL | seuil | CONTRAINTE | contrain |
| RÉCIPROCITÉ | récipro | PROPORTION | proportion |
| PÉRIODICITÉ | périod | TRANSFORMATION | transform |
| RÉCURSIVITÉ | récurs | TRACE · MÉMOIRE | trace, mémoire, mémori |
| ÉMERGENCE | émerg | CROISSANCE | croiss, croît |
| HIÉRARCHIE | hiérarch | COMMUNAUTÉ | communaut |
| RÉSEAU | réseau | RÉSONANCE | réson |
| POLARITÉ | polar, pôle | INCERTITUDE | incertain, incertitude |

**Lire le résultat.** Un recouvrement ne rend pas l'ancrage faux : une source peut écrire « seuil » à bon droit. Il le
rend **suspect**, et oblige à une vérification : en retirant le mot du passage, le fait remplit-il encore un marqueur
de la carte ? Si oui, l'ancrage tient ; sinon, le mot a fait le travail, et l'ancrage descend à f ou tombe (A7, portée à
juger). Consigner chaque recouvrement et son verdict dans `assets/journal-lacunes.md`. Si les recouvrements suspects
reviennent souvent, ce sera la donnée qui justifiera un signal du moteur, comme celui des requêtes A7 formées sur le nom
d'une carte (0.7.2) ; pas avant.

### 25.3 Ce que ces tests ne mesurent pas

Ni la justesse d'une lecture, ni l'accord entre deux humains (A4 reste requis), ni la sensibilité du codeur à l'ordre
des fiches ou aux critères d'exclusion, que Halterman et Keith testent aussi et que la 0.7.47 n'a pas retenus (coût
élevé, gain moindre). Les explications écrites par un modèle (garantie, ligne A6) ne prouvent pas qu'il a raisonné
ainsi : les tests portent sur ses décisions, pas sur ses justifications.

**Où consigner.** Dans cette section, à la suite des tests, comme au §24 : cas, pièces, sortie de `depouiller` (25.1),
liste des recouvrements et verdicts (25.2).

## 26. Fuites temporelles dans les tests régressifs (0.7.48)

**Pourquoi.** Les tests T6, T7, P-0001 et FR-RU (§18 à §23) sont régressifs : date d'information au 30 juin 2026,
limite de connaissance du modèle qui les a joués, issue déjà acquise au moment du test, pièces récoltées après coup
par recherche en direct. P-0001 a déjà été marqué `rejeu`, des résultats de septembre étant apparus pendant la récolte.
Deux travaux mesurent ce risque. El Lahib et al. (2026, arXiv 2602.00758) : sur 393 questions Metaculus, une recherche
filtrée par date ramène pour 71 % des questions au moins une page contenant une information postérieure qui contraint
fortement l'issue, et pour 41 % une page qui la donne ; un modèle qui prévoit avec ces pages obtient un Brier de 0,10,
contre 0,24 avec des pages propres. Paleka et al. (ICLR 2026, arXiv 2506.00723) classent les pièges de l'évaluation
rétrospective. Le skill tenait les tests régressifs hors V4 (0.7.45) ; il ne disait pas comment réduire la fuite qui en
gonfle les scores.

**Quatre voies de fuite par les pièces** (El Lahib et al. ; Paleka et al. §2.2) :
1. **Page mise à jour** : l'article ou la base consultée a été complété après sa date affichée.
2. **Encadrés** : « articles liés », barres latérales, commentaires, publicités injectent l'actualité dans une page
   ancienne.
3. **Horodatage faux** : la date affichée (« mis à jour en mai 2020 ») ne correspond pas au contenu.
4. **Absence parlante** : une chronologie publiée après coup qui ne mentionne pas l'événement dit qu'il n'a pas eu lieu.

S'y ajoute une fuite plus difficile à voir : le moteur de recherche **classe** les pages d'aujourd'hui avec son savoir
d'aujourd'hui, et fait remonter ce qui est devenu important après la date d'information.

**Procédure (test régressif).**
- **Pièces figées.** Lire chaque pièce dans un instantané daté au plus tard à la date d'information (Wayback Machine),
  et le déclarer au carnet : `recolter … --archive https://web.archive.org/web/AAAAMMJJ…/adresse`. Le moteur lit la date
  de l'instantané et refuse un `disponible_le` antérieur : un instantané ne prouve que ce qui existait à sa date.
  `recolter --jusqu-au` liste les faits `sans_archive`. Une pièce lue en direct reste admise ; elle est exposée, et se voit.
- **Contrôle de fuite.** Avant de coder une pièce lue en direct, la noter de 0 à 4 (échelle d'El Lahib et al.) :
  0 aucune information postérieure ; 1 postérieure mais sans rapport avec l'issue ; 2 indice faible ; 3 indice fort ;
  4 issue donnée. **Une pièce notée 2 ou plus sort du dossier** ; si elle a été lue avant le scellement du jugement, le
  test devient `rejeu`. La note se consigne dans le texte du dossier ; le moteur ne la contrôle pas.
- **Limite de connaissance du codeur.** `date_limite_connaissance` est une déclaration, pas une garantie : un modèle peut
  savoir des choses postérieures à sa limite annoncée (Paleka et al. §2.3). Une fenêtre qui s'ouvre au lendemain de cette
  limite, comme dans T6, T7, P-0001 et FR-RU, est la plus exposée. Le score d'un tel test se lit comme une **borne
  haute** de la performance, jamais comme une mesure.
- **Choix de la question (fuite logique, Paleka et al. §2.1).** (a) Lister les questions candidates **avant** toute
  recherche portant sur la fenêtre, puis tirer au sort, comme pour P-0001. (b) Ne pas tirer les candidates de
  l'actualité de la fenêtre : la presse parle des événements qui ont eu lieu, pas de ceux qui n'ont pas eu lieu, et la
  série penche vers le « oui ». (c) Fixer la fin de fenêtre à la date d'information, sans regarder l'issue. (d) Écarter
  une question dont le fait même qu'elle soit déjà résolue trahit l'issue (« … avant 2030 ? » résolu en 2026 : « oui »).
- **Pas de prévisions humaines avant le scellement.** Cotes de marché (Polymarket, Kalshi), prévisions Metaculus ou
  avis d'experts publiés ne se lisent qu'**après** le jugement scellé et le calcul figé. Un bras qui les a vues les
  recopie peut-être (Paleka et al., « piggybacking »). Les lire pour **trancher l'issue** reste admis (§22).

**Ce que le skill avait déjà** : tests régressifs hors V4 et bilan séparé (0.7.45) ; `rejeu` ; résolutions par absence
comptées comme fragiles (0.7.44) ; difficulté par question et Brier non comparable entre questions de fréquences de
base différentes (§1, §23 point 3) ; score logarithmique en regard du Brier (0.7.5). Ces deux papiers ne les changent pas.

**Limites.** Un instantané peut lui-même porter des encadrés chargés plus tard par le navigateur ; les instantanés
manquent pour beaucoup de pages, surtout hors des grands médias ; la note de fuite est un jugement du codeur, non
vérifié. La seule évaluation sans fuite reste le test **prospectif**, publié avant l'échéance (§14).

## 27. Critère de levée de L7, fixé avant les données (0.7.49)

**Décision d'auteur, le 2026-11-04, avant toute question géopolitique résolue par le bot Metaculus.** L7 (§14) limite
la prévision chiffrée aux strates de `strates_prevision`, aujourd'hui la seule strate 7, et prévoyait qu'une strate
s'ajoute « quand ses cartes ont un accord mesuré ». Le premier passage réel du bot (zone de test, 2026-11-04) l'a rendu
concret : deux questions sur trois relevaient de la strate 6 et ont été refusées. Le critère de levée est écrit
**maintenant**, avant de voir des résultats, pour que le moment de la levée ne soit pas choisi d'après eux.

**Deux conditions, toutes deux nécessaires, pour ajouter une strate s à `strates_prevision` :**

1. **En strate 7, les cartes n'abîment pas le taux de base.** Sur au moins **20 questions géopolitiques résolues**
   (prospectives : prévision publiée chez un tiers horodaté avant l'échéance, §14), où les bras B (classe de référence)
   et C (alphabet) existent tous deux, la différence appariée de Brier **C − B est ≤ 0** (C ne fait pas moins bien que B).
   Les questions comptent une fois par épisode (`episodes_suspects`, §22). Si C − B > 0, L7 reste en l'état pour toutes
   les strates : des cartes qui dégradent le taux de base dans leur seule strate documentée ne s'étendent pas.
2. **En strate s, les cartes sont lisibles à deux** : la condition d'origine de L7 (accord mesuré, A4) sur les cartes
   de s, et des équivalents de s au statut Documenté pour les cartes que la lecture y ancre.

**Ce que la levée n'autorise pas.** Elle ouvre le chiffre dans s, elle ne valide pas les multiplicateurs : C − B ≤ 0 en
strate 7 dit seulement que les cartes ne nuisent pas. « C bat B » (C − B < 0 avec un intervalle qui exclut 0) est un
résultat distinct, à publier comme tel, et non une condition de levée. La levée est une décision d'auteur datée,
consignée ici avec la sortie de `score_registre.py` (ou de `scorer`) qui la fonde.

**Lectures scellées hors strate 7.** Une lecture faite hors de `strates_prevision`, scellée avant l'issue et non chiffrée,
reste admise (mode LIRE). Si s est levée plus tard, ces lectures peuvent être chiffrées après coup par le moteur, à
paramètres fixés : le dossier est daté et scellé, le calcul déterministe. Elles comptent alors comme un premier test de
s, à part des questions prospectives, et jamais dans la condition 1.

---

## 28. Alignement avec le bot Metaculus (0.7.50)

**Décision d'auteur, le 2026-11-05.** Le bot Metaculus (dépôt `Othman-Benbrahim/metac-bot-template`, version 0.5.1)
joue ce skill sur des questions réelles. Entre ses versions 0.1 et 0.5.1, il a changé sa façon d'enregistrer et de
mesurer, après un audit externe, deux relectures et une veille documentaire. Cette section reporte ces changements dans
le skill, pour que les deux s'élaborent de la même façon. Même statut que le §15 : ce sont des contrôles
d'**enregistrement** et de **mesure**. Aucune règle d'interprétation nouvelle, aucun paramètre touché, aucune
probabilité changée ; le gel du §14 reste la règle. Les outils de mesure décrits au point 4 vivent dans le bot
(`score_registre.py`), non dans le moteur : le skill ne gagne pas d'outil.

**1. La vue extérieure en deux temps.** Constat du registre du bot : sur une même question, trois estimations du taux
de base allaient de 0,2 % à 8 %, parce qu'elles ne comptaient pas la même classe (« 0 cas sur 22 périodes biennales »,
« 0 sur 46 présidences », « 1 sur 11 fenêtres glissantes »). Une médiane de trois classes n'est pas une médiane : c'est
un tirage (Hájek, « The reference class problem is your problem too », *Synthese* 156, 2007). Procédure :
- **définir** la classe avant de compter : ce qui compte pour un cas (et ce qui n'en est pas un), la population ou les
  périodes du dénominateur, la période, la mise à l'échelle vers la fenêtre, où se trouvent les cas ;
- **compter** ensuite, sur cette classe seulement ; quand plusieurs comptages indépendants sont faits, retenir la vue
  **médiane** (médiane basse si leur nombre est pair) : une vraie vue, avec sa source, jamais une moyenne qui fabriquerait
  un chiffre ; consigner l'écart entre les comptages, qui mesure alors la variance de mesure et non un changement de
  classe ;
- une source qui se déclare elle-même « de mémoire », « registre mental » ou « sans consultation » ne fonde pas un taux
  de base ; un registre **nommé** et vérifiable le peut ;
- des questions de prévision **déjà résolues** et comparables (par exemple sur Metaculus) peuvent fonder la classe,
  à trois conditions : on n'en lit que l'**issue**, jamais les prévisions publiées (§26) ; elles sont résolues avant la
  date d'information ; cinq au moins comptent le même type d'événement sur une fenêtre comparable ;
- `disponible_le` de la vue ne dépasse pas la date d'information.

**2. La strate à l'aveugle.** La strate de l'événement commande le droit de chiffrer (L7). Constat du bot : la même
question a été lue SEUIL@13, puis SEUIL@7 après que la consigne eut mentionné que seule la strate 7 se chiffre. Le
codeur choisit donc la strate d'après le mécanisme des faits, **avant** de consulter `strates_prevision`. La stabilité de
l'étiquette se mesure sur les questions lues plusieurs fois, **à version égale** seulement : un changement de consigne
n'est pas une instabilité.

**3. L'état nul qualifié.** Un état nul est une lecture légitime (« aucune structure lue ») ; il peut aussi être un
angle mort de la recherche. Pour les distinguer :
- chaque rejet commence par sa catégorie : `[aucun_fait]` (aucun fait pertinent dans les résultats : problème de
  recherche), `[non_cherchee]` (la requête n'a pas été lancée), `[marqueur_non_rempli]` (des faits existent mais ne
  remplissent pas le marqueur), `[contredit]` (un fait de la situation contredit la carte : la seule catégorie qui
  renseigne sur l'alphabet lui-même) ; et il dit ce qu'aurait montré un fait suffisant, avec l'extrait le plus proche
  trouvé. C'est la mesure de l'écart entre ce que le codeur sait et ce qu'il ancre ;
- si l'état est nul alors que des candidates sont `[aucun_fait]` ou `[non_cherchee]`, une **relance** de recherches
  nouvelles, formées sur le phénomène que décrit leur marqueur, précède l'état nul (une seule fois) ;
- l'état nul se déclare ensuite `structure_absente` (chaque candidate écartée sur pièces) ou `angle_mort` (il en reste
  une non vérifiée), et la **dynamique observée** se décrit en une ou deux phrases, sans nom de carte, hors calcul ;
- un état nul n'est **jamais** compté comme une prévision égale au taux de base : il se suit à part, par nature.

Ces descriptions sont la matière d'une éventuelle carte manquante. Elle ne se cherche qu'**après** l'évaluation des
situations prédites, dans le respect des règles de création des cartes, et une carte née d'échecs passés n'est éprouvée
que sur des questions nouvelles : les questions qui l'ont fait naître ne comptent pas pour elle.

**4. La mesure.** Le tournoi Metaculus note au **score logarithmique** (les scores de pair sont des différences de
scores log) ; le critère du §27 reste en **Brier**, inchangé (décision du 2026-11-04 : le skill ne dépend pas du
règlement d'un tournoi). Le bot rapporte les deux, et le lecteur ne les confond pas. Dans le bot :
- une question compte **une fois** (sa dernière prévision publiée) ; les passages à blanc et la zone de test sont
  exclus ; chaque probabilité est bornée à [0,001 ; 0,999], pour la mesure comme à l'envoi ;
- l'écart C − B se lit par une **séquence de confiance** et un test séquentiel par pari, valides à tout moment de
  consultation (Waudby-Smith et Ramdas, *JRSS-B* 2024 ; Choe et Ramdas, *Operations Research* 2024) : on peut lire le
  score chaque semaine sans fausser la conclusion. Le verdict est « meilleur », « moins bon » ou **« indéterminé »**.
  Seule l'hypothèse fixée d'avance (C fait mieux que B) est testée au niveau α ; les trois autres comparaisons faites sur
  les mêmes questions, au niveau α/3 ;
- pour C contre B, l'écart par question est borné par la structure du moteur : la cote de C reste dans un facteur
  `plafond_LR` (10) de celle de B (§15), soit au plus 100 × ln 10 ≈ 230 points ; si cette borne était dépassée, le test
  le signale et reprend la borne générale ;
- ordre de grandeur de la puissance (écart-type supposé de 40 points par question, à remplacer par l'écart-type
  observé) : environ 80 questions appariées pour établir un gain de 20 points, 180 pour 10, 660 pour 5.

**Ce que cela dit du §27.** Vingt questions sont un **seuil d'examen** de la levée de L7, non une preuve : sur vingt
questions, un gain de 10 points ne se distingue pas du hasard. Le §27 le disait déjà (la levée n'est pas une
validation) ; les chiffres ci-dessus le rendent mesurable.

**5. Le sens unique de C.** Tous les λ étant ≥ 1 (décision d'auteur 9), pour un événement « apparait » C ne peut que
monter au-dessus de B : il gagne sur les OUI, perd sur toutes les NON, et surestime en moyenne si B est la fréquence
d'une classe qui mêle situations avec et sans cartes (`graphe.md` §2.1). Le bot mesure ce biais (déplacement moyen de C
par rapport à B, gain séparé selon l'issue, taux de OUI réel contre B et C moyens). Pour le corriger sans chiffre
inventé, il apprend sur des **tests régressifs** un seul paramètre, un décalage b (logit p′ = logit p_C + b) :
- contrôles de fuite du §26, plus une recherche bornée à la date d'information (pages non datées écartées) et une
  **sonde** : la question est exclue si le modèle connaît déjà l'issue ; le moteur refuse de lui-même toute pièce
  postérieure à la date d'information ;
- la fuite résiduelle va dans un sens connu : un codeur qui devine l'issue ancre des cartes sur les OUI et n'en trouve
  pas sur les NON, ce qui flatte C ; le décalage appris est donc au pire trop faible, jamais trop fort ;
- la correction n'est écrite qu'à partir de 15 questions où C est chiffré, et si elle gagne hors échantillon ;
- elle reste **en ombre** : la prévision corrigée est scellée et scorée à part, jamais publiée, et elle ne modifie pas
  le p du moteur. Si le biais n'est pas un décalage global (certaines cartes coûtent sur les NON, d'autres non), c'est la
  décision 9 qu'il faudra rouvrir, sur données.

**6. Étudié, non appliqué.** Le bot calcule chaque semaine ce que gagneraient une recalibration logistique à deux
paramètres (mesurée hors échantillon, à partir de 20 questions) et un plafonnement de la valeur publiée (grille
0,01–0,05). Rien n'est appliqué : ce sont des décisions d'auteur réservées. Le plafonnement change le score du
tournoi, pas la mesure de C − B, qui se fait sur les bras enregistrés.

**7. Ce qui reste propre au bot.** Les règles du tournoi (pas d'humain dans la boucle, commentaire privé obligatoire,
une prévision par question, passage à blanc réservé à la zone de test), la cadence (contrôle toutes les 20 minutes,
plafond quotidien), le budget, le scellement du commentaire envoyé et du jeu de questions reçu à chaque passage.
Ces points n'ont pas d'équivalent dans le skill, qui ne publie rien lui-même : le registre du §14 en tient lieu.

**Levée du gel pour un seul outil (0.7.51, décision d'auteur du 2026-11-05).** Le §27 fonde la levée de L7 sur la
sortie de `score_registre.py` (bot) **ou** de `scorer` (skill). Si seul le bot portait une inférence valide à tout
moment de relecture, les deux outils pourraient conclure différemment sur la même décision. `scorer` publie donc, pour
chaque différentiel par épisode (dont `v4_vue_exterieure`, la comparaison C contre B), une **séquence de confiance** à
1 − α sur la moyenne de d (Brier − référence), obtenue en inversant les e-processus qu'il calculait déjà depuis la
0.7.12, et un verdict à trois valeurs : « meilleur que la référence (établi) », « moins bon que la référence
(établi) », « indéterminé ». Rien d'autre ne change : ni les paramètres, ni les règles de décision de V4 (§11), ni le
critère du §27, qui reste « C − B ≤ 0 sur 20 questions » ; le verdict se lit à côté. Les autres outils de mesure du bot
(test séquentiel détaillé, puissance, correction du biais en ombre, recalibration, plafonnement) restent dans le bot :
pour eux, le gel tient.

---

## 29. Bras exploratoire hors L7 (0.7.52)

**Décision d'auteur, le 2026-11-08.** Sur les premières questions réelles du bot Metaculus, l'alphabet n'a produit
aucun chiffre : la prévision chiffrée exige une question binaire, en strate 7 (L7), hors état nul. À ce rythme, la
lecture n'est jamais mesurée hors de sa seule strate documentée, et la condition 2 du §27 ne peut pas se préparer.
L'auteur lève donc L7 **pour un calcul à part**, sans toucher à la règle de publication.

**Ce que fait `--exploratoire`.** Sur `calculer` (et `sonde`, `attribuer`), l'option lève le seul refus L7 : le moteur
chiffre une lecture hors de `strates_prevision`, avec les mêmes paramètres, les mêmes contrôles (dossier, A1 à A7,
dates) et le même calcul. Le résultat porte `exploratoire: true` et un drapeau en tête. L'option refuse `--journal` (le
chiffre ne va pas au journal prospectif) et `--demo`.

**Ce qu'elle ne change pas.**

1. **Rien n'est publié** : le bot scelle le chiffre exploratoire dans son registre, avant l'issue, et poste comme avant
   (C en strate 7, B en état nul, A sinon). `strates_prevision` reste `[7]`.
2. **Hors du verdict et du calibrage** : le chiffre exploratoire est scoré dans une section à part, par strate (C
   exploratoire contre B), jamais dans le verdict principal, la correction rétrospective, la recalibration ni la
   condition 1 du §27.
3. **Statut pour le §27** : ces chiffres sont des lectures scellées hors strate 7, chiffrées au moment même plutôt
   qu'après coup (§27, dernier paragraphe). Ils comptent comme un premier test de leur strate, à part des questions
   prospectives de la strate 7. La levée d'une strate reste une décision d'auteur datée, sur les deux conditions du §27.
4. **Ni état nul chiffré ni C = B** : sans carte ancrée, il n'y a pas de chiffre exploratoire.

**Ce qu'il faut savoir en le lisant.** Hors de la strate 7, les équivalents des cartes sont moins souvent Documentés : le
chiffre exploratoire mesure la lecture **telle qu'elle est**, multiplicateurs hypothétiques compris. Un C exploratoire
moins bon que B dans une strate dit que cette strate n'est pas prête, pas que l'alphabet est faux.

## 30. Le marqueur décide de l'intensité, pas de l'existence (0.7.53)

**Décision d'auteur, le 2026-11-10.** Sur le premier passage du bras exploratoire (§29), neuf lectures — trois binaires,
six non binaires dérivées — ont toutes fini en état nul : seize rejets sur seize classés « marqueur non rempli ». Le
lecteur exigeait la forme complète de l'`attendu` (par exemple, pour CROISSANCE, trois mesures aux incréments
croissants et une saturation nommée) avant d'ancrer la moindre carte. Lue ainsi, la règle d'A6 rend f presque
impossible : le cerceau devient aussi exigeant que le pistolet, et l'alphabet ne produit jamais de chiffre. L'auteur
juge que la sévérité du marqueur n'est pas ce qui définit une carte : la *Définition* et la *Structure mathématique*
la définissent ; le marqueur dit à quel point elle est visible.

**La règle.**

1. **Ancrage f (cerceau ou paille).** Un fait de la situation, sourcé et daté, qui montre le mécanisme de la
   *Définition* et remplit **au moins un** des *Marqueurs observables* de la fiche ancre la carte en f. La forme
   complète de l'`attendu` n'est pas exigée pour f.
2. **Ancrage F (pistolet ou double).** Inchangé : test suffisant, ligne A6 qui écarte les voisines, passage pour les
   cas réels. C'est là que la forme complète de l'`attendu`, corroborée, sert.
3. **Rejet « marqueur non rempli ».** Réservé aux cartes pour lesquelles des faits existent mais n'en remplissent
   **aucun** marqueur observable.
4. **Rejet « contredit ».** Un fait qui dit le contraire de l'`attendu` ou réalise ce que nomme `contredirait`
   élimine la carte (cerceau échoué). Un `attendu` seulement **incomplet** n'est pas contredit.

**Ce qui ne change pas.** Aucun paramètre, aucun multiplicateur, aucune règle de décision ; `moteur.py` ne vérifie
toujours que la forme (F exige `pistolet` ou `double`). La publication reste celle du §28 (C en strate 7, B en état
nul, A sinon) ; L7 ne se lève que par le §27.

**Ce qu'il faut savoir en le lisant.** Plus d'ancrages f veut dire plus de chiffres, donc plus de mesures, mais aussi
plus de cartes faiblement ancrées : les chiffres produits après cette version sont scorés à part de ceux d'avant
(`version` dans le registre), et un C moins bon que B après 0.7.53 désignerait cette règle comme première suspecte.

## 31. Fait de série : l'alphabet lu dans des données (0.7.54)

**Décision d'auteur, le 2026-11-10.** Les cartes sont des structures mathématiques ; la lecture ne les cherchait que
dans des faits rédigés (presse, documents). L'auteur admet qu'un **relevé de données** soit un fait au sens de la
règle d'ancrage, pour tester l'alphabet **sans texte** (banc `alphabet-chaine` : jetons de la chaîne Solana,
protocole fixé avant les données dans `protocole-alphabet-sans-texte.md` du projet).

**Ce qu'est un fait de série.** Une valeur relevée, avec : le **champ** et sa **valeur** (`fait`), le **producteur**
(`source`, par exemple « RugCheck »), le **point d'accès** (`source_url`), l'**heure du relevé** (date du fait et
`date_consultation`), et l'emplacement dans la réponse (`passage.localisation`, par exemple `topHolders[0].pct`).
Il obéit aux mêmes règles que tout fait : daté au plus tard à la date d'information, jamais inventé, jamais calculé
par le lecteur (un ratio se cite s'il est fourni par la source ou calculé par le code du banc, avec sa formule).

**Ce qui en découle.**

1. **Corroboration** : un relevé d'API est une source primaire (`unique`) ; deux API qui relaient la même chaîne ne
   sont pas indépendantes pour une valeur sur la chaîne (même origine, §24).
2. **Statut des équivalents** : en strate 6 (Économie), les équivalents des cartes lues dans ces données sont
   « proposés », pas Documentés ; les chiffres restent exploratoires (§29), jamais publiés.
3. **Règle §30 inchangée** : définition + un marqueur observable → f ; F exige un test suffisant. Une valeur seule
   (« 45 % des jetons chez dix portefeuilles ») est un marqueur ; le mécanisme de la carte doit se lire dans la
   configuration des relevés, pas dans le nom du champ.

**Ce qui ne change pas.** Aucun paramètre, aucune règle de décision ; `moteur.py` ne vérifie que la forme. Les
chiffres du banc sont scorés à part de ceux du bot Metaculus.

## 32. Équivalents de données pour les jetons (0.7.55)

**Décision d'auteur, le 2026-11-10.** Premier passage du banc `alphabet-chaine` en protocole 2 : relevés riches
(série de bougies, fenêtres de transactions, distribution des détenteurs), lecture rigoureuse, mais état nul. Les
marqueurs du noyau sont écrits pour des situations rédigées (« les acteurs se classent eux-mêmes dans deux camps »,
« un chemin de transmission nommable ») ; aucun texte ne disait quel relevé vaut marqueur. Le lecteur a aussi classé
CROISSANCE « contredit » sur une série qui monte puis s'effondre, alors que la définition inclut saturation et déclin.

**La règle.** `references/equivalences/donnees-chaine.md` traduit les marqueurs de dix cartes en termes de relevés
(seuils fixés avant toute issue) et laisse six cartes Vides, faute de marqueur visible dans ces données. Tous les
équivalents sont **Proposés** (plafond A3, aucun emprunt). Choix consignés : la concentration est une PROPORTION, pas
une HIÉRARCHIE (détenir n'est pas commander) ; un plafond sans cause nommée est une saturation (CROISSANCE), pas une
CONTRAINTE.

**Chargement.** Le fichier n'est lu que lorsque le réglage `ALPHABET_EQUIV_DONNEES` est activé (banc seulement). Le
bot Metaculus ne le charge pas. Il le chargera après une **décision d'auteur datée**, sur l'un de ces fondements :
verdict « C meilleur que A et que B » du banc à 200 questions par type, ou équivalents promus Documentés.

**Garde-fou.** Le bras A du banc (même modèle, mêmes relevés, sans alphabet) dit si ces équivalents ajoutent une
lecture ou ne font que nommer ce que le modèle voit déjà. Aucun paramètre ni règle de décision ne change.

## 33. Lecture causale de la matrice, et deux sondes en ombre (0.7.56)

**Décision d'auteur, le 2026-11-10**, après lecture du chapitre « Causality » de Veitch et D'Amour (dans Murphy,
*Probabilistic Machine Learning: Advanced Topics*, ch. 36), consignée dans `reference-murphy-causalite.md`.

**Quatre précisions de doctrine, sans effet sur aucun chiffre.**

1. **Les λ sont stipulés** (`graphe.md` §2.1) : posés par l'auteur, employés *comme* des rapports de vraisemblance.
2. **L'hypothèse du produit est écrite** (`graphe.md` §2.1) : indépendance des cartes conditionnellement à
   l'événement, vraie si elles en sont des symptômes, fausse si elles en sont des causes ; le signe de l'erreur suit
   la structure (substituables ou cause commune : surestimation ; conjointement nécessaires : sous-estimation).
3. **Les paires mutuelles se lisent d'un pas au suivant** (`dynamiques.md` §0) : un pas de calcul, arêtes directes ;
   l'équilibre dans un même état n'est pas couvert.
4. **L'écart C − B est un contraste du dispositif**, jamais un contrefactuel : C est la lecture entière (toutes cartes
   ensemble) appliquée à B ; « ce qui se serait passé sans telle carte » exigerait la forme fonctionnelle d'un modèle
   causal complet, que le moteur n'a pas.

**Deux sondes en ombre, dans `sensibilite`, hors bande et hors p publié** (à titre comparatif, pour l'avenir) :

- **Règle des médiateurs** (`mediation`) : si A et M sont deux sources de la cible et que la matrice porte A → M
  sans M → A, l'arête A → cible est lue comme un effet **total**, qui inclut le chemin par M ; M est écarté. Une
  paire mutuelle est ambiguë : rien n'est écarté. La matrice compte 81 configurations de ce type, dont 39 vers SEUIL :
  appliquée au chiffre publié, la règle en changerait la plupart, d'où l'ombre.
- **Ablation** (`ablation`) : chaque carte retirée seule, toutes choses égales ; `apport` = p de référence − p sans
  elle. C'est un contraste **dans le modèle**, pas un contrefactuel dans le monde.

**Ce qui ne change pas.** Le p publié, les λ, la matrice, les règles de décision, L7. La règle des médiateurs ne
pourra remplacer le calcul actuel que par une nouvelle décision datée, si elle fait mieux sur des issues réelles
(banc `alphabet-chaine` et bot Metaculus, où elle est scellée à côté de C). Refusé : présenter la porte dérobée ou le
do-calcul comme une validation de la matrice ; ils disent ce qui est identifiable *étant donné* un graphe, pas si le
graphe est vrai.

## 34. Causes ou indices, et quand cesser de chercher : deux ombres de plus (0.7.57)

**Décision d'auteur, le 2026-11-10**, après lecture de Poole et Mackworth, *Artificial Intelligence: Foundations of
Computational Agents*, 3ᵉ éd., Cambridge University Press, en accès libre (artint.info), consignée dans
`reference-poole-mackworth.md` du projet.

**Ombre `noisy_or` : les cartes lues comme des causes.** Le §33 écrit que le produit des λ suppose les cartes
indépendantes sachant l'événement (des indices), et qu'il se trompe quand elles en sont des causes. Le *noisy-or*
(§9.3 du livre) est le modèle standard de ce second cas : chaque cause active a sa propre chance, indépendante des
autres, de produire l'événement, et l'événement survient si l'une d'elles réussit. Pour chaque source, p_i est le p
qu'elle donnerait seule (le calcul actuel) ; son poids est w_i = (p_i − f)/(1 − f) ; la combinaison est
p = 1 − (1 − f)·Π(1 − w_i). Une source qui baisse (λ < 1, aucune aujourd'hui) laisse passer la fraction p_i/f. **Avec
une seule carte, les deux combinaisons rendent le même p** ; elles divergent à partir de deux, le noisy-or montant
moins vite (exemple du livre : 0,35 contre 0,86 pour la combinaison additive sur la cote). Le reste du calcul (révision
par les cas, plafond) est inchangé.

**Ombre `valeur_information` : borne de ce qu'une recherche de plus pourrait changer.** La valeur d'une information
n'est jamais négative, et elle est **nulle si la décision reste la même quelle que soit l'information obtenue** (§12.4
du livre). Transposé au moteur : pour chaque carte absente de la strate de la cible (hors « Hors domaine »), on
calcule p si elle était ancrée, en f puis en F. La **borne** est le plus grand écart absolu à p. Si elle est sous
`seuil_valeur_information` (0,02, nouveau paramètre, sans effet sur aucun p), aucune lecture supplémentaire ne peut
déplacer la prévision du moteur de plus de deux points : `arret` vaut vrai. Ce n'est pas la valeur de l'information au
sens strict, qui pondérerait chaque issue par sa chance d'être trouvée : c'est sa **borne haute dans le modèle**. Elle ne
dit rien de ce que le bras A pourrait apprendre hors de l'alphabet.

**Usage.** Les deux ombres sont calculées dans `sensibilite`, hors bande et hors p publié, et scellées à côté de C par le
bot et le banc. Le critère d'arrêt n'arrête rien : le nombre de tours de recherche reste fixé (6 dans le bot). On
mesurera sur les issues réelles (a) si le noisy-or fait mieux que le produit là où deux cartes ou plus sont ancrées, et
(b) si les questions où `arret` était vrai dès le premier tour ont des C aussi bons que les autres. Toute adoption passe
par une décision datée.

**Code tiers.** Le code Python du livre (AIPython) est sous licence Creative Commons BY-NC-SA, incompatible avec la
licence MIT du skill : rien n'en est copié. Les deux formules sont réécrites ici, en quelques lignes, à partir du texte.

## 35. Tempérer les cartes, et répéter le modèle seul : deux ombres d'après Murphy (0.7.58)

**Décision d'auteur, le 2026-11-10**, après lecture de Kevin Murphy, « Agentic Forecasting using Sequential Bayesian
Updating of Linguistic Beliefs », arXiv 2604.18576 (ICML 2026), consignée dans `reference-murphy-blf.md` du projet.

**Le constat qui motive la décision.** L'article teste une forme explicite très proche du bras C : logit p = logit b₀ +
α·Σ log λ, les λ demandés au modèle observation par observation. Elle bat le seul taux de base (Brier Index 65,7 contre
63,1) mais perd contre la croyance laissée en langage naturel (70,4), sur 80 questions. Le meilleur α est 0,35 : les
rapports de vraisemblance bruts étaient trop forts. Deux réserves de l'auteur lui-même : α a été choisi **sur
l'échantillon même**, et l'échantillon est petit.

**Ombre `tempere` (moteur).** Le même calcul avec le produit des λ élevé à la puissance α, avant la révision par les cas.
Les α sont **fixés ici, avant toute donnée** : 0,5 pour la comparaison principale, 0,25 et 0,75 à titre descriptif
(`alphas_temperage`, sans effet sur aucun p publié). α = 1 est le calcul publié. Choisir α d'après les issues, puis le
mesurer sur ces mêmes issues, est exclu : c'est l'erreur que l'article signale chez lui.

**Ombre « A répété » (bot).** L'article gagne en moyennant plusieurs essais indépendants du modèle seul (moyenne
simple, un peu mieux que la moyenne des logits). Le bot peut sceller K essais du bras A (`ALPHABET_A_ESSAIS`, 1 par
défaut, donc éteint) ; le premier reste le bras A publié ; la moyenne est comparée à part. **Pourquoi c'est nécessaire
pour nous** : si C ne bat qu'un A tiré une seule fois, une partie de l'écart peut venir du bruit d'un tirage, pas des
cartes. La comparaison honnête est C contre A moyenné.

**Ce qui ne change pas.** Le p publié, les λ, la règle de publication, L7. Toute adoption passe par une décision datée.

## 36. Un programme génératif conditionné sur la lecture (0.7.59)

**Décision d'auteur, le 2026-11-10**, après la lecture de Murphy (2026) et de la programmation probabiliste (van de
Meent, Paige, Yang & Wood, *An Introduction to Probabilistic Programming*, 2018), consignée dans
`reference-wood-programmes-probabilistes.md` du projet.

**Le problème.** Murphy nomme deux conditions d'une mise à jour exacte : des vraisemblances bien spécifiées, et la prise
en compte de la dépendance entre indices. Le produit des λ échoue à la seconde par construction (§33). Un programme
génératif la traite par construction ; il ne règle pas la première, il la rend nommée et mesurable.

**Le programme** (`p0_generatif`, en ombre, dans `sensibilite`). Dans la strate de la cible :
1. chaque carte est une variable latente, présente avec la probabilité π ;
2. une arête A → B de la matrice, lue comme **effet direct**, multiplie par λ(A → B) la cote que A et B soient présentes
   ensemble : un médiateur non observé est inféré de sa cause, un médiateur observé n'ajoute que son effet direct ;
3. le lecteur ancre une carte présente en F ou f (sensibilités sF, sf), une carte absente par erreur (pF, pf) ; **une
   candidate examinée puis rejetée est une observation** (« cherchée, pas trouvée ») ; une carte non examinée n'apprend
   rien ;
4. l'événement survient par noisy-or (§34), la fuite étant réglée pour que, **sans aucune observation, p₀ = f** : la
   fréquence de base contient déjà les structures non vues.

L'inférence est **exacte** : énumération des 2¹⁵ états de la strate, en Python standard, sans tirage aléatoire. Les
sources d'autres strates restent des causes certaines. La révision par les cas homologues est celle du calcul publié.

**Paramètres stipulés, nommés** (`generatif` : π = 0,1 ; sF = 0,5 ; sf = 0,3 ; pF = 0,01 ; pf = 0,05), avec une bande
(π ÷ 2, π × 2, lecteur deux fois plus bruité). Ils pourront être **estimés** : les taux du lecteur par double lecture et
accord entre codeurs (modèle de Dawid et Skene), π par la base de cas. C'est le gain sur les λ, qui mêlent tout en un
nombre.

**Ce que l'ombre apporte de neuf.** Les rejets entrent dans le calcul (ils n'y entraient pas) ; deux cartes reliées ne
se comptent plus deux fois. Sur l'exemple (CROISSANCE + CONTRAINTE → SEUIL@7, f = 0,121) : produit 0,306 sur p₀,
génératif 0,225 ; avec CONTRAINTE non lue et CROISSANCE seule, 0,172, et 0,145 si CONTRAINTE a été cherchée et rejetée.

**Ce qui ne change pas.** Le p publié, les λ, la matrice. Toute adoption passe par une décision datée, sur issues
réelles (bot et banc, `generatif` scellé à côté de C).

## 37. Lecture probabiliste : traduire les textes en instructions du programme (0.7.60)

**Décision d'auteur, le 2026-11-10**, d'après L. Wong, G. Grand, A. K. Lew, N. D. Goodman, V. K. Mansinghka,
J. Andreas, J. B. Tenenbaum, « From Word Models to World Models: Translating from Natural Language to the Probabilistic
Language of Thought », arXiv 2306.12672 (2023) ; consignée dans `reference-wong-goodman-lecture-probabiliste.md` du projet.

**L'idée.** Le modèle de langue ne raisonne pas : il **traduit** des phrases en instructions d'un langage probabiliste,
et l'inférence raisonne sur le programme obtenu (« rational meaning construction »). Chez les auteurs, deux sortes
d'instructions : des définitions qui modifient le modèle du monde, et des conditions qui l'observent. Chez nous, les
conditions existent déjà : les ancrages (F, f) et les rejets (§36). Il manquait les **définitions propres au cas** : ce
que le texte dit des liens entre structures, que la matrice générale ne sait pas.

**Le langage, volontairement petit** (`programme` du dossier, trié par `programme_valide`, jamais bloquant) :

| Instruction | Sens | Effet dans le programme génératif |
|---|---|---|
| `lien` A → B | le texte dit que A produit B dans ce cas | cote de co-présence × λ_M |
| `lien` A → cible | le texte dit que A mène à l'événement ici | A devient une cause de poids λ_M (si la matrice ne dit pas plus) |
| `bloque` A | le texte dit que la voie de A vers l'événement est coupée ici | poids de A vers la cible = 0 |
| `exclut` A, B | le texte dit que A et B ne peuvent coexister ici | cote de co-présence × `facteur_exclusion` (0,1) |

Chaque instruction cite un **extrait** des textes trouvés ; l'appelant (le bot) vérifie l'attribution sans modèle et
écarte ce qui n'est pas retrouvé. Les cartes doivent être dans la strate de la cible. La normalisation sur f est refaite
sur le modèle modifié : sans aucune observation, p₀ reste f.

**Garanties.** Le traducteur est un appel **séparé**, après la lecture : la consigne de lecture ne change pas, donc C non
plus. Le programme n'écrit aucun chiffre ; il ne fait que dire quelles relations le texte affirme. Le calcul reste exact
et déterministe. Ombre `lecture_probabiliste` dans `sensibilite` : p, effet sur C, effet sur `generatif`, instructions
retenues et écartées.

**Ce qui ne change pas.** Le p publié, la consigne de lecture, les λ, la matrice. Toute adoption par décision datée.

## 38. Relecture par Murphy, ch. 4, 9, 29 et 30 : ce qui est retenu, ce qui est rejeté (0.7.61)

**Décision d'auteur, le 2026-11-10**, après quatre synthèses critiques de K. P. Murphy, *Probabilistic Machine
Learning: Advanced Topics* (MIT Press, 2023) : ch. 4 (modèles graphiques), 9 (passage de messages), 29 (modèles
d'espace d'états), 30 (apprentissage de graphes, extrait). Chaque critique a été vérifiée contre le code ; le tri complet
est dans `relecture-murphy-pgm.md` du projet.

**Ce que le calcul publié est, nommé exactement** (ch. 4, §4.3.4.1). Le produit des λ sur la cote est un **modèle
log-linéaire à coefficients stipulés** : logit p₀ = logit f + Σ log λ, une régression logistique dont les poids et la
constante sont fixés, jamais estimés. C'est un **score**, pas un produit de vraisemblances : l'indépendance des cartes
sachant l'événement est fausse pour des causes (explaining away, §4.2.4.2), comme le §33 l'écrivait déjà. Le plafond à
10 est une **troncature** de ce score : avec f = 0,1, p₀ ne dépasse pas 0,53, et il mord dès la troisième carte forte.

**Ce que le programme génératif est** (§4.5.4.1) : un **graphe en chaîne**, champ de Markov sur les cartes normalisé par
Z, puis lois conditionnelles dirigées pour l'événement (noisy-or) et pour les observations. Le joint est bien défini
(une critique le disait non normalisé : elle est rejetée, le code normalise sur toutes les configurations des cartes).

**Ce que la matrice est** (§29.5.5) : la structure **entre deux tranches** d'un réseau bayésien dynamique, en
association (barreau A). Ce qui manque pour dérouler proprement plusieurs pas : des transitions normalisées, et une
évaluation à plusieurs pas. `trajectoires` déroule (noyau à risques concurrents, chemins entiers pondérés), mais **aucune
trajectoire n'est scellée ni scorée au-delà d'un pas** : un score à un pas ne dit rien de la dynamique (§29.13.3).

**Corrigé dans le code (ombres seulement).**
1. **Couplage unique par paire** (§4.3.2.1, §9.4.2) : les 10 paires mutuelles étaient couplées deux fois dans le même pas
   (λ(A→B) × λ(B→A)) ; un seul couplage, le plus fort des deux.
2. **Rejets selon l'effort de recherche** (§29, observé ou manquant) : contredit et marqueur non rempli 1 ; aucun fait
   trouvé et non classé 0,5 ; non cherchée 0 (`generatif.effort_rejet`). Le bot transmet les catégories
   (`rejets_categories` du dossier) ; sans catégories, l'effort reste 1.
3. **Ombre `sans_plafond`** : le même calcul sans troncature, pour mesurer ce qu'elle coûte sur les issues.
4. **Largeurs d'arbre mesurées** (§9.5.3, `moteur.py largeur`, élimination min-fill), au lieu d'« exact par
   énumération » :

| Graphe | Nœuds | Largeur | Lecture |
|---|---|---|---|
| cartes d'une strate (56 arêtes non orientées) | 16 | 7 | l'exact coûte ~16 × 2⁸ : trivial |
| génératif moralisé, pire cible (SEUIL, 14 parents) | 16 | 14 | le noisy-or à 14 parents marie tout : c'est lui, pas la matrice, qui rend l'énumération nécessaire ; décomposé (variables d'activation en chaîne), il redescendrait près de 8 |
| 13 strates reliées comme dans le calcul publié | 208 | 103 | **l'exact est hors de portée** : tout programme inter-strates exigera une méthode approchée, validée d'abord contre l'exact d'une strate |

**Rejeté, avec la raison.** Tempérage « sans statut hors Gibbs » (c'est le Bayes généralisé, Grünwald & van Ommen 2017) ;
« bloque A » comme do(A) (bloque coupe l'arête A → cible, ne fixe pas A) ; exclusion « en potentiel nul » (facteur 0,1) ;
révision Beta « double comptage » (p₀ est la moyenne a priori que les cas actualisent) ; « taux de base compté deux fois »
(λ ne contient pas la fréquence de la carte) ; « MPM pris pour MAP » (`trajectoires` pondère des chemins entiers) ;
« prévision scellée = contrefactuel ».

**Reporté, faute de données.** Apprendre les λ (comptage, pseudo-vraisemblance, gradient de log Z) et la structure
(ch. 30) : il faut des issues, et une matrice d'épisodes N × D que le bot exporte désormais (`episodes.csv`). Les
couplages de co-présence entre cartes, eux, s'apprendront sans issues, sur les lectures, quand il y en aura assez.

**Ce qui ne change pas.** Le p publié, les λ, la matrice, le plafond publié, L7.

## 39. Invariance du lecteur : deux vues, mêmes cartes (0.7.62)

**Décision d'auteur, le 2026-11-10**, d'après R. Balestriero & Y. LeCun, « Proving and Improving the Platonic
Representation Hypothesis with JEPAs », arXiv 2610.39302 (29 octobre 2026).

**L'idée reprise.** Une représentation saisit la situation, et non le style du document, si deux observations distinctes
d'un même état du monde (de « bonnes vues ») y tombent au même point. Les auteurs montrent que les objectifs qui
rapprochent les morceaux d'un même document (« mauvaises vues ») encodent la « nuisance » propre au document : son
registre, sa forme.

**Transposé au lecteur.** Le lecteur de l'alphabet est un encodeur vers un vocabulaire fermé : il doit ancrer les mêmes
cartes quelle que soit la source qui décrit la situation. **Test** (bot, en ombre, sur une part des questions) : les
mêmes requêtes, le même plan, la même consigne, mais deux vues aux **sources disjointes** (chaque site va à une seule
vue). Mesures : Jaccard des cartes ancrées, part des lectures identiques, κ de Cohen sur les décisions « ancrée / non
ancrée » des candidates. C'est un accord **d'un codeur avec lui-même sur deux textes**, à côté de l'accord de deux
codeurs sur un même texte (`reference-accord-codeurs.md`).

**Lecture.** Un κ faible dit que le lecteur suit le registre des sources plus que la situation ; c'est alors le lecteur,
pas la matrice, qu'il faut corriger. **Réserve, celle des auteurs :** leur théorème suppose que chaque observation
détermine l'état ; une vue partielle (moins de sources, un aspect seulement) peut légitimement ancrer moins de cartes.
Le registre garde donc le nombre d'items de chaque vue, et un désaccord par **absence** (une vue n'ancre pas ce que
l'autre ancre) se lit autrement qu'un désaccord par **contradiction** (deux intensités ou deux cartes opposées).

**À noter, sans changement :** les équivalents de données (§32) sont déjà des paires de bonnes vues (le même marqueur lu
dans un texte et dans une série chiffrée) ; apprendre cette correspondance au lieu de l'écrire est une piste, pas une
décision.

**Ce qui ne change pas.** Le p publié, la lecture publiée, les λ, la matrice.

## 40. Surprise d'une lecture (0.7.63)

**Décision d'auteur, le 2026-11-10**, d'après le signal de « surprise » des modèles du monde de type JEPA (LeWorldModel,
2026, présenté par M.-M. Maudet, « JEPA et modèles du monde ») : un modèle du monde signale qu'il ne s'attendait pas à ce
qu'il voit. C'est le contrôle de mauvaise spécification noté dans la lecture de Wood et de Schmitt et al.

**Mesure** (`generatif.surprise`, en ombre). Le programme génératif (§36) donne la probabilité de la lecture observée
(ancrages et rejets), P = Z/Z₀. On la compare à celle de la même lecture si chaque carte était tirée seule avec sa
probabilité marginale a priori. **Surprise relative** = log P(indépendantes, mêmes marges) − log P(couplées).
- **≈ 0** : une seule observation, ou des cartes que la matrice ne relie pas.
- **< 0** : l'assemblage est plus cohérent que ses éléments pris un à un (deux cartes reliées, ancrées ensemble).
- **> 0** : la matrice jugeait l'assemblage improbable (exemple : CROISSANCE ancrée, CONTRAINTE, sa conséquence forte,
  contredite : +0,16). Deux lectures possibles, à départager : le lecteur s'est trompé, ou la situation sort de ce que la
  matrice sait représenter.

**Usage.** Le bot scelle la surprise avec C ; le score dira si C se trompe davantage quand la surprise est forte. Aucune
règle ne s'appuie dessus avant une décision datée.

**Ce qui ne change pas.** Le p publié, la lecture, les λ, la matrice.

## 41. Relecture par Murphy, ch. 3 et 13 : tri (0.7.64)

**Décision d'auteur, le 2026-11-11**, après deux synthèses critiques de Murphy, *Probabilistic Machine Learning:
Advanced Topics* : ch. 3 (statistique) et ch. 13 (Monte Carlo séquentiel). Vérifié contre le code ; documentation seule.

**Retenu, écrit ici.**
1. **Double comptage possible entre f et la révision par les cas** (ch. 3, §3.2.1). f est la moyenne a posteriori d'une
   Beta(k₀·réf, k₀·(1 − réf)) révisée sur l'échantillon de la base (`frequence_de_base`) ; les cas homologues de la
   révision sont tirés **du même échantillon**. Leurs issues pèsent donc deux fois : dans f, diluées, puis dans la
   révision. L'effet est faible tant que les homologues sont une petite part de la base ; la correction (f calculée hors
   des homologues) est à faire avant tout usage chiffré au-delà de L7.
2. **Condition préquentielle** (§3.8.4) : le score logarithmique cumulé n'est la vraisemblance marginale séquentielle que
   si chaque prévision n'utilise que le passé. C'est le cas : paramètres versionnés, prévisions scellées, correction
   rétrospective calculée sur les seules questions déjà résolues. Toute révision qui utiliserait une issue postérieure
   ferait du score un score adaptatif, à déclarer comme tel.
3. **Rejets et données manquantes** (§3.11) : un rejet est un indicateur de révélation, pas une valeur nulle ; s'il
   dépend de ce que le lecteur attendait, le manque est non ignorable. Le poids par effort (§38) l'atténue sans le régler.
4. **Une grille plus fine que les données** (§3.2.1.6) : avec une dizaine de cas, l'incertitude sur f (± 0,3 environ)
   est de l'ordre de l'effet d'une carte forte. Les écarts entre F, M et f ne sont pas mesurables aujourd'hui.
5. **Plusieurs pas** (ch. 13, §13.2.3.2) : un déroulé par particules perd la diversité des chemins en remontant le temps
   (dégénérescence des chemins) ; aucune trajectoire longue ne sera promise sans étape de rafraîchissement (resample-move)
   et contrôle de la taille effective d'échantillon (ESS).

**Rejeté, avec la raison.** « f est un estimateur plug-in, nul si aucun événement » : non, c'est une moyenne a
posteriori avec k₀ pseudo-observations, jamais nulle si la référence ne l'est pas. « Aucune quantité ne décroît avec les
données » : le poids de l'a priori dans la révision vaut k/(n_A + k). « Intervalle de crédibilité présenté comme une
couverture » : le moteur parle de crédibilité, le score du bot de suites de confiance (fréquentistes), chacun à sa place.
« Notre score serait log Ẑ, biaisé » : le score est le score logarithmique de prévisions scellées contre des issues, pas
une constante de normalisation estimée. « Le tempérage doit être un chemin adaptatif » : notre α est une puissance de
vraisemblance (Bayes généralisé, §35), pas un recuit d'échantillonneur.

**Reporté, faute de données.** Rétrécissement hiérarchique de f entre strates (§3.6) ; lignes de transition en
Dirichlet estimées par Bayes empirique (§3.7.3), qui remplaceraient les λ ; contrôles prédictifs sur des statistiques non
suffisantes (§3.9) ; échantillonneur SMC à tempérage adaptatif pour l'arbre entier (§13.6.2). Piste notée : avec π = 0,1,
la masse se concentre sur les configurations à peu de cartes présentes, ce qui permettrait une énumération tronquée
au-delà d'une strate, à valider contre l'exact.

**Ce qui ne change pas.** Le p publié, le code du moteur, les λ, la matrice.

## 42. Équivalents en SSSOM, accord à deux niveaux (0.7.65)

**Décision d'auteur, le 2026-11-11**, d'après `asago-policy-mapper` (asago-ai, Apache 2.0), qui relie des textes de
politique à des catalogues de risques.

**SSSOM.** Les équivalents (carte abstraite → traduction locale par strate) s'exportent au format SSSOM, standard ouvert
de correspondances entre vocabulaires (`moteur.py sssom`) : prédicat SKOS qualifié (Attesté et Documenté →
`closeMatch`, Proposé → `relatedMatch`), confiance (0,9 / 0,7 / 0,4, qui traduit le statut de preuve, pas une mesure),
justification `semapv:ManualMappingCuration`. Vide et Hors domaine ne sont pas des correspondances et sont exclus. Les
fichiers de strate restent la source ; l'export permet de les relire et de les comparer avec des outils standards.

**Accord à deux niveaux.** Comme leur évaluation (risque exact, puis catégorie), l'accord entre deux lectures se mesure
au niveau de la **carte**, puis de la **famille** : la carte et ses voisines A6 (« à ne pas confondre avec »), dans la
même strate (`accord_deux_niveaux`). Deux lectures qui ancrent deux voisines se trompent de carte, pas de famille : le
second niveau sépare une confusion fine d'un désaccord de fond. Le bot l'applique au test d'invariance (§39).

**Reporté.** Présélectionner les candidates par recherche hybride (mots-clés et sens) : les questions sont en anglais,
les fiches en français, et la recherche par le sens demande un modèle de plongement que le dépôt n'embarque pas.

**Ce qui ne change pas.** Le p publié, les fichiers d'équivalents, la lecture.

## 43. Monde synthétique : mesurer le lecteur contre une vérité connue (0.7.66)

**Décision d'auteur, le 2026-11-11**, d'après LLMMatrix (J. Prokopets, 2026), banc de prévision sur une économie
simulée dont la vérité est connue par construction.

**Le manque.** Les paramètres du lecteur dans le programme génératif (sensibilités sF, sf ; faux positifs pF, pf) sont
stipulés : sans vérité terrain, on ne pouvait pas les mesurer.

**Le test** (bot, workflow manuel). (1) `tirer_situation(strate, graine)` tire un ensemble de cartes présentes selon la
loi a priori du programme génératif (tirage exact, graine fixée) ; (2) un modèle-narrateur écrit un court texte factuel
qui décrit la situation **sans nommer les cartes** ; (3) le lecteur, avec sa consigne ordinaire, lit ce texte sur des
candidates qui mêlent cartes présentes et absentes ; (4) on compte : carte présente ancrée en F ou en f (sensibilités),
carte absente ancrée (faux positifs). Sans contamination par construction : la situation n'existe nulle part ailleurs.

**Réserves.** Un narrateur de la même famille que le lecteur peut écrire les marqueurs trop lisiblement (ou en suggérer
d'autres) : la mesure est une borne optimiste de la sensibilité. Elle ne remplace pas le test d'invariance sur des
sources réelles (§39). Les valeurs mesurées ne remplacent les paramètres stipulés que par décision datée.

**Ce qui ne change pas.** Le p publié, les paramètres du génératif.

## 44. Le critère de Klein et la place de l'alphabet (0.7.67)

**Décision d'auteur, le 2026-11-11**, d'après V. Venkatasubramanian, *Beyond Proofs: Can AI Invent Mathematics
Humans Have Never Imagined?* (SSRN 7646378, 16 octobre 2026). L'auteur distingue trois niveaux d'apport : nouveaux
résultats, nouvelles connexions, nouveaux **langages** ; il s'appuie sur Poincaré (les mathématiques donnent « le même
nom à des choses différentes ») et sur Klein (une géométrie se définit par ce qui reste invariant sous un groupe de
transformations), et propose quatre tests : généralisation, interventions causales, comparaison avec les formalismes
établis, vérification indépendante.

**1. Critère de Klein pour une nouvelle carte** (`protocole.md` A2, étape 3). Une carte est ce qui reste invariant
quand on change de strate : sa structure mathématique nommée. Une carte candidate (née du journal des lacunes et des
dynamiques observées des états nuls) doit donc montrer la **même** structure dans au moins **trois** strates (deux
auparavant), seuls les marqueurs changeant. Deux strates peuvent partager une forme par coïncidence ; trois rendent
l'invariant plausible. Aucune carte n'est en cours d'admission : la règle s'appliquera à la première.

**2. La place de l'alphabet, dite honnêtement.** Selon ces trois niveaux, l'alphabet n'est **pas** un langage inventé
par une IA : c'est un langage conçu par un humain (seize cartes, chacune rattachée à une structure mathématique
connue), que des modèles appliquent et que les données mettent à l'épreuve. Son apport revendicable est au niveau des
**connexions** (le même nom porté à travers treize strates par des équivalents), et il reste à démontrer. Le seul lieu où
le troisième niveau pourrait apparaître est la **découverte de cartes manquantes** à partir des états nuls, sous le
critère de Klein.

**3. Ses quatre tests, et leurs équivalents dans le skill et le bot.**

| Test | Mécanisme |
|---|---|
| Généralisation | levée de L7 (§27) ; bras exploratoire hors strate 7 (§29) |
| Interventions causales | ablation carte par carte (§33) |
| Comparaison avec les formalismes établis | structure mathématique nommée de chaque carte ; reconstruction de la matrice ; SSSOM (§42) |
| Vérification indépendante | invariance du lecteur (§39) ; monde synthétique (§43) ; second codeur |

**Réserve.** L'explication que l'auteur propose de l'émergence d'une structure sémantique (la « téléodynamique
statistique ») est sa propre théorie, peu reprise : elle n'est pas importée.

**Ce qui ne change pas.** Le p publié, les seize cartes, la matrice.

## 45. CONTRAINTE resserrée : une règle qui retire une option, plus seulement une règle qui existe (0.7.68)

**Décision d'auteur, le 2026-11-11**, après les deux premiers passages du monde synthétique (§43). Sur 22
situations lues, CONTRAINTE a été lue dans les **5 situations sur 5** où elle était absente : en F les deux fois où
COMMUNAUTÉ était présente, en f les trois autres.

**Le motif.** Les marqueurs d'une fiche sont des alternatives : un seul rempli suffit pour f. Le premier marqueur de
CONTRAINTE (« règle écrite ou sanction observée ») constatait l'**existence** d'une règle, et presque tout récit
géopolitique en contient une (traité, règlement, sanction). Or ce qui définit la carte est la contrainte **active**
(structure : contrainte qui lie la solution, multiplicateur de Lagrange non nul) : une option retirée à quelqu'un. Les
marqueurs de COMMUNAUTÉ (« contributions et règles d'appartenance », « sanction, exclusion ») retombaient
mécaniquement dans ce premier marqueur.

**Le changement.** Premier marqueur : « règle écrite ou sanction qui retire une option nommée à un acteur ». Les deux
autres marqueurs sont inchangés ; l'équivalent local de la strate 7 (« option commerciale retirée par une sanction,
ou option militaire plafonnée par un traité ») le disait déjà.

**À vérifier.** Les prochains passages du monde synthétique, avec le vérificateur indépendant, diront si les fausses
lectures de CONTRAINTE baissent, et si d'autres cartes ont un marqueur aussi large.

**Ce qui ne change pas.** Le p publié, la matrice, les autres cartes.

## 46. Marqueurs : chaque ligne est une alternative complète (0.7.69)

**Décision d'auteur, le 2026-11-11**, après le quatrième passage du monde synthétique : « les cartes doivent être
calibrées, sans quoi elles reviendront sans cesse, ou dans le mauvais ordre, à cause d'une question de vocabulaire ».

**Le défaut.** La règle du §30 dit qu'un seul marqueur rempli suffit pour f : chaque ligne de « Marqueurs
observables » est donc une **alternative**. Or plusieurs fiches écrivaient une seule condition sur plusieurs lignes
(une phrase coupée : « un élément présent dont l'origine est datable ; qui continue d'orienter les conduites ; et
qui… »), ou une composante qui, seule, ne montre pas le mécanisme de la définition (« au moins trois mesures datées
d'une même grandeur », sans hausse ; « au moins deux rythmes propres », sans alignement). Lue comme une alternative,
la première ligne suffisait : un traité daté de 2004 ancrait TRACE·MÉMOIRE, trois pays et une organisation ancraient
RÉSEAU. Constat chiffré : RÉSEAU lu 4 fois et TRACE·MÉMOIRE 3 fois quand ils étaient absents, sur 12 situations.

**La règle d'écriture, désormais.** Chaque ligne de marqueurs, prise **seule**, montre le mécanisme de la *Définition*.
Une condition qui n'a de sens qu'avec une autre est écrite sur la **même** ligne.

**Les fiches corrigées** (le contenu est conservé, seule la coupe change, sauf mention) :

| Carte | Changement |
|---|---|
| PÉRIODICITÉ | occurrences et intervalle constant sur une ligne ; phases identifiables sur un cycle déjà vu deux fois |
| RÉCURSIVITÉ | une seule ligne (le discours ET son effet sur ce qu'il décrit) |
| ÉMERGENCE | régularité et absence de prescription sur une ligne ; imitation ou convergence inchangée |
| RÉSEAU | les trois nœuds ne suffisent que si la situation dépend de leurs liens (ce qui passe ou non) |
| PROPORTION | une seule ligne : le rapport suivi à deux dates (la définition porte sur sa conservation ou sa rupture) |
| TRANSFORMATION | état de départ et état en cours avec un invariant ; étapes intermédiaires entre deux états |
| TRACE · MÉMOIRE | une seule ligne (origine datable, influence actuelle, et maintien par l'histoire) |
| CROISSANCE | une hausse qui s'accélère ou un taux estimable (fidèle au §30 : pas trois mesures exigées) ; une limite sur une grandeur qui croît |
| RÉSONANCE | rythmes ET alignement sur une ligne ; canal de couplage entre deux rythmes identifiés |

Inchangées : SEUIL, RÉCIPROCITÉ, HIÉRARCHIE, POLARITÉ, INCERTITUDE, CONTRAINTE (§45), COMMUNAUTÉ.

**Garde-fou du §30.** Il ne s'agit pas de rendre f plus difficile : une ligne reste suffisante seule, et la forme
complète de l'*attendu* n'est toujours pas exigée pour f. Seules les lignes qui ne montraient pas le mécanisme
deviennent des conditions complètes. Le monde synthétique dira si les fausses lectures baissent sans que la
sensibilité s'effondre.

**Ce qui ne change pas.** Le p publié, la matrice, les définitions et structures mathématiques des cartes.

## 47. Apprendre les λ sur les données (0.7.70)

**Décision d'auteur, le 2026-11-11**, après le calcul de puissance du test C contre B (bot `puissance_lecteur.py`).
Dans le propre modèle du skill (strate 7, 1 000 questions simulées), même un C égal à la vraie probabilité ne gagnerait
que 1,3 point de score par question sur B (2,1 sur les questions où une carte lue est reliée à la cible) : les
structures n'y déplacent la probabilité que de 5 points en moyenne. Le premier goulot n'est pas le lecteur, mais la
force que le modèle prête aux cartes, **stipulée** (λ_F 3 ; λ_M 1,8 ; λ_f 1,2 ; π 0,1).

**La décision.** Les λ seront appris sur les issues, au lieu d'être seulement posés :
- modèle : celui du calcul publié sans plafond, logit p = logit f + Σ n_classe · ln λ_classe, où n_classe compte les
  cartes lues ayant une arête de cette classe vers la cible ;
- estimation : maximum a posteriori, a priori normal sur ln λ centré sur la valeur stipulée (écart-type 0,5) ; avec
  peu de questions, l'estimation reste près du stipulé ;
- données : questions résolues du bot Metaculus et du banc alphabet-chaine (résolues en 24 heures) ;
- contrôle : perte log hors échantillon (validation croisée en 5 blocs), stipulés contre appris.

**En ombre d'abord.** Le bot écrit chaque semaine `registre/lambda-appris-<date>.json`. Les λ du skill ne changent que
par une décision datée, quand l'estimation repose sur au moins 50 questions et bat les stipulés hors échantillon.

**Ce qui reste à décider.** Faire de l'ombre générative (§36) le C publié : l'auteur attend des tests (le calcul de
puissance la donne gagnante, le C publié perdant même avec un lecteur parfait, faute d'utiliser les absences).

**Ce qui ne change pas.** Le p publié, la matrice, les λ en vigueur.

## 48. Freins : des arêtes inhibitrices dans la matrice (0.7.72)

**Décision d'auteur, le 2026-11-11** (« il vaut mieux limiter les dégâts »), après la lecture de la prospective
stratégique (repérer, pour chaque signal, ce qui l'accélère **et ce qui le freine**) et parce que l'arbre de la
connaissance doit pouvoir fermer des branches, pas seulement en ouvrir.

**Le défaut corrigé.** Jusqu'en 0.7.71, les 66 arêtes de la matrice avaient toutes λ ≥ 1 : une carte lue ne pouvait
que rendre une apparition plus probable (`graphe.md` §2.1, « Conséquence, à mesurer »). Pour un événement « apparait »,
C était toujours au moins égal à la fréquence de référence : il gagnait sur les OUI et perdait sur **toutes** les NON.
Une contrainte de capacité ne pouvait pas freiner une croissance ; une hiérarchie qui prescrit l'ordre ne pouvait pas
rendre moins probable un ordre non prescrit.

**La règle d'inscription, plus stricte que pour un moteur.** Un frein n'est inscrit que si la **structure
mathématique** de la carte source borne ou exclut le mécanisme de la cible, avec une référence ; une simple tension
documentée (`antagonismes.md` §4) ne suffit pas. Un frein ne double jamais une arête de la matrice (contrôlé par
l'audit). Six freins, classe I, λ_I = 0,556 (l'inverse de λ_M, stipulé comme les autres) :

| Frein | Mécanisme | Référence |
|---|---|---|
| CONTRAINTE ⊣ CROISSANCE | une capacité limite active borne le taux de croissance (logistique) | Verhulst 1838 |
| HIÉRARCHIE ⊣ ÉMERGENCE | un ordre prescrit par une autorité préempte l'ordre non prescrit, que l'émergence exige par définition | `cartes.md` (ÉMERGENCE : « sans avoir été prescrite par un agent central ») |
| TRACE·MÉMOIRE ⊣ TRANSFORMATION | verrouillage par rendements croissants : le chemin suivi résiste au changement de forme | Arthur 1989, David 1985 |
| TRACE·MÉMOIRE ⊣ ÉMERGENCE | une convention verrouillée occupe la place d'une convention nouvelle | Arthur 1989 |
| INCERTITUDE ⊣ CROISSANCE | l'incertitude des acteurs retarde les engagements irréversibles (investissement, embauche) qui portent la croissance | Dixit & Pindyck 1994 ; Bloom 2009 |
| POLARITÉ ⊣ COMMUNAUTÉ | un champ organisé en deux pôles divise le collectif de plus de deux membres que la coopération exige | McCoy & Somer 2019 |

**Le calcul publié.** Un frein est une source de λ_I < 1 : logit p = logit f + Σ ln λ, le terme du frein est négatif.
- Même strate, ou transfert ancré ; **jamais** abaissé vers une autre strate (un frein ne se propage pas sans
  mécanisme déclaré).
- « Bouge » renforce le frein (λ_I / 1,5), comme il renforce un moteur.
- Le produit des λ est désormais borné des deux côtés : [1/10 ; 10]. L'écart maximal entre C et B reste ln 10 sur
  chaque issue : la borne du test C contre B (`score_registre.borne_gain_C_B`) tient.
- Redondance (inclusion, renforcement, transfert) : on garde la source la plus forte **en valeur absolue** de ln λ.
- Un frein ne rend pas une apparition atteignable : le noyau et le classement des transitions de la base de cas ne
  comptent que les sources de λ > 1.

**Ce qui ne change pas, et pourquoi.** La matrice des moteurs (66 arêtes), les λ F, M, f, le plafond de p₀. Le
programme génératif (§36) et le tirage du monde synthétique (§43) ne lisent que la matrice des moteurs : les freins
n'y entrent pas encore (un couplage négatif de co-présence est une autre hypothèse, à décider sur données) ; le
noisy-or (§34) les traite déjà (une source de λ < 1 « laisse passer la fraction p_i/f »).

**À mesurer.** Dans le bot, la perte de C sur les questions où un frein est lu, contre B ; l'apprentissage des λ (§47)
estime λ_I comme une quatrième classe, avec le même a priori.

## 49. Freins en ombre, et ce qu'ils peuvent apporter (0.7.73)

**Décision d'auteur, le 2026-11-11**, le même jour que le §48, après vérification : les freins ne touchent presque
jamais le chiffre posté. Les 13 événements calculés du registre du bot et les 12 du banc alphabet-chaine sont tous
« SEUIL apparaît » (une question binaire se traduit presque toujours par un franchissement de seuil), et aucun frein ne
vise SEUIL. Le défaut que décrit le §48 (C jamais sous B pour une apparition) reste donc entier là où il coûte au score.

**Ce qui change.** Les freins sortent du p publié, conformément à la règle des ombres :
- `calculer` ne les lit pas ; `sensibilite` publie l'ombre `avec_freins` (p et effet), comme `sans_plafond` ;
- la simulation (`trajectoires`, l'arbre de la connaissance) les lit : c'est là qu'ils servent, à fermer des branches ;
- le produit des λ reste borné à [1/10 ; 10] (sans effet tant que tout λ publié est ≥ 1).

**Ce qui corrige le défaut pour le score**, déjà en ombre : C corrigé du biais (décalage appris, 0.5.0), le programme
génératif qui lit les absences (§36 ; gagnant dans le calcul de puissance), les λ appris (§47).

**Le test des freins.** Seul un jeu de séquences historiques codées peut dire si, CONTRAINTE présente, CROISSANCE
apparaît moins souvent (les occasions d'éprouver une arête, `base-de-cas.md`). La base de cas réels n'en compte que
quatre : l'étendre est la condition du test (feuille de route, « Arbre de la connaissance »). Le monde synthétique ne
peut pas servir : il mesure la lecture, et son tirage ne lit pas les freins.

## 50. Valeur attendue de l'information (0.7.74)

**Décision d'auteur, le 2026-11-11**, après lecture de `voivod` (Forecasting Research Institute, statistiques pour
évaluer les questions de prévision elles-mêmes).

**Le défaut.** La valeur de l'information du §34 classe les cartes absentes par l'écart maximal qu'elles produiraient
si on les trouvait, sans tenir compte de la chance de les trouver, ni de ce que leur absence apprendrait.

**La mesure ajoutée, en ombre.** Pour chaque carte absente : VoI = P(C)·KL(P(U|C) ‖ P(U)) + (1 − P(C))·KL(P(U|¬C) ‖ P(U)),
en nats, avec P(C) = π (`generatif.pi_presence`) et P(U|¬C) tirée de la cohérence (P(U) = P(C)·P(U|C) + (1 − P(C))·P(U|¬C)).
C'est la réduction attendue de l'erreur de prévision (score log) si l'on cherchait cette carte. `sensibilite` publie
`plus_informatives_voi` et `voi_max` à côté de `plus_influentes`.

**Pour l'arbre.** C'est la mesure qui dit quelle branche vaut d'être explorée : celle dont la recherche, en moyenne,
apprend le plus. Elle rend aussi visible ce que le calcul publié ignore : une carte cherchée et non trouvée devrait
faire baisser p (P(U|¬C) < P(U) dès que P(U|C) > P(U)), comme le fait l'ombre générative (§36).

**Ce qui ne change pas.** Le p publié, la règle d'arrêt (borne de l'écart, §34).

## 51. Averti : une liaison pour l'indice (0.7.75)

**Décision d'auteur, le 2026-11-12**, nom choisi par l'auteur, après le cinquième passage du banc ForecastBench.

**L'origine.** Le lecteur a inventé des liaisons hors de la liste (« informe », « renforce », « coexiste », « borne »,
« alimente »). Quatre ont une tête dans la grammaire (renforcement, indépendance, tension, transfert). « Informe » n'en a
pas : il dit qu'une situation **renseigne** sur une autre sans la causer. C'est la distinction de Pearl entre voir et
faire, et celle du §34 entre indices et causes, qui n'avait pas de symbole.

**La liaison.** `A —averti→ B` : observer A rend B plus ou moins attendu, sans que A agisse sur B (critère dans
`grammaire.md` §4). Elle vaut dans une strate et entre strates, et peut viser l'événement calculé.

**Sa place dans le calcul, en ombre.** Le p publié combine les sources en produit des λ, c'est-à-dire qu'il les lit
toutes comme des indices (§33-§34) ; l'ombre `noisy_or` les lit toutes comme des causes. *Averti* permet au lecteur de
trancher source par source. L'ombre `mixte_averti` combine les sources déclarées *averti* vers la cible en produit, et
les autres en noisy-or : P = cote(noisy-or des causes) × Πλ des indices, le produit borné par `plafond_LR`. Aucun
paramètre nouveau, aucun λ nouveau : *averti* ne s'additionne pas à la matrice, ce qui compterait deux fois la même
carte. Calculée seulement si au moins un *averti* vise la cible.

**Ce qu'on mesurera.** Sur les issues réelles, si `mixte_averti` fait mieux que le produit et que le noisy-or là où le
lecteur a déclaré des indices. Et, à part, combien de fois chaque liaison hors liste revient, et chez combien de
lecteurs différents : un verbe inventé par plusieurs modèles sans concertation est un symbole candidat, pas un tic de
langue. Toute adoption passe par une décision datée.

**Ce qui ne change pas.** Le p publié ; les neuf autres types.

