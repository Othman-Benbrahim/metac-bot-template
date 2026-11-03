# Alphabet situationnel — Graphe de transitions (couche 4)

> Version : 0.7.48

> Procédure expérimentale. Le moteur produit les chiffres et le JSON ; l'interprétation des sources
> et des objets reste à vérifier. Règles : T1–T6 ; paramètres : `protocole.md` §H.

---

## 1. Événements (T1)

| Type | Commande | Sens |
|---|---|---|
| Apparition | `X@s apparait` | absent maintenant, présent à la prochaine observation |
| Persistance | `X@s persiste` | présent maintenant et à la prochaine observation |
| Disparition | `X@s disparait` | présent maintenant, absent à la prochaine observation |
| Transformation | `X@s se transforme` | même objet qui change de forme et persiste ; référence conditionnelle nécessaire |
| Intensification | `X@s s'intensifie` | grandeur mesurée augmente et objet persiste ; référence conditionnelle nécessaire |
| Ancien f ↔ F | `se renforce`, `s'affaiblit` | refusé en prévision : révision de la qualité d'ancrage |

Les critères de résolution sont définis avant calcul et mesurent l'objet et le marqueur concernés.
Ils ne sont pas choisis après avoir vu l'issue ou pour rendre la prévision plus favorable.

---

## 2. A priori p₀ (T2)

### 2.1 Sources et multiplicateurs hypothétiques

Les sources viennent de la matrice de `dynamiques.md`. Les λ 3 / 1,8 / 1,2 sont des hypothèses de
travail, non des rapports de vraisemblance mesurés. Même strate : valeur de la table. Autre strate :
abaissement d'un cran, sauf propagation explicitement admise ou transfert ancré. Sources liées par
inclusion, renforcement ou transfert : garder la plus forte, pour limiter le double comptage.
*Bouge* multiplie le λ de la source par 1,5 ; *manque* ajoute une source moyenne. Le produit est
plafonné à 10. Ces règles ne démontrent ni causalité ni indépendance ; elles sont à comparer au
modèle `--sans-cartes`. Ce dernier désactive également les homologues : il mesure l'apport conjoint
de la modulation et de la sélection structurelle, pas l'effet isolé d'un seul mécanisme.
Les effets inhibiteurs ne sont pas estimés dans cette version ; ne pas en inventer.

**Ce que le calcul lit, et ce qu'il ne lit pas (0.7.14).** La grammaire écrit plus que l'inférence n'en
utilise. Tout symbole qui n'entre pas dans le calcul est **déclaré non inférentiel** (P7 : la confiance
affichée correspond à ce qui est utilisé) ; `calculer --json` le recopie dans `modele.quotient` et signale
toute liaison de l'état qui n'agit pas.

| Symbole de l'état | Lu par le calcul | Effet numérique |
|---|---|---|
| `carte@strate` | oui | choix des sources (matrice) |
| `[F]` / `[f]` | indirectement | aucun sur λ ; seulement l'identité H1 et la pondération H1.5 (`variantes_codage`) |
| `{qualificatif}` | identité H1 seulement | aucun sur λ |
| objet, rôle | non (validation G6 seulement) | aucun : deux situations qui ne diffèrent que par là sont le même état |
| liaison `transfert` | oui | évite l'abaissement d'un cran entre strates, et déduplique |
| liaisons `inclusion`, `renforcement` | oui | déduplication : la source la plus forte est gardée |
| liaisons `conflit`, `tension`, `appui`, `reproduction`, `écho` | **non** | aucun |
| liaison `indépendance` | validation G6 seulement | aucun |
| position `bouge` | oui | λ × 1,5 : ne peut qu'augmenter |
| position `manque` | oui | **ajoute** une source λ = 1,8 : une lacune ne peut qu'appeler son comblement, jamais empêcher |

