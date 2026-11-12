# Alphabet situationnel — Simulation et sortie (couche 5)

> Version : 0.7.75

> Les chiffres et empreintes viennent du moteur. Format des restitutions, sans transformer une
> simulation conditionnelle en prévision empiriquement validée.

---

## 1. Modèle de sortie complet (mode PRÉVOIR)

La ligne d'ouverture et la ligne de signalement sont celles de `constitution.md` §3 et de S5, sans
variante ; `moteur.py calculer` les imprime telles quelles en tête de sa sortie humaine.

```
⚠ Prévision · cet outil prend un risque déclaré.
⚠ ρ[n] · [barreau] · [source en clair] · p₀ [x] % · p [y] % [intervalle] · échéance [date] · journal [id]   (une par prévision)
Base : [actifs éligibles / test exclus / archives / fictifs si démonstration]
Calcul : moteur.py v[version] · date d'information [date]

════ BLOC ANALYTIQUE ════
Question : [objet, événement, horizon exact, fenêtre, nombre de pas, sémantique]
Strates examinées : [faits et sources]

| Carte@strate | Équivalent et statut | Fait, objet, source et date | Passage (localisation · relation) | Test (paille, cerceau, pistolet, double) | Confiance F/f | Contre-observation | Final |
A6 · [voisines et raisons]
Garantie · [pour chaque F : mécanisme · attendu · ce qui contredirait]
Option · [pour chaque F : acteur · option avant → option après]
Q · [qualificatifs ancrés]
Cartes inactives : [rejets motivés]
État présent : [date | fenêtre] [mots]
Liaisons : [faits et mécanismes]
Positions : [si ≥3 mots]
Statut de lecture : [Descriptif | Spéculatif | Nul]
Questions qui départagent : [1 à 3 questions ; pour chacune, la carte si oui, la carte si non ou
 « indéterminé », ce qui y répondrait (observation, source) et, par branche, pourquoi la réponse
 établit la carte ; éventuellement une question de documentation : la preuve qui manque à un ancrage]
Ce que l'alphabet ne voit pas ici : [entrées de `angles-morts.md` concernées, ou « rien de répertorié »]
Coût du codage : [faits examinés et écartés (dont faits sans option changée) ; candidates ouvertes et
 non retenues ; rejets A7 ; hésitations consignées]

| Événement | Résolution externe | p / non estimé | Intervalle conditionnel | ρ | Comparateur même horizon | Calcul et limites |
[sous la ligne S5 : la lecture en association (« si le motif observé se répète, alors… ») ; les deux
 bandes de sensibilité, celle des hypothèses de modèle et celle de la classe de référence, avec la
 mention « classe instable » si le niveau d'homologie ou l'effectif retenu change ; si la bande retenue
 traverse 50 %, « non identifié » et l'origine de la traversée ; si elle est large (plus de 30 points),
 le dire : le résultat dépend des hypothèses non calibrées ; si elle est saturée (une variante touche
 le plafond des cartes), dire que la bande ne mesure rien ; l'écart entre niveaux d'homologie quand il
 dépasse `ecart_niveaux_max` (§H, 10 points : le seuil c_min_rho1 décide seul du niveau retenu) ; le sceau du dossier de lecture
 s'il a été fourni ; le jugement scellé avant le calcul ;
 la probabilité sans cartes et l'écart en points ; le placebo d'homologie et l'apport de l'homologie
 (p − p_placebo), y compris nul ; **sans cas réel actif, la paire « sans cartes → avec cartes » en tête**,
 avant p seul (0.7.12 : arêtes non éprouvées, P8) ; si p tombe dans la plage à 90 % du placebo, « homologie
 indiscernable d'une sélection au hasard » ; la **bande d'horizon** (p à 1, 3 et 6 fenêtres, même
 sémantique) à côté de la bande de sensibilité : l'horizon est la question, pas une incertitude, mais c'est
 lui qui déplace le plus p ; les **variantes de codage** (p si chaque mot f, puis tous, étaient absents) :
 un ancrage f pèse autant qu'un F dans les multiplicateurs, et c'est cette plage qui dit ce qu'il coûte (0.7.13) ; si le dossier est incomplet (plancher A7), statut de lecture Spéculatif et
 manques dans « À vérifier » ; un écart nul se dit : la question
 ne teste que l'inertie ;
 afficher p en pourcentage entier (une décimale sous 1 % et au-dessus de 99 %) avec son intervalle ;
 ρ dit d'où vient le chiffre, pas sa fiabilité ; recopier les valeurs non arrondies dans le journal et
 conserver le JSON complet]

Trajectoires si demandées : [états, probabilités, R1, R2, limites]

════ BLOC SYMBOLIQUE ════
Signature : [noms ; glyphes facultatifs]
Lecture : [sans chiffre ni affirmation supplémentaire]

════ À AJOUTER À VOS FICHIERS ════
journal-previsions.jsonl : [prévisions chiffrées seulement, contrat validation.md]
journal-lacunes.md : [si motif descriptif réellement hors corpus]

À vérifier auprès de vous : [sources, objets, références, résolutions et limites non levées]
```

