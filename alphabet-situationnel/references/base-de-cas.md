# Alphabet situationnel — Base de cas (couche 3)

> Version : 0.7.64

> Format, codage et contrôles. `valider` et `calculer` appellent le même validateur. Une base valide
> syntaxiquement n'est pas une base factuellement certifiée. Règles : B1–B5.

---

## 1. Rôle et constitution

La base contient des observations datées, sourcées et codées. Choisir les configurations **avant**
de connaître les issues, puis échantillonner les cas dans une population et une période définies,
y compris ceux sans événement. Une sélection de crises saillantes ne représente pas une fréquence.
Commencer par une strate et quelques événements opérationnels ; comparer la référence seule et le
modèle complet. Ne pas remplir artificiellement toutes les cases de l'alphabet.

Trois statuts : `actif`, admissible après contrôles ; `proposition`, recodage complet contrôlé comme
un cas actif mais dont les sources n'ont pas encore été lues (`sources_verifiees: false`,
`motif_proposition` requis), exclu des calculs ; `archive_a_revoir`, conservé mais exclu de tout
calcul et contrôlé seulement comme archive lisible. Une proposition devient active quand l'auteur a
lu ses sources : `sources_verifiees: true`, `statut_donnees: actif`. Les quatre fiches de
`assets/cas-reels.jsonl` sont des archives (0.6.8) : rejeux codés avant les règles courantes, conservés
comme trace ; leur témoignage original est dans `assets/cas-reels-originaux.jsonl` (`feuille-de-route.md`,
étape 2). Les 40 cas d'exemple sont fictifs et demandent `--demo`.

---

## 2. Fiche de cas

Exemple entièrement fictif, au schéma courant (JSONL : une ligne par cas) :

