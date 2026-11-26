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

## Amendement du 2026-11-26 : brique hors domaine, contradicteur et terrain (écrit avant tout code)

Origine : Trump–Poutine (page 46751, question d'entraînement du 2026-11-25). La question acceptait « meet in person OR
talk on the phone » ; la brique « rencontres » (COLT, rencontres en personne seulement) l'a reconnue sur le mot « meet »
et a posté 0,049 à la place du raisonnement du modèle (0,90). Le juge disposait du motif « brique hors domaine » mais ne
voyait pas le domaine de la brique, et sa marge (10 points) n'aurait de toute façon permis que 0,15. Rustine posée le
jour même dans `rencontres_regle.py` (abstention sur appel ou échange à distance) ; elle sera retirée quand le mécanisme
général ci-dessous aura prouvé qu'il attrape seul ce cas.

Décisions de l'auteur :
- 10 h 49 : pas de disjoncteur mécanique ; « privilégier la réalité du terrain plutôt que la mesure, quand c'est contre
  intuitif ; c'est le rôle du contradicteur de dire ça, et du juge de le prendre en compte » ; il valide le reste des
  propositions (audit des briques, domaine donné au juge).
- 10 h 54 : « Oui, c'est bon » (brique hors domaine annulée ; marge de 30 points pour le terrain).
- 10 h 57 : corriger le biais quand il se présente, de façon générale, plutôt que des exceptions brique par brique.
- 11 h 08 : contradicteur appelé seulement quand une brique s'applique et diverge fortement du raisonnement — « c'est à
  tester », pour laisser le moins de place possible au hasard. Contrainte de l'auteur : chaque question coûte des crédits.

### A. Domaine déclaré
Chaque brique porte une phrase de domaine (ce qu'elle compte, ce qu'elle ne compte pas), écrite dans son module et
recopiée dans le dossier (`briques[].domaine`). Exemple : « rencontres en personne de chefs d'État ou de gouvernement ;
ne compte ni les appels, ni les envoyés, ni les ministres ».

### B. Déclenchement du contradicteur (à tester)
Le contradicteur n'est appelé que si (1) une brique s'applique et (2) |p_brique − p_raisonnement| ≥ S. Le seuil S n'est
pas fixé ici : il sera choisi par le test de la section E, puis soumis à l'auteur. Hors déclenchement, rien ne change.

### C. Rôle du contradicteur (après la mesure, avant le juge)
Il reçoit le titre, les critères de résolution, le domaine de la brique, la mesure et la recherche. Réponse fermée :
- `conforme` ;
- `hors_domaine` + citation exacte du titre ou des critères qui sort la question du domaine ;
- `contre_terrain` + liste de faits datés et sourcés (URL, date) qui contredisent la mesure.
Il ne donne pas de probabilité.

### D. Juge
Il reçoit le verdict du contradicteur. Deux changements :
- `brique_hors_domaine` admis (citation vérifiée par le code) : la brique est annulée et l'on poste le raisonnement du
  modèle, comme s'il n'y avait pas de brique ; pas de plafond, puisqu'il n'y a plus de mesure.
- nouveau motif `contre_terrain` : marge de 30 points au plus, exigeant au moins deux sources indépendantes et datées
  (règle de corroboration et force de la preuve de la § 5 bis).
Les deux restent sous la règle d'arrêt des e-valeurs (§ 6), calculée séparément par motif.

### E. Test avant branchement (une passe)
1. Audit sans modèle de langue : toutes les briques rejouées sur les questions résolues du corpus ; liste des
   déclenchements, des pertes, et des titres à risque (« or », négation, « any of », « at least one »).
2. Jeu de test : les déclenchements de l'audit dont la perte est la plus forte, plus autant de déclenchements à faible
   perte tirés au hasard (graine fixée), plus Trump–Poutine. Taille plafonnée à 40 questions (coût).
3. Pour chacun : raisonnement du modèle (bras A, modèle bon marché), puis contradicteur. On mesure : part des
   mauvaises reconnaissances attrapées (rappel), part des bonnes briques contestées à tort (fausses alertes), et perte
   log de la chaîne avec et sans contradicteur.
4. Branchement si la perte avec contradicteur est inférieure à la perte sans, et si les fausses alertes restent sous
   un quart. Sinon, on n'ajoute rien et on rapporte.

### E bis. Précision du test, écrite avant tout appel de modèle (2026-11-26, vers 11 h 45)
Raison : une recherche rétrospective sur des questions résolues fuit l'issue (ForecastGym, veille du 2026-11-18), et les
modèles peuvent connaître ces issues. Le test est donc scindé :
1. **Hors domaine, hors ligne, texte seul.** Le contradicteur ne reçoit que le titre, la famille, la phrase de domaine
   et la mesure ; aucune recherche. Jeu : les 21 déclenchements distincts de l'audit dont le titre porte une forme à
   risque (hors compétitions, dont la brique a changé de rôle le jour même avant le test), Trump–Poutine, et 15
   déclenchements sans forme à risque tirés au hasard (graine 20261126, hors compétitions). Étiquettes « hors domaine »
   posées par Claude sur les titres seuls, avant tout appel, dans `mise_au_point/banc_contradicteur_jeu.json`.
   Mesures : rappel (hors domaine attrapés) et fausses alertes (dans le domaine contestés). Critère : rappel ≥ 3 sur 4
   et fausses alertes ≤ 1 sur 4. Modèle : celui du contradicteur du bot (variable ALPHABET_CONTRADICTEUR), une passe.
2. **Contre le terrain, en ombre sur les questions vivantes.** Il ne peut pas se tester proprement sur le passé. Le
   contradicteur tourne dans le bot sur les questions où une brique s'applique ; son verdict est journalisé, sans effet
   sur la prévision, jusqu'à ce qu'assez de questions soient résolues pour le juger. L'application au juge (D) attend
   ce résultat et une décision de l'auteur.
Ce qui est branché sans attendre : la phrase de domaine dans le dossier (A), lue par le juge actuel.

### Résultat du banc hors domaine (une passe, 2026-11-26, run 45802865087, modèle azure_ai/grok-4.7)
- Rappel : 8 sur 8 hors domaine attrapés (Trump–Poutine compris), citations toutes vérifiées par le code.
- Fausses alertes : 6 sur 29 (0,21), sous le plafond d'un quart. **Critère tenu.**
- Les 6 contestations « à tort » : France, Royaume-Uni ou Allemagne frappe l'Iran (deux fois) ; occuper ou bloquer
  l'île de Kharg ; blocus ou « quarantaine » de Taïwan ; la Russie attaque ou envahit la Finlande ; Bitcoin descend à
  105 000 $ en août. Quatre d'entre elles se défendent (blocus, quarantaine et occupation ne sont pas des frappes ;
  plusieurs États attaquants joints par « or ») : les étiquettes de Claude étaient peut-être trop larges. Une est
  incohérente (Finlande contestée, Lettonie acceptée pour la même forme). Rien n'est réétiqueté après coup.
- Suite : le contradicteur reste en ombre pour le volet « contre le terrain » (E bis.2). L'application du verdict
  « hors domaine » au juge (annulation de la brique) attend la décision de l'auteur.
- **Branché (2026-11-26, 11 h 46, décision de l'auteur : « je valide ; c'est ce qu'on appelle un garde-fou utile ») :**
  le verdict « hors domaine » admis par le code annule la brique ; le bot poste son raisonnement, puis le juge agit
  comme sur une question sans brique. Si le contradicteur échoue ou ne répond pas, la brique reste appliquée. La
  rustine des appels dans `rencontres_regle.py` est gardée tant que le contradicteur peut faire défaut.

Copie figée datée par un tiers (Zenodo) de l'état du 2026-11-26, amendement et banc compris : DOI 10.5281/zenodo.24559290.