---

## 2. Règles de remplissage

- Descriptif : tous les ancrages F, sources vérifiées et contre-observations traitées.
  Spéculatif : sinon ; Nul : aucun mot. Le statut des équivalents ne change pas le statut de lecture
  (A3) : les équivalents non vérifiés sont listés dans « À vérifier auprès de vous ».
- F/f mesure la qualité de l'ancrage. Une hausse réelle se décrit par une grandeur distincte.
- p=null : « probabilité non estimée » ; ne pas convertir en 0, 50 % ou 1/3.
- **Aucun mot de probabilité sans son chiffre** (0.6.6). « Probable », « sérieuse possibilité » ou
  « peu vraisemblable » ne s'écrivent jamais seuls dans le bloc analytique : Kent (1964) rapporte que
  les membres de son propre comité lisaient « serious possibility » de 20 % à 80 %. Le chiffre vient en
  premier ; le mot, s'il est employé, l'accompagne. À l'inverse, un jugement de l'utilisateur donné en
  mots (« c'est probable ») ne se convertit pas : demander le chiffre avant de sceller. Une table de
  correspondance réintroduirait l'écart qu'elle prétend réduire.
- Mots F d'un cas réel actif à source unique (`corroboration: "unique"`) : les lister dans « À vérifier
  auprès de vous ».
- Intervalle null : « non estimé ». Intervalle existant : approximation conditionnelle à 80 %, qui
  n'intègre pas toutes les incertitudes ; plus large que `largeur_max_affichage` (§H, 30 points), la
  probabilité s'écrit `~y % (large : a–b)` (S5), ce que `moteur.py` fait lui-même.
- Niveau ρ : provenance, pas confiance empirique. Afficher « non encore évalué prospectivement ».
- Journal : probabilités non arrondies, résultat JSON, empreintes et même horizon pour le comparateur.
- Dates : la commande refuse une échéance incompatible avec la fenêtre ; reformuler avant calcul.
- Toute démonstration fictive est explicitement identifiée et exclue de V4.

---

## 3. Trajectoires de l'état (S3)

Noyau à risques concurrents : au plus un changement par pas ; intensité −ln(1−p), statu quo exp(−Σλ),
répartition des changements proportionnellement aux intensités. Toutes les probabilités sont bornées.
**C'est un second modèle, pas une conséquence du premier (0.7.13).** La normalisation dépend de tous les
candidats et exclut les réalisations simultanées : deux événements à 50 % isolément y reçoivent 37,5 %
chacun, et le statu quo 25 %. Les marginales d'une trajectoire ne sont donc pas les probabilités de
`calculer` ; la sortie publie l'écart au premier pas (`ecart_marginales_pas1`) et le signale au-delà de
`delta_discriminant`. **Estimande (0.7.14)** : le noyau donne la probabilité qu'un événement soit **le
premier** changement — formule exacte pour des horloges indépendantes tronquées à un changement. Il ne
représente pas les changements simultanés : `masse_simultanee_pas1` publie la masse que des horloges
indépendantes de mêmes marginales leur donneraient (37,5 % sur la démonstration), et que le noyau reporte
sur les états à un seul changement. **`moteur.py noyau`** (0.7.14) construit, sur une **frontière** de 2 à
10 événements déclarés, la loi jointe d'un pas dont les marginales sont exactement les p de `calculer`
(entropie maximale sous ces contraintes : indépendance, sauf paires déclarées exclusives par
`--exclusion`), et publie pour chaque événement les deux estimandes — `p_horizon` (réalisé à l'échéance)
et `p_premier` (premier changement) —, la masse « aucun / exactement un / deux ou plus » et les
configurations. Il ne change aucun p ; il n'estime aucune dépendance. Une distribution jointe explicite sur quelques événements liés, dont les
marginales découleraient, reste à construire (`apports-theoriques.md` §17).
Le niveau ρ de chaque branche hérite de toutes les estimations entrant dans la normalisation.
Les apparitions candidates couvrent les strates présentes et celles examinées par `--strates`.
Un nouveau mot est f : aucun fait nouveau ne l'ancre. Les liaisons invalidées par un retrait sont
supprimées. Les qualificatifs conservés participent à l'identité des états fusionnés.

Élagage : pas conditionnel <5 % ou hors faisceau de 300. R1 regroupe les états finaux rares ; R2 la
masse abandonnée. La somme états + R1 + R2 est contrôlée. R2>30 % : avertissement de non-représentativité.
La date d'information ne progresse pas vers de nouvelles données : la simulation utilise le jeu de
preuves figé. Les trajectoires sont exploratoires ; pour un événement, utiliser `calculer`.

---

## 4. Rédiger une prévision

Définir objet, événement observable, source de résolution, critère, seuil et date avant calcul.
Le critère doit mesurer le marqueur local et la grandeur concernée, pas un événement voisin.
Un composé exige `--resolution` avec ces champs ; pour l'intensification : grandeur, unité,
comparaison et au moins deux observations numériques datées connues au départ. La fréquence de
hausse conditionnelle à la persistance est distincte de la fréquence de persistance.
L'indicateur de bascule prépare une future révision ; il ne réécrit jamais un ancien pari.
La condition de réfutation définit l'issue de la question, pas l'invalidation d'un modèle probabiliste
par une observation unique. Si aucun critère externe n'est disponible, ne pas produire de pari chiffré.

**Événement de calendrier (0.6.9).** Un événement dont la date est fixée par un texte (scrutin,
proclamation, échéance budgétaire ou légale) n'est pas une transition aléatoire : le moteur, qui ne
connaît pas le calendrier, le calcule sur un taux générique (test brésilien : « un vainqueur est
proclamé dans la semaine du second tour », 6,8 %, alors que la proclamation était programmée). Pour un
tel événement, fournir une référence externe (`--fref` avec sa source, ou `--references`), ou ne pas
le chiffrer. Déclarer `--temporalite programmee` : sans référence externe, le moteur répond « non
estimée », **même avec des cas homologues** (0.6.13) : ces cas sont appariés par cartes, pas par
calendrier, et partagent le même angle mort. **Durée de vie propre (0.6.10)** : même règle pour un phénomène dont la durée de vie n'a
rien à voir avec la fenêtre de référence de 3 mois (test Polo : un cyclone, ÉMERGENCE@11, « persiste »
à 96,75 % sur 7 jours par l'inertie trimestrielle générique, et se dissipe le quatrième jour) :
`--temporalite duree_de_vie`, puis une référence de domaine (durée de vie des cyclones du bassin) ou
pas de chiffre. **Lecture sémantique (0.7.16, Copley 2009).** `programmee` correspond à ce que la
sémantique du futur appelle un *futurate* : la phrase présuppose un **directeur** capable de fixer
l'événement (l'autorité qui fixe la date du scrutin) et affirme qu'il s'y est engagé ; `generique`, à un
futur générique ordonné par l'inertie, où le cours normal du monde suffit, sans directeur. Test : y a-t-il
quelqu'un dont on peut nommer la capacité à fixer l'événement, et un texte qui montre son engagement ?
Sinon, l'événement n'est pas programmé. Un dossier qui déclare `programmee` porte
`programmation` {qui, engagement}. `duree_de_vie` n'a **pas** de correspondant chez Copley (la distance
entre l'énoncé et l'événement est une question qu'elle laisse ouverte) : c'est une catégorie propre au
skill, à justifier par elle-même. Une réponse « non estimée » se journalise comme abstention (`validation.md` §1) :
elle compte, sans score. Ne pas non plus le coder comme la disparition d'INCERTITUDE : la proclamation lève une
incertitude, pas la structure ; recours et contestations peuvent la prolonger. La structure qui porte
un calendrier est PÉRIODICITÉ.

**Quatre formes d'imprévisibilité (0.7.20, Grossetti).** Grossetti (*Sociologie de l'imprévisible*, PUF,
2004, ch. 1 ; repris dans « L'imprévisibilité dans les parcours sociaux », *Cahiers internationaux de
sociologie* 120, 2006) croise deux questions : le **moment** de la situation à l'issue incertaine est-il
prévu, et ses **issues** sont-elles délimitées d'avance ? Les deux textes ne numérotent pas les cases de la
même façon ; on les cite donc par leur nom.

| | Issues délimitées d'avance | Issues non délimitées |
|---|---|---|
| **Moment prévu** | **Carrefour** : scrutin, concours, match, palier d'orientation | **Transition, changement d'état programmé** : négociation au calendrier fixé, retraite, entrée dans l'âge adulte |
| **Moment imprévu** | **Risque anticipé** : maladie, chômage, catastrophe à plan de secours | **Crise** : rien n'est cadré, ni le moment ni les issues |

Ce que chaque case demande au skill, sans rien changer au calcul :

- **Carrefour** : le moment est fixé par un texte, c'est `programmee` ; l'issue est la question elle-même,
  et elle a une partition déclarée. C'est le cas déjà traité plus haut : référence externe, ou pas de
  chiffre. Grossetti ajoute une raison : cette imprévisibilité est **organisée** (isoloir, règles du jeu,
  épreuves simultanées), et les acteurs veulent qu'elle reste entière ; aucune carte ne la lit.
- **Transition programmée** : la date est fixée, pas les issues. `programmee` s'applique à la date ; mais
  une prévision exige un événement observable déclaré avant calcul (§4, premier paragraphe). Tant qu'aucune
  issue ne peut être nommée avec son critère de résolution, la question n'a pas d'estimande : lecture
  seule (mode LIRE), pas de pari.
- **Risque anticipé** : c'est la case où les fréquences d'homologues ont un sens, et Grossetti dit
  pourquoi : une situation imprévisible **pour la personne** (on ne prévoit pas de tomber malade) est sans
  surprise **au niveau agrégé** (le médecin sait qu'il y aura des malades). La fréquence que rend le moteur
  est de ce second niveau. Elle ne dit pas ce qui arrivera dans **ce** cas, et c'est une raison de plus
  pour que le skill ne décide rien sur une personne.
- **Crise** : ni moment ni issues. Il n'y a pas de question formulable, donc pas d'estimande. Le skill
  lit (LIRE), ne chiffre pas, et le dit. Grossetti note que la plupart des crises se **resserrent** ensuite
  en un petit nombre d'options : une crise devient un carrefour quand les acteurs ont construit les
  branches. C'est à ce moment, et pas avant, qu'une prévision peut être rédigée.

**Nouvelle occurrence (0.7.38).** « Le Conseil adoptera-t-il un **nouveau** paquet de sanctions ce trimestre ? » ne
se pose ni en « apparaît » (la structure CONTRAINTE@7 est déjà présente, G6), ni en « se renforce » (F/f est une
confiance, non une intensité). Elle se pose en **« s'intensifie »** sur une **grandeur cumulée** : le nombre d'actes
(paquets adoptés, frappes, expulsions). `--resolution` porte la grandeur, l'unité, la comparaison (« supérieur à
l'échéance à sa valeur à la date d'information ») et au moins deux observations datées ; `--references` porte la
fréquence conditionnelle « CTR@7 hausse|persiste », c'est-à-dire la part des trimestres où un nouvel acte a eu lieu,
sachant la structure présente. Le moteur rend p = P(persiste) × P(hausse | persiste). **Si la persistance est quasi
certaine dans le domaine** (un régime de sanctions en vigueur depuis douze ans), donner aussi sa référence (« CTR@7
persiste ») : sinon l'inertie par défaut (0,90 sur 3 mois) tire p vers le bas. Sur le test du 2026-11-03 : 0,90 × 0,79
= 0,71 avec l'inertie par défaut ; 0,99 × 0,79 = 0,78 avec la référence. Les cartes n'y ajoutent rien tant que les cas
de la base ne comptent pas les actes : la prévision est celle de la classe de référence, dite comme telle.

Une situation change de case en cours de route : une négociation bien cadrée tourne à la crise, un match
à la catastrophe, une crise se resserre en alternative (le paradigme ancien ou le nouveau, chez Kuhn). Une
prévision posée sur un carrefour suppose que la partition tient jusqu'à l'échéance ; si une issue hors
partition devient possible, c'est un **indicateur de bascule** à écrire (il prépare une révision et ne
réécrit pas le pari, §4). Le moment de la décision n'est pas pour autant le moment où l'on sait : chez
Grossetti, le degré d'imprévisibilité d'une situation est « lui-même partiellement imprévisible ».