```json
{
  "id": "C-0041-S07",
  "version_regles": "0.7.0",
  "titre": "Cas fictif 1",
  "strates": [
    6,
    7
  ],
  "fenetre": "3 mois",
  "sequence": [
    {
      "date": "2005-04",
      "etat": "[2005-04 | 3 mois] CONTRAINTE@6[F] + POLARITÉ@7[F]",
      "mots": [
        {
          "carte": "POL",
          "strate": 7,
          "intensite": "F",
          "fait": "Fait fictif n° 1 remplissant un marqueur local de POLARITÉ (strate 7)",
          "source": "Source fictive n° 1 ; source fictive n° 1 bis, indépendante de la première (exemple construit)",
          "corroboration": "independantes",
          "classe_source": "contemporain",
          "passage": [
            {"localisation": "source fictive n° 1, § 3", "relation": "soutient"},
            {"localisation": "source fictive n° 1 bis, p. 2", "extrait": "extrait court, fictif", "relation": "soutient"}
          ],
          "contre_observation": "Contre-observation fictive (marginale)",
          "portee": "marginale",
          "a6": "POLARITÉ@7 : CONTRAINTE → (deux camps nommés, pas une règle qui retire des options) ; SEUIL → (aucun passage irréversible daté)",
          "test": "pistolet",
          "garantie": {"mecanisme": "les deux blocs se définissent l'un par l'autre et organisent les votes", "support": {"type": "texte", "reference": "ouvrage fictif sur la formation des blocs (exemple de format)", "disponible_le": "2000-01-01"}, "attendu": "alignements exclusifs : rejoindre un bloc écarte de l'autre", "contredirait": "une troisième position stable ou des alignements croisés durables"},
          "option": {"acteur": "les États tiers", "avant": "rester non alignés", "apres": "choisir un bloc pour obtenir un soutien"},
          "objet": "objet simulé C-0001-GEO strate 7"
        },
        {
          "carte": "CTR",
          "strate": 6,
          "intensite": "F",
          "fait": "Fait fictif n° 2 remplissant un marqueur local de CONTRAINTE (strate 6)",
          "source": "Source fictive n° 2 (exemple construit)",
          "contre_observation": "Contre-observation fictive (marginale)",
          "portee": "marginale",
          "a6": "CONTRAINTE@6 : SEUIL → (options retirées, aucun nouvel état) ; HIÉRARCHIE → (règle, pas rang) ; POLARITÉ → (règle, pas deux pôles) ; INCERTITUDE → (option fermée, non laissée ouverte) ; TRACE·MÉMOIRE → (plafond décidé, pas héritage)",
          "objet": "objet simulé C-0001-GEO strate 6"
        }
      ],
      "questions": [
        {"question": "Les votes des États tiers s'alignent-ils de façon exclusive sur l'un des deux blocs ?", "si_oui": "POL@7", "si_non": "indetermine",
         "resolution": "votes nominatifs publiés au registre fictif sur la fenêtre",
         "justification": {"oui": "des alignements exclusifs datés sont l'attendu de la garantie de POLARITÉ"},
         "statut": "ouverte"},
        {"question": "Quel texte fixe le plafond, et à quelle date entre-t-il en vigueur ?", "type": "documentation", "carte": "CTR@6",
         "manque": "la date d'entrée en vigueur : l'annonce du plafond ne suffit pas", "resolution": "journal officiel fictif"}
      ],
      "liaisons": [],
      "positions": null,
      "disponible_le": "2005-04",
      "retraits": []
    },
    {
      "date": "2005-07",
      "etat": "[2005-07 | 3 mois] CONTRAINTE@6[F] + POLARITÉ@7[F] + RÉSEAU@6[f]",
      "mots": [
        {
          "carte": "RES",
          "strate": 6,
          "intensite": "f",
          "fait": "Fait fictif n° 4 remplissant un marqueur local de RÉSEAU (strate 6)",
          "source": "Source fictive n° 4 (exemple construit)",
          "contre_observation": "Contre-observation fictive (marginale)",
          "portee": "marginale",
          "objet": "objet simulé C-0001-GEO strate 6"
        }
      ],
      "liaisons": [],
      "positions": null,
      "retraits": [],
      "disponible_le": "2005-07"
    },
    {
      "date": "2005-10",
      "etat": "[2005-10 | 3 mois] CONTRAINTE@6[F] + HIÉRARCHIE@7[f] + POLARITÉ@7[F] + RÉSEAU@6[f]",
      "mots": [
        {
          "carte": "HIE",
          "strate": 7,
          "intensite": "f",
          "fait": "Fait fictif n° 6 remplissant un marqueur local de HIÉRARCHIE (strate 7)",
          "source": "Source fictive n° 6 (exemple construit)",
          "contre_observation": "Contre-observation fictive (marginale)",
          "portee": "marginale",
          "objet": "objet simulé C-0001-GEO strate 7"
        }
      ],
      "liaisons": [],
      "positions": null,
      "retraits": [],
      "disponible_le": "2005-10"
    }
  ],
  "issue": {
    "date": "2006-01",
    "etat": "[2006-01 | 3 mois] CONTRAINTE@6[F] + HIÉRARCHIE@7[f] + RÉSEAU@6[f]",
    "mots": null,
    "liaisons": [],
    "positions": null,
    "retraits": [
      {
        "mot": "POLARITÉ@7",
        "fait": "Fait fictif : POLARITÉ n'est plus observé (exemple construit)",
        "source": "Source fictive (exemple construit)"
      }
    ],
    "evenement_cle": "",
    "disponible_le": "2006-01"
  },
  "sans_evenement": false,
  "codage": {
    "mode": "manuel",
    "codeurs": [
      {"id": "codeur-1", "role": "humain"}
    ],
    "regle_declenchement": null,
    "debut": "2026-10-29",
    "accord": "exemple construit",
    "independants": false,
    "au_moins_un_humain": true
  },
  "usage": "test",
  "usage_fige_le": "2026-10-29",
  "notes": "EXEMPLE CONSTRUIT — données fictives, ne pas utiliser pour prévoir",
  "fictif": true,
  "statut_donnees": "actif"
}
```