Les deux dernières lignes sont des contraintes de signe du modèle, pas des choix de lecture : tant que
tous les λ sont ≥ 1, un empêchement ne peut s'écrire qu'en aide supplémentaire (décision d'auteur 9).

**Quelle forme a ce calcul (0.7.14).** logit p₀ = logit f + Σ ln λᵢ est **exactement** la conditionnelle
d'un modèle log-linéaire à paires sur des indicatrices (bⱼ = logit fⱼ, θᵢⱼ = ln λᵢⱼ) : sur la
démonstration, logit 0,05 + ln 1,8 + ln 1,2 = −2,174, soit p₀ = 10,2079 %. Mais une famille de
conditionnelles n'admet une loi jointe que sous des conditions (Arnold et Press 1989) ; pour un champ non
orienté, θᵢⱼ = θⱼᵢ. La matrice ne l'est pas : sur 66 couples ordonnés, 12 entrées (6 paires) sont
réciproques à intensité égale, 8 ont une réciproque d'intensité différente, 46 n'en ont aucune. Le produit
des λ est donc une **pseudo-vraisemblance** (Besag 1975) : cohérente pour prédire un événement
conditionnellement à l'état, sans loi jointe garantie. **L'asymétrie n'est pas à corriger** : SEUIL → TRACE
· MÉMOIRE (F) contre TRACE·MÉMOIRE → SEUIL (f) est la thèse de la fiche (le retour est fermé) ;
symétriser pour obtenir un champ détruirait l'irréversibilité. La lecture cohérente avec l'asymétrie est
celle d'un **générateur** de transitions hors équilibre, qui n'a pas à être réversible
(`apports-theoriques.md` §18).

**Support et exigence (0.7.17, d'après le Digital Consciousness Model, Shiller et al. 2026).** Un
indicateur a deux propriétés distinctes : son **support** (le rapport de vraisemblance positif,
sensibilité / (1 − spécificité) : à quel point il est plus fréquent quand la propriété est là) et son
**exigence** (*demandingness*, spécificité / (1 − spécificité) : à quel point il est rare quand elle n'est
pas là). Un indicateur que presque tous les cas portent ne dit rien par sa présence, beaucoup par son
absence. Transposé à une arête i → j (apparition de j) : sensibilité = P(i présent | j apparaît),
spécificité = P(i absent | j n'apparaît pas). λ tient lieu du **support**, postulé. Deux choses manquent,
et elles se distinguent : (1) le moteur **n'utilise jamais l'absence d'une carte comme preuve** — seules
les cartes présentes sont des sources, alors que le DCM met à jour sur les absences (rapport
(1 − sensibilité) / spécificité) ; (2) l'exigence d'une arête n'est ni déclarée ni mesurée. Ce n'est pas
cette absence qui empêche une arête défavorable : un rapport de vraisemblance inférieur à 1 s'écrit avec
un seul paramètre ; c'est la grille λ ≥ 1 qui l'interdit (décision d'auteur 9).
**Règle de mesure, fixée avant les cas.** Dès qu'une arête i → j compte au moins `n_min_ancrage`
transitions où j apparaît et autant où il n'apparaît pas, sur cas réels actifs, on publie pour elle
sensibilité, spécificité, rapport positif, rapport négatif et exigence, avec leurs intervalles de Wilson ;
une arête dont le rapport positif est compatible avec 1 est déclarée **sans support mesurable**, quelle que
soit son intensité postulée. Ces mesures ne remplacent pas λ dans le calcul : les y faire entrer
changerait des p (version séparée, étape « Estimer » de la feuille de route).

**Portée des cartes.** Les multiplicateurs ne s'appliquent qu'aux **apparitions**. Sans base de cas,
la probabilité d'une persistance ou d'une disparition ne dépend que de l'inertie de la carte : une
telle question ne teste pas la lecture structurelle, quel que soit son score. `calculer` imprime donc
à côté de p la probabilité sans cartes, et le journal la conserve (`p_sans_cartes`, `validation.md`
§1). Pour éprouver la lecture, préférer des apparitions, ou des persistances sur une base où les
homologues diffèrent des transitions non homologues.

### 2.2 Fréquence de référence f

La fréquence est spécifique à **un événement et une fenêtre**. Une référence externe comporte source
consultée, définition, période, fenêtre, date de disponibilité. Exemple de fichier de références
externes, fourni par l'utilisateur et passé à `--references` (aucun fichier de ce nom n'est livré ;
ne pas le confondre avec `assets/parametres.json`) :

```json
{
 "POL@7 persiste": {"frequence": 0.85, "source": "SOURCE À REMPLACER PAR UNE RÉFÉRENCE VÉRIFIÉE", "definition": "les deux blocs restent présents", "periode": "période de la série", "fenetre": "3 mois", "disponible_le": "2026-10-01"},
 "POL@7 hausse|persiste": {"frequence": 0.2, "source": "SOURCE À REMPLACER PAR UNE RÉFÉRENCE VÉRIFIÉE", "definition": "hausse de la mesure parmi les épisodes où la polarité persiste", "periode": "période de la série", "fenetre": "3 mois", "disponible_le": "2026-10-01"}
}
```

Ces nombres sont **fictifs**, pas des références prêtes à l'emploi. Les clés utilisent les
abréviations canoniques. Pour la transformation : `RES@7 transformation|persiste` par exemple.
Aucune fréquence scalaire n'est partagée entre deux composantes. Pour un événement simple seulement,
`--fref` est un raccourci avec `--source-ref`, `--periode-ref`, `--disponible-ref` obligatoires.
Le moteur contrôle les champs et dates ; l'existence et la pertinence de la source sont humaines.

Base disponible : chaque cas se partage un poids total ≤1 entre ses transitions éligibles, puis
pondération par l'âge. f = (succès pondérés + k₀ × référence) / (poids total + k₀).
Référence : externe si fournie ; sinon défaut de 5 % sur 3 mois pour une apparition ou inertie pour
une persistance. Sans source externe, f est publié comme comparateur dès un effectif pondéré
≥ `n_min_publication` (1), et dit **ancré** — accès à ρ3 — à partir de `n_min_ancrage` (20, soit k₀ :
les données pèsent au moins autant que la référence) ; 0.7.7 a dédoublé l'ancien seuil unique (10).
**Ce qu'est f (0.7.5).** f n'est pas une fréquence observée : c'est la moyenne a posteriori d'une loi
Beta(k₀·réf, k₀·(1 − réf)) révisée par les observations pondérées ; **k₀ = 20 est un nombre de
pseudo-observations** de la référence. Publié ne veut pas dire précis : à n = 10, un écart-type de proportion vaut √(0,05 × 0,95 / 10) ≈ 6,9
points pour un taux de 5 %, et la référence pèse encore 20 / 30 = 67 % de f ; `calculer` affiche donc
l'intervalle à 80 % de cette loi et la part de la référence. Aucun de ces seuils ne change p (f est
calculé avant eux) ; ils décident de ce qui est publié comme comparateur et de ρ.
Les dates d'issue **et de disponibilité des preuves** sont antérieures ou égales à la date d'information.

### 2.3 Combinaison

**Sensibilité (0.6.0).** Le moteur compte une centaine de paramètres non calibrés pour quelques cas :
le système est sous-déterminé, une infinité de jeux de paramètres reproduisent les cas connus et
divergent sur le suivant. `calculer` relance donc chaque calcul sous six variantes (multiplicateurs
d'un cran plus bas et plus haut, inerties − 0,05 et + 0,05, fréquence par défaut × ½ et × 2) et
imprime la bande obtenue. Elle mesure l'incertitude de **modèle**, que l'intervalle bêta (bruit
d'échantillonnage) ne couvre pas. Si la bande traverse `seuil_decision` (§H, 50 %), la ligne S5
écrit « non identifié » : le sens de la réponse dépend d'hypothèses non calibrées. **Bande large
(0.6.5)** : indépendamment de tout seuil, une bande plus large que `largeur_max_affichage` (§H, 30
points) est signalée (`bande_large`) ; une bande de 10 à 45 % ne traverse pas 50 % mais ne permet
aucune lecture. **Portée** : les six variantes déplacent tous les paramètres d'un même type ensemble.
C'est une sensibilité *paramétrique globale*, pas une incertitude *structurelle* : une seule transition
fausse parmi les 66 de la matrice déplacerait à peine la bande, et le modèle serait faux quand même.
Une bande étroite ne dit donc pas que la matrice est juste. Sur l'exemple 1,
la bande (19–28 %) est plus étroite que l'intervalle bêta (5–43 %) : pour ce calcul, l'incertitude
d'échantillonnage domine celle des hypothèses.

**Classe de référence (0.7.3).** Les six variantes ne touchaient que l'a priori ; or le choix des cas
retenus dépend du seuil de Jaccard, des lissages k et k₀ et de la demi-vie. Huit variantes de **classe**
(Jaccard ± 0,1 ; k, k₀ et demi-vie × ½ et × 2) donnent une seconde bande, rendue à part ; la classe
est dite **instable** si l'ensemble des cas retenus change d'une variante à l'autre (un simple
changement d'étiquette de niveau sur les mêmes cas ne compte pas). La bande retenue réunit les deux, et
`origine_seuil` nomme celle qui traverse 50 %. Une sonde « toutes les forces abaissées à f »
(`effet_force`) est rendue à part, hors de la bande : c'est une autre lecture, pas une hypothèse de
modèle. **Les multiplicateurs viennent de la matrice** (intensité F/M/f d'une arête, `dynamiques.md`),
jamais de la force F/f d'un mot : la force n'agit que par la sélection des homologues, donc pas du tout
sans base. **Fragilité de niveau** : le niveau d'homologie retenu (§3) se décide sur un compte
(`c_min_rho1`) ; `calculer` rend p pour chaque niveau non vide (`niveaux`) et signale un écart supérieur
à `ecart_niveaux_max` (§H, 10 points) entre niveaux.

```
p₀ = f × LR / (1 − f + f × LR)
```

0 et 1 sont traités sans division par zéro ; aucune entrée hors [0,1] ou non finie.
Persistance à défaut : r = inertie^(durée / 91,3125 jours). En position *bouge* : r^1,5.
Disparition : complément de la persistance, sauf référence explicitement propre à la disparition.
Le moteur distingue ces événements ; il ne réinterprète pas une fréquence de disparition comme une
fréquence de persistance. L'échelle de risque décrit la provenance et n'atteste aucune calibration.

**Plafond (0.6.9).** `plafond_p0` (§H, 95 %) borne l'effet des cartes, pas la fréquence : il ne
s'applique que si les multiplicateurs élèvent p au-dessus de la fréquence f, et jamais sous f. Avant
0.6.9, il s'appliquait à toute probabilité : une persistance d'inertie à 99,5 % sur 7 jours tombait à
95 % sans que son complément bouge (somme 96,2 %), et 7 pas quotidiens plafonnés donnaient 0,95⁷ ≈ 70 %
pour la même question (audit du test brésilien, octobre 2026). Propriétés désormais vérifiées par
autotest : persistance et disparition somment à 1 ; la persistance et l'apparition sans
multiplicateur ne dépendent pas du découpage temporel. **Limite connue** : avec multiplicateurs,
l'apparition dépend légèrement du découpage (SEUIL@7 sur 3 mois : 10,2 % en un pas, 10,4 % en 13 pas
hebdomadaires), parce que λ multiplie la cote et non le taux ; avec une base de cas, dont les fréquences
sont observées à la fenêtre des cas, l'invariance ne peut pas tenir. Calculer à la fenêtre de la question.

### 2.4 Un événement sur plusieurs pas

Soient a l'apparition par pas et r la persistance par pas. Sources et paramètres supposés fixes.

| Question temporelle | Calcul |
|---|---|
| Absent au départ, présent à h | q₀=0 ; qₜ₊₁=qₜr+(1−qₜ)a |
| Présent au départ, présent à h | même chaîne avec q₀=1 |
| Apparition au moins une fois | 1−(1−a)^h |
| Persistance continue | r^h |
| Disparition au moins une fois | 1−r^h |
| Absence à l'échéance depuis un état présent | 1−q_h |

`--semantique presence`, `continue` ou `au-moins-une-fois`, selon l'événement. Défauts : presence
pour apparition, continue pour persistance, au-moins-une-fois pour disparition. À un pas, le modèle
observe les états aux bornes ; il ne détecte pas un changement transitoire à l'intérieur de la fenêtre.
**Lecture aspectuelle (0.7.16).** Les trois valeurs suivent la propriété de sous-intervalle (Bennett et
Partee 1978, reprise par Copley 2009, p. 5-7) : `continue` est un **état** évalué sur tout l'intervalle
(vrai sur chacun de ses sous-intervalles) ; `presence` un état évalué à l'échéance ; `au-moins-une-fois`
un **événement**, vrai sur l'intervalle sans l'être sur ses parties. Les défauts en découlent : une
apparition est un événement, qui ne se constate qu'après coup et se lit donc à l'échéance (`presence`) ;
une persistance, un état (`continue`) ; une disparition, un événement (`au-moins-une-fois`). C'est une
correspondance qui **justifie** les défauts, non une démonstration qu'ils sont les seuls possibles : le
moteur admet les autres combinaisons, et elles posent d'autres questions. Deux questions de sémantique
différente ne se comparent pas au score sans le dire. *Non retenu* : exiger une sémantique constante
dans une classe d'homologues — les cas codés ne portent pas de sémantique, ce sont des transitions d'un
pas, et la sémantique ne s'applique qu'à la composition sur l'horizon, après leur sélection.
La fréquence de base est propagée avec **la même formule** ; si une composante de référence manque,
le comparateur est non évaluable. Le niveau ρ hérite des composantes réellement utilisées.
Aucun intervalle multi-pas : propager seulement les bornes d'une composante ignorerait les autres.
**Hypothèse de taux constant (0.7.5).** Le modèle est une chaîne de Markov d'ordre 1 sur l'état codé,
à taux constant : l'inertie est ramenée à la fenêtre par inertie^(durée / 91,3125 j), et la persistance
continue vaut r^h (loi géométrique, analogue discret de l'exponentielle). La probabilité qu'un mot
disparaisse ne dépend donc pas du nombre de pas où il est déjà présent. *Formulation de la 0.7.5,
conservée telle quelle :* « Ce n'est **pas** une négation de l'hystérésis de SEUIL ni de la dépendance
au chemin de TRACE·MÉMOIRE : celles-ci portent sur la *situation* et sont portées par l'état lui-même
(une inertie de 0,97, les arêtes qui suivent SEUIL, une carte TRACE·MÉMOIRE qui inscrit le passé dans
l'état). » **Corrigé en 0.7.13** : une inertie
de 0,97 représente une **persistance**, pas une hystérésis. L'hystérésis demande que l'aller et le retour
basculent à des valeurs **différentes** d'un paramètre de contrôle ; l'état codé ne contient pas ce
paramètre, et aucune règle de transition ne distingue l'aller du retour. Le modèle **ne représente donc pas**
l'hystérésis de SEUIL : il en représente une conséquence observable (un SEUIL franchi tend à rester),
pas le mécanisme. La présence d'une carte TRACE·MÉMOIRE n'y suffit pas non plus : elle inscrit qu'un passé
compte, pas lequel ni comment. Ce qui n'est pas modélisé, c'est la dépendance
à l'**âge** du mot (un SEUIL franchi depuis un an tient-il mieux qu'un SEUIL franchi hier ?). Elle se
mesure par `moteur.py confronter` (maintien selon l'âge) ; une loi à taux variable (Weibull discrète,
forme c ≠ 1) attend des cas réels pour estimer c. Sur la base d'exemple, fictive : 85 % de maintien à
l'âge 0, 88 % à l'âge 1 ou plus, écart de 2,7 points pour un écart détectable d'environ 17 points :
le test ne tranche rien, et la base fictive ne renseigne que sur sa fabrication.
**La fenêtre** est le levier le plus fort de ce calcul (ÉMERGENCE@11 persiste : 97 % sur une semaine,
65 % sur trois mois, 42 % sur six). Ce n'est pas une variante de modèle mais la question posée ; elle
reste hors des bandes. Ce qui la relie à la durée du phénomène est `temporalite`, et, depuis 0.7.5,
`duree_caracteristique_jours` dans le dossier de lecture : une durée sourcée inférieure à la moitié de
la fenêtre (`ratio_duree_fenetre`) avec une temporalité générique est refusée sans justification.
Composés : un pas seulement, sinon erreur explicite.

**Ce que le multi-pas ne voit pas (0.7.18).** Les arêtes valent pour un pas (`transitions` : paires d'états
consécutifs). Au-delà, `presence` suit une vraie récurrence de Markov à deux états sur la carte cible
(q ← q·r + (1 − q)·a) ; `au-moins-une-fois` et `continue` supposent des pas indépendants. Dans tous les cas, les
**autres cartes restent figées** à leur valeur initiale (la sortie le dit : « sources et probabilités supposées
fixes sur l'horizon »). Un lien indirect, qui passe par une carte relais, n'y a aucun chemin : à partir de trois
variables, l'amélioration de la prévision à un pas ne capte pas les liens indirects, qui n'apparaissent qu'à des
horizons plus longs et exigent deux conditions au lieu d'une pour être exclus (Bruneau et Nicolaï 1994, système
autorégressif stationnaire : l'analogie vaut pour la forme, non pour la formule). Le multi-pas est la prévision
d'**une** carte, contexte figé, non celle du système ; les trajectoires (`simulation.md` §3) font bouger
plusieurs cartes, sans dépendance estimée. Comparer, sur un cas connu, le p à trois pas contexte figé et le p
obtenu en faisant bouger la carte relais dirait ce que coûte le gel ; ce test attend des cas.

---

## 3. Cas homologues (T3)

### 3.1 Unité de comptage

Une transition relie deux états espacés d'une fenêtre calendaire exacte. Un cas avec dix transitions
ne pèse pas dix cas : poids de chaque transition = pondération d'âge / nombre de transitions
éligibles de ce cas dans le lot. n_A et n_E sont les sommes pondérées ; c_A est le nombre de cas.
Cela limite la pseudo-réplication mais ne prouve pas l'indépendance entre cas ; des épisodes liés
peuvent nécessiter un regroupement supplémentaire. Dates et preuves futures sont exclues aussi de f.

### 3.2 Échelle de similarité

| Niveau | Condition |
|---|---|
| H1 | mêmes cartes, mêmes F/f, mêmes qualificatifs ; état non vide |
| H1.5 | Jaccard pondéré de toutes les cartes (F=1 ; f=0,5), ≥0,7 et intersection non vide |
| H2 | toutes les sources non vides de l'événement présentes |
| H3 | sources et cible traduites dans une autre strate, tous équivalents vérifiés |

Retenir le niveau le plus strict qui atteint 3 cas distincts (`c_min_rho1`) ; sinon le plus strict
non vide. Raison : H1 ⊆ H1.5, si bien que la règle de 0.4.0 (« le niveau qui offre le plus de cas »)
ne retenait jamais H1 sous 30 cas et échangeait la comparabilité contre l'effectif sans le dire. Le prix
est un intervalle plus large ; il est affiché. Une pondération continue par la similarité (le Jaccard
pondéré est déjà calculé) serait plus cohérente encore ; elle est différée faute de données pour en
fixer la forme. H3 seulement sans homologue local. Deux ensembles de mots forts vides ne créent plus H1.
Cette similarité ne code pas l'identité des objets, les positions ou les liaisons ; l'utilisateur doit
examiner la pertinence des cas retenus. Les transitions, dates, issues et poids figurent dans le JSON.

**Deux seuils (0.7.7).** Le niveau retenu atteint `c_min_niveau` cas distincts ; ρ1 en exige
`c_min_rho1`. Les deux valent 3 : la séparation est structurelle, sans effet. Porter `c_min_niveau` à 2
(décision 4 de l'auteur) change un calcul de démonstration (SEUIL@7 à trois pas : 52,0 % → 51,7 %, ρ1 →
ρ4) : c'est une version dédiée, séparée de toute version qui ne change aucun p.
**Ce que cette règle arbitre (0.7.6).** H1 est le niveau le plus *spécifique* : il conditionne sur le plus
d'informations (mêmes cartes, mêmes forces), donc le modèle le plus complexe, biais faible et variance
forte ; H1.5, H2, H3 regroupent davantage, biais plus fort et variance plus faible. La règle retient le
plus spécifique dès qu'il atteint un plancher de variance (`c_min_rho1`, 3 cas), et ne regroupe qu'en
dessous. La règle de parcimonie de la sélection de modèles (« à scores de validation comparables, le
modèle le moins complexe », Dreyfus et al. 2008) suppose des scores de validation, qui n'existent pas
encore ; appliquée ici, elle favoriserait le regroupement, pas H1. Le choix est donc déclaré comme un
compromis biais-variance à plancher fixe ; son coût est publié (`fragilite_niveau`, §2.3) et il sera
arbitré par les scores, pas par la doctrine. **Concentration** : `n_eff_kish` = (Σw)² / Σw², les w étant
les poids par cas, et la part du cas le plus lourd disent si c_A cas pèsent comme c_A cas (Kish 1965) ;
sur la démonstration, 9,3 pour 10 cas, le plus lourd à 16 %.

### 3.3 Ce que postule l'homologie, et ce que teste le placebo (0.7.5)

L'estimateur ne dépend que de (n_E, n_A), jamais de l'identité des cas retenus : les transitions d'une
classe d'homologues sont traitées comme **échangeables** (« événements équivalents », de Finetti 1937).
L'axiome a deux moitiés. **Dans** la classe, les cas sont interchangeables ; le calcul le suppose, rien
ne le teste. **Entre** la classe et le reste de la strate, ils ne le sont pas : sinon choisir des
homologues n'apporterait rien. Le placebo (0.7.4) teste **cette seconde moitié** : il tire autant de
cas au hasard dans la strate et la fenêtre ; si `apport_homologie` ≈ 0, la strate entière se comporte
comme une seule classe échangeable pour cet événement, et l'homologie n'est pas pertinente ; s'il
s'écarte nettement de la plage des tirages, la classe est une sous-population distincte. Le théorème
de représentation de de Finetti suppose une suite infinie échangeable *a priori* ; la classe est finie,
petite et choisie après observation. *Formulation de la 0.7.5, conservée telle quelle :* « il donne la
**forme** Beta-binomiale de l'estimateur (§4), pas sa validité, qui reste une hypothèse empirique. »
**Corrigé en 0.7.13** : le théorème justifie, sous ces hypothèses,
une représentation des issues comme **mélange de lois de Bernoulli** ; il ne donne pas la forme
Beta-binomiale. Le choix d'une loi bêta pour ce mélange est une **hypothèse de modélisation
supplémentaire**, retenue pour sa conjugaison et sa simplicité (§4). La validité de l'ensemble reste une
hypothèse empirique.

**Décomposition.** p − p_sans_cartes = (p − p_placebo) + (p_placebo − p_sans_cartes) : la première part
mesure le choix des homologues, la seconde les multiplicateurs et les cas de la strate pris au hasard.
`p_sans_cartes` vaut **exactement f** : sans cartes, LR = 1 donc p₀ = f, et aucun homologue n'est retenu,
donc P = k·f / k = f. Le comparateur est une ablation stricte des deux couches à la fois. Il peut donc
être battu dans les deux sens : des homologues défavorables tirent p sous f. C'est un test de
**contenu prédictif incrémental**, de la famille de la causalité au sens de Granger (1969), que la
littérature propose elle-même d'appeler « prédictabilité » : ni série temporelle, ni décalages, ni
régression emboîtée ici, seulement la même question posée avec et sans les cartes. Barreau A.

### 3.4 Capacité et sonde des paramètres (0.7.6)

**Capacité.** Le moteur porte 66 intensités d'arêtes, 16 inerties, 3 multiplicateurs et 4 propagations
inter-strates, plus une trentaine de réglages : aucun n'a été ajusté sur des données, tous sont postulés.
La généralisation d'un modèle dépend du rapport entre le nombre d'exemples et ce qu'il faut estimer ;
le compte global ne la mesure pas ici, car chaque arête ne s'éprouve que sur les transitions où sa source
est présente et sa cible absente. `confronter` compte ces occasions : sur la base d'exemple, fictive,
36 arêtes sur 66 en ont au moins une, 19 au moins dix ; sur des cas réels actifs, **zéro**. Tant que c'est
le cas, la valeur de la matrice n'est pas seulement non présumée (P8) : elle est **non estimable**, arête
par arête. Une apparition à un pas n'utilise pas l'inertie de sa cible ; les paramètres actifs dépendent
de la question.

**Sonde** (`moteur.py sonde`, « variable sonde » de Dreyfus et al. 2008). Le même calcul avec une
matrice altérée au hasard : 66 arêtes tirées parmi les 240 paires possibles (`aretes`), étiquettes F/M/f
permutées (`intensites`), inerties permutées (`inerties`). La référence décisive est **p sans
multiplicateurs, cas gardés** : elle sépare la révision par les cas de l'apport de la matrice. Sur la
démonstration (SEUIL@7, état canonique, 200 tirages) : f 12 %, cas seuls 19 %, matrice réelle 22 %. La
révision par les cas apporte +6,8 points, la matrice +3,2 ; une matrice aléatoire médiane apporte
+0,0 (62 % des tirages ne déclenchent aucun multiplicateur), et la vraie se place au 99ᵉ centile ; des
intensités permutées la placent au 83ᵉ centile, sans la départager du hasard. Un seul événement, une
base fictive : la sonde décrit la mécanique, pas la valeur. Elle est le seul test des paramètres
exécutable avant le premier cas réel.

**Centile du placebo (0.7.18).** Le drapeau `homologie_discernable` dit seulement si p tombe dans la plage à
90 % des tirages ; le placebo publie aussi `centile_placebo`, calculé comme le centile de la sonde (ex æquo
comptés pour moitié, résolution 1/200). C'est une p-value prédictive au sens de Gelman et al. (BDA3 §6.3),
lue sous une nullité nommée : « la sélection des homologues ne fait pas mieux que des cas tirés au hasard ».
Un centile proche de 0,5 dit que l'instrument ne trouve rien, non que tout va bien ; sur la démonstration,
0,63. Deux p également « indiscernables » à 0,62 et 0,97 ne sont pas dans la même situation, et seul le
centile s'agrège entre questions. La nullité de la sonde est autre (la matrice sans effet) : le code est le
même, l'interprétation ne se transporte pas.

**Voisins et unicité de la base (0.7.18, `moteur.py voisins`).** Avant toute prévision, une question
préalable : la base contient-elle des répétitions ? Pour chaque transition, son meilleur voisin par la
similarité du moteur, correspondances triviales exclues (même cas, ou fenêtres qui se recoupent, comme la
zone d'exclusion de la matrice de profil de stumpy). Sur la démonstration : 69 transitions sur 78 ont un
jumeau H1 exact, médiane du meilleur voisin 1,000, 73 sur 78 au-dessus de 0,7. La base est **saturée par
construction** — peu de combinaisons de cartes, répétées —, ce qui explique `homologie_discernable = false` :
un tirage au hasard contient lui aussi presque toujours des jumeaux. Sur une base réelle, une médiane à 1
signalerait un vocabulaire trop pauvre, une médiane basse des cas singuliers. Le même diagnostic publie
l'**unicité moyenne** ū de López de Prado (2018, ch. 4, l'inverse de la moyenne harmonique de la
concurrence mensuelle) : 0,705 sur la démonstration, 42 transitions sur 78 partagent des mois avec celles
d'un autre cas, concurrence maximale 4 — dans la plage d'un tirage aléatoire (médianes 0,6 et 0,7 chez la
source). Le calcul de p n'en tient pas compte : le garde `1/counts` corrige les transitions d'un même cas,
qui ne se recoupent jamais ici, non le recouvrement entre cas distincts. Pondérer par ū ramènerait p vers
p₀ et élargirait l'intervalle (−31,6 % de poids effectif en démonstration, selon la note) : version séparée.

**La décroissance est chronologique, contre l'avis de la source (0.7.18).** López de Prado (2018, §4.7)
fait décroître les poids selon l'**unicité cumulée**, non le temps : « une décroissance chronologique
réduirait les poids trop vite en présence d'observations redondantes ». Le moteur applique
0,5^(âge/`demi_vie_ans`) avec un âge chronologique ; sur la démonstration, l'horloge d'unicité avancerait
environ 30 % moins vite. Choix assumé, non oubli : `demi_vie_ans` est publié et entre dans la bande de
classe ; changer d'horloge changerait sa sémantique et toutes les probabilités. Unicité et décroissance par
unicité, si elles venaient, iraient en sens opposés sur le poids des cas anciens : jamais dans la même
version. Et une précision de vocabulaire : le produit des λ est la forme d'une **pseudo-vraisemblance**
(produit de conditionnelles, Besag 1975), non d'un champ moyen ; mais une pseudo-vraisemblance n'est
consistante que si ses paramètres sont estimés, et ici ils sont stipulés (`feuille-de-route.md` §1, item 1.0).

---

## 4. Révision (T3)

P = (n_E + k × p₀)/(n_A + k), k = 2 : la moyenne a posteriori d'un modèle **Beta-binomial**, d'a priori
Beta(k·p₀, k·(1 − p₀)) ; **k est un nombre de pseudo-observations** (l'a priori p₀ vaut deux cas). La
loi bêta de paramètres n_E+k p₀ et n_A−n_E+k(1−p₀) fournit des quantiles 10–90 % seulement si les deux
paramètres sont positifs et n_A>0. **Ce qui est exact, ce qui ne l'est pas (0.7.5).** Les quantiles sont
calculés exactement ; mais la vraisemblance est **pondérée** (décroissance d'âge, un cas pèse au plus
une observation), si bien que n_A et n_E sont des effectifs fractionnaires et les transitions d'un cas
ne sont pas des épreuves indépendantes : l'intervalle est exact pour ce pseudo-modèle, approché pour la
probabilité qu'il vise. Il est conditionnel à k, à p₀ et au choix des cas ; ni le codage, ni les λ, ni
le choix de modèle n'y sont incertains (bandes de sensibilité, §2.3). Rapport des deux a priori : k₀ = 20
pseudo-observations pour f contre la strate (§2.2), k = 2 pour p₀ contre les homologues ; ils ne portent
pas sur la même quantité, et le rapport 10× n'est pas « dix fois plus de confiance dans le défaut que
dans les homologues ». `calculer` publie les deux poids (« part de l'a priori dans f », « part de p₀
dans p »). Le nombre de cas n'est pas une preuve de calibration. Sans cas ou loi dégénérée : null.
**Deux étapes sur les mêmes données (0.7.13).** f est estimée sur les transitions de la strate (§2.2), puis
p₀, qui en dérive, est révisé par les homologues — qui sont une partie de ces mêmes transitions. C'est un
**lissage bayésien empirique en deux étapes**, pas une mise à jour bayésienne ordinaire avec un a priori
fixé indépendamment des observations : un même cas peut compter dans l'a priori et dans la
vraisemblance. L'intervalle de §4 est donc conditionnel à cet a priori **estimé**, et plus étroit qu'il
ne devrait ; l'effet est faible quand f repose surtout sur sa référence externe (k₀ = 20) et grand quand
la strate compte peu de cas. Aucune correction n'est appliquée : elle demanderait d'estimer f hors des
homologues (validation croisée), ce qui attend une base réelle.
Les seuils ρ sont définis par T3 ; double codage insuffisant, absence de cas sans événement et
non-stationnarité empêchent ρ0. Les sources de référence et les cas sont versionnés.

---

## 5. Emprunt entre strates (T4)

Exiger des équivalents Documentés/Attestés des cartes sources **et de la cible** dans les deux
strates. Les équivalents non sourcés livrés en 0.4.0 ne permettent aucun emprunt. Après documentation,
le poids w=0,5 reste une hypothèse à tester, et non une garantie de transportabilité. Un emprunt ne
remplace pas une observation du domaine cible ; le signalement ρ2 est obligatoire.

**Ce que vaut w = 0,5 (0.7.18).** Une **convention de repli**, non une estimation : le moteur donne le même poids
à toute transition empruntée (H3), quelle que soit la distance entre la strate source et la strate cible. Or le
passage d'un niveau à l'autre n'est pas une agrégation (Coleman 1990 : une interdépendance doit être modélisée ;
deux règles du jeu, la transmission des conséquences et la dérivation des résultats, dont le skill n'a que la
seconde), il peut aller du haut vers le bas (Bhaskar 1975 : le niveau supérieur fixe les conditions aux limites
de l'inférieur), et une corrélation mesurée sur des ensembles peut avoir un signe opposé à celle des membres,
d'autant plus forte que le regroupement est grossier (Boudon 1963, effet de groupement). Un scalaire ne peut pas
suivre un biais qui croît avec l'écart : toute conclusion qui dépend d'un emprunt H3 est suspendue, et H3 est
une **substitution**, non une parenté établie. La base d'exemple ne couvre que 2 strates sur 13, chacune avec les
mêmes 40 cas (`moteur.py voisins`, répartition par strate) : partout ailleurs, l'emprunt ou l'a priori seul est
le régime normal. Une émergence se teste par contrefactuel (Bhaskar) : le cours des choses diffère-t-il si la
strate inférieure opérait seule ? Le skill prédit des événements de situation, non des comportements
d'individus : une phrase qui nomme un acteur illustre, elle ne conclut pas.

---

## 6. Plusieurs événements pour une même question (S1)

Les événements binaires séparés ne somment pas nécessairement à 1. Une partition comporte des issues
exclusives et exhaustives ; sa somme et celle de son comparateur doivent valoir 1, avec exactement
une issue réalisée. Le scoreur compte la partition comme **une question**. Ne pas fabriquer une
partition par multiplication de marginales : la dépendance doit être modélisée ou une distribution
jointe externe justifiée doit être fournie. En l'absence de modèle joint, conserver les binaires.
Le moteur ne propose pas de génération automatique de partitions arbitraires. Tous les résultats
et leur comparateur doivent porter sur le même horizon et la même définition de résolution.

---

## 7. Exemple chiffré, reproductible

```bash
python3 scripts/moteur.py calculer --demo --base assets/base-de-cas.exemple.jsonl \
  --etat "[2026-09 | 3 mois] POLARITÉ@7[F] + CONTRAINTE@6[F]" \
  --evenement "SEUIL@7 apparait" --liaison "CONTRAINTE@6 echo POLARITÉ@7" --temporalite generique --json
```

Base entièrement fictive. Les sorties courantes, régénérées avec le moteur livré, figurent dans
`exemples.md`. Pour une comparaison à quatre pas : ajouter `--pas 4 --semantique presence` ; le
comparateur est lui aussi porté à quatre pas, ou null s'il n'est pas estimable. Aucun ancien chiffre
0.3.x n'est présenté comme une sortie de la nouvelle version.

Pour un composé, fournir également `--resolution resolution.json` : objet, source, critère, seuil,
marqueur ; pour l'intensification, grandeur, unité, comparaison et `observations` sous la forme
`[{"date":"2026-08-01","valeur":10},{"date":"2026-09-01","valeur":12}]`. Ce sont les observations
connues au départ, pas les valeurs futures de résolution. La comparaison future est figée en texte.