---

**Persistance et disparition : l'inertie de l'objet (0.7.39).** L'inertie du moteur est celle d'une carte, un chiffre
par trimestre (INCERTITUDE : 0,40), quel que soit l'objet. Une doctrine en place depuis des décennies et une trêve d'une
semaine y persistent pareillement : sur le test T2 de la deuxième série (`validation.md` §17), 0,40 contre une issue
réalisée. Hors démonstration, `persiste` et `disparait` exigent donc une référence de l'objet : `--fref` avec
`--definition-ref` (la classe dans les mots de la source, par exemple « doctrines de défense publiques maintenues un
trimestre »), ou `--references`. Sans elle : non estimé, motif journalisé, abstention. Les paramètres ne changent pas.

## 5. Bloc symbolique (P9)

Aucun chiffre, pourcentage ou niveau ρ. Les mots résument seulement les constats et hypothèses du
bloc analytique, sans ajouter d'intuition prédictive. Référencer une question par son intitulé court.
La signature peut faciliter la mémorisation ; elle n'est pas un résultat scientifique supplémentaire.

---

## 6. Sorties des autres cas

**LIRE** : état, sources, alternatives et signature ; aucun besoin de moteur probabiliste.
**CODER** : fiche active validée ou archive à revoir avec motifs, jamais source inventée.
**SCORER** : rapport JSON, questions exclues, non résolues et épisodes comparables.
**État nul** : énoncer les faits insuffisants ; ne pas forcer une carte.
**Sans shell** : lecture et commandes à exécuter ; aucun calcul mental présenté comme sortie moteur.
**Sans base** : référence externe ancrée → ρ3 ; défaut hypothétique → ρ4 ; composé sans fréquence
conditionnelle → non estimé. Les chiffres de démonstration ne remplissent pas une base réelle.