| Champ | Exigence |
|---|---|
| `id` | C-NNNN-SNN ; stable, fixé avant codage ; `id_legacy:true` seulement pour anciens identifiants conservés |
| `version_regles` | même version mineure que la version courante pour un cas actif (0.5.x en 0.5.0) ; un correctif ne force pas le recodage, car `valider` applique les règles courantes à chaque fiche ; ancienne version mineure conservée dans une archive |
| `strates` | entiers uniques 1–13, couvrant les strates de tous les états |
| `fenetre` | durée strictement positive ; même fenêtre dans toutes les phrases |
| `sequence`, `issue` | au moins un état avant l'issue, avec dates de fiche et de phrase identiques |
| `date`, `disponible_le` | date de l'observation, puis date réelle à laquelle ses preuves sont accessibles |
| `mots` | nouveaux mots, changements F/f ; premier état entièrement documenté ; null si aucun changement ; [] interdit |
| `objet` | périmètre concret de chaque mot documenté ; nécessaire au contrôle humain des incompatibilités |
| `intensite` | F/f doit égaler la phrase ; il s'agit de qualité d'ancrage (A6), pas de grandeur physique |
| `fait`, `source`, `contre_observation` | texte renseigné, pertinent ; la contre-observation dit aussi où l'on a cherché |
| `portee` | portée de la contre-observation (A7) : `marginale`, `substantielle`, `dominante` ou `aucune` ; `dominante` interdit le mot ; `substantielle` exige `intensite` f et `force_initiale` F (un mot déjà f est rejeté) |
| `force_initiale` | `"F"` seulement avec une portée substantielle ; sur un mot qui persiste, admis seulement s'il était F, ou déjà rétrogradé depuis F, à l'état précédent |
| `garantie` | requis pour F (cas réel) : `mecanisme`, `attendu`, `contredirait` (A6), `contredirait` différent d'`attendu` ; forme type dans chaque fiche de `cartes.md`. **Depuis 0.7.10** (fiche de cette version ou après, et tout dossier) : `support` `{type: texte\|loi\|donnee\|cas, reference, disponible_le}`, sur quoi repose le mécanisme ; `argument` refusé ; `disponible_le` au plus tard à la disponibilité de l'état (protocole A6, « Support ») |
| `option` | requis pour F (cas réel) : `acteur` (« le système » admis), `avant`, `apres` différents (pertinence, O1) |
| `questions` | requis au premier état non nul d'un cas réel (cas fictif exempté) : liste non vide, dont au moins une question de **discrimination** `{question, si_oui, si_non}` ; `si_oui` et `si_non` sont deux CARTE@strate **différents**, ou une carte et `"indetermine"` (« non A » ne vaut pas « B » : la réponse laisse le codage ouvert), l'une au moins présente dans l'état. Une question dont les deux réponses mènent à la même carte, ou toutes deux à l'indétermination, est décorative et refusée (abduction, `grammaire.md` §7). **Cas réel (0.7.2)** : chaque question porte `resolution` (l'observation et la source qui y répondraient) ; une question de discrimination porte `justification` `{oui, non}`, une phrase par branche menant à une carte (pourquoi cette réponse l'établit), les deux différentes. Facultatif : `type: "documentation"` avec `carte` (dans l'état) et `manque` (la preuve qui fait défaut à l'ancrage), qui documente sans départager ; `statut` = `ouverte`, `partielle`, `resolue` (avec `reponse` oui/non) ou `presuppose_invalide`, chacun sauf `ouverte` avec sa `preuve` |
| `passage` | requis pour F d'un cas réel **actif** (0.7.2) ; contrôlé s'il est fourni ailleurs : objet ou liste `{localisation, relation, extrait?}`. `localisation` dit où le fait se lit (page, section, paragraphe, horodatage) ; `relation` = `soutient`, `partiel`, `contredit`, `absent_de_la_piece` (élargir la lecture) ou `non_soutenu` (retirer l'ancrage) — `insuffisant` est refusé depuis 0.7.11, il confondait ces deux cas ; `extrait` facultatif, 300 caractères au plus ; `forme` facultative (0.7.16) : `prospective`, `retrospective`, `attribuee` ou `inclassable` — un passage qui soutient dans une pièce autre que prospective ne compte pas pour F (`protocole.md` A6, « Forme de la pièce »). F exige un passage qui **soutient** le fait tel qu'il est écrit (« peut être activé » ne soutient pas « a été activé ») ; un soutien partiel donne f ; une pièce qui contredit va en contre-observation (A7), une pièce qui ne permet pas de conclure n'ancre rien ; `corroboration: "independantes"` exige deux passages qui soutiennent. Aucun effet sur le calcul (contrôle affirmation–passage, `protocole.md` A6) |
| `corroboration` | requis pour F d'un cas réel **actif** (une proposition le reçoit à son activation) : `"independantes"` si le fait repose sur au moins deux sources indépendantes, nommées dans `source` et séparées par « ; » ; `"unique"` sinon, admis seulement pour une source primaire (texte officiel, donnée publiée) et signalé dans « À vérifier auprès de vous » ; un fait repris d'un seul relais secondaire s'ancre en f (0.7.1). **Depuis 0.7.11** (fiche de cette version ou après, et tout dossier) : `"independantes"` exige `independance` = `{critere: origine\|producteur\|transmission, motif}`, ce qui rend les pièces indépendantes ; interdit avec `"unique"`. Aucun effet sur le calcul (qualité de l'information, 0.6.6) |
| `source_url`, `date_consultation` | facultatifs (0.7.1) : adresse http(s) de la source et date de consultation (AAAA-MM-JJ), contrôlées si présentes ; recommandés pour tout cas réel, ils permettent à un tiers de relire la source |
| `classe_source` | requis pour tout mot documenté d'un cas réel **actif** et d'un dossier de lecture (0.7.5) : `contemporain` (source produite au moment des faits), `historiographie` (analyse postérieure), `memoire` (témoignage, récit rétrospectif). Une base codée après coup peut encoder la reconstruction des récits (Bartlett 1932) et la sélection de ce que les sources rapportent (Weidmann 2016) plutôt que les situations ; le champ permettra de comparer les taux de transition par classe. Aucun effet sur le calcul |
| `test` | requis pour F de cas réel : `pistolet` ou `double` (fait suffisant) ; facultatif pour f (`paille`, `cerceau`, aussi admis) ; tests de process tracing, `protocole.md` A6 (0.7.0) |
| `a6` | requis pour F : chaque voisine de `cartes.md`, verdict `→` ou `+`, justification non vide ; contrôle complet sur cas réel, cas fictif exempté |
| `retraits` | exactement les mots disparus, chacun avec fait et source |
| `liaisons`, `preuves_liaisons` | mots existants, types compatibles avec les strates, une preuve par liaison |
| `preuves_qualificatifs` | dictionnaire CARTE@strate → ligne Q pour chaque mot qualifié |
| `positions`, `preuve_positions` | null ou tient/bouge/manque avec ≥3 mots, contraintes de présence et preuve |
| `sans_evenement` | `true` seulement si aucun mot n'apparaît, ne disparaît ni ne change de force sur toute la séquence (B4) |
| `codage` | `recodage` : qui a proposé le codage quand ce n'est pas le codeur (un modèle, par exemple) ; s'il est renseigné, un cas **actif** exige `recodage_confirme` `{par, date}` : un codeur humain nommé, pas le modèle, a relu ce qui a été proposé (0.6.7). **Codeurs** (0.6.14) : chacun `{id, role}`, `role` = `humain` ou `modele` ; un cas réel actif en
compte au moins un humain, et `recodage_confirme.par` est l'`id` d'un codeur humain de la fiche, pas un
nom libre. Les fiches fictives et les archives gardent la forme courte (chaîne). Puis : mode, codeurs distincts ; `independants` et `au_moins_un_humain` booléens s'ils sont présents ; si deux codeurs : indépendance et au moins un humain explicitement attestés |
| `fictif` | booléen ; tout cas fictif est exclu hors --demo et de V4 |
| `sources_verifiees` | true pour un cas réel actif ; ne pas déclarer sans avoir consulté les sources |
| `statut_donnees` | actif, proposition (exige `motif_proposition` et `sources_verifiees: false`) ou archive_a_revoir (exige `motif_archive`) ; seuls les cas actifs entrent dans les calculs |
| `usage` | partage par empreinte ; les cas test ne contribuent jamais aux estimations |
| `usage_fige_le` | requis pour toute fiche hors archive (0.7.4) : date à laquelle le partage a été fixé, recopiée de la sortie de `partager`, qui l'inscrit au registre `partage.jsonl` (fichier de l'utilisateur, jamais réécrit) ; un partage non daté rend la fiche non valide. `valider --registre partage.jsonl` recoupe chaque cas réel avec le registre, qui fait foi |
| `codeurs[].signe_suffisant`, `declare_le` | facultatifs (0.7.6), à remplir au second codeur (étape 5) : ce que le codeur tient, **avant tout codage**, pour un signe suffisant d'une carte (`declaration`, `execution` ou `trace`), et la date de cette déclaration, ≤ `codage.debut`. Auto-déclaration, jamais attribution ; elle permettra de comparer l'accord entre codeurs de même déclaration et de déclarations différentes |
| `codage.debut` | requis pour un cas réel (0.7.4) : date du début du codage ; `usage_fige_le` ≤ `codage.debut` (B5 : partage fixé avant codage). Le partage n'a pas à précéder le premier état : un cas historique a des états anciens et un partage récent |

