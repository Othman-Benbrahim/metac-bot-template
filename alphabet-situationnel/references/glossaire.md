# Alphabet situationnel — Glossaire

> Version : 0.7.58

> Un terme, un sens. Le mot « niveau » est réservé à trois usages, toujours qualifiés : *niveau de
> risque* (ρ), *niveau d'homologie* (H1–H3), *niveau 2* de la taxonomie (disciplines). La force d'un
> ancrage (F / f) ne s'appelle pas « niveau ».

| Terme | Définition | Où |
|---|---|---|
| A priori (p₀) | probabilité d'un événement avant les cas : fréquence de référence modulée par la structure | T2, `graphe.md` §2 |
| Ancrage | fait de la situation qui remplit un marqueur d'une carte dans une strate | A1, A5 |
| Anti-résonance | recherche de la contre-observation la plus forte, qui peut rejeter une carte | A7 |
| Base de cas | fichier `base-de-cas.jsonl` tenu par l'utilisateur, une fiche par ligne | couche 3 |
| Carte | l'une des 16 structures de l'alphabet, inspirée de structures mathématiques, sans universalité prédictive établie | `cartes.md` |
| Cas distincts (c_A) | nombre de cas d'où proviennent les transitions homologues ; fonde le niveau de risque | T3 |
| Classe de référence externe | fréquence publiée d'un phénomène défini de la même façon, citée, qui ancre l'a priori sans base | T2 |
| Couche | l'un des sept étages de l'outil (0 ontologie à 6 validation) | `constitution.md` §4 |
| Enchevêtrement | liaison entre ancrages de strates différentes : transfert, écho, conflit | G3 |
| Équivalent | traduction locale d'une carte dans une strate, avec son marqueur local et son statut | `equivalences/` |
| État | phrase datée : ensemble des mots ancrés dans une fenêtre | G2 |
| Événement | apparition, persistance, disparition, transformation ou intensification mesurée ; f↔F est une révision de confiance ; objet d'une prévision | T1 |
| Fenêtre de référence | 3 mois : durée pour laquelle sont définies la fréquence par défaut, les inerties ; le moteur ramène ces probabilités à la fenêtre de l'état | T2 |
| Force d'ancrage | qualité de l'ancrage : F (Fort), f (Faible) ou Nul ; distincte de l’intensité réelle et du statut de l'équivalent | A6, A3 |
| Fréquence de base | proportion des transitions où l'événement s'est produit, quel que soit l'état de départ ; « concurrent paresseux » du score | T2, V1 |
| Homologie (H1, H1.5, H2, H3) | similarité des cartes (y compris faibles), exacte ou pondérée ; H1 interdit aux états vides | `graphe.md` §3 |
| Inertie | probabilité a priori qu'une carte reste ancrée au pas suivant | `dynamiques.md` |
| Intervalle | quantiles 10–90 % de la loi Beta a posteriori dont p est la moyenne (Beta-binomial), exacts pour une vraisemblance pondérée, conditionnels à k, p₀ et aux cas ; sans incertitude de codage/modèle | `graphe.md` §4 |
| Pseudo-observations | unité de k (2, a priori p₀ face aux homologues) et de k₀ (20, référence face aux cas de la strate) : l'a priori pèse autant que ce nombre de cas | `graphe.md` §2.2 et §4 |
| Échangeabilité | « événements équivalents » de de Finetti : les cas d'une classe sont interchangeables ; le placebo teste que la classe se distingue du reste de la strate | `graphe.md` §3.3 |
| Confrontation | `moteur.py confronter` : apparitions observées classées selon leur atteignabilité par la matrice ; maintien selon l'âge | `graphe.md` §2.4 |
| Différentiel de perte | d = perte du moteur − perte de la référence, moyenné par épisode ; publié avec σ(d), l'autocorrélation d'ordre 1 et les tests exacts du signe et de Wilcoxon (Diebold et Mariano 1995) | `validation.md` §5 |
| PABAK | accord ajusté de la prévalence et du biais, 2·pₒ − 1 (Byrt, Bishop et Carlin 1993) ; porte le verdict d'accord sous faible prévalence, sous plafond des taux de manque | `base-de-cas.md` §6 |
| Taux de manque | part des ancrages d'un codeur que l'autre ne fait pas, b/(a+b) et c/(a+c) ; les deux se publient, aucun codeur n'est la référence | `base-de-cas.md` §6 |
| Audit des rejets | relecture aveugle d'un tirage non choisi des candidates écartées d'un dossier ; taux d'annulation publié | `validation.md` §6 |
| Concession | rétrogradation ou retrait consécutif à une contestation, notée de 1 à 5 au journal du dossier | `validation.md` §6 |
| Comparateur externe | second bras, aveugle à l'état, aux cartes et à p, scellé avant le moteur et publié ; contaminé s'il a vu l'un d'eux ou vient de la même session ; mesure le dispositif entier | `validation.md` §5 |
| Classe tautologique | classe de référence définie avec le nom d'une carte : refusée, elle compterait les codages de l'alphabet | `frequences-externes.md` |
| Question discriminante | question dont p s'écarte, avant l'issue, d'au moins 2 points de probabilité de p_sans_cartes ou de p_placebo ; V4 est publié aussi sur elles seules | `validation.md` §5 |
| Seuils d'ancrage | `n_min_publication` (f publié comme comparateur) et `n_min_ancrage` (f « ancré », accès à ρ3), dédoublés en 0.7.7 | `graphe.md` §2.2 |
| Sonde | `moteur.py sonde` : le calcul refait avec des arêtes tirées au hasard, des intensités ou des inerties permutées ; la matrice réelle est située parmi ces tirages, contre la référence « cas seuls, sans multiplicateurs » | `graphe.md` §3.4 |
| Taille effective (Kish) | (Σw)² / Σw² sur les poids par cas : nombre de cas équivalents à poids égaux | `graphe.md` §3.2 |
| Couverture des arêtes | nombre d'arêtes ayant au moins une (dix) occasion d'être éprouvées : source présente, cible absente | `graphe.md` §3.4 |
| Signe suffisant | déclaration préalable d'un codeur : déclaration, exécution ou trace ; datée avant le codage | `base-de-cas.md` §2 |
| Classe de source | contemporain, historiographie ou mémoire : d'où vient un fait d'ancrage | `base-de-cas.md` §2 |
| Liaison | relation qualifiée entre deux mots d'un même état | G3 |
| Marqueur | fait type qui ancre une carte : abstrait (noyau) ou local (équivalent) | `cartes.md`, `equivalences/` |
| Mode solo | moins de 20 % ou moins de 20 cas double-codés dans la strate : ρ0 inaccessible | A4 |
| Mot | carte ancrée dans une strate, avec sa force : `SEUIL@7[F]` | G1 |
| Niveau de risque (ρ0–ρ4) | provenance d'une prévision : cas, emprunt, a priori ancré ou non ; ne mesure pas sa calibration | S4 |
| Noyau à risques concurrents | modèle des trajectoires : statu quo ou un seul changement par pas | S3 |
| Partition | ensemble d'issues incompatibles par construction ; seule situation où l'on somme à 100 % | S1 |
| Pas | durée d'une fenêtre d'état ; unité de l'horizon | S2 |
| Positions | *tient*, *bouge*, *manque*, pour un état d'au moins trois mots | G4 |
| Prévision binaire | événement prévu seul, sans somme à 100 % avec d'autres | S1 |
| Proxémie | déroulé des suites possibles d'un état : événements sur plusieurs pas et trajectoires | S3 |
| Qualificatif | manière dont une structure se déploie : rétroaction, échelle, délai, multi-strate | G1 |
| Scellement | empreinte SHA-256 du journal publiée avant l'échéance, contre la réécriture | `validation.md` §8 |
| Multiplicateur hypothétique (λ, LR) | facteur par lequel une carte source multiplie la cote de l'événement | T2 |
| Résolution externe | source, critère et seuil qui décideront de l'issue d'une prévision sans recoder | S1, V1 |
| Rejeu | prévision calculée alors que l'issue était connue ; exclue de l'évaluation V4 | V1, `validation.md` §8 |
| Résultat nul (∅) | aucune carte ancrée : pas de prévision | A8 |
| Statut d'équivalent | Attesté, Documenté, Proposé, Vide, Hors domaine | A3 |
| Statut de lecture | Descriptif, Spéculatif, Nul ; porte sur la lecture, pas sur les prévisions | `simulation.md` §2 |
| Strate | l'un des 13 registres où se rangent les faits (niveaux d'organisation, domaines, longue durée) | `strates.md` |
| Test de preuve | classement d'un fait d'ancrage selon qu'il est nécessaire et/ou suffisant (paille, cerceau, pistolet, double ; Collier 2011) ; F exige pistolet ou double | A6 |
| Transition | paire d'états consécutifs d'un cas ; unité de comptage | `graphe.md` §3 |
| Abstention | prévision journalisée dont le calcul figé est « non estimé » (`probabilite` null) ; sans Brier, comptée à part par `scorer` | `validation.md` §1 |
| Angle mort | ce qu'aucune carte ne peut exprimer dans une strate ; entrée réfutable, ou exclusion déclarée « délibéré » | `angles-morts.md` |
| Bande de sensibilité | p le plus bas et le plus haut sur six variantes des hypothèses non calibrées ; « non identifié » si elle traverse `seuil_decision`, « bande large » au-delà de 30 points, « saturée » si une variante touche le plafond des cartes ; sensibilité paramétrique globale, pas structurelle | `graphe.md` §2.3 |
| Barreau | degré causal d'une transition (Pearl) : A association, I intervention documentée, C contrefactuel documenté ; toutes les transitions sont A | `dynamiques.md`, S5 |
| Recodage confirmé | relecture datée, par un codeur humain nommé, d'un codage proposé par un modèle ; exigée avant qu'un tel cas devienne actif | `base-de-cas.md` §2 |
| Corroboration | déclaration, pour un mot F de cas réel actif, que son fait repose sur des sources indépendantes (au moins deux, nommées) ou sur une source unique ; sans effet sur le calcul | `base-de-cas.md` §2 |
| Difficulté | 0,5 − \|f − 0,5\| par question, f étant la fréquence de référence : 0 pour une question jouée d'avance, 0,5 pour une question à 50 % | `validation.md` §1 |
| Garantie | troisième terme d'un ancrage F de cas réel : mécanisme par lequel le fait relève de la carte, ce qu'elle rend attendu, ce qui la contredirait | A6 |
| Jugement scellé | probabilité du codeur écrite et hachée (`sceller-jugement`) **avant** le moteur ; prouve l'intégrité, pas l'antériorité | `validation.md` §1 |
| Nom local | phrase par laquelle une discipline nomme le phénomène dans son vocabulaire, sans le mot de la carte ; exigé pour Documenté | `equivalences.md` §2 |
| Manifeste | `SHA256SUMS` : empreinte de chaque fichier livré, vérifiée par `audit` et `sha256sum -c` ; régénérée en dernier avant livraison | `README.md` |
| Option | filtre de pertinence d'un ancrage F de cas réel : un acteur et l'option qu'il avait avant et n'a plus après, ou l'inverse | O1 |
| Question qui départage | question posée au premier état d'un cas réel dont les deux réponses mènent à deux cartes différentes, ou à une carte et à l'indétermination (abduction) ; pour un cas réel, avec sa résolution et une justification par branche | `grammaire.md` §7 |
| Indéterminé (`indetermine`) | branche d'une question dont la réponse ne permet pas de conclure : « non A » ne vaut pas « B » ; état de l'information, pas issue du monde, jamais probabilisé | `grammaire.md` §7 |
| Question de documentation | question qui cherche la preuve manquante d'un ancrage (`carte`, `manque`) ; ne départage pas deux cartes et ne remplace pas une question qui départage | `base-de-cas.md` §2 |
| Résolution d'une question | observation et source qui répondraient à une question de lecture ; distincte de la résolution externe d'une prévision (S1) | `base-de-cas.md` §2 |
| Statut d'une question | ouverte, partielle, résolue (avec la réponse) ou présupposé invalidé, chacun avec la preuve qui l'a fait changer | `base-de-cas.md` §2 |
| Passage | localisation, dans la source, du fait d'ancrage et relation à ce fait (soutient, partiel, contredit, absent de la pièce, non soutenu) ; F exige un passage qui soutient le fait tel qu'il est écrit | A6 |
| Indépendance | ce qui rend deux pièces corroborantes indépendantes : origine, producteur ou chaîne de transmission distincts ; sans elle, l'accord ne protège que des erreurs de transcription | A6 |
| Support, exigence | support : rapport de vraisemblance positif d'un indicateur (λ en tient lieu, postulé) ; exigence : sa rareté quand la propriété est absente (spécificité / (1 − spécificité)), ni déclarée ni mesurée ici | `graphe.md` §2.1 |
| Agnosticisme structuré | engagements explicites, crédences révisées, probabilités plutôt que verdicts, sensibilité publiée comme telle (Chandaria et al. 2026) | `constitution.md` §1 |
| Forme de la pièce | prospective, rétrospective (décrit le fait à travers son issue), attribuée (rapporte sans assumer) ou inclassable (non datable) ; seule une pièce prospective soutient F | A6 |
| Directeur | entité capable de fixer un événement programmé et engagée à le faire (Copley 2009) ; sans elle, l'événement n'est pas `programmee` | `simulation.md` §4 |
| Inertie (deux sens) | dans le moteur, une probabilité de persistance par fenêtre (0,40 à 0,97) ; en sémantique du futur (Dowty 1979, Copley 2009), un principe qui retient les mondes où les choses suivent leur cours. Même mot, deux objets | `graphe.md` §2.2 |
| Quotient | ce que l'état calculé ne distingue pas (objets, rôles, positions *tient*, six types de liaisons) ; déclaré dans `modele.quotient` : un quotient non déclaré est une affirmation implicite | `graphe.md` §2.1 |
| Pseudo-vraisemblance | lecture exacte du produit des λ : conditionnelles log-linéaires sans loi jointe garantie (matrice non symétrique) | `graphe.md` §2.1 |
| Estimande | ce que p mesure : `p_horizon` (réalisé à l'échéance, `calculer`) ou `p_premier` (premier changement, trajectoires) ; non interchangeables | `simulation.md` §3 |
| Frontière | événements déclarés d'une question sur lesquels `noyau` construit une loi jointe d'un pas | `simulation.md` §3 |
| Gabarit (P, G, I) | prédicat, générateur, invariant d'une carte ; critère d'un équivalent descriptif, local ou transversal | `cartes.md` |
| Clôture | `moteur.py conservativite` : toutes les conséquences à un pas d'une base (chaque état, chaque carte de ses strates), et leur empreinte ; deux versions sont conservatrices si aucune ne change | `validation.md` §9 |
| État de travail | résumé révisable d'un dossier long, séparé des pièces et des prévisions scellées, au contenu minimal fixé ; un index, jamais une preuve | `simulation.md` §7 |
| Dossier de lecture | fichier JSON d'une lecture en mode PRÉVOIR (état, candidates par strate et rejets, pièces de chaque F, questions, événements déclarés), contrôlé par `moteur.py dossier` avec les mêmes règles qu'une fiche, et scellé avant le calcul (`calculer --dossier`) ; contrôle la forme, pas la justesse | `SKILL.md` |
| Bande de classe | seconde bande de sensibilité : huit variantes sur le choix des cas retenus (Jaccard, lissages k et k₀, demi-vie) ; « instable » si l'ensemble des cas retenus change | `graphe.md` §2.3 |
| Fragilité de niveau | écart de p entre niveaux d'homologie non vides ; signalée au-delà de `ecart_niveaux_max`, car le niveau retenu se décide sur un compte | `graphe.md` §2.3 |
| Placebo d'homologie | même calcul avec autant de cas tirés au hasard dans la strate et la fenêtre, moyenné sur 200 tirages sous graine dérivée de la question ; p − p_placebo = apport de l'homologie | `validation.md` §1 |
| Registre du partage | `partage.jsonl`, fichier de l'utilisateur où `partager` inscrit id, usage et date, sans réécriture ; recoupé par `valider --registre` | B5 |
| Plancher A7 | minimum de couverture des recherches d'un dossier : trois familles par carte de l'état, une discrimination par paire de candidates ; en dessous, dossier incomplet | A7 |
| Banc d'essai | épreuves de stabilité et de réexamen, avec corrigé indépendant et comparaison qui isole l'apport, par lesquelles une modification du skill doit passer avant de devenir une règle | `validation.md` §9 |
| Rabbit | construction ad hoc d'un codage (carte, strate, règle inventée en cours de route) ; dette ouverte jusqu'à sa résorption | `validation.md` §6 |
| Temporalité | déclaration d'une prévision : générique, programmée (échéance fixée par un texte) ou durée de vie propre ; hors générique, le taux générique (ρ4) est refusé | `validation.md` §1 |
| Vide clos | case Vide après trois recherches documentées sans équivalent : non concluant, comptée comme traitée | `equivalences.md` §3 |
| Support | ce sur quoi repose le mécanisme d'une garantie (*backing* de Toulmin) : un texte, une loi, une donnée ou un cas, jamais un autre argument ; daté, disponible à la date d'information | A6 |
| Répétabilité | accord d'un codeur avec lui-même, sur les mêmes cas, en deux passes aveugles séparées d'au moins `repetabilite_ecart_min_jours` ; à distinguer de la reproductibilité (accord entre codeurs, κ) | A4 |
| Procédure du jugement | manière dont une probabilité d'origine `jugement` a été produite : seul, compromis, simulation, analogies, autre | `validation.md` §1 |

La force F/f, l’intensité F/M/f d’une arête de la matrice et une grandeur physique sont trois notions
distinctes. Les deux premières ne fournissent pas une unité de mesure de la troisième.