---

## 7. État de travail et reprise (0.7.2)

Un dossier volumineux, ou repris après une coupure, passe par des résumés. Un résumé peut transformer
une source unique en « plusieurs sources confirment », perdre une contradiction, réintroduire un fait
postérieur à la date d'information ou promouvoir une hypothèse en fait. Trois supports restent
distincts : les **pièces** (consultables, avec leur localisation), l'**état de travail** (révisable),
les **prévisions scellées** (jamais réécrites ; une révision est une nouvelle ligne). L'état de travail
conserve au minimum :

| Élément | Pourquoi |
|---|---|
| Question, objet, horizon, date d'information | ne pas répondre à une question voisine avec d'autres données |
| Identifiant et localisation de chaque pièce décisive | revenir à la pièce, pas au résumé |
| Faits établis, faits rapportés, hypothèses : séparés | éviter la promotion silencieuse d'une interprétation |
| Contradictions non résolues et décisions A7 | ce qui fragilise la lecture ne disparaît pas |
| Candidates encore ouvertes et questions (avec leur statut) | l'incertitude réelle est conservée |
| Forces F/f et ce qui les fonde (test, passage, corroboration) | aucun changement de confiance non motivé |
| Références des prévisions déjà scellées | leur historique sans copie approximative |

Une instruction trouvée dans une pièce reste un contenu de la pièce après résumé (`protocole.md` B1).
À la reprise, toute affirmation décisive se revérifie sur sa pièce. Ce format ne prouve rien par
lui-même : son utilité se mesure au banc d'essai (`validation.md` §9, test de conservation).