Deux états consécutifs sont espacés d'une fenêtre **calendaire exacte**. Les mois finissant plus tôt
rabattent le jour au dernier jour du mois. Une transition irrégulière n'est pas un pas régulier ;
la conserver en archive ou la rééchantillonner explicitement avec des observations vérifiables.
Les cas actifs sans mot nouveau peuvent porter `mots:null` ; une archive n'est contrôlée que comme
archive lisible, jamais présentée comme « active recevable ».

**Plusieurs mots dans un état ne font pas une cause conjointe (0.7.22).** Une fiche qui code ensemble
deux cartes, ou un `mecanisme` de `garantie` qui en mobilise deux, décrit une co-activation. Le calcul
additionne leurs effets dans l'a priori ; seule la fréquence des homologues peut porter la trace d'une
interaction, sans la nommer. Voir `dynamiques.md`, paragraphe « Additif, pas configurationnel », près de
la loi de composition.

**Carnet de faits et grille des sources (0.7.32).** Avant tout codage, `recolter` ajoute au carnet (JSONL) un fait
observé : texte, source, adresse, date du fait, date de disponibilité, date de consultation, `classe_source`, et,
facultatifs, l'indépendance et la **grille à deux axes** du renseignement (code de l'Amirauté, STANAG 2511) :
`fiabilite_source` de A (sûre) à E (peu sûre), F (non évaluable), et `credibilite` de 1 (confirmée par d'autres
sources) à 5 (improbable), 6 (non évaluable). Le carnet ne code rien : ni carte, ni strate, ni force. `recolter
--jusqu-au` liste les faits disponibles à une date d'information, brouillon d'un dossier qui ne peut citer que ce qui
était connu. Les deux champs de la grille sont admis dans un mot de fiche ou de dossier ; s'ils sont remplis, **un
ancrage F exige une source A à C et une information 1 à 3** (`valider`, `dossier`). Ils n'ont aucun effet sur le
calcul. Ils précisent, sans la remplacer, la règle de `corroboration`. **Depuis 0.7.48**, `--archive` déclare un instantané Wayback de la pièce
(`archive`, `archive_le` lu dans l'adresse) ; `disponible_le` ne peut pas précéder la date de l'instantané, et
`--jusqu-au` liste les faits `sans_archive` (`validation.md` §26).

---

## 3. Coder un cas historique (mode CODER)

1. Définir configuration, population, fenêtre et règles d'issue avant sélection des exemples.
2. Attribuer l'id ; exécuter `partager` (dans le dossier de travail : il inscrit l'id, l'usage et la date
   au registre `partage.jsonl`) ; recopier `usage_fige_le` ; noter `codage.debut` ; publier le registre.
