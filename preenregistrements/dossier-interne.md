# Dossier interne et juge informé : procédure écrite avant tout code

Statut : **validé par l'auteur le 2026-11-24 à 22 h 12**, avec l'amendement de la § 5 bis.

Décisions de l'auteur à l'origine de ce projet :
- 2026-11-24, ~21 h 45 : encadrer strictement l'IA, tout en lui laissant une marge suffisante dans des cas bien particuliers. « Le modèle va piocher dans l'actualité, mais il n'a pas accès aux ressources internes pour juger. »
- 22 h 04 : tout le processus sera automatisé ; l'information donnée à l'IA doit être standardisée, et compartimentée « pour que l'IA reçoive les bonnes informations au bon moment ».
- 22 h 06 : « Ok » pour écrire d'abord cette procédure.

Constat qui motive ce projet : le prototype `mise_au_point/dossier_interne.py` a été passé le 2026-11-24 sur les 18 questions binaires ouvertes du bot.
- Une seule question est couverte par une brique (Engie, autres accords).
- La brique des prix se tait sur le Brent : FRED publie avec environ 7 jours de retard, au-delà de la fraîcheur maximale de 5 jours.
- Le rattachement par pays seul fait entrer des compartiments hors sujet. Exemples : USA vers l'Afrique, l'Antarctique et le Groenland ; une source radioactive volée vers « nominations par intérim ».
- Le texte libre déverse tout en bloc.

## 1. Forme standard : un objet à clés fixes

Chaque dossier est un objet JSON de schéma fixe, versionné (`schema: "dossier-1"`). Ce n'est jamais du texte rédigé. Les clés sont toujours présentes, dans cet ordre :

```
question  : id, titre, échéance, horizon_jours, date_information, structure, famille
briques   : liste d'éléments, ou un silence
prix      : élément, ou un silence            (familles « prix » seulement)
carte     : liste de relations, ou un silence
questionneur : élément (toujours rempli)
sondes    : liste d'éléments, ou un silence
a_chercher : liste de faits que nos mesures réclament (pour l'étape de recherche)
empreinte : SHA-256 de l'objet sans ce champ
```