3. Réunir les faits avec dates d'événement **et de disponibilité des sources**.
4. Coder chaque état à partir des seules informations alors disponibles ; identifier les objets.
5. Documenter nouveaux mots, révisions de confiance et retraits, puis preuves des liaisons et Q.
6. Un second codeur reçoit les faits, jamais le premier codage ; enregistrer son identité et son rôle.
7. Exécuter `valider`. Toute fiche active invalide bloque le calcul ; ne pas masquer l'erreur.
8. Si source absente, temporalité ambiguë ou règle ancienne non recodée : archiver avec motif.
9. **Traceback (0.6.0).** Nommer ce qui, absent de l'alphabet au départ, a été nécessaire pour rendre
   le cas codable (une carte, une strate, un qualificatif, une règle), ou écrire « rien ». Une
   construction nécessaire s'inscrit dans `assets/rabbits.jsonl`, avec le fait daté qui la rendait
   nécessaire ; une difficulté de lecture n'en est pas une. Trois occurrences indépendantes d'une même
   construction ouvrent A2.

Une validation structurale ne remplace pas A6/A7. Une contre-observation substantielle impose sa
baisse de confiance ; ne pas écrire « substantielle mais F maintenu ». Les observations nouvelles
ne modifient jamais rétroactivement un journal déjà publié.

**Coder une bifurcation après coup (0.7.20, Grossetti 2004, ch. 4 §2).** Quatre précautions de méthode,
qui ne changent aucun champ de la fiche.

- **Nommer les issues qui ne se sont pas produites.** Pour qu'un état soit lu comme un franchissement
  contingent plutôt que comme une suite obligée, il faut des alternatives : plusieurs issues assez
  équivalentes, et la raison de penser qu'elles étaient les seules. Granovetter et McGuire en trouvaient
  trois pour l'industrie électrique américaine, à partir des débats de l'époque et des données. Deux
  sources possibles : la controverse entre acteurs, ou l'analyse des données quand une décision a été prise
  sans débat. Le champ `option` (`avant`, `apres`) porte l'issue retenue ; les autres s'écrivent dans les
  notes de codage, avec leur source. Sans elles, le codage tombe dans l'un des deux pièges que Grossetti
  nomme : tout est singulier, ou tout devait arriver. Un résultat présenté **après coup** comme
  « parfaitement inévitable » (son exemple, dans l'article de 2006 : le référendum de 2005) est un signal d'alerte, non une preuve.
- **Témoignages (`classe_source: memoire`).** Les récits rationalisent, et pas tous dans le même sens : un
  créateur d'entreprise raconte sa stratégie, un artiste le « hasard des rencontres ». Ils ramènent aussi
  tout à soi et sous-estiment l'action des autres. Contre-mesures : poser des questions concrètes (faits,
  noms, dates) plutôt que demander un commentaire ; relancer à chaque choix présenté comme naturel (« aviez-
  vous envisagé d'autres solutions ? ») ; croiser les témoignages et les sources écrites. C'est la règle de
  `corroboration` appliquée à la mémoire.
- **Où commencer la fenêtre.** Remonter d'une bifurcation à la précédente n'a pas de fin. Grossetti
  s'arrête « lorsque le problème change suffisamment de nature » : quand remonter plus loin poserait une
  autre question. Le premier état d'un cas est ce point d'arrêt, déclaré ; ce n'est pas une origine.
- **Le ralenti n'entre pas dans une fiche.** La méthode du « ralenti » (Suter 1997) détaille les moments
  supposés décisifs et résume les autres. Une fiche ne le permet pas : ses états sont séparés de fenêtres
  égales (B1). Le ralenti se fait dans les notes de codage ; si un moment exige un grain plus fin, c'est
  un autre cas, à une autre fenêtre, et il n'est pas homologue du premier. La continuité entre le moment et
  ses conséquences doit, elle, se montrer pièce par pièce (`liaisons`, `preuves_liaisons`) : « la chaîne
  causale peut comprendre des moments d'imprévisibilité mais elle ne doit pas se rompre ».

---

## 4. Cas sans événement (B4)

Inclure les cas sans événement selon un plan représentatif et consigner la population de référence.
Le repère d'un tiers à défaut d'estimation est une alerte de collecte, pas un quota à imposer aux
données. Sans cas sans événement dans les homologues, ρ0 est interdit. Le champ ne remplace pas
les issues explicites des transitions : celles-ci sont calculées depuis les états.

**Le risque sans conséquence (0.7.20).** Grossetti range dans une case à part les séquences très
incertaines restées sans effet durable : l'accident « évité de justesse », le couple qui a failli se
séparer, l'offre d'emploi envisagée puis laissée (`dynamiques.md`, paragraphe sur le livre de Grossetti).
Ce sont les cas qu'une reconstruction rétrospective oublie le plus, parce que rien ne s'y est « passé ».
Ils comptent comme cas sans événement pour l'événement qui ne s'est pas produit. Le drapeau
`sans_evenement: true` reste plus strict : il exige qu'aucune apparition, disparition ni changement de
force ne survienne sur toute la séquence ; une approche du seuil qui change une force ne le permet pas.

---

## 5. Partage apprentissage / test (B5)

SHA-256 de l'id : premier caractère 0–4 → test (5/16), sinon apprentissage. Le validateur impose
ce partage ; ne pas renuméroter pour changer de lot. Le hasard du partage ne supprime pas les fuites
entre épisodes liés ni les fuites temporelles. Une évaluation doit aussi regrouper les épisodes liés
et réserver une période postérieure. Les fenêtres chevauchantes d'un même événement restent dans
le même ensemble scientifique, même si les identifiants doivent être revus avant toute collecte.

---

## 6. Contrôles de qualité de la base

| Contrôle | Action |
|---|---|
| Sources non consultées | archive, pas apprentissage |
| Date d'issue ou disponibilité après la prévision | transition exclue, y compris de la fréquence de base |
| Plusieurs transitions d'un cas | poids total ≤1 avant décroissance temporelle |
| Double codage | ≥20 cas et ≥20 % dans la strate pour sortir du mode solo ; ne prouve pas κ |
| Accord par carte | `moteur.py accord --a --b --c --d` : publier la table 2×2 (a : les deux ancrent ; b : le premier seul ; c : le second seul ; d : aucun), pₒ, pₑ, κ et son intervalle (« indéfini » si pₑ = 1, jamais 0), PABAK = 2·pₒ − 1, les accords spécifiques positif et négatif, et **les deux** taux de manque b/(a+b) et c/(a+c). Examiner la **forme** des désaccords, pas seulement leur ampleur (Reidsma et Carletta 2008) |
| Prévalence | une carte est absente de la plupart des états (base d'exemple : 205 présences sur 1 888 décisions carte × état, 10,9 % ; huit cartes jamais présentes) : κ y sous-estime l'accord et devient indéfini à prévalence nulle (Feinstein et Cicchetti 1990 ; Byrt, Bishop et Carlin 1993). Les repères `kappa_min` 0,67 et `kappa_rapportable` 0,80 (Krippendorff, cité par Carletta 1996) s'appliquent donc à **PABAK**, et seulement si aucun codeur ne manque plus de `fnr_max` (20 %) des ancrages de l'autre : PABAK seul ne voit pas un codeur qui n'ancre jamais (0,908 pour 87 ancrages contre 0). Sous `accord_min_ancrages` ancrages, non estimable ; une carte que personne n'ancre est sans objet. Ce sont des résultats, pas des échecs |
| Répétabilité (0.7.10) | `moteur.py accord --repetabilite --ecart-jours N` : le même codeur recode à l'aveugle, dans un ordre tiré, des fiches qu'il a déjà codées ; mêmes statistiques que l'accord, lues « première passe / seconde passe » ; sous `repetabilite_ecart_min_jours` (30 j), non recevable (la seconde passe mesure la mémoire du codage). Publiée à part de κ |
| Cas futurs, test, archives | exclus des estimations |
| Cas fictifs | démonstration explicite seulement, jamais validation prospective |
| Référence documentaire absente | équivalent Proposé, confiance f au maximum |

---

## 7. Données personnelles

Appliquer les limites de `constitution.md` §6 : minimisation, pseudonymes des personnes privées,
pas de diagnostic ou décision individuelle à partir du score. Ne conserver que les faits nécessaires
et leur provenance ; ne pas transformer l'accord d'un codeur en consentement d'une personne citée.