**Élément.** Chaque élément porte les champs suivants :
- `valeur` ;
- `unite` ;
- `source` (nom et URL publique) ;
- `date_donnee` (date de la dernière donnée utilisée) ;
- `n` (nombre de cas sur lequel la mesure repose) ;
- `regle_entree` (identifiant de la règle de la section 3 qui l'a admis) ;
- `perf`, quand elle existe : la perte de la brique contre la référence, mesurée hors échantillon, avec ses dates.

**Relation de la carte.** Une relation porte :
- `de`, `vers`, `effet`, `delai`, `force` ;
- `phrase` : la phrase sourcée de la fiche. C'est le seul texte rédigé admis ;
- `source` de la fiche ;
- `statut_verification` : vérifiée, série à revoir, ou non vérifiée.

**Silence.** Le silence est un code pris dans une liste fermée :
- `aucune_brique` ;
- `donnees_anciennes` (avec la date de la dernière donnée) ;
- `hors_domaine` (la brique reconnaît la forme mais pas le niveau, par exemple un ministre au lieu d'un chef d'État) ;
- `hors_carte` ;
- `rattachement_insuffisant` ;
- `sonde_inactive` ;
- `coefficient_nul`.

On ne retire jamais une rubrique. Le modèle doit pouvoir distinguer « on ne sait rien » de « la mesure s'est tue pour telle raison ».

## 2. Compartimenter dans le temps : ce que chaque étape reçoit

| Étape | Reçoit | Ne reçoit pas |
|---|---|---|
| Recherche (le modèle va sur l'actualité) | `question` et `a_chercher` seulement | les valeurs internes |
| Bras A (le modèle seul, scellé) | rien d'interne, comme aujourd'hui | tout le dossier |
| Briques, carte, sondes | du code pur, sans IA | — |
| Juge informé (après le sceau du bras A) | le dossier complet, la recherche, le p du bras A | — |

**`a_chercher`.** Ce sont des faits précis, tirés de silences réparables :
- `donnees_anciennes` sur un prix → « dernier cours de <actif> à la date la plus récente, avec sa source » ;
- famille accords sans relevé de guerre récent → « état des combats et dernière date de combat sourcée » (réutilise `guerres_releve.py`) ;
- maintien → « le titulaire est-il toujours en fonction, à quelle date, avec quelle source ».

Le code vérifie ce que la recherche rapporte avant tout usage, selon la même règle que `guerres_releve.py` : la date doit être passée et l'URL doit figurer dans la recherche. Si la vérification échoue, le fait est ignoré.

Le bras A reste aveugle. C'est la mesure de référence : sans lui, on ne peut pas savoir si le dossier aide ou nuit.

## 3. Compartimenter dans le contenu : règles d'entrée (appliquées par le code, jamais par le modèle)

- **R-brique.** La brique reconnaît la question (sa fonction `reconnaitre` ou `estimer` ne rend pas None) et ses données respectent sa fraîcheur. Sinon, on écrit le silence correspondant.
- **R-prix.** Il s'agit de la famille prix. On donne le dernier cours, sa date, la volatilité sur 30 jours et la source. Si le cours a plus de 5 jours, l'élément est remplacé par le silence `donnees_anciennes` et une entrée `a_chercher`. Une source de cours plus fraîche, gratuite et compatible avec les robots.txt sera proposée à part, à valider par l'auteur.
- **R-carte.** Un compartiment n'entre que s'il est rattaché par l'**objet** de la question : un mot de l'objet (`ecosysteme_objet`) ou une trace de série qui porte sur cet objet. Le pays seul ne suffit jamais. Une relation n'entre que si elle vise un compartiment admis et que son délai tient dans l'horizon. On en garde au plus 5, par force décroissante. Si aucun compartiment n'est admis par l'objet, on écrit le silence `rattachement_insuffisant`.
- **R-questionneur.** Toujours. On donne la part de oui des questions résolues de même structure (`structures_questions`) si n ≥ 20, sinon celle de tout le corpus. On indique n et la période.
- **R-sonde.** La sonde est active, son coefficient du moment est non nul, et elle lit la question. Sinon, on écrit le silence correspondant.

## 4. Table d'aiguillage par famille

La famille est fixée par la première brique qui reconnaît la question, dans l'ordre de la chaîne actuelle du bot. À défaut, c'est la structure de la question.

| Famille | Rubriques consultées | `a_chercher` possibles |
|---|---|---|
| prix (seuils) | briques, prix, carte, questionneur | dernier cours |
| événements comptés | briques, carte, questionneur | dernier compte |
| maintien | briques, questionneur, carte | titulaire en fonction |
| escalade, accords, cessez-le-feu, tenue | briques, carte, questionneur | état des combats |
| banque centrale | briques, questionneur | date de la prochaine réunion |
| rencontres, sommets, justice | briques, questionneur | calendrier annoncé |
| sans famille | questionneur, carte (si R-carte admet), sondes | aucun |

Pour une question sans famille, le dossier porte la mention fixe « aucune mesure interne : marge réservée aux faits nouveaux sourcés ».

## 5. Le juge informé : réponse contrainte

Le juge rend un objet JSON fermé :
- `decision` : « mesure » (garder la probabilité issue des briques, ou celle du pipeline sans brique), ou « ecart » ;
- si `decision` vaut « ecart » :
  - `motif` dans la liste fermée : `fait_nouveau_source`, `brique_hors_domaine`, `critere_resolution` ;
  - `preuve` : l'URL et la date pour un fait nouveau, ou la phrase du critère de résolution ;
  - `p_juge`.

Le code borne `p_juge` au plafond de la marge autour de la mesure. Il rejette l'écart si le motif n'est pas dans la liste, ou si la preuve n'est pas vérifiable selon la règle de la section 2. En cas de rejet, c'est la mesure qui est postée.

### 5 bis. Fait nouveau sourcé : corroboration et force de la preuve

Décision de l'auteur, 2026-11-24, 22 h 12 : une source isolée est un risque. Le fait doit se retrouver plusieurs fois, et la force de la preuve dépend de la source.

Pour le motif `fait_nouveau_source`, `preuve` est une **liste** de sources. Chaque source porte une URL et une date. Le code les classe selon des critères objectifs, jamais au jugement du modèle :
- **Primaire** : le domaine appartient à l'acteur du fait. Cela comprend :
  - un domaine gouvernemental ou institutionnel (.gov, .gouv.fr, .gob, .gc.ca, .gov.uk, .europa.eu, .int) ;
  - une banque centrale, une cour ou une organisation internationale ;
  - le domaine de l'entreprise nommée dans la question ;
  - les domaines des sources déjà citées dans les fiches et les briques.
- **Agence** : une agence de presse mondiale, prise dans une liste fermée : Reuters, AP, AFP, Bloomberg, Xinhua, Kyodo, ANSA, EFE, dpa.
- **Autre** : tout le reste.

**Indépendance.** Deux sources ne comptent pour deux que si les trois conditions suivantes sont réunies :
- leurs domaines enregistrables diffèrent ;
- elles ne reprennent pas la même dépêche. Le code ouvre la page, en respectant robots.txt et sans rien garder du texte, et cherche la mention d'une agence (« (Reuters) », « AFP », « Associated Press »…). Deux pages qui créditent la même agence comptent pour une seule ;
- chacune figure dans la recherche et a une date passée (règle de la section 2).

Une page inaccessible ne compte pas.

**Force et marge** (le plafond de la marge vaut 10 points, décision de l'auteur) :

| Force | Condition | Marge admise |
|---|---|---|
| forte | 1 primaire et au moins 1 autre source indépendante, OU au moins 3 sources indépendantes dont 2 agences | 10 points |
| moyenne | au moins 2 sources indépendantes dont au moins 1 agence ou 1 primaire | 5 points |
| insuffisante | tout le reste, dont une source primaire seule et toute source « autre » seule | écart rejeté, on poste la mesure |

Le classement et l'indépendance de chaque source sont scellés dans le journal. On pourra ainsi mesurer après coup si la force prédit la qualité des écarts.

## 6. Journal et contrôle

- Le dossier envoyé est scellé dans `registre/journal-juge.jsonl`, avec son empreinte, la réponse du juge, la probabilité postée et le p du bras A.
- Arrêt et amplification suivent la même règle que pour les sondes (e-valeurs), calculée sur les questions résolues :
  - log E = Σ log(p_posté(issue) / p_mesure(issue)) ;
  - log E ≤ −ln 20 : la marge du juge est fermée (on poste la mesure) ;
  - log E ≥ ln 20 : la marge est élargie selon la décision de l'auteur.
- Tests :
  - chaque rubrique respecte sa règle d'entrée (une question qui ne cite qu'un pays ne fait entrer aucune relation de la carte) ;
  - le bras A ne voit aucune clé du dossier ;
  - un écart sans motif admis est rejeté ;
  - le schéma est complet (aucune clé manquante).

## 7. Choix de l'auteur (2026-11-24, 22 h 12 : « Je valide le reste »)
1. **Poids des briques** : quand une brique s'applique, elle sert de base (le mélange au quart est abandonné pour ces
   questions) ; le juge n'agit que dans la marge.
2. **Plafond de la marge** : 10 points, modulé par la force de la preuve (§ 5 bis) ; élargissement seulement par la
   règle des e-valeurs et décision de l'auteur.
3. **Motifs d'écart** : les trois de la § 5 ; « fait nouveau sourcé » soumis à corroboration (§ 5 bis).
4. **Source de prix fraîche** : à chercher (gratuite, robots.txt respecté) et à soumettre avant usage.

## Limites déclarées

- Les briques couvrent aujourd'hui peu des questions ouvertes (1 sur 18 la semaine du 2026-11-24). Sur la plupart des questions, le dossier se réduira au biais du questionneur et à quelques silences.
- Le juge est un modèle de langue. Sa marge est bornée et contrôlée, mais pas éliminée.
- Conflit d'intérêts déclaré : le modèle qui rédige cette procédure est un modèle d'Anthropic.

## Mise en œuvre (0.10.510, 2026-11-24)

Fichiers :
- `dossier_interne.py` : schéma, règles d'entrée et aiguillage ;
- `sources_preuve.py` : § 5 bis ;
- `juge.py` : consigne fermée, bornes et règle d'arrêt ;
- `alphabet_bot.py` : faits demandés ajoutés à la recherche, brique en base, juge après le sceau du bras A, journal `registre/journal-juge.jsonl` ;
- workflow de score : `python juge.py` écrit `registre/juge-etat.json`.

Le juge s'éteint avec `ALPHABET_JUGE=0`.

Précisions de R-carte, écrites au moment du code :
- les « termes de la question » sont les termes des listes validées (`listes/valides.txt`, `proposes-rattachement.txt`) ;
- un terme qui est un nom de pays ou un gentilé ne rattache jamais seul.

Passage sur les 18 questions ouvertes du 2026-11-24 :
- le rattachement par pays a disparu ;
- deux bruits restent, qui viennent des listes de mots validées et non du dossier : « confirmed » mène à « nominations par intérim » (sources radioactives volées), et « agreement » mène à « gisements de la dette émergente » (Engie). Leur correction relève des listes, donc de l'auteur.

Source de prix fraîche (§ 7, point 4) : API Ninjas, validée par l'auteur le 2026-11-24 à 22 h 50 (`cours_frais.py`, clé `API_NINJAS_KEY`) ; dernier règlement seulement, volatilité gardée sur FRED, jamais de regard vers l'avant.
