# Bot Metaculus de l'alphabet situationnel

Version 0.10.100 · skill alphabet-situationnel 0.7.77 · auteur Othman Ben Brahim · licence MIT pour les fichiers du bot
(`LICENSE-alphabet` : `alphabet_*.py`, `score_registre.py`, `tests/`, workflows `*alphabet*`) ; le reste du dépôt est
le modèle de Metaculus, sous ses propres conditions. Résumé en anglais : [`ABSTRACT-alphabet.md`](ABSTRACT-alphabet.md).

Ce document décrit **le bot**. Le skill qu'il fait tourner (cartes, strates, moteur, règles de validation) est décrit
dans [`alphabet-situationnel/README.md`](alphabet-situationnel/README.md).

## En bref

Le bot prévoit des questions du tournoi FutureEval de Metaculus et pose une seule question de fond : **une lecture
structurelle de la situation (le skill) améliore-t-elle un simple taux de base ?** Pour chaque question binaire, il
calcule trois probabilités indépendantes, les scelle dans un registre avant l'échéance, poste l'une d'elles sur
Metaculus, puis les compare une fois la question résolue, avec le score logarithmique de Metaculus.

## Les trois bras

| Bras | Ce qui produit la probabilité | À quoi il sert |
|---|---|---|
| **A** | le modèle de langage seul (le raisonnement du bot modèle de Metaculus) | le témoin : ce qu'on obtient sans le skill |
| **B** | une classe de référence : « sur des situations comparables, combien de fois l'événement s'est produit » | le taux de base |
| **C** | le skill : lecture de la situation, puis calcul par le moteur du skill, à partir du taux de base B | C contre B = ce que la lecture apporte |

A est calculé et scellé **avant** toute lecture : il ne peut pas être influencé par B ou C.

## Le déroulé d'une question

1. **Question** : le bot récupère les questions ouvertes du tournoi (MiniBench par défaut).
2. **Bras A** : le modèle seul répond, comme le bot modèle de Metaculus. La réponse est scellée.
3. **Plan** : le modèle dit quel événement correspond au OUI, ce qu'il faut chercher pour le taux de base, et ce qu'il
   faut chercher pour la lecture. Le bot vérifie le plan et le renvoie une fois s'il est mal formé. La strate de
   l'événement est choisie **à l'aveugle** : le plan ne sait pas quelles strates le moteur chiffre (L7), pour que
   l'étiquette ne soit pas tirée vers celle qui ouvre le calcul.
4. **Bras B** : le bot lance les recherches de taux de base (moteur de recherche web) et retrouve sur Metaculus des
   questions **déjà résolues** d'apparence voisine (leur issue seulement : jamais les prévisions de la communauté).
   Le modèle en tire une fréquence sourcée et datée, ou déclare qu'il n'y a pas de base honnête ; il n'utilise les
   questions résolues que si au moins cinq comptent le même type d'événement. Une source postérieure à la date du jour
   est refusée, de même qu'une source qui se déclare « de mémoire ». **La classe de référence est d'abord définie une
   fois** (ce qui compte pour un cas, sur quelle population, quelle période) ; puis le comptage est fait **trois fois
   sur cette même classe, chaque fois sur une source différente des précédentes** (0.8.0 : avant, trois appels du même
   prompt rendaient trois fois le même chiffre). Chaque estimation rend aussi son calcul en arithmétique pure
   (`expression`) : **le code le refait**, et c'est la valeur de la formule qui est retenue (un écart de plus de 20 %
   avec le chiffre déclaré est marqué `calcul_corrige`) ; une source trop proche d'une source déjà prise est refusée. B est la vue médiane (une
   vraie vue, avec sa source : aucune moyenne fabriquée), et l'écart entre les trois est enregistré : c'est alors un
   écart de mesure, non un changement de classe.
   **Puits de données (0.7.0)** : avant de compter, le modèle choisit jusqu'à trois appels à des bases ouvertes (voir
   « Puits de données » plus bas). Leurs relevés datés rejoignent les résultats de recherche. Si une série mesure
   exactement le critère de résolution, le **code** compte combien de fenêtres de la durée de la question ont vu le
   seuil atteint. Si la série mesure **exactement** la grandeur du critère, **ce compte est le taux de base** ; la
   médiane des estimations du modèle reste en ombre (`p_modele`) (0.8.0 : le compte n'entre plus dans une médiane de
   vues d'une autre nature). Si elle mesure une grandeur **proche** (autre pays, mesure voisine, série plus large), le
   compte est montré à la **première** estimation seulement, qui le retient, l'ajuste en nommant l'écart, ou l'écarte
   (`usages_compte`) ; les deux autres restent aveugles, et leur médiane (`p_sans_ancre`) sert de mesure indépendante.
   Le compte est scellé à part (`p_compte`, `correspondance`) et scoré en ombre (`compte_sur_B`) contre une mesure
   qui ne le contient pas (`p_modele` ou `p_sans_ancre`). Une série de niveaux (taux, indice) ne se somme pas par mois
   ou par an, et « atteint » ou « franchit » exigent un seuil.
5. **Bras C** : le bot lance les recherches de lecture (12 au plus, les autres sont notées « non cherchées ») ; le
   modèle écrit un dossier à partir des seuls résultats ; le moteur du skill le juge et calcule. Un refus est renvoyé
   au modèle pour correction, deux fois au plus. **Le moteur reste juge : le bot ne fabrique aucun chiffre.**
   **Angles morts** : si la lecture n'ancre aucune carte alors que certaines candidates ont été écartées faute de
   recherche (`aucun_fait`, `non_cherchee`), le bot relance une fois des recherches ciblées sur elles (6 au plus),
   formées sur le phénomène que décrit leur marqueur, puis fait relire. L'état nul n'est accepté qu'ensuite, et il est
   qualifié : `structure_absente` (chaque candidate écartée sur pièces) ou `angle_mort` (il en reste une non vérifiée).
   Le lecteur décrit aussi, en une ou deux phrases et sans nommer de carte, la dynamique que montrent les faits
   (`dynamique_observee`, hors calcul ; une description qui nomme une carte est gardée mais signalée). Ce corpus servira,
   après évaluation, à chercher une structure qui manquerait à l'alphabet.
   **Contrôle d'attribution, sans modèle** (`attribution` au registre) : pour chaque carte ancrée, le bot vérifie que
   les extraits cités se retrouvent dans les résultats de recherche et que chaque nombre du fait y figure. Un mot qui
   échoue est « non attribué » ; un mot sans extrait ni nombre, « non vérifiable ». Diagnostic seulement : la lecture et
   le calcul ne changent pas.
6. **Choix du bras posté** (voir ci-dessous), commentaire public expliquant le choix, envoi à Metaculus.
7. **Registre** : une ligne scellée (SHA-256) avec les trois bras, et le dossier de lecture complet, enregistrés dans
   le dépôt par le workflow.

Pour les questions **non binaires** (numériques, choix multiples, dates), le bot se comporte comme le bot modèle de
Metaculus (bras A) et journalise sa prévision à part.

## Ce que le bot poste

| Situation | Bras posté |
|---|---|
| Le moteur du skill donne une probabilité | **C** |
| La lecture ne trouve aucune structure (« état nul »), y compris après la relance de ses angles morts | **B**, le taux de base non ajusté |
| Pas de taux de base honnête, question hors du champ du skill, lecture refusée, erreur | **A** |

Aujourd'hui, le skill ne chiffre que la géopolitique (décision L7 du skill). Hors de ce domaine, le bot enregistre le
taux de base B et poste A. Cette règle ne changera pas avant la levée de L7, sur mesures.

**Bras C exploratoire (0.9.0, décision d'auteur du 2026-11-08 ; skill `validation.md` §29).** Pour laisser sa chance
à l'alphabet hors de la géopolitique, le bot lit **aussi** chaque question binaire hors strate 7, et le moteur la
chiffre avec `--exploratoire` (L7 levée pour ce seul calcul). Ce chiffre est **scellé** au registre
(`bras.C.exploratoire` : statut, `p_C`, strate) et noté dans le commentaire comme « not the posted forecast » ; il
n'est **jamais posté** : le statut reste `hors_strate` et A est posté, y compris quand la lecture exploratoire est un
état nul (pas de B hors strate 7). Il est scoré **à part** (`C_exploratoire_sur_B`, au total et par strate), hors du
verdict principal, de la correction rétrospective, de la recalibration et de la condition 1 du §27. Un état nul
exploratoire ne donne pas de chiffre (pas de C = B). Coût : une lecture complète de plus par question binaire hors
strate 7. `ALPHABET_EXPLORATOIRE=0` pour couper.

**Correction du biais à la hausse, en ombre (0.9.1, décision d'auteur du 2026-11-08).** Le moteur ne fait que monter
la probabilité (multiplicateurs ≥ 1, décision 9 du skill) : sans correction, C ne peut gagner que sur les questions
résolues OUI. Deux corrections, scellées, jamais postées :

- **symétrique** (`bras.C.symetrique`, `p_C_symetrique`) : une candidate écartée parce que les faits la
  **contredisent** compte **contre** l'événement : elle divise la cote par le λ qu'elle aurait apporté (mêmes
  multiplicateurs, même matrice, même plafond, lus dans le skill). Elle vaut en strate 7 comme en exploratoire, et
  même en état nul : la lecture peut enfin **abaisser** B. Sans carte ancrée ni candidate contredite, pas de chiffre.
  Hypothèse déclarée : la symétrie des preuves, à mesurer. Score : `C_symetrique_sur_B`, par canal ;
- **décalage appris** (`p_C_corrige`), appliqué aussi au C exploratoire, et appris sur les tests rétrospectifs, C
  exploratoires compris (`n_exploratoires`). Score : `C_exploratoire_corrige_sur_B`.

**Questions non binaires, en exploratoire (0.9.1).** Une question numérique, à date ou à choix multiple est ramenée à
**une question binaire dérivée**, au point le plus informatif de la prévision du bras A : la médiane (« strictement
au-dessus ? », « strictement après ? », p_A = 0,5) ou l'option la plus probable (« sera-ce elle ? », p_A = sa
probabilité). Tout le pipeline (B, puits, lecture, moteur) s'y applique ; **tout y est exploratoire**, même en strate 7 :
rien n'est posté, la prévision postée reste celle de A. Le résultat est scellé dans `journal-autres.jsonl`
(`exploratoire`), le dossier dans `dossiers-explo/`, et une ligne du commentaire Metaculus l'horodate. L'issue de la
question dérivée se déduit sans ambiguïté de l'issue d'origine. Score à part : `exploratoire_non_binaire` (C contre B,
C contre A au même seuil, symétrique contre B). `ALPHABET_EXPLORATOIRE_AUTRES=0` pour couper.

## Quand il tourne et ce qu'il coûte

- **Toutes les 20 minutes**, il regarde s'il y a des questions nouvelles (elles ne restent ouvertes que 3 heures, à
  heure aléatoire). Un contrôle sans question nouvelle ne coûte rien et n'écrit rien.
- **Toutes les questions ouvertes sont traitées** depuis 0.6.0 (`ALPHABET_MAX_QUESTIONS` vide ou `0`). Un plafond
  quotidien reste possible : donner un nombre à cette variable.
- **Lancement manuel** (*Actions → Bot alphabet situationnel → Run workflow*) : champ `max_questions` (`0` = toutes). Le mode `test_questions` (zone de test de Metaculus) est enregistré comme essai
  et n'entre pas dans le score.
- Par question binaire : environ cinq appels au modèle principal (dont trois estimations du taux de base), quelques
  appels au petit modèle, jusqu'à quinze recherches (doublées si une seconde source est configurée), quelques appels
  gratuits à l'API de Metaculus, plus le bras A.

## Modèles : suites de secours et contradicteur (0.6.0)

Chaque rôle reçoit une **suite** de modèles, séparés par des virgules. Au début d'un passage qui a des questions, le
bot sonde chaque suite dans l'ordre par un appel minuscule et garde, **pour tout le passage**, le premier modèle qui
rend un JSON correct : une question n'est jamais lue par deux codeurs. Les modèles retenus sont écrits dans chaque
ligne du registre (`modeles`), et le score est séparé par modèle (`par_modele`, option `--modele`) : changer de
modèle, c'est changer de codeur.

| Variable | Rôle | Configuration provisoire (Fantasy AI) |
|---|---|---|
| `ALPHABET_LLM` | réflexion : plan, taux de base, lecture, bras A | `openai/mistral-large-3,openai/mistral-large-latest` |
| `ALPHABET_PETIT_LLM` | tâches légères : résumés, analyse des réponses | `openai/mistral-small3.2:24b,openai/mistral-large-3` |
| `ALPHABET_CHERCHEUR` | recherche ; `{petit}` = le petit modèle retenu | `smart-searcher/{petit}` |
| `ALPHABET_CONTRADICTEUR` | contradicteur, en ombre (facultatif) | `openai/qwen3.8:27b,openai/gpt-oss:latest` |
| `ALPHABET_API_BASE` | adresse d'une passerelle compatible OpenAI | `https://fantasyai.cloud/api/v1` |
| secret `FANTASY_API_KEY` | clé de la passerelle (remplace `OPENAI_API_KEY`) | — |

Pour revenir à Claude : remettre `ALPHABET_LLM`, `ALPHABET_PETIT_LLM` et `ALPHABET_CHERCHEUR` sur les modèles
`anthropic/…`, et vider `ALPHABET_API_BASE` ; rien d'autre ne change.

**Le contradicteur** (d'une autre famille que le lecteur) relit chaque dossier chiffré face aux résultats de
recherche et ne peut que **contester** : maintenir, affaiblir (F → f) ou retirer une carte. Il n'ajoute rien et ne
donne aucun chiffre ; le moteur recalcule sur une copie du dossier. Le résultat (`bras.C.critique`, `p_C_critique`)
est **scellé en ombre et jamais posté** ; le score le compare à C (`C_critique_sur_C`). Il ne sera posté que si le
registre montre qu'il améliore le score.

**Recherche (0.6.1 à 0.6.3)** : chaque requête essaie, dans l'ordre, Exa (première clé, puis seconde clé
`EXA_API_KEY_2` quand la première échoue, pour le reste du passage), Tavily (`TAVILY_API_KEY`), TinyFish (`TINYFISH_API_KEY`, gratuit, sans carte), puis GDELT (sans
clé). Un moteur sans clé est sauté ; l'ordre se change par la variable `ALPHABET_RECHERCHE_ORDRE`
(`exa,tavily,tinyfish,gdelt` par défaut). TinyFish ne sait pas borner par date : quand une date limite
s'applique, il ne garde que les résultats datés et antérieurs. Brave Search, qui exige une carte bancaire même en offre gratuite, a été retiré. Chaque recherche du registre porte son `moteur`. La
recherche générale du bras A suit le même secours. Les tests rétrospectifs n'utilisent qu'Exa et GDELT, les deux
qu'on sait borner à une date passée.

**Surveillance** (workflow « Santé des modèles », toutes les 3 heures) : chaque modèle des suites est sondé, la liste
des modèles de la passerelle est relue, et une ligne s'ajoute à `registre/sante-modeles.jsonl` si l'état change. Si
aucun modèle principal ne répond, le workflow passe en rouge et GitHub prévient par e-mail.

## Puits de données (0.7.0)

Le module `alphabet_puits.py` interroge directement des bases ouvertes. Chaque appel est **borné à la date
d'information** : en prévision réelle, la date du jour ; en test rétrospectif, la date passée de la question. Le
modèle ne choisit que la source, ses paramètres et, pour un compte, le seuil (pris dans le critère de résolution) ; il
ne fournit aucun nombre. Les relevés sont aussi donnés au lecteur du bras C, comme faits citables, et le contrôle
d'attribution les inclut.

| Source | Clé | Usage |
|---|---|---|
| FRED, et ses millésimes ALFRED | `FRED_API_KEY` | séries américaines, telles qu'elles étaient publiées à la date d'information |
| Banque mondiale, BCE, Eurostat | aucune | indicateurs par pays, monnaie, statistiques européennes |
| Treasury FiscalData, BLS | aucune (`BLS_API_KEY` facultative) | finances fédérales, emploi et prix américains |
| Census Bureau, indicateurs économiques (0.10.93) | aucune (`CENSUS_API_KEY` facultative) | ventes au détail, logement, construction, biens durables, stocks, commerce extérieur (mensuel, sans millésime) |
| UNHCR, OCHA FTS, catalogue HDX | aucune | réfugiés, financement humanitaire, jeux de données humanitaires |
| UCDP | `UCDP_TOKEN` (en attente) | violence organisée et morts estimés |
| USGS, GDACS, NASA EONET | aucune | séismes, alertes de catastrophes, événements naturels |
| NASA FIRMS | `FIRMS_MAP_KEY` | feux actifs |
| Federal Register, Wikidata | aucune | documents présidentiels américains, titulaires d'un poste |
| Wikipedia, Wayback Machine | aucune | un article ou une page **tels qu'ils étaient** à la date d'information |

Une source sans sa clé n'est pas proposée au modèle. Un appel qui échoue est noté et n'arrête rien. Variables :
`ALPHABET_PUITS` (`0` pour couper), `ALPHABET_PUITS_MAX` (appels par question, 3 par défaut). Le workflow « Sonde des
puits de données » fait un appel réel par source, sans rien écrire ni poster.

**Le compte** : fenêtres disjointes de la durée de la question, comptées à rebours depuis la date d'information.
Mode `evenement` (au moins un événement dans la fenêtre), `atteint` (au moins une valeur remplit la condition) ou
`franchit` (la condition n'était pas remplie au début, elle l'est ensuite). Moins de cinq fenêtres : pas de compte. À
0 ou à n fenêtres sur n, la fréquence est ramenée à 1/(2n) ou 1 − 1/(2n), car le moteur exige une fréquence dans ]0, 1[.

## Comment il est jugé

Metaculus classe les participants au **score logarithmique** (les scores de pair sont des différences de scores log).
Le registre est donc scoré de la même façon (`score_registre.py`, chaque lundi par le workflow « Score du bot
alphabet ») :

- **par bras** : perte log, et score de référence de Metaculus (100 × (log₂ p + 1) ; 0 = pile ou face) ;
- **comparaison appariée**, sur les questions où les trois bras existent : **gain de C sur B** et de C sur A, en points
  de score de pair (100 × écart de ln p sur l'issue réelle ; positif = C meilleur), questions gagnées et perdues ;
- **un verdict** (`verdict`) : « meilleur (établi) », « moins bon (établi) » ou « **indéterminé** », et une
  **séquence de confiance** à 95 % sur le gain moyen (`intervalle_sequentiel_95`), valide **quel que soit le moment
  où l'on regarde** : on peut lire le score chaque semaine sans fausser la conclusion. Derrière, un test séquentiel
  (`test_sequentiel`) : une valeur e pour « fait mieux », une pour « fait moins bien ». L'hypothèse pré-enregistrée,
  C meilleur que B, est établie au-delà de 20 (niveau 5 %) ; les trois autres comparaisons faites sur les mêmes
  questions (C moins bon que B, C contre A dans les deux sens) au-delà de 60, pour ne pas multiplier les fausses
  conclusions ;
- **la puissance** (`puissance`) : combien de questions appariées il faudrait pour détecter un gain de 5, 10 ou 20
  points, avec l'écart-type observé (ou supposé, tant qu'il y a moins de 5 questions), pour le test séquentiel
  réellement appliqué (simulé) et, pour mémoire, pour un test classique lu une seule fois. Pour C contre B, le test
  utilise la borne structurelle du moteur (cote de C dans un facteur 10 de celle de B, soit ≈ 230 points par
  question) ; si elle était un jour dépassée, il le signale (`borne_depassee`) et retombe sur la borne générale ;
- **la fragilité** : le gain sans la pire question, simple diagnostic d'influence, pas un test ;
- **la stabilité de la strate** : sur les questions passées plusieurs fois **sous la même version**, la part des
  passages qui reprennent la même strate (elle commande le droit de chiffrer) ;
- **les statuts par version** (`statuts_par_version`) : taux de `hors_strate`, `sans_vue`, dispersion moyenne de B et
  sort de la classe figée (`figee`, `echec`, `desactivee`), pour vérifier les effets attendus de chaque version ;
- **le Brier apparié** (`brier_critere_L7`) reste calculé : c'est le critère de levée de L7 du skill
  (`validation.md` §27, C − B ≤ 0), qui est propre au skill et ne dépend pas du règlement de Metaculus. Borné, il
  signale aussi quand le log est dominé par une ou deux probabilités extrêmes qui se sont trompées (`accord_avec_log`) ;
- **les états nuls** ne sont pas assimilés à C = B : ils sont suivis à part, par nature (`structure_absente` ou
  `angle_mort`), avec la tenue du taux de base et son gain sur le modèle seul.

Une question compte une fois (sa dernière prévision publiée) ; toute probabilité est bornée à [0,001 ; 0,999], comme
à l'envoi ; une ligne dont le sceau ne correspond plus est écartée et listée. Sur quelques dizaines de questions, aucune
conclusion.

## Ce que garde le registre

| Fichier | Contenu |
|---|---|
| `registre/journal-bot.jsonl` | une ligne scellée par question binaire : bras A, B, C, bras posté, statut, `publie`, `mode`, et le commentaire envoyé (couvert par le sceau) |
| `registre/dossiers/` | le dossier de lecture de chaque question, nommé `<question>-<horodatage>.json` ; son sceau (`dossier_sha256`) est **relu** au score : une ligne dont le dossier a changé ou disparu sort du score (`dossiers_non_conformes`) |
| `registre/journal-autres.jsonl` | une ligne scellée par question non binaire (bras A), avec le commentaire envoyé |
| `registre/passages.jsonl` | une ligne par passage qui envoie des questions : date, déclencheur, identifiants de toutes les questions reçues (`trouvees_ids`), questions envoyées ; puis une ligne `fin` (prévues, en échec, remplacements de modèles, usage des moteurs de recherche) ; un passage arrêté faute de modèle ou de configuration écrit `sans_modele` ou `configuration` ; un contrôle sans question n'écrit rien |
| `registre/issues.jsonl`, `registre/issues-autres.jsonl` | les issues constatées, jamais réécrites |
| `registre/score.json` | le dernier score calculé |

L'historique Git date chaque écriture : c'est ce qui rend les prévisions vérifiables après coup.

**Aucune prévision sans sa ligne (0.8.0)** : si la ligne ne peut pas s'écrire, la question n'est pas postée ; elle
échoue et sera reprise au passage suivant. **Aucune ligne de test dans le registre** : toute écriture passe par une
garde qui refuse le vrai registre pendant un test (des lignes fictives y avaient été publiées de la 0.6.3 à la 0.7.3).

### Motifs d'écartement d'une carte

Chaque carte écartée par la lecture porte un motif, compté au score : `aucun_fait` (problème de recherche),
`non_cherchee` (recherche coupée par le plafond), `marqueur_non_rempli` (problème de marqueur ou vraie absence),
`contredit` (vraie absence de structure, le seul qui renseigne sur le skill lui-même).

## Limites

- **Pas d'humain dans la boucle** (règle du tournoi) : le bot mesure « le skill joué par un modèle », pas le skill codé
  par un humain.
- **Les multiplicateurs du moteur sont encore hypothétiques** : aucun cas réel n'est actif dans le skill. C'est
  précisément ce que la comparaison C contre B éprouve.
- **Prévisions publiées** : le plan, qui commande les recherches des bras B et C, interdit cotes de marché et
  prévisions publiées, mais la recherche peut en ramener ; le bras A n'a pas cette consigne.
- **Stabilité du taux de base** : sur une même question, B a varié d'un passage à l'autre (2,5 % puis 8 %). Depuis
  0.3.0, B est la médiane de trois estimations et leur dispersion est mesurée à chaque question (`vues` au registre) :
  si elle reste forte, la classe de référence sera à contraindre davantage.
- **Commentaire public en anglais**, avec les indicateurs du moteur en français.

## Installation

Le dépôt est prêt : fork de `Metaculus/metac-bot-template`, fichiers du bot à la racine, copie exacte du skill dans
`alphabet-situationnel/` (contrôlée par `moteur.py audit` avant chaque passage). Les workflows d'origine ne se lancent
plus qu'à la main, pour que deux bots ne postent pas sur le même compte.

1. Compte bot sur <https://www.metaculus.com/futureeval/participate/>, jeton, formulaire de participation.
2. *Settings → Secrets and variables → Actions* :
   - **Secrets** : `METACULUS_TOKEN` ; une clé de modèle (`ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY` ou
     `OPENAI_API_KEY`) ; une recherche web (`EXA_API_KEY`, ou une clé AskNews). Le proxy de modèles de Metaculus
     n'existe plus : sans clé de modèle, le bot s'arrête en rouge.
   - **Variables** : `ALPHABET_LLM` (ex. `anthropic/claude-sonnet-5-5`), `ALPHABET_PETIT_LLM`
     (ex. `anthropic/claude-haiku-5-5`), `ALPHABET_CHERCHEUR` (ex. `smart-searcher/anthropic/claude-haiku-5-5` avec
     Exa, ou `asknews/news-summaries`) ; facultatives : `ALPHABET_MAX_QUESTIONS`, `ALPHABET_LECTURE_HORS_STRATE`,
     `ALPHABET_CHERCHEUR_2` (seconde source de recherche, interrogée en plus de la première, par exemple
     `asknews/news-summaries` quand les crédits AskNews seront obtenus), `ALPHABET_VUES` (estimations du taux de
     base, 3 par défaut ; 1 pour économiser), `ALPHABET_HISTORIQUE` (`0` pour couper la recherche des questions
     résolues).
   - **Puits de données** (secrets, tous gratuits) : `FRED_API_KEY`, `FIRMS_MAP_KEY`, `UCDP_TOKEN` (quand il
     arrivera), `BLS_API_KEY` (facultative). Les autres sources n'ont pas de clé.
3. *Actions* : lancer d'abord en mode `test_questions`, vérifier sur Metaculus et dans `registre/`.

Au démarrage, le bot vérifie sa configuration et s'arrête en rouge si elle ne peut rien poster ; à la fin, il affiche
un bilan du passage. En local : `cp .env.template .env`, remplir, puis
`uv run python alphabet_bot.py --mode test_questions --sans-publier`. Le passage à blanc (`--sans-publier`) est
refusé hors de la zone de test : regarder les sorties du bot sur des questions ouvertes du tournoi, puis l'ajuster,
est interdit par le règlement.

## Tests

```
ALPHABET_SKILL_DIR=alphabet-situationnel python -m unittest discover -s tests
```

Modèle et recherche simulés, vrai moteur du skill. Ils tournent, avec l'audit du skill, à chaque modification du dépôt
(workflow « Contrôle du bot alphabet »).

## Tests rétrospectifs : corriger le biais de C

Avec des multiplicateurs tous ≥ 1 (décision 9 du skill), C ne peut que monter au-dessus de B : sur une classe qui
mêle situations avec et sans cartes, il surestime en moyenne. Pour **ce seul point**, le bot apprend une correction sur
des questions déjà résolues (*Actions → Tests rétrospectifs de l'alphabet → Run workflow*, nombre de questions et date
au choix ; rien n'est posté) :

- **fuite limitée** : questions **ouvertes** après la date choisie (0.8.0 : le filtre portait sur la résolution, alors
  que la date d'information est l'ouverture), à fixer après la date de connaissance du modèle ;
  recherche Exa bornée à la date d'information (pages non datées écartées), et le moteur du skill refuse de lui-même
  toute pièce postérieure ; une sonde demande d'abord au modèle s'il connaît l'issue, et la question est exclue s'il
  la connaît ; le bras A n'est pas calculé ;
- **sens de la fuite résiduelle** : un modèle qui devine l'issue fait paraître C meilleur ; le décalage appris est donc
  au pire trop faible, jamais trop fort ;
- **correction à un seul paramètre** : logit p' = logit p_C + b, apprise sur les tests rétrospectifs, évaluée hors
  échantillon, écrite dans `registre/correction-retro.json` seulement à partir de 15 questions chiffrées et si elle
  gagne hors échantillon, **borne basse à 95 % comprise** (0.8.0) ; elle expire au bout de 120 jours ;
- **appliquée en ombre** : chaque prévision réelle porte alors `p_C_corrige`, scellé et scoré (`C_corrige_sur_B`),
  **jamais posté** : la règle de postage ne change pas avant la levée de L7.

Les puits de données sont bornés à la **date de publication**, pas à la date de la période : une valeur annuelle
n'est connue que des mois après la fin de l'année (Banque mondiale +200 j, HCR +170 j, BLS +45 j, Eurostat et BCE
selon la fréquence, Trésor +15 j). FTS, sans millésime, est refusé pour une date passée. Ces séries restent sans
millésime : une valeur révisée depuis peut entrer ; seul FRED (ALFRED) donne la valeur telle qu'elle était publiée.

Coût : celui d'une question réelle par question testée (environ 7 appels au modèle, 15 recherches Exa). Exige la
recherche Exa (`smart-searcher`), seule bornable dans le temps ici.

## Règles de changement (0.10.85)

Les règles de validation (réparateur, moteur) sont un juge que l'on retouche : une règle corrigée peut faire monter
un score sans que la lecture ait changé (billet « eval harness », 2026-11-14 : une notation retouchée seule a fait
passer un lot de 57 à 86). Trois règles écrites :

1. **Table des bascules.** Toute version qui touche le réparateur ou le moteur publie, dans sa demande de fusion et
   dans l'historique, ce que SA modification change sur les lectures enregistrées : `rejeu_banc.py --bascules` donne,
   ligne par ligne, statut et p de C enregistrés contre ceux du code ; le contrôle des demandes de fusion calcule la
   table avec le code de la base et celui de la branche, sur les mêmes lignes, et affiche la différence
   (`comparer_bascules.py`, résumé du contrôle ; ne bloque pas la fusion).
2. **Juge et lecteur séparés.** Une correction du juge (réparateur, moteur, contrôles) et une modification de ce que
   lit le modèle (consignes) vont dans des versions distinctes quand c'est possible, pour savoir ce qui a bougé. Quand
   elles partagent une version, l'historique le dit et la table des bascules isole l'effet du juge (le rejeu reprend
   les lectures enregistrées, donc les anciennes consignes).
3. **Plafond par passage.** Le banc s'arrête au nombre de questions OU au plafond en dollars (`--budget`, 15 $ par
   défaut ; formulaire du banc) : avant chaque question, si le coût cumulé plus la question la plus chère vue jusqu'ici
   dépasserait le plafond, le banc s'arrête.

## Règle éthique des sources : personnes et personnalités publiques (décision d'auteur du 2026-11-16, 13 h 47)

Toutes les sources du bot parlent, directement ou non, d'êtres humains. La règle :
- **permis** : les actes publics des **personnalités publiques et des dirigeants**, dans leur fonction (déplacements
  officiels, avions d'État, déclarations, décisions, sanctions qui les visent), comptés de façon **agrégée par pays** ;
  une vie publique n'est pas secrète, et ces acteurs influent sur le cours des événements ;
- **exclu** : la **vie privée**, y compris celle des personnalités publiques (relations, santé, famille, liaisons), sauf
  ce que la presse a déjà publié, qui entre par la collecte de presse et seulement par elle ; tout **suivi de
  particuliers** (recherche de personnes, téléphones, visages, comptes individuels) ;
- les registres ne gardent que des **comptes** (pays, jour, famille de source), jamais un dossier sur une personne.

## Règle d'adoption commune (0.10.98)

Elliot Tower, *AI for Science × Philosophy of Science*, ch. 2 (chemins qui bifurquent) et 3 (arrêt et preuve) : un
critère propre pris seul ne protège ni d'essais menés en parallèle ni d'un regard répété qui s'arrête au premier passage
favorable. `essais.py` :

1. **Compter** : tout essai qui peut changer ce qui est posté ou calculé est inscrit avec son critère avant son premier
   regard, et son pré-enregistrement est commité dans `preenregistrements/` (la date du commit fait foi, pas le texte) ;
   le rapport de score dit combien sont ouverts.
2. **Corriger** : un critère à intervalle (« l'intervalle à 90 % sous 0 », risque unilatéral 5 %) est jugé au risque
   5 % / k, k = nombre d'essais ouverts de ce type (Bonferroni) ; le critère nominal reste affiché.
3. **Regarder à date fixe** : verdict sur les N premières lignes admissibles ; un « indécis » donne droit à un second
   regard sur les 2N premières, au risque partagé ; au-delà, l'essai est clos ou repris sous un critère neuf.
   L'apprentissage des liens se juge une seule fois, à la fin (son tiers de jugement est fixe : le relire à chaque passe
   l'userait).

## Décisions en attente

- **Plafonner la valeur postée ?** Les bots les mieux classés plafonnent leurs probabilités extrêmes (par exemple
  0,02–0,98) : avec un score log, un 0,001 qui se trompe coûte très cher. Le registre garde 0,001–0,999 pour mesurer ;
  la question est de plafonner **ce qui est envoyé**. Ce plafonnement change le score Metaculus, pas la mesure de
  C − B, qui se fait sur les bras bornés à 0,001–0,999 : il n'aide donc pas la puissance du test. Décision reportée par Othman après des tests de prédiction
  suffisants : le score étudie chaque semaine ce qu'aurait changé le plafonnement (`plafonnement_etudie`) et affiche
  un **rappel** à partir de 30 questions résolues.
- **Recalibrer ?** Le score calcule chaque semaine, à partir de 20 questions résolues par bras, ce que gagnerait une
  recalibration logistique (deux paramètres, mesurée hors échantillon : `recalibration_etudiee`). Rien n'est appliqué :
  c'est la méthode prévue pour calibrer l'alphabet, quand les données le permettront.

## Historique utile

- **0.10.196** — collecteur ACAPS (`collecte_acaps.py`, workflow hebdomadaire « Collecte hebdomadaire ACAPS ») : liste des risques des analystes d'ACAPS (214 risques, date d'entrée, probabilité, impact, statut) et instantanés de l'indice INFORM Severity ; indicateur `acaps` (risques nouveaux du pays sur 6 mois, champs non révisés seulement) et état dans l'observatoire. CrisisWatch écarté (site fermé aux serveurs de GitHub).
- **0.10.197** — diagramme de Murphy (`murphy.py`, décision d'auteur du 2026-11-16, 17 h 53, après lecture de Ren, « Does a Better Brier Score Buy Better Decisions? ») : valeur captée par seuil coût-perte θ (1 = prescience, 0 = taux de base par source) et pour quatre profils d'utilisateurs (uniforme = Brier, précaution, seuil haut, enjeux égaux), avec intervalles bootstrap par question. Ajouté au résumé du Banc B (`murphy`) et au résumé du workflow ; `python murphy.py registre/banc-b.jsonl` le recalcule sans relancer le banc (écrit `registre/banc-b-murphy.json`). Lecture descriptive : le critère d'adoption reste la règle commune.
- **0.10.198** — deux mesures après lecture de La Note de Rens' n° 25 (décision d'auteur du 2026-11-16, 18 h 03, appliquées directement, sans ombre) :
  1. *Reprises* : `collecte_rss.py` compte des titres distincts. Un article repris (même titre normalisé, à moins de 30 jours) dans un autre flux ou par un autre média ne compte qu'une fois, contre le blanchiment d'information. Familles éditoriales seulement (presse, voix citoyennes, économie, renseignement, lettres, Parlement européen) ; « officiel » et « santé » répètent légitimement un intitulé pour des événements distincts. Titres de moins de 5 mots non dédoublonnés. Registre `registre/rss-titres.csv` (empreintes et jours, jamais les titres). Les comptes antérieurs ne sont pas recalculés : pendant 14 jours, le rapport « presse » compare une quinzaine dédoublonnée à une quinzaine qui ne l'était pas (biais à la baisse, faible).
  2. *Injection de consignes* : `garde_injection.py`. Tout texte collecté qui entre dans un prompt (résultats de recherche du pipeline et des bancs A, L, M, signaux ; recherche du bot de base `main.py` ; résumés de revues) est tronqué, nettoyé (caractères invisibles et de direction, balises de bloc falsifiées), neutralisé (tournures d'injection remplacées par « [consigne retirée] », comptées sans texte) et encadré par deux balises avec un avertissement : données non fiables, à citer, jamais à suivre. Les empreintes et le contrôle des extraits portent toujours sur le texte reçu.
- **0.10.199** — en ombre (décision d'auteur du 2026-11-16, 18 h 28) : flux CERT-FR (ANSSI) dans `collecte_rss.py`, famille « cyber ». Ce sont les rapports « Menaces et incidents » qui comptent : ils nomment parfois un attaquant ou un pays. Les avis sur des produits ne nomment pas de pays. Pays reconnus aussi par les adjectifs de nationalité (« iranienne », « Russian » ; source mledoze/countries, ODbL) : un adjectif porté par plusieurs territoires va au seul membre de l'ONU (« French » → FR), sinon il est écarté (« Congolese ») ; expressions trompeuses masquées (« Latin American », « océan Indien ») ; « Polish » seulement avec majuscule. Pour toutes les familles, comptes parallèles « famille_large » (noms et adjectifs) ; les comptes historiques gardent leur définition (noms seuls), pour ne pas casser les séries. États d'observatoire `rss_cyber` et `rss_presse_large` (rapport sur 28 jours, mesurable à partir du 15 décembre 2026).
- **0.10.200** — en ombre (décision d'auteur du 2026-11-16, 18 h 37) : Correctiv, rédaction d'enquête allemande, dans `collecte_rss.py`. Deux familles : « verification » (flux Faktencheck : la pression de désinformation sur un pays) et « enquete » (flux général ; les vérifications, lues d'abord, n'y sont pas recomptées). Noms de pays allemands (CLDR « de ») en plus des noms anglais, français et des adjectifs, pour ces deux familles seulement. États d'observatoire `rss_verification` (≥ 3 vérifications en 14 jours) et `rss_enquete`. Mécanisme candidat noté, non chiffré : une révélation d'enquête précède une mobilisation (Potsdam, janvier 2024).
- **0.10.201** — pilote IRSEM (`mecanismes_irsem.py`, workflow « Mécanismes proposés à partir de l'IRSEM », décision d'auteur du 2026-11-16, 18 h 47) : récolte des publications (série « Brève stratégique » par défaut), texte des PDF passé par la garde contre l'injection, et extraction par Haiku (Bedrock) d'au plus deux mécanismes énoncés par publication (indicateur, délai, portée). Plafond de 1 $ par défaut. Règle d'arrêt fixée avant le pilote : moins de 3 mécanismes avec indicateur, délai énoncé et portée régionale ou générale → on arrête. Textes non conservés. Lancer d'abord en vérification (gratuit).
- **0.10.202** — trois fiches tirées du rapport KAS *Cognitive Warfare* (décision d'auteur du 2026-11-16, 18 h 56), inscrites au catalogue, en ombre : **M12** « le récit monte avant l'acte » : nouveau collecteur `collecte_recit_russe.py` (GDELT DOC 2.0, articles de sources russes qui nomment chaque pays, fenêtre glissante de trois mois, variante « alibi » provocation, mise en scène, faux drapeau), indicateur `recit_russe` ; **M13** « la réponse s'use à la répétition » : `collecte_gdelt.py` compte aussi les actes hostiles d'acteurs russes par pays (racines CAMEO 18, 19, 20 ; `gdelt-hostilites-ru.csv`), domaine des questions de réponse, pas d'état d'observatoire ; **M14** « les dates de mémoire attisent les tensions » : calendrier fixe `registre/dates-memoire.csv` (à relire par l'auteur), indicateur `dates_memoire` (date dans les 14 jours suivants, aucune fuite). États d'observatoire `recit_russe` et `dates_memoire`.
- **0.10.203** — pilote des analyses stratégiques corrigé (décision d'auteur du 2026-11-16, 19 h 14) : `mecanismes_irsem.py` lit aussi Le Rubicon (`--source rubicon`, entrée « source » du workflow, renommé « Mécanismes proposés à partir des analyses stratégiques ») ; la règle d'arrêt ne s'appuie plus sur la portée déclarée par le modèle (trop généreuse au pilote IRSEM) mais sur un critère extérieur : indicateur rattaché à l'une de nos sources de données (liste fermée `REGISTRES`), rattachement vérifié par les mots de l'indicateur (expression régulière, sans modèle), et délai énoncé.
- **0.10.204** — module Chine, couche 2 (décision d'auteur du 2026-11-16, 21 h 42), en ombre : registre tenu à la main `registre/chine-contremesures.csv` (date, liste, pays_vise, entites, source) pour les annonces chinoises (liste des entités non fiables, liste de contrôle des exportations, contre-sanctions), indicateur `contremesures_chine` (annonces visant le pays dans les 90 jours) et état d'observatoire. Pas de collecte automatique : le site du ministère du Commerce interdit les robots (robots.txt), et l'API de Global Trade Alert est payante ; le site de Global Trade Alert (gratuit, CC BY-NC 4.0) sert de source pour la saisie.
- **0.10.205** — module Chine, couche 2, sans saisie à la main (décision d'auteur du 2026-11-16, 21 h 45 : pas de travail quotidien, pas de lecture du chinois) : le registre manuel de 0.10.204 est retiré ; `collecte_gdelt.py` compte, dans les fichiers déjà lus, les sanctions, embargos et boycotts imposés par un acteur chinois (code CAMEO 163) par pays visé (`gdelt-chine-sanctions.csv`). L'indicateur `contremesures_chine` (90 jours) lit ce registre ; état d'observatoire à partir de 3 événements. GDELT code les dépêches, pas les listes officielles : le compte mesure les contre-mesures rapportées par la presse, bruit compris.
- **0.10.206** — module Chine, couche 3 (décision d'auteur du 2026-11-16, 21 h 51), en ombre : `collecte_avis_navigation.py` lit les avertissements de navigation en cours republiés par la NGA (HYDROPAC ; domaine public, sans clé), car les administrations maritimes chinoises refusent les connexions étrangères. Filtre fixé d'avance : zone chinoise nommée (mers, détroit de Taïwan, provinces côtières) et activité militaire (exercices, tirs, missiles) ; pays riverains selon la zone. Historique construit au fil des passages. Indicateur `avis_navigation` (14 jours) et état d'observatoire. Workflow avec `sonde = oui` par défaut (vérification sans écriture).
- **0.10.207** — sanctions de l'Union européenne (décision d'auteur du 2026-11-16, 22 h 05), en ombre : `collecte_sanctions.py` lit aussi la liste consolidée des sanctions financières de l'UE (CSV public de la Commission), regroupée par entité ; date d'inscription (ou première publication de règlement), pays visé par le code du programme (programme Ukraine → Russie ; terrorisme, cyber, droits de l'homme → sans pays). Lignes « ue » recalculées en entier à chaque passage ; historique reconstruit d'un coup, sans les radiations (biais du survivant, déclaré). L'indicateur `sanctions` additionne désormais les trois sources et donne `ue_14j`.
- **0.10.208** — feux par pays vus par satellite (décision d'auteur du 2026-11-16, 22 h 07), en ombre : `collecte_feux.py` (NASA FIRMS, API « country », VIIRS ; clé gratuite `FIRMS_MAP_KEY`) compte chaque jour les points chauds par pays, en fenêtres de 5 jours ; produit choisi pour chaque fenêtre d'après les dates publiées par FIRMS (`data_availability`, même logique que la source « firms » du puits, 0.10.94), archive standard avant temps quasi réel, fenêtre ignorée si aucun produit ne la couvre ; une fenêtre sans aucune détection dans le monde est tenue pour non publiée (jamais pour « zéro feu »). Indicateur `feux` : log(14 jours / 14 jours précédents) et part de confiance forte ; état d'observatoire ±0,4. Les brûlis agricoles saisonniers font l'essentiel du bruit : l'observatoire juge, rien n'est lu directement.
- **0.10.209** — **M15 « le silence statistique annonce une mauvaise nouvelle »** (décision d'auteur du 2026-11-16, 22 h 19), en ombre : calendrier officiel 2026 du Bureau national des statistiques chinois recopié dans `registre/calendrier-nbs.csv` (122 publications prévues, source : stats.gov.cn, 26 décembre 2025 ; à renouveler chaque année) ; `collecte_calendrier_nbs.py` lit chaque jour la liste des communiqués anglais et rattache chaque titre à une publication (motifs fixes). Indicateur `silence_statistique` (Chine seulement) : publications prévues dans les 30 jours et jugeables, parues en retard (plus de 3 jours, le site anglais ayant un ou deux jours de décalage) ou absentes ; seules les publications observées avant la date comptent. État d'observatoire et fiche M15 au catalogue.
- **0.10.210** — récit russe (M12), après le premier passage (32 pays lus, 164 refus « 429 » de l'API DOC de GDELT, les adresses de GitHub étant partagées) : 8 secondes entre requêtes, deux nouvelles tentatives après un refus (30 puis 90 secondes), arrêt après 8 refus d'affilée en gardant ce qui est lu, et les pays les moins à jour lus d'abord pour que les passages suivants complètent. Délai du workflow porté à 150 minutes.
- **0.10.211** — feux : l'API « country » de FIRMS répond « 400 Invalid API call » à tout appel, même à la liste des pays (sonde du 2026-11-16 ; elle expliquait aussi les 400 « sans motif » du 14 novembre), tandis que l'API « area » répond. `collecte_feux.py` lit désormais les détections MONDIALES par fenêtre de 5 jours (une requête par fenêtre au lieu d'une par pays) et rattache chaque point à un pays par les frontières de Natural Earth 1:50 m (domaine public ; shapely chargé par le workflow ; points en mer sans pays ; Somaliland et Chypre du Nord rattachés au pays de droit). La source « firms » du puits lit ce registre au lieu d'appeler l'API (ISO3 ou ISO2 acceptés ; jours non couverts : ErreurSource).
- **0.10.212** — feux : un seul satellite tant que possible (NOAA-20 en archive standard puis en temps quasi réel), pour ne pas comparer une quinzaine vue par Suomi NPP à une quinzaine vue par NOAA-20 ; le premier rattrapage (57 jours, 12 requêtes, 0 échec, 2,9 millions de détections rattachées) avait changé de satellite au 30 octobre, le temps quasi réel de Suomi NPP s'arrêtant au 2 novembre. Registre effacé, à recollecter.
- **0.10.213** — feux, après le rattrapage depuis juin : (1) une fenêtre ne change plus de produit en son milieu : elle est coupée à la date de fin du produit qui couvre son premier jour (la fenêtre du 31 juillet au 4 août était passée sur NOAA-21, entre la fin de l'archive standard de NOAA-20 et le début de son temps quasi réel ; ces cinq jours sont retirés du registre et seront relus) ; (2) « Exceeding allowed transaction limit » (la limite de 5 000 transactions par 10 minutes se compte au volume, et une requête mondiale pèse lourd ; 7 fenêtres refusées sur 23) : pause de 10 minutes puis une nouvelle tentative.
- **0.10.214** — prix alimentaires en temps réel de la Banque mondiale (décision d'auteur du 2026-11-17, 0 h 21, à la place des blogs de la Banque, analyses publiées après coup et sans flux RSS officiel), en ombre : `collecte_prix_alimentaires.py` lit le fichier pays « Monthly estimates of food prices and inflation by country » (WLD_2021_RTFP-CTRY_v02_M, 37 pays surtout fragiles, mensuel ; données ouvertes, attribution requise) par l'API du catalogue de la Microdata Library. Ce sont des estimations de modèle recalculées à chaque version : chaque version est gardée comme un millésime daté, et l'indicateur `prix_alimentaires` ne lit que la dernière version publiée avant la date (inflation alimentaire sur un an calculée sur l'indice Close, accélération sur trois mois). Pas de millésime avant notre première collecte : indicateur absent sur le passé. État d'observatoire (≥ 20 % contre < 5 %). Workflow hebdomadaire, sonde par défaut.
- **0.10.215** — banc de fidélité des synthèses de recherche (décision d'auteur du 2026-11-17, 0 h 45 ; May, Nunan, Marshall & Palace, « A Taxonomy of Bullshit », Policing, 2026, via les Chroniques de la Recherche n° 28 de Veille Magazine), mesure seule : `banc_fidelite.py` fait résumer par le modèle les faits datés et chiffrés de résultats de recherche bornés à la date d'information (questions de séries ForecastBench résolues), puis le code vérifie que chaque nombre de la synthèse (au moins deux chiffres, ou décimal ; formats français et anglais) figure dans le corpus lu. Borne haute des erreurs de fidélité : un absent peut être un calcul, une conversion d'unité ou une connaissance du modèle ; les cas sont gardés avec un extrait de la synthèse, jamais de la source. La mesure ne pouvait pas être rétrospective : les dossiers du bot gardent les requêtes, pas le texte des recherches. Registre `registre/banc-fidelite.jsonl`, résumé `registre/banc-fidelite.json`. Ne change rien au bot.
- **0.10.216** — silence statistique chinois (M15), deux faux signaux corrigés après le premier passage complet (15 pages, 137 publications depuis octobre 2025 ; 100 publications prévues sur 104 à temps) : (1) le site anglais du NBS ne publie pas pendant les congés officiels chinois (PMI du 30 avril paru le 6 mai, PMI du 30 septembre paru le 8 octobre) : la date limite est désormais prolongée d'un jour par jour férié (`registre/jours-feries-chine.csv`, calendrier 2026 du Conseil d'État, à renouveler chaque année avec le calendrier NBS) ; (2) le communiqué annuel s'intitule « Profit of Industrial Enterprises… » au singulier : motif corrigé. Reste une limite connue : le site anglais peut publier très en retard alors que le chinois est à l'heure (prix des logements de février : chinois le 16 mars, anglais le 17 avril) ; l'indicateur mesure le silence du site anglais.
- **0.10.217** — prix alimentaires (RTFP) : la première sonde a reçu « 400 Bad Request » sur l'adresse numérique du catalogue ; l'API NADA de la Microdata Library attend l'identifiant texte de l'étude (`WLD_2021_RTFP-CTRY_v02_M`). Le collecteur essaie désormais `api/catalog/resources/{idno}`, puis deux variantes, et rapporte chaque échec.
- **0.10.195** — sondes des sources d'alerte précoce (`sonde_alerte_precoce.py`, workflow « Sondes alerte précoce ») : forme des pages CrisisWatch (International Crisis Group) et points d'accès de l'API ACAPS (calendrier saisonnier, INFORM Severity), sans écriture ; FEWS NET écarté pour l'instant (service suspendu puis partiellement rouvert).
- **0.10.194** — documentation de l'API Metaculus (lue le 2026-11-16) : une passerelle de filtrage met la résolution à null sauf pour les questions sur lesquelles le compte a prévu (ou d'un projet accordé) ; le score du bot n'est donc pas en cause (ses premières questions se résolvent le 27 novembre). Les conditions d'utilisation interdisent d'utiliser les données pour entraîner, évaluer ou développer des algorithmes sans autorisation écrite : la récolte complète du B Metaculus est suspendue (variable `METACULUS_RECOLTE_AUTORISEE=oui` exigée) jusqu'à l'autorisation demandée par le formulaire « Metaculus Data Needs ».
- **0.10.193** — diagnostic Metaculus : l'API renvoie `question.resolution = None` (et `resolution_criteria = None`) au compte bot, même pour des questions résolues ; le score du bot n'avait donc enregistré aucune issue (`registre/issues.jsonl` vide). Les workflows « Score du bot alphabet » et « Récolte des questions Metaculus résolues » prennent en priorité le secret `METACULUS_TOKEN_LECTURE` (jeton d'un compte personnel), s'il existe.
- **0.10.192** — récolte Metaculus : la page de chaque post ne donnait pas non plus la résolution (4 754 posts lus, aucun gardé) ; mode « diagnostic » par défaut (3 posts : toutes les clés qui ressemblent à une résolution, liste et détail, rien d'écrit) ; un post sans résolution lue n'est plus marqué « vu » ; liste des posts vus remise à zéro.
- **0.10.191** — pilote des revues : vérification passée pour 13 revues sur 14 ; « cdlj » retiré (aucune notice).
- **0.10.190** — Banc du taux de base, option « audit_alfred = oui » : recalcule les questions FRED déjà au banc avec le contrôle de provenance et compare l'ancien B au nouveau (questions gardées, questions refusées), sans rien ajouter au banc (`registre/banc-b-alfred.jsonl`).
- **0.10.189** — audit « fuite temporelle ALFRED / FRED » (2026-11-16) : une série FRED révisable n'est plus jamais lue au présent pour une date passée ; sans millésime ALFRED valide (moins de 20 points, ou relevé marqué « millésime indisponible »), le banc ne calcule pas de B et le puits refuse la lecture. Seules les cotations de marché d'une liste fermée (`MARCHES_NON_REVISES` : indices boursiers, taux du Trésor, ICE BofA, changes, SOFR…) gardent le repli. Provenance notée dans chaque ligne du banc B (`provenance`). Tests de non-régression `tests/test_audit_alfred.py`.
- **0.10.188** — pilote des revues : mode « vérification » par défaut (une page OAI par revue, exemple, liste des collections du serveur en cas d'échec ; gratuit, rien d'écrit) ; le pilote complet demande « verification = non ».
- **0.10.187** — pilote « mécanismes proposés à partir des revues » (`mecanismes_revues.py`, workflow manuel) : récolte OAI-PMH d'OpenEdition (14 revues, articles depuis 2005 touchant aux crises), extraction de 0 à 2 mécanismes par résumé par le petit modèle Bedrock, plafond de dépense ; résumés non conservés ; propositions soumises à l'auteur avant tout ajout au catalogue.
- **0.10.186** — fiche M11 (diffusion spatiale) : indicateur `voisins`, manifestations et émeutes de GDELT dans les pays frontaliers (table GeoNames, CC BY 4.0, mise en cache dans `registre/voisins.json`), 14 jours contre 14 précédents ; deux états dans l'observatoire.
- **0.10.185** — Cloudflare Radar : les coupures ordonnées pendant les examens nationaux (repérées dans la description) sont marquées « examens » et écartées de l'état « coupure décidée par l'État » ; premier passage : 65 coupures depuis juin, dont 25 en Irak (saison des examens). PortWatch passe à 4 h 13 (heure creuse du quota ArcGIS).
- **0.10.184** — collecteur Cloudflare Radar : fin de période = maintenant (une fin future est refusée, erreur 400), fenêtres de 30 jours, texte de l'erreur affiché.
- **0.10.183** — collecteur PortWatch : le quota ArcGIS (6 000 unités par minute) est partagé par tous les utilisateurs du service ; une erreur 429 est retentée après 65 s (jusqu'à 5 fois), et 15 s séparent deux détroits.
- **0.10.182** — relevé du nowcast d'inflation : le genre de chaque tableau (variation mensuelle, glissement annuel, trimestre annualisé) est lu dans le titre qui le précède (à défaut, l'ordre de la page) ; le premier relevé, qui étiquetait « mois » le glissement annuel, est corrigé ; la source `nowcast_inflation` prend un paramètre `genre`.
- **0.10.181** — nowcasts publics branchés comme données d'entrée : source `gdpnow` (GDPNow de la Fed d'Atlanta par FRED, millésimes ALFRED à la date de la question) et source `nowcast_inflation` (Fed de Cleveland, relevés quotidiens du bot, `collecte_nowcast_inflation.py`, workflow « Relevé quotidien du nowcast d'inflation ») ; note « nowcast public ou modèle propre » dans `preenregistrements/contexte-par-regime.md`.
- **0.10.180** — règle éthique des sources (personnes et personnalités publiques, décision d'auteur du 2026-11-16) ; collecteur des avions d'État (`collecte_avions_etat.py`, plane-alert-db « Dictator Alert », vols OpenSky de la veille, comptes par pays seulement) ; indicateur `avions_etat` et état « visite d'avions d'État » dans l'observatoire. Pas d'historique (coût en crédits OpenSky) : jugeable après quelques semaines de collecte.
- **0.10.179** — calendrier des élections nationales (`collecte_elections.py`, Wikidata CC0, workflow hebdomadaire « Calendrier des élections ») ; indicateur `elections` (30 jours avant la date, sans fuite ; 30 jours après, fuite possible déclarée) ; fiche M10 du catalogue des mécanismes.
- **0.10.178** — collecteur des sanctions (`collecte_sanctions.py`, workflow « Collecte quotidienne des sanctions ») : OFAC (pages quotidiennes « Recent Actions », étiquettes de programme des entrées ajoutées, domaine public) et liste britannique (historique des modifications GOV.UK, Open Government Licence), par pays visé (tables fixes) ; indicateur `sanctions` (désignations des 14 jours) et état « sanctions nouvelles » dans l'observatoire.
- **0.10.177** — collecteur Cloudflare Radar (`collecte_radar.py`, workflow « Collecte quotidienne Cloudflare Radar », secret `CLOUDFLARE_RADAR_TOKEN`) : coupures d'internet par pays avec leur cause (CC BY-NC 4.0) ; indicateur `radar` (coupures commencées dans les 14 jours) et trois états dans l'observatoire : toute coupure, coupure décidée par l'État ou militaire, panne électrique.
- **0.10.176** — collecteur PortWatch (`collecte_portwatch.py`, workflow « Collecte quotidienne PortWatch ») : passages quotidiens de navires dans huit détroits (IMF PortWatch), à petite dose (une requête par détroit et par jour, année en cours) ; décision d'auteur après la réponse automatique du FMI. Indicateur `portwatch` par pays riverain, décalé d'une semaine (délai de publication) ; état « le trafic du détroit chute / monte » dans l'observatoire.
- **0.10.175** — collecteur OONI (`collecte_ooni.py`, workflow « Collecte quotidienne OONI ») : censure d'internet par pays et par jour (sites web ; Telegram, WhatsApp, Signal, Messenger), données OONI sous CC BY-NC-SA 4.0 ; indicateur `ooni` (part des mesures anormales, 14 jours moins les 14 précédents, absent sous 50 mesures web ou 20 de messageries) et deux états dans l'observatoire. Historique complet.
- **0.10.174** — récolte Metaculus : la liste des posts ne donne pas la résolution ; lecture du détail de chaque post (une requête par question, 0,7 s d'intervalle), écriture au fil de l'eau et reprise automatique d'un passage à l'autre (registre/metaculus-posts-vus.txt), durée bornée à 200 minutes.
- **0.10.173** — collecteur GDELT (`collecte_gdelt.py`, workflow « Collecte quotidienne GDELT ») : comptes quotidiens de manifestations (CAMEO 14) et d'émeutes (145) par pays du lieu de l'action, codes FIPS convertis en ISO ; indicateur `gdelt` dans les indicateurs de niche (14 jours contre 14 jours précédents) et deux états dans l'observatoire. Historique complet : mesurable sur les questions déjà résolues.
- **0.10.172** — récolte Metaculus : la combinaison « statuses=resolved, forecast_type=binary » rendait 0 post ; essai de plusieurs variantes de paramètres sur la première page, la première qui rend des posts est gardée (tri oui/non local).
- **0.10.171** — récolte Metaculus : noms de pays par un client sans le jeton Metaculus (9 noms au lieu de 475) ; tri par date de résolution prévue ; diagnostic de la première page et décompte des posts écartés ; aucun registre écrit si rien n'est gardé.
- **0.10.170** — collecteur RSS : ONU Info retiré (flux anglais en 404, flux français bloqué à la source, même dans un navigateur).
- **0.10.169** — collecteur RSS : Lefaso.net et Hespress lus par des relais FeedBurner créés par l'auteur (blocages intermittents des serveurs de GitHub).
- **0.10.168** — collecteur RSS : ONU Info par son flux français (`un.org/apps/newsFr/rss/rss_top.asp`), à la place des flux régionaux en 404.
- **0.10.167** — collecteur RSS : ECFR et ReliefWeb retirés (inaccessibles, même par relais) ; second essai aussi sur le code 415.
- **0.10.166** — récolte des questions Metaculus binaires résolues (`recolte_metaculus.py`, workflow « Récolte des questions Metaculus résolues ») : champs de l'API, pays, domaine, forme et seuils par des règles fixées d'avance, sans modèle ; descriptions non gardées. Première étape du B Metaculus.
- **0.10.165** — collecteur RSS : flux du Parlement européen lus par des relais FeedBurner créés par l'auteur (le site renvoie une page vide aux serveurs de GitHub).
- **0.10.164** — collecteur RSS : ONU Info par ses 5 flux régionaux (le flux « toutes les actualités » renvoie 404).
- **0.10.163** — collecteur RSS : l'API de l'OMS n'est plus confondue avec le flux de l'IATA (qui passait par le décodeur JSON) ; code HTTP noté dans la santé des flux ; second essai avec l'en-tête d'un navigateur ordinaire si le site refuse l'agent du bot (401, 403, 406, 429) ou renvoie une page HTML.
- **0.10.162** — collecteur RSS : santé des flux (registre/rss-sante.csv : dernier essai, statut, dernier succès, dernier nouvel article) et bilan dans le résumé du passage (flux en erreur, vides, muets depuis 7 jours).
- **0.10.161** — collecteur RSS : communiqués de l'IATA (demande aérienne passagers et fret) dans « economie ». Écartés après examen : crypto.ro, CSSF (régulateur luxembourgeois), alertes NasdaqTrader (avis techniques et suspensions de cotation, sans dimension pays).
- **0.10.160** — collecteur RSS : investingLive (ex-ForexLive) dans « economie » ; famille dérivée « notation » (article économique qui nomme une agence de notation et un mot de notation) et état « une agence de notation est citée » dans l'observatoire.
- **0.10.159** — collecteur RSS : familles « think_tanks » (ECFR, articles et publications) et « economie » (Investing.com en français : actualité économique, indicateurs économiques), avec leurs états dans l'observatoire.
- **0.10.158** — collecteur RSS : Fonds mondial (communiqués, mises à jour) dans la famille « sante » ; nouvelle famille « voix_citoyennes » (Global Voices, 11 flux régionaux) et état « Global Voices en parle » dans l'observatoire.
- **0.10.157** — collecteur RSS : famille « sante » (OMS Disease Outbreak News par l'API OData du site, ECDC : rapport hebdomadaire des menaces, mises à jour épidémiologiques, évaluations de risque, grippe aviaire) ; état « l'OMS ou l'ECDC en parlent » dans l'observatoire. Flux IMDRF écarté (figé depuis 2021, dispositifs médicaux).
- **0.10.156** — collecteur RSS : ONU Info (toutes les actualités) dans la famille officielle ; lettres confidentielles d'Indigo Publications en titres seuls : Intelligence Online et Africa Intelligence (famille « renseignement », état « les lettres de renseignement en parlent » dans l'observatoire), La Lettre et Glitz (famille « lettres_fr », collectée, non branchée sur les conflits).
- **0.10.155** — collecteur RSS : famille « parlement_ue » (Parlement européen : relations extérieures, commissions AFET, DROI, SEDE, propositions de résolution, textes adoptés), état « le Parlement européen s'en saisit » dans l'observatoire. Les ordres du jour des plénières sont notés pour le B Metaculus (questions de vote européen), sans code.
- **0.10.154** — découverte des canaux Telegram élargie (option B de l'auteur, 2026-11-15, 21 h 46) : mots-clés régionaux (international, Afrique, Moyen-Orient, Asie, Amérique latine), au moins 10 000 abonnés, les 40 plus suivis, titres en alphabet latin ; premier passage : 7 canaux seulement, dont 3 hors sujet.
- **0.10.153** — **brouillage GPS** (décision d'auteur du 2026-11-15, 21 h 35) : part quotidienne des zones « rouges » de gpsjam.org (avions à navigation dégradée, depuis le 2022-02-14) rattachées aux pays par les frontières Natural Earth ; indicateur `brouillage_gps` (14 jours avant la date) dans l'observatoire, mesurable sur les questions passées. Fichiers quotidiens non documentés par gpsjam : lecture tolérante et vérification au démarrage. Module `h3` installé hors du verrou du bot.
- **0.10.152** — **flux RSS en ombre** (décision d'auteur du 2026-11-15, 21 h 26) : collecteur quotidien (6 h 37 UTC, file à part) des flux officiels (ReliefWeb, avis de voyage britanniques, GDACS, USGS) et de 14 titres de presse francophone internationale tirés de l'atlas atlasflux (un titre par groupe ; France, Suisse, Canada, Afrique, Asie) ; pays reconnus en anglais et en français (Unicode CLDR), comptes seulement ; indicateurs `rss_presse` et `rss_officiel` dans l'observatoire, sur les dates couvertes.
- **0.10.151** — Telegram : la recherche globale ne remonte presque pas dans le passé (passage 43754624230 : 166 couples sur 185 à zéro message) ; remplacée par l'historique de canaux proposés par une règle fixée (`decouvrir_canaux_telegram.py`, workflow « Découverte des canaux Telegram » : mots-clés neutres, canaux publics, au moins 20 000 abonnés, les 25 plus suivis), utilisés seulement après validation par l'auteur (`registre/telegram-canaux.json`). Les mesures de la recherche globale sont ignorées par l'observatoire.
- **0.10.150** — fiche pays : REST Countries a retiré ses versions v1 à v4 (v5 avec compte et clé) ; notre appel /v3.1 ne renvoyait plus rien (d'où les échecs depuis GitHub). Remplacé par la table des pays de la Banque mondiale (code ISO, capitale, coordonnées ; gratuite, sans clé), repli Open-Meteo inchangé.
- **0.10.149** — **GeoConfirmed pour Metaculus** (décision d'auteur du 2026-11-15, 20 h 57) : nouvelle source du bot (`geoconfirmed`) : images de guerre vérifiées par géolocalisation (export KML public par conflit), avec distance à une localité et rayon ; complète `front_ukraine` (DeepState, producteur unique) par un producteur indépendant. Lecteur de dates tolérant ; sonde du format réel dans le workflow des indicateurs de niche.
- **0.10.148** — Telegram : la clé de session est extraite du secret même si l'en-tête « === CLÉ DE SESSION … === » a été collé avec elle (passage 43752517798 : 430 caractères commençant par « = »).
- **0.10.147** — **Violations Watch en ombre** (décision d'auteur du 2026-11-15, 20 h 32) : collecteur quotidien (workflow programmé, 6 h 17 UTC) qui ne garde que des comptes pays × jour × gravité (site sans licence, éditeur anonyme, données depuis le 2026-11-06) ; indicateur « incident grave signalé dans les 14 jours » dans l'observatoire inductif, mesuré seulement sur les dates couvertes (jeux à venir).
- **0.10.146** — Telegram : la clé de session est nettoyée (retours à la ligne, espaces, guillemets collés depuis PowerShell : « Not a valid string » au passage 43750832459) ; en cas de refus, le journal donne sa longueur et son premier caractère, jamais son contenu.
- **0.10.145** — vols : « 0 arrivée puis 0 arrivée » compte comme non mesuré (régions sans récepteurs OpenSky : 45 cas sur 66) ; identifiants Telegram lus dans les secrets ou les variables (`TELEGRAM_API_ID` absent des secrets au passage 43746883769).
- **0.10.144** — vols OpenSky : 2 jours par demande (limite d'OpenSky, « 2 partitions »), 2 jours avant la date contre les 2 mêmes jours quatre semaines plus tôt ; code pays par la table d'OurAirports (la recherche précédente échouait pour 65 pays). Deuxième passage des niches : modifications Wikipedia 155/185, prix alimentaires 50/185 (le WFP couvre surtout les pays en développement).
- **0.10.143** — indicateur de niche « telegram » (décision d'auteur du 2026-11-15) : recherche globale de Telegram (tous les canaux publics, aucun choix de canaux), nom du pays, messages des 14 jours avant la date contre les 14 précédents ; session de l'auteur (`TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_SESSION` en secrets ; script `outils/telegram_session.py`) ; Telethon installé hors du verrou du bot ; dans l'observatoire inductif.
- **0.10.142** — indicateurs de niche, premier passage presque vide, corrigé : Wikipedia limitait les appels (réessais 2, 4, 8 s), la recherche HDX cherchait « WFP » dans des titres qui ne le contiennent pas (jeux « wfp-food-prices-for-<pays> »), le refus d'OpenSky est désormais noté (code et message) ; seules les mesures réussies comptent comme faites, les échecs sont retentés.
- **0.10.141** — **contexte météo, seconde version** (décision d'auteur du 2026-11-15, 17 h 34, d'après chensirui3/kalshi-weather-forecaster) : moyenne de cinq modèles mondiaux (GFS, ECMWF, ICON, GEM, ARPEGE), deux prévisions de même échéance (7 jours) pour annuler le biais vers la moyenne saisonnière, incertitude selon le désaccord entre modèles ; aucun paramètre appris ; jugée sur les jeux postérieurs au 2026-09-27 et sur des questions construites (une station Météo-France par date, dates à partir du 2026-10-04, jamais regardées), essai `contexte_meteo_v2` ; la première version est close (non atteinte).
- **0.10.140** — indicateur de niche « vols » (OpenSky Network, client API de l'auteur : `OPENSKY_CLIENT_ID` en variable, `OPENSKY_CLIENT_SECRET` en secret) : arrivées à l'aéroport principal du pays (OurAirports, le plus grand aéroport à vols réguliers le plus proche de la capitale) les 7 jours avant la date, contre les 7 jours un mois plus tôt ; dans l'observatoire inductif. NOTAM écartés par l'auteur.
- **0.10.139** — banc du contexte météo : stations d'outre-mer géocodées (codes pays RE, MQ, GF…), questions en échec retentées. Premier passage : météo 0,645 contre B 0,694 (212 questions), sens juste 69 % ; gain net dans 5 lots sur 7, pertes lourdes dans 2 (août : la prévision à 7 jours exagère le retour vers la normale après des jours chauds) ; critère non atteint.
- **0.10.138** — **indicateurs de niche** (décision d'auteur du 2026-11-15, 16 h 54) : modifications des pages politiques Wikipedia (Oswald, CISS Munich 2026) et prix alimentaires de détail du WFP sur un an (Bellemare, AJAE 2015), mesurés avant la date de chaque question du banc des indicateurs pertinents, puis passés par l'observatoire inductif (`indicateurs_niche.py`, workflow « Indicateurs de niche »). Espace aérien : bulletins EASA (CZIB) datés mais historique des révisions difficile d'accès ; NOTAM archivés payants ou limités (ICAO : 100 appels) ; OpenSky (vols par aéroport) gratuit avec compte.
- **0.10.137** — essais `desaccord` et `signaux_couteux` clos (décision d'auteur du 2026-11-15, 16 h 43) ; le piège des tests trivialement solubles inscrit dans les règles des pré-enregistrements (Hoover, Blayney et Whittington, arXiv 2026).
- **0.10.136** — décisions d'auteur du 2026-11-15 (16 h 33) : essais `b_tendance`, `b_chronos`, `indicateurs_pertinents` clos (non adoptés) ; verdicts des conflits sur la forme « une fois » seulement (« dix fois plus » trivialement soluble, décrite à part ; amendement de `jugements-intermediaires.md` avant son second regard) ; plan du contexte par régime causal (physique, macroéconomique, marchés) : `preenregistrements/contexte-par-regime.md`.
- **0.10.135** — **contexte physique** (décision d'auteur du 2026-11-15 : une série sans son contexte ne donne rien) : pour les questions de température Météo-France à 7 jours, probabilité de hausse tirée de la prévision Open-Meteo archivée avec son échéance (émise avant la date), σ = 2,7 °C fixé d'avance, aucun paramètre appris. Banc gratuit `banc_meteo.py` (workflow « Banc du contexte météo »), essai `contexte_meteo`, `preenregistrements/contexte-meteo.md`. Le test macroéconomique n'est pas faisable : environ 11 questions macro (inscriptions au chômage) dans les jeux.
- **0.10.134** — **observatoire inductif** (`induction.py`, décision d'auteur du 2026-11-15 : « réfléchir par induction plutôt que par déduction ») : chaque jeu est un lot ; pour chaque indicateur × famille × état, OUI observés contre attendus sous B ; une régularité n'est candidate que si elle garde le même sens dans au moins 3 lots sur 4 (au moins 4 lots, 20 questions). Premier passage (199 questions, 9 lots) : les deux candidates (mobilisation moins fréquente que B) s'expliquent plus simplement par B qui surestime les émeutes (5 oui pour 9,7 attendus), pas par les indicateurs.
- **0.10.133** — **conseil aux voyageurs durci** (décision d'auteur du 2026-11-15, 15 h 31 : variable retenue) : B + 0,5 logit sur les questions de violence quand le conseil s'est durci dans le mois, sens et force fixés d'avance (aucun paramètre appris ; sur les questions déjà vues, l'effet s'annule). Jugé sur les jeux à venir (`banc_indicateurs_frais.py`, essai `conseil_durci`, `preenregistrements/conseil-durci.md`). Test des indicateurs pertinents : échec (0,644 contre 0,492 pour B).
- **0.10.132** — **taux de base par modèle de fondation** (décision d'auteur du 2026-11-15, d'après arXiv 2610.07232) : probabilité de hausse lue sur la distribution prévue par Chronos-2 (modèle ouvert, sur processeur, sans réentraînement), contre B, sur les séries FRED et DBnomics. Banc gratuit `banc_chronos.py` (workflow « Banc du taux de base Chronos », torch installé hors du verrou du bot), essai `b_chronos`, `preenregistrements/b-chronos.md`.
- **0.10.131** — **taux de base récent** (décision d'auteur du 2026-11-15, étape 2) : B_tendance, mêmes intervalles que B pesés par une demi-vie de 90 jours, seulement sur les séries fréquentes (Σ poids ≥ 20) ; motivé par le garde-fou (écarts de crédit FRED : 40 % annoncés, 75 % observés). Banc gratuit `banc_bt.py` (workflow « Banc du taux de base récent »), essai `b_tendance`, `preenregistrements/b-tendance.md`.
- **0.10.130** — **garde-fou sur B** (`audit_b.py`, décision d'auteur du 2026-11-15, « institutionnaliser le doute ») : pour chaque forme de question, oui observés contre oui attendus sous B ; alerte au-delà de 3 écarts-types sur 20 questions, si l'écart se répète dans au moins 3 jeux (sinon « à surveiller », mouvement commun probable). Il aurait signalé l'erreur ACLED « dix fois » (−7,1 écarts-types, 6 jeux sur 6). Branché dans les résumés des bancs A, B, M et indicateurs pertinents. Silence : `preenregistrements/silence-a-refaire.md` (angle mort, calme réel, silence suspect).
- **0.10.129** — **indicateurs placés là où ils ont un sens** (décision d'auteur du 2026-11-15) : exploration de chaque indicateur sur chaque type d'événement et de 298 combinaisons (76 questions « une fois ») ; modèle figé (conseils aux voyageurs → violence, pluie → manifestations et émeutes) jugé sur les questions ACLED « une fois » jamais lues, sans modèle de langue (`banc_indicateurs_frais.py`, workflow « Banc des indicateurs pertinents », essai `indicateurs_pertinents`, `preenregistrements/indicateurs-pertinents.md`). L'ancien essai `indicateurs` est clos.
- **0.10.128** — décisions d'auteur du 2026-11-15 (13 h 12) après l'erreur du B ACLED : ½A + ½B n'est plus posté (`POSTER_AB = False`) ; essais `recalibrage_conflits`, `silence`, `aiguillage` clos comme caducs, `a_plus_b` suspendu ; tous à refaire avec B corrigé. La pluie est retenue comme indicateur pertinent pour les manifestations et les émeutes (test sur questions fraîches à pré-enregistrer).
- **0.10.127** — **erreur du taux de base ACLED corrigée** : pour les questions « plus de dix fois plus que un plus la moyenne », B calculait la probabilité de dépasser UNE fois la moyenne (≈ 40 % annoncés, 0 oui sur 74 questions). Seuil 10·m et moyenne m − 1 désormais. Sur les 150 questions ACLED du banc A, B passe de 0,493 à 0,241 (A : 0,443). Conséquences sur les essais : `preenregistrements/erreur-b-acled-2026-11-15.md`.
- **0.10.126** — workflows des bancs : l'étape « Enregistrer » ajoutait le registre et son résumé d'un seul `git add` ; si le résumé n'existait pas encore (passage annulé), rien n'était enregistré. Chaque fichier est maintenant ajouté séparément.
- **0.10.125** — banc des indicateurs : délai de 20 s par appel (au lieu de 60), durée imprimée par site, plafond du passage à 90 min ; les lignes déjà écrites sont gardées et un nouveau passage reprend où il s'est arrêté.
- **0.10.124** — **jugements intermédiaires avant le jugement global** (décision d'auteur du 2026-11-15, d'après la thèse d'O. Sibony, Paris-Dauphine 2017) : sur les questions ACLED jamais lues, le modèle note d'abord sept critères séparés (cartes CROISSANCE, RÉCIPROCITÉ, TRACE·MÉMOIRE, SEUIL, CONTRAINTE, PÉRIODICITÉ, PROPORTION), de 1 à 4 par rapport à l'ordinaire du pays, sans probabilité ; puis le jugement final, les notes sous les yeux. Comparé à A sur les mêmes entrées (`banc_m.py`, workflow « Banc des jugements intermédiaires », essai `jugements_intermediaires`, `preenregistrements/jugements-intermediaires.md`).
- **0.10.123** — **recalibrage et silence, à confirmer sur questions fraîches** (décision d'auteur du 2026-11-15) : paramètres figés sur les 150 questions ACLED déjà lues (Platt de A ; silence de la presse, γ = −0,44 quand aucun extrait n'est trouvé), jugés sur les questions ACLED nouvelles (`juge_silence.py`, deux essais pré-enregistrés : `preenregistrements/silence-et-calibrage.md`).
- **0.10.122** — CI réparée : depuis 0.10.111, la CI (unittest, sans conftest) échouait sur 20 tests écrits avant la règle AB ; ils coupent maintenant la règle au niveau du module. Banc des indicateurs : premier passage invalidé (ioda et pluie jamais mesurés, restcountries.com muet depuis Actions) ; repli sur le géocodage d'Open-Meteo ; écart déclaré dans le pré-enregistrement avant le second passage ; registre du banc vidé.
- **0.10.120** — `gdelt_comptes.py` et le workflow « Comptes GDELT » : comptes quotidiens d'événements par pays (manifestations, violences, menaces ; codes CAMEO 14, 18-20, 13) tirés des fichiers quotidiens publics de GDELT 1.0, pour tester les seuils de mobilisation et la croyance des acteurs (note du projet `claude/croyance-des-acteurs.md`). Limite : GDELT compte des articles codés automatiquement, pas des événements vérifiés.
- **0.10.119** — **banc des indicateurs indirects** (signaux faibles, décision d'auteur du 2026-11-15) : attention Wikipedia, coupures d'internet (IODA), changements des conseils aux voyageurs du Royaume-Uni touchant à la sécurité, anomalie de pluie (Open-Meteo), mesurés avant la date pour chaque question de conflit, ajoutés à A recalibré ; validation croisée par jeu ; essai pré-enregistré (`preenregistrements/indicateurs.md`). Gratuit, sans modèle de langue. Signaux coûteux : hypothèse non confirmée (coefficients inversés ; critère non atteint).
- **0.10.118** — **aiguillage enregistré à chaque question, en ombre** (décision d'auteur du 2026-11-15 : coder les avancées ; la participation aux tournois attendra une avancée significative). Au registre (`aiguillage`) : type et régime causal par mots clés, régimes lus dans les cartes de l'alphabet, et pour les conflits (type conflit ou strate 7/13) A recalibré (Platt, a = −1,354, b = 0,775, appris sur 150 questions ACLED : 0,414 contre 0,443 pour A en validation croisée) et ½ A recalibré + ½ B. Le bras posté ne change pas. Au banc, les mêmes champs (sans A). Calibrage : A et B surestiment fortement sur les conflits (30 % et 33 % annoncés pour 12 % de OUI).
- **0.10.116-0.10.117** — sonde des indicateurs indirects (signaux faibles, Ansoff 1975) : FMI via DBnomics accessible mais en retard d'un an ; prix alimentaires WFP (HDX) et Open-Meteo à jour ; ajout de sources niches (Wikipedia, IODA, conseils aux voyageurs du Royaume-Uni, GDACS, USGS, OpenSky).
- **0.10.115** — `type_question.py` (demande de l'auteur du 2026-11-15) : classement des questions par type (conflit, élection et politique, annonce, marché, météo, macro, santé) et régime causal, par gabarits et mots clés, SANS modèle de langue ; « indéterminé » plutôt qu'une case forcée. Sur les séries ForecastBench, chaque source tombe dans son type attendu (ACLED → conflit, températures → météo, FRED → macro). Premier regard descriptif (jeux vus) sur l'alphabet comme aiguilleur : cartes PÉRIODICITÉ → B saisonnier, TRACE·MÉMOIRE ou CONTRAINTE → B autorégressif, sinon B ; 203 questions : 0,681 contre 0,696 pour B (régime mesuré sur la série : 0,674).
- **0.10.114** — **banc des signaux coûteux** (hypothèse de l'auteur du 2026-11-15 : l'intention de celui qui parle prime sur l'information). Suite du banc du langage, dont le coefficient des actes était négatif : chaque acte est qualifié gratuit (parole seule) ou coûteux (engagement public, mobilisation, dépense, décision officielle), d'après Crawford et Sobel (1982) et Fearon (1997) ; deux coefficients, validation croisée par jeu ; essai pré-enregistré (`preenregistrements/signaux-couteux.md`). Langage comme acte : critère atteint (150 questions, 0,4415 contre 0,4434 pour A), apport modéré ; désaccord : effet nul.
- **0.10.113** — **aiguillage par régime causal** (idée de l'auteur du 2026-11-15 : types de causalité et principes actifs, classés par mécanisme mesurable). Le banc du taux de base mesure, avant la date, la saisonnalité (règle 0.10.32), l'inertie (bande de Bartlett) et l'entropie de permutation, et choisit B saisonnier, B autorégressif ou B ; essai pré-enregistré (`preenregistrements/regimes-causaux.md`) sur les questions nouvelles.
- **0.10.112** — **banc du langage** (décision d'auteur du 2026-11-15) : deux idées neuves sur les conflits, le langage comme acte (les engagements des sources, distingués des descriptions) et le désaccord comme signal (dispersion des probabilités suggérées par les sources, qui rapproche A de B). Un paramètre chacun, validation croisée par jeu ; deux essais pré-enregistrés (`preenregistrements/langage.md`). Aiguillage : critère atteint au premier regard (106 questions ACLED nouvelles, A 0,454 contre B 0,506), décision d'auteur en attente.
- **0.10.111** — **premier critère atteint : ½A + ½B** (banc du bras A, 200 questions, intervalle corrigé sous 0 ; gain concentré sur les conflits). Décision d'auteur du 2026-11-15, option prudente : le bot Metaculus poste ½A + ½B (moyenne des logits) seulement pour les événements en strate 7 ou 13 qui ont un taux de base (`POSTER_AB`, `STRATES_AB`, bras « AB » au registre et dans le commentaire) ; ailleurs, la règle précédente.
- **0.10.110** — code de jugement des deux essais du 2026-11-15 : `classes_signature.py` (l'alphabet organise la mémoire des cas : B_sig par signature de lecture, sans modèle de langue) et, dans `banc_a.py`, le critère d'aiguillage sur les questions ACLED nouvelles, avec l'option `--sources acled` (champ « sources » du workflow). Essai « motifs + A » clos avant son regard, sans adoption (décision d'auteur).
- **0.10.109** — essai des motifs ordinaux clos sans adoption (exécution 43658780674 : 585 questions, motifs moins bons que B ; entropie de permutation 0,91, séries presque sans structure ordinale). Premier passage du banc du bras A (110 questions, 1,42 $) : A 0,573, B 0,585, ½A + ½B 0,577 ; gain surtout sur ACLED ; critère A + B indécis au premier regard, second regard à 200.
- **0.10.108** — **banc des motifs ordinaux** (décision d'auteur du 2026-11-15 : « l'état précède l'essence », un alphabet découvert dans les états). `banc_o.py` et le workflow du même nom : motifs ordinaux de Bandt et Pompe (d = 3) dans la même série et à travers les autres séries du même jeu, entropie de permutation, contre B ; avec le bras A, combinaison ⅓A + ⅓B + ⅓O contre ½A + ½B. Méthodes publiées, réglages usuels, Diebold-Mariano à côté du bootstrap par blocs ; deux essais pré-enregistrés (`preenregistrements/motifs-ordinaux.md`). Gratuit, sans modèle de langue.
- **0.10.107** — banc du bras A : ordre des questions entrelacé entre les jeux (sinon les 100 premières questions tombaient dans un ou deux blocs « jeu × source ») ; amendement déclaré dans `preenregistrements/a-plus-b.md` ; les 10 lectures du premier passage sont hors critère.
- **0.10.106** — **banc du bras A** (décision d'auteur du 2026-11-15) : `banc_a.py` et le workflow du même nom jouent le jugement du modèle, qui voit les mêmes données que B (taux de base, derniers points de la série, recherche bornée), sur des séries ForecastBench résolues postérieures aux connaissances des modèles ; comparé à B et à la combinaison fixée ½ A + ½ B (logit). Essai pré-enregistré (`preenregistrements/a-plus-b.md`, `essais.py`). Registre à part ; plafond en dollars par passage.
- **0.10.105** — **banc du taux de base, premier passage** (exécution 43653595776 ; 400 questions de séries de jeux non vus, juillet-août, sans modèle de langue) : **B autorégressif et B saisonnier non adoptés**, essais clos (verdicts dans les pré-enregistrements). Le saisonnier gagne sur DBnomics, perd lourdement sur FRED ; une règle limitée à DBnomics serait un nouvel essai. Correctif : les regards du critère se font dans l'ordre même si 2N lignes arrivent d'un coup.
- **0.10.104** — **marges de B** (décision d'auteur du 2026-11-15 : jouer sur les marges de manœuvre réelles ; C reste en ombre pour tester l'ancrage). (1) `b_saison` : taux de base saisonnier pour les séries (intervalles qui commencent à ±15 jours de la même date du calendrier, 10 ans), en ombre, essai pré-enregistré (`preenregistrements/b-saisonnier.md`, `essais.py`). Motif : sur DBnomics (températures surtout), B annonce ~50 % pour 26 % de OUI. (2) `banc_b.py` et le workflow « Banc du taux de base » : B, B autorégressif et B saisonnier par le code, SANS modèle de langue, sur toutes les questions de séries ForecastBench résolues ; registre à part (`registre/banc-b.jsonl`). Ordre des questions pour les critères fixé avant calcul (jeu le plus ancien d'abord, puis identifiant). `critere_ombre_b` généralise le critère du B autorégressif.
- **0.10.103** — **ombre combinée** (décision d'auteur du 2026-11-15) : sur la lecture SANS matrice, le p du programme génératif puis la correction symétrique (`ombre_sans_matrice.combinee`). Rien n'est posté ; descriptif, hors verdict (`score_registre` : `ombre_combinee`, par lecteur, contre B et le C officiel). Limite déclarée : le génératif compte déjà les candidates contredites, la symétrie peut les recompter ; les deux composantes sont gardées à part (`p_generatif`, `p_symetrique_produit`). Contrôle préalable sur le registre (lecture officielle, 2026-11-15) : le génératif améliore C sans battre B.
- **0.10.102** — `AZURE_AI_API_BASE` lu en secret ou en variable du dépôt ; adresse de ressource seule complétée en `/openai/v1` ; message clair si elle manque (la sonde du 14 novembre l'a trouvée vide).
- **0.10.101** — Azure AI Foundry : `alphabet_modeles.adapter` traduit `azure_ai/<déploiement>` en appel OpenAI v1 (adresse et clé Azure passées à chaque appel, sans toucher `OPENAI_API_BASE`) ; modèles de raisonnement (gpt-5, o-séries) : `drop_params`, pas de température imposée. Tous les points de construction des modèles du bot passent par `am.llm`.
- **0.10.100** : **plusieurs fournisseurs, plusieurs IA** (contrainte d'auteur du 2026-11-14 ; plan dans
  `TRANSITION-FOURNISSEURS.md`). Version exacte du modèle servi relevée à chaque appel (`modeles_servis`, traceur
  litellm) ; Azure AI Foundry branché (`azure_ai/<déploiement>`, secrets `AZURE_AI_API_KEY`, `AZURE_AI_API_BASE`) ;
  réglage Mistral (top_p = 1) reconnu chez tout fournisseur ; l'ombre sans matrice se juge sur un seul lecteur
  (Mistral Medium, quel que soit le point d'accès), les autres lecteurs comptés à part.
- **Clôture de l'apprentissage des liens** (2026-11-14, décision d'auteur, hors version du bot) : arrêt à 268 lectures
  Mistral, jugement lu une fois : C empirique 0,660 contre B 0,659 en perte log, intervalle à 90 % [−0,035 ; +0,042] :
  **non adopté**. Les liens les plus fréquents de la matrice (CTR, POL, HIE → SEU) ne disent rien ; INC→SEU pousse
  sur l'apprentissage seulement. Détail dans `preenregistrements/apprentissage-liens.md`. Trois essais restent ouverts
  (B autorégressif, ombre absence, sans matrice : 35 lectures sur 50, en attente).
- **0.10.99** : **l'ombre sans matrice reçoit la boucle de correction de l'officiel** (écart de protocole déclaré le
  2026-11-14 avant le calcul de son résultat). Premier passage : 9 lectures sans matrice refusées sur 48 (19 %), contre
  0 pour l'officiel, qui a droit à deux corrections. Le compte du premier regard repart à zéro à partir de 0.10.99 ;
  les 48 lectures antérieures sont rapportées à part. Détail dans `preenregistrements/sans-matrice.md`.
- **Veille quotidienne** (2026-11-14, hors version du bot) : `veille_articles.py` lit aussi GitHub (dépôts créés dans
  la fenêtre) et Zenodo (dépôts publiés), en plus d'arXiv et de DAIR.AI ; passage chaque jour, fenêtre de 2 jours,
  12 éléments au plus, déjà vus écartés ; mots-clés ajoutés (harnais d'évaluation, runtime assurance, sélection par
  stabilité, vocabulaires contrôlés, ontologies). Motif : la prospection LinkedIn du jour renvoyait presque toujours à
  un dépôt GitHub ou Zenodo, lisibles directement.
- **0.10.98** : **règle d'adoption commune** (section ci-dessus ; `essais.py`). Quatre essais ouverts, dont trois à
  intervalle (liens empiriques, B autorégressif, ombre absence) : risque corrigé 1,7 %, intervalle à 96,7 %. Verdicts
  de B autorégressif et de l'ombre sans matrice calculés aux regards fixés (100 et 50 premières lignes, puis 200 et 100).
  Ne fait que durcir l'adoption.
- **0.10.97** : **critère d'adoption du B autorégressif, enregistré** (décision d'auteur du 2026-11-14), après le
  test rétrospectif (188 questions de séries des jeux 2026-09-27, 10-11 et 10-25 : perte log 0,666 contre 0,690 pour
  B ; gain surtout sur FRED du 25 octobre, 5 blocs seulement) et avant toute donnée nouvelle. B_AR remplacera B pour
  les séries si, sur au moins 100 questions de jeux NON VUS par ce test, sa perte log est inférieure à celle de B et
  l'intervalle à 90 % par blocs de l'écart reste sous 0 ; puis décision datée. Calculé par `score_registre`
  (`ombre_b_ar.critere`).
- **0.10.96** : **doubles permutés des liens, en ombre** (Neirz, Allende et Saavedra, *Scientific Reports* 2026 :
  le bootstrap sur un seul échantillon réutilise la même coïncidence et donne des faux positifs persistants ; la
  stabilité reste descriptive). Pour chaque lien, 100 doubles à la même rareté, indicateur permuté entre les lectures
  d'apprentissage ; `p_doubles` = part des doubles dont |z| atteint celui du lien ; « bat ses doubles » sous 0,05. Le
  rapport donne aussi le nombre de liens attendus sous ce seuil par hasard ; sous 5 cas, pas de verdict (un lien vu une
  fois « battait » ses doubles, dont la permutation était dégénérée). Au 2026-11-14 : 2 liens sur 10 testables battent
  leurs doubles (« persiste:INC » 0,03, « INC→SEU » 0,02), pour 0,5 attendu par hasard. Le critère d'adoption ne change pas.
- **0.10.95** : **FIRMS choisit le produit qui couvre la fenêtre** (sonde du 2026-11-14 : 400 sans motif, en NRT comme
  en SP). FIRMS publie les dates couvertes par chaque produit (`data_availability`) ; le premier qui couvre la fenêtre
  est pris (SNPP, NOAA-20, MODIS, standard puis temps réel), sinon l'erreur dit les plages disponibles. Même sonde :
  Census (316 points) et UCDP (1 612 événements, versions candidates comprises) répondent ; la clé BLS est refusée.
- **0.10.94** : **sonde des puits du 2026-11-14**. UCDP : le filtre `Country` attend le code Gleditsch-Ward, pas un
  nom (400 pour « Sudan ») ; table des pays fréquents (`code_gw`), code numérique accepté tel quel. Toute erreur HTTP
  ou réponse non JSON cite désormais le début de la réponse, sans clé (Census : réponse non JSON, clé pas encore
  activée ; FIRMS : 400 sans motif). BLS : un statut autre que « REQUEST_SUCCEEDED » (quota du jour, série inconnue)
  est une erreur dite, plus un relevé vide.
- **0.10.93** : **puits Census Bureau** (`census_eits` : Economic Indicators Time Series, API publique ; ventes au
  détail, mises en chantier, ventes de logements neufs, dépenses de construction, biens durables, stocks, commerce
  extérieur). Comptable, borné à la date d'information avec un retard de publication de 45 jours ; valeurs actuelles,
  sans millésime (révisions possibles, comme BLS). Clé facultative `CENSUS_API_KEY`. Ajouté à la sonde des puits.
- **0.10.92** : **second taux de base autorégressif pour les séries, en ombre** (décision d'auteur du 2026-11-14 : le
  but est la meilleure prévision possible, pas de prouver C contre B). Pour FRED et DBnomics, `b_ar` ajuste un AR(1) à
  constante sur les différences des mêmes points que B (5 ans, strictement avant D), en déduit la loi gaussienne de la
  variation à l'horizon et P(hausse) = (1 − part des intervalles sans changement) × Φ(moyenne / écart-type) ; règle
  fixée avant toute mesure (`banc_forecastbench.py`). Gardé dans `ombre_b_ar`, résumé par `score_registre`.
  `retro_b_ar.py` (workflow « Ombre B autorégressif (rétro) », gratuit, sans modèle de langue) le rejoue sur les
  questions de séries déjà au registre, séries retéléchargées avant la date d'information, et compare la perte log à
  celle de B, avec intervalle par blocs.
- **0.10.91** : **plan et lecture sans la matrice, en ombre** (décision d'auteur du 2026-11-14). Registre : 93 % des
  cartes ancrées dans la strate de l'événement et 93 % des candidates du plan sont des cartes que la matrice donne comme
  faisant apparaître la carte visée (32 lectures « CROISSANCE apparaît » sur 41 ancrent le même jeu ÉMERGENCE,
  POLARITÉ, RÉCURSIVITÉ, RÉSONANCE) : la consigne du plan montre la matrice et demande d'y choisir les candidates. Sur
  une part des questions (`ALPHABET_SANS_MATRICE_TAUX`, champ « sans_matrice » du banc, 1 par défaut au banc, 0
  ailleurs), un second plan choisit les candidates d'après les faits (matrice cachée ; événement, strates et corpus
  inchangés ; étiquettes de cartes retirées des recherches montrées), puis une seconde lecture passe le réparateur, les
  contrôles et le moteur (`ombre_sans_matrice`, lecture dans le rejeu). `apprentissage_liens.py --lecture
  sans_matrice` apprend sur ces lectures. Critère d'utilité pré-enregistré (`score_registre`, après 50 lectures) : la
  part des parents de la matrice tombe à 60 % ou moins ; à 80 % ou plus, l'ombre est inutile et s'arrête. Coût : deux
  appels de plus par question lue.
- **0.10.90** : **skill 0.7.77, frontière du contrôle de vue extérieure** (passage du 2026-11-14). Huit dossiers
  « non estimés » du banc (FRED et ACLED, tous « CROISSANCE apparaît ») avaient un rapport de cotes p₀ / B de
  10,000000000000002 : des cartes au plafond de LR donnent exactement 10, et l'arrondi flottant franchissait le seuil.
  Tolérance relative de 1e-9 dans le moteur. Correction du juge : table des bascules, 8 « non estimé » → « estimé »
  (C n'est pas posté ; l'apprentissage des liens n'utilise pas C).
- **0.10.89** : **apprentissage des liens : le jugement prend des jeux entiers** (décision d'auteur du 2026-11-14).
  Les jeux ForecastBench les plus récents, en entier, jusqu'à couvrir au moins le tiers des lectures, servent au
  jugement ; les plus anciens à l'apprentissage ; un jeu n'est jamais coupé. Choisi sur le principe (séparation dans
  le temps, texte du protocole), pas sur les résultats, que l'auteur et Claude avaient vus pour les trois variantes.
  L'ancien découpage reste calculé en ombre (`ombre_ancien_decoupage`).
- **0.10.88** : **bootstrap par blocs « jeu × source », en ombre** (dépôt calibrain-harness : des décisions qui se
  recouvrent valent moins que leur nombre). Les questions d'un même jeu et d'une même source partagent la même semaine
  du monde. `apprentissage_liens.py` donne, à côté du critère officiel, l'intervalle de l'écart et la stabilité des
  liens tirés par blocs entiers. Au 2026-11-14 : stabilité de « persiste:INC » 76 % par lecture, 66 % par blocs ; le
  tiers de jugement ne compte que **2 blocs** (`2026-10-11:fred` 43 lectures, `2026-10-11:dbnomics` 2) : le découpage
  par nombre de lignes, trié par identifiant, met presque toutes les questions FRED du dernier jeu au jugement.
  Signalé ; le critère officiel ne change pas sans décision.
- **0.10.87** : **deux contrôles sans coût** (Al Mamun, « From Data to Decision », ch. 10, 12, 32, 50). (1) Stabilité
  des liens, en ombre, dans `apprentissage_liens.py` : part de 200 tirages bootstrap où l'intervalle reste du côté du
  statut ; seuil 80 %. Au 2026-11-14, « persiste:INC retient » : 76 %, **limite**. Le statut du protocole ne change
  pas. (2) `controle_regles_series.py` : taux de déclenchement des règles d'ancrage par les séries sur des séries de
  substitution sans structure. CROISSANCE se déclenche sur 5 % du bruit blanc, 10 % d'une marche aléatoire et 22 %
  d'une marche avec dérive, contre 4 % sur les séries réelles du registre (102) : la règle ne distingue rien du bruit.
  PÉRIODICITÉ ne se déclenche presque jamais ; INCERTITUDE, 0 à 2 % sur le bruit contre 4 % sur le réel (4 cas). Aucun
  effet sur le p : outils d'analyse seulement.
- **0.10.86** : **sources sans B par le code écartées du banc** (passage du 2026-11-14, jeu 2026-09-27 : actions
  seules et questions Wikipedia, Elo d'échecs et vaccins ; 13 « sans_vue » sur 14, la vue extérieure du modèle refuse
  d'estimer le taux de base ; aucune lecture, mais comptées dans n). Elles ne sont plus jouées tant qu'aucun B calculé
  par le code n'existe pour elles (`sans_b_code` ; `ALPHABET_FB_SANS_B=1` les rouvre, comme une relecture
  `memes_que`). Correction du harnais, pas du juge : table des bascules vide.
- **0.10.85** : **règles de changement écrites** (section ci-dessus) : table des bascules (`rejeu_banc.py --bascules`,
  `comparer_bascules.py`, contrôle des demandes de fusion), juge et lecteur dans des versions distinctes, plafond en
  dollars par passage du banc (`--budget`, 15 $). Aucune règle de lecture ni de calcul ne change : table des bascules
  de cette version vide.
- **0.10.84** : **cartes ancrées en surnombre** (banc du 2026-11-14 : cinq cartes ancrées en strate 7, refus maintenu
  sur trois lectures ; chaque ancrée est une candidate et le moteur en refuse plus de 4 par strate). Le réparateur
  retire les ancrées au-delà de 4 (carte de l'événement gardée d'abord, puis F, contre-candidates, recherches, plan,
  ordre du lecteur) ; la consigne de lecture dit « au plus 4 ». Version mixte (juge et consigne, voir règle 2) ; table
  des bascules du juge (code 0.10.83 contre 0.10.84, 178 lignes) : 1 refus devient estimé (`acled:f1f34d2f…`), aucun
  autre verdict ni p ne change (`fred:GASREGW`, compté d'abord, avait été sauvé par une version antérieure).
- **0.10.83** : **nouveau départ à contexte vide, en ombre** (billet « idea basins », Bespoke Labs ; registre : la
  première correction aboutit 16 fois sur 16, la deuxième ne sauve aucun dossier, 0 sur 12). Au moment de la deuxième
  correction, une lecture neuve est faite avec la consigne d'origine et une ligne nommant la règle enfreinte, sans
  l'historique ; elle passe le réparateur, les contrôles et le moteur, et son statut est gardé à part
  (`ombre_nouveau_depart`, lecture dans le rejeu). La boucle officielle et l'apprentissage des liens ne bougent pas.
- **0.10.82** : **B posté là où C est estimé** (décision d'auteur du 2026-11-14 ; `POSTER_C = False`). Au banc, en
  strate 7, C fait 0,87 de perte log contre 0,59 pour B (27 questions ACLED) ; au premier passage d'apprentissage, 10
  questions ACLED chiffrées, C moyen 0,62, aucune résolue OUI. C reste calculé, scellé et journalisé en ombre ; le
  commentaire publié le donne comme non posté. Règle revue à la fin de l'apprentissage des liens.
- **0.10.81** : premier passage d'apprentissage (50 questions, Mistral Medium) : un dossier refusé parce que
  source_url était rendue comme une liste d'une adresse ; le réparateur la remet en forme (première adresse ; espaces
  retirés), sans rien inventer.
- **0.10.80** : **apprentissage empirique des liens** (`apprentissage_liens.py` ; protocole enregistré le 2026-11-14,
  décision d'auteur : le sens et la portée d'un lien carte → événement se mesurent sur les issues). Lecteur unique
  Mistral Medium ; seules les lignes du banc à partir de 0.10.80 comptent. logit P = logit B + Σ β·lien, a priori
  normal (écart-type 0,5), β négatif permis ; deux tiers anciens pour apprendre, le tiers récent pour juger. Statut de
  chaque lien : pousse, retient, ne dit rien, indéterminé (intervalle à 90 %, 30 cas au moins). Critère d'adoption
  (fixé d'avance) : sur au moins 100 lectures de jugement, perte log du « C empirique » sous celle de B, intervalle à
  90 % de l'écart apparié sous 0 ; même alors, en ombre, et remplacement de la matrice par décision d'auteur datée.
- **0.10.79** : **suite du diagnostic de la surconfiance de C** (décision d'auteur du 2026-11-14). Les duels d'actions
  yfinance ne sont plus lus au banc (ni écrits ni comptés ; B = 0,5 par symétrie ; C y faisait moins bien que B ;
  `ALPHABET_FB_DUELS=1` ou une relecture `memes_que` les rouvrent). Règle « fond ou dynamique » (`ombres_auto.est_fond`,
  fixée avant mesure) et `diagnostic_levee.py` (rejeu : multiplicateurs réduits, levée par nombre de cartes et par
  lien, C sans les faits de fond), à refaire à chaque palier. Premier passage : retirer les faits de fond améliore C
  sans l'amener au niveau de B, et les lectures qui gardent des faits « dynamiques » sont les plus surconfiantes : la
  règle n'isole pas le signal ; elle n'entre pas dans le calcul.
- **0.10.78** : **trois corrections après le banc du 2026-11-13** (20 questions). Ombre des séries : au banc, la série
  que le banc télécharge pour B (FRED, DBnomics) lui est transmise, bornée strictement avant la date d'information
  (le puits du bot n'est pas appelé pour ces questions : 0 cas mesuré). Ombre du filtrage : faits perdus comptés par
  règle (doublon, hors question ; 10 faits perdus sur 50 au premier passage). Réparateur : au plus 4 candidates par
  strate, en gardant les cartes ancrées, les contre-candidates, les cartes visées par une recherche, puis celles du
  plan ; les autres sortent, avec leur rejet, et c'est tracé.
- **0.10.77** : **strate illisible** : le contre-exemple trouvé par les tests par propriétés est corrigé. Un mot dont la
  strate reste illisible après normalisation est retiré par le réparateur, et la réparation est tracée ; la lecture
  continue avec les autres mots au lieu de tomber entière.
- **0.10.76** : **tests par propriétés** (`tests/test_proprietes.py`, Hypothesis, dépendance de développement). Des
  centaines de dossiers tirés au hasard contre les règles affirmées par le code : le réparateur ne fait qu'affaiblir ;
  la combinaison publiée reste une probabilité et ne baisse jamais quand on ajoute une source (matrice à λ ≥ 1, freins
  en ombre) ; l'ombre « absence » ne dépasse jamais B ; le rejeu est déterministe. Tout tient, sauf un contre-exemple :
  un mot à strate illisible (absente, vide, « x ») fait planter le réparateur au lieu d'être retiré, et la lecture
  entière tombe (test marqué « échec attendu » en attendant la décision).
- **0.10.75** : **calibration par sous-groupe**, en ombre (Decker et Tresp 2026, arXiv 2611.03592 : une calibration
  correcte en moyenne peut cacher de gros écarts par horizon ou par sous-groupe). Banc : par source, strate de
  l'événement, horizon, lecteur ; bot Metaculus : par horizon (≤ 30 j, 31-90, 91-365, > 365) et strate. Pour B et C :
  effectif, moyenne annoncée contre fréquence observée, Murphy (5 bacs), AUC ; groupe de moins de 30 marqué « petit ».
  Le banc ne joue qu'un horizon (7 jours, premier horizon résolu de chaque question) : pas de mélange d'horizons.
- **0.10.74** : **FRED sans millésime** (banc du 2026-11-13 : SP500 refusé en 400, seul échec FRED du registre ; la
  clé fonctionne pour les autres séries). Quand FRED refuse le millésime ALFRED, la série publiée aujourd'hui est
  relue, coupée à la date d'information, et le relevé le dit (« millésime indisponible »).
- **0.10.73** : **deux tâches du modèle refaites par le code, en ombre** (`ombres_auto.py`, décision d'auteur ; règles
  fixées avant toute mesure). Filtrage des recherches : passages en double ou sans aucun mot de la question retirés
  (jamais les relevés des puits) ; on mesure la part de texte économisée et les faits ancrés qu'il aurait fait perdre
  (adoptable seulement à 0). Ancrage par les séries : CROISSANCE (hausse qui s'accélère), PÉRIODICITÉ (au moins
  quatre sommets régulièrement espacés, période constatée), SEUIL (seuil de la question franchi sur les 10 derniers
  points), INCERTITUDE (volatilité récente ≥ 1,5 fois l'ensemble), lues dans les relevés des puits et comparées à la
  lecture du modèle carte par carte. Rien ne change dans ce que lit le modèle ni dans p ; bilan dans le rapport du
  banc (`ombres_auto`).
- **0.10.72** : **triplets jugés sur ce que le vérificateur voit** (passage 43488958193 : 10 triplets sur 10 écartés
  pour erreur du narrateur ; leurre réalisé au lieu d'être évoqué 8 fois sur 10, accord avec des cartes en trop 9 fois
  sur 10). Validité relative : l'accord montre les mêmes cartes que l'ancre, le leurre les mêmes moins la sienne
  (« à une carte près » rapporté à part, jamais compté). Une réécriture par texte refusé, avec le motif du refus
  (réécritures et sauvetages comptés : à abandonner si elles ne sauvent rien). Exemple de quasi-réalisation dans la
  consigne du leurre. Une ligne par situation dans le journal ; situations écrites au fur et à mesure
  (`registre/partiel-monde-synthetique.json`, hors de tout cumul) et enregistrées même après un arrêt.
  Rejoué sur le passage du 13 novembre, le seul critère relatif ne sauve aucun triplet (2 accords valides, 0 leurre) :
  le leurre est le goulot.
- **0.10.71** : **discrimination et accord entre lecteurs**, en ombre, hors critère. Chaque comparaison de bras
  donne l'AUC de chacun (part des couples OUI/NON bien classés, indépendante de la calibration). Le rapport du banc
  donne l'alpha de Krippendorff (nominal) entre lecteurs sur les mêmes questions : carte de l'événement, carte et
  type, statut. Premiers chiffres (43 questions estimées) : AUC B 0,55, C 0,57 ; C classe à peine mieux que B.
- **0.10.70** : **ombre « absence »** (hypothèse enregistrée le 2026-11-13, décision d'auteur). Constat exploratoire
  sur le banc (jeu du 2026-10-25) : sur 11 états nuls d'absence (structure absente, carte visée absente), 1 OUI pour
  3,9 attendus par B, alors que B est calibré sur l'ensemble (60 OUI pour 59,5) ; les angles morts ne montrent rien
  (4 sur 5, surtout des duels d'actions à 0,5). Hypothèse : sur les états nuls d'absence À VENIR, B à cote × 0,5 bat
  B en perte log. Facteur fixé, jamais ajusté ; seules comptent les lignes à partir de 0.10.70 (séquence de
  confiance, hypothèse principale de sa famille) ; jamais postée. C'est aussi la moitié que le moteur ne sait pas
  exprimer (multiplicateurs ≥ 1, décision 9) : un premier élément pour la rouvrir le moment venu.
- **0.10.69** : **étape 2, cohérence du moteur** (`verif_moteur.py`, rien n'est corrigé ni écrit au registre). Chaque
  calcul est recoupé par une bibliothèque indépendante, sur les mêmes entrées (157 paires B et 48 paires C résolues du
  banc) : Brier et perte log (scikit-learn, properscoring), Wilson (statsmodels), loi Beta (scipy), recalibration
  logistique avec et sans rappel (statsmodels), AR(1) du taux de base (statsmodels, arch) : identiques à la précision
  machine. Décomposition de Murphy du moteur : identique à scikit-learn une fois la convention des bords alignée (le
  moteur range p = 0,5 dans le bac [0,5 ; 0,6[, scikit-learn dans [0,4 ; 0,5] ; 54 valeurs B sur un bord). Inférence
  séquentielle : couverture simulée 100 % (bot et moteur) et 98 % (confseq), largeur proche de confseq (+5 % pour
  score_registre) ; fausses alarmes de l'e-valeur à tout instant 1,5 % (≤ 5 %). Seuils du compte AR(1) contre
  Dickey-Fuller : le mélange s'ouvre à t < −2,5, entre les valeurs critiques à 10 % (−2,58) et 5 % (−2,89) ; 13 % des
  marches aléatoires de 120 points y entrent (avec un poids faible) ; AR(1) seul à t < −3,5 : 1 %, au niveau 1 %.
  Dépendances hors du bot ; confseq demande deux retouches de compilation (voir l'en-tête du script).
- **0.10.68** : **recherches et candidates** (banc multi-lecteurs, Mistral Medium sur les 20 questions de 0.10.55 :
  10 dossiers refusés, tous parce que les recherches du plan visaient des cartes absentes des candidates de la lecture ;
  Sonnet les recopiait, Mistral jamais). Le réparateur retire d'une recherche les cartes absentes des candidates (il ne
  les ajoute pas : les classer « non cherchée » ferait d'un état nul un angle mort et relancerait des recherches) ; une
  recherche sans carte sort du dossier (Spéculatif). La consigne demande de recopier candidates et contre-candidates du plan, et
  rappelle que transfert et écho ne relient jamais deux cartes d'une même strate. Rejeu des 20 lectures : 17 estimées,
  3 états nuls, 0 refus (contre 7, 3, 10 enregistrés).
- **0.10.67** : **triplets durs du monde synthétique** (d'après Blair, Procaccia et Tambe, « Embeddings for
  Preferences, Not Semantics », NeurIPS 2026 ; décision d'auteur du 2026-11-13). Le test d'invariance que l'alphabet
  n'avait jamais passé : une carte se lit-elle pareil quels que soient le domaine et les mots ? Pour chaque situation
  lue (l'ANCRE), le narrateur écrit un ACCORD (mêmes cartes cachées, strate 13 ou 6, autres acteurs, autre vocabulaire)
  et un LEURRE (même canevas, une carte présente écrite en quasi-réalisation : évoquée, annoncée, approchée, démentie,
  jamais réalisée). Mesure : triplet réussi si les cartes lues dans l'accord sont plus proches de l'ancre que celles du
  leurre (0,5 = hasard) ; la carte du leurre est-elle discriminée ou suivie par la surface ; invariance moyenne
  (Jaccard ancre-accord). Entrée `triplets` du workflow (0 par défaut : quatre appels de plus par situation).
- **0.10.66** : **UCDP** (clé reçue le 2026-11-13 ; 5 000 requêtes par jour). Version annuelle 26.1 (jusqu'à fin
  2025) prolongée par les versions **candidates** mensuelles (26.0.X, moins vérifiées, marquées « [candidat] »). Un
  mois n'est lu que si sa version était publiée à la date limite (prudence : fin du mois suivant), pour qu'un test
  rétrospectif ne lise pas une donnée sortie après sa date d'information. `UCDP_CANDIDAT=0` les coupe. (0.10.65 :
  version 26.1 par défaut.)
- **0.10.64** : **quatre pistes de Snowden** (skill 0.7.76, décision d'auteur du 2026-11-13, `validation.md` §52). (1)
  Tiers de POLARITÉ : la consigne demande au lecteur ce qui se tient hors des deux camps (médiateur, arbitre,
  abstention, ou « aucun ») ; un tiers mal formé ou hors de POL est retiré, un troisième pôle stable retire POLARITÉ
  (il contredit sa garantie) ; les tiers sont relevés au registre (`tiers_polarite`), sans effet sur p. (2) Période
  constatée, jamais postulée, et sans état « normal ». (3) Le commentaire publié nomme C une propension, non une
  affirmation causale. (4) `foret_strates.py` compte, dans les lectures gardées par le rejeu, les cartes ancrées hors de
  la strate de l'événement et celles qu'une liaison déclarée entre strates y relie (hypothèse de la forêt pour l'arbre
  de la connaissance). Monde synthétique : protocole 11. (0.10.63 : sondes Mistral, SambaNova et Cerebras.)
- **0.10.62** : **banc des petites tâches** (décision d'auteur du 2026-11-13 : NVIDIA pour les tâches courtes, à
  condition de mesurer jusqu'où chaque modèle est fiable). `banc_petites_taches.py` et le workflow du même nom
  soumettent à d'autres modèles les MÊMES consignes courtes que Claude a reçues sur les questions ForecastBench d'une
  version passée (0.10.55 par défaut) : le plan et la sonde de connaissance. Mesures : tenue (délai, JSON lisible),
  plan recevable, accord avec la référence (hors alphabet ou non, carte, strate, type ; « connait »), et chaque écart
  listé. Claude Haiku sert de témoin : son accord avec Sonnet dit ce qu'est un « bon » accord. Rien n'est écrit au
  registre.
- **0.10.61** : au banc, une question jugée hors alphabet garde son B (calculé par le code avant toute lecture) ; il
  manquait à la ligne. 0.10.60 : `sonde_nvidia.py` et le workflow « Sonde NVIDIA » (appels directs, sans litellm :
  code HTTP, délai jusqu'au premier octet, réponse). Le 2026-11-13 à 2 h 30 : Nemotron 3 Ultra et MiniMax M3.1 Flash
  répondent ; DeepSeek V4.1 Flash, GLM-5.3 Flash, Gemma 4 31B et gpt-oss-20b, listés, n'envoient rien en 120 s.
- **0.10.59** : **délais imposés par le bot**. Le premier essai de DeepSeek V4.1 Flash (NVIDIA) est resté bloqué 44
  minutes sur la sonde de disponibilité, sans erreur : le délai confié à la bibliothèque n'a pas été tenu. La sonde
  abandonne maintenant à 90 s (`ALPHABET_SONDE_DELAI`) avec une erreur lisible (passagère : ressayée deux fois), et
  au banc chaque appel au modèle abandonne à 600 s (`ALPHABET_APPEL_DELAI`), compté comme panne du harnais.
- **0.10.58** : **test multi-lecteurs** (décision d'auteur du 2026-11-13). Le banc accepte deux entrées : `lecteur`
  (le modèle principal de CE passage : plan, lecture, bras A) et `memes_que` (relire les questions jouées par une
  version passée, ex. 0.10.55). Une question déjà lue par un autre codeur peut être relue ; le registre note le codeur
  de chaque ligne, et le rejeu compare les lectures à réparateur et moteur égaux. Si le lecteur demandé ne répond pas,
  le passage s'arrête : pas de repli silencieux sur un autre modèle, qui fausserait la comparaison. NVIDIA (offre de
  développement, banc et monde synthétique seulement, jamais le tournoi) : secret `NVIDIA_API_KEY`, modèles
  `nvidia_nim/<identifiant>` (ex. `nvidia_nim/deepseek-ai/deepseek-v4.1-flash`).
- **0.10.57** : **septième passage ForecastBench (bot 0.10.55) : aucun refus** ; 18 lectures chiffrées sur 20, 2 états
  nuls, « averti » employé 4 fois, aucune liaison hors liste. **Premier rejeu** (sans modèle) des 20 lectures : il
  redonne exactement les p enregistrés, et il a révélé un défaut que la correction du lecteur masquait. Quand le
  réparateur affaiblit un mot (F → f), l'état n'était pas recalculé : le moteur refusait le dossier (« force
  contradictoire ») et une correction payée du lecteur rattrapait l'écart. L'état suit désormais les réparations.
  Le rejeu garde aussi les dates présentes dans les résultats (`dates_corpus`, pas le texte), pour rejouer le retrait
  des faits futurs.
- **0.10.56** : **empreintes des sources** (idée reprise du reçu de NightFalcon, Intuit ; décision d'auteur du
  2026-11-12). Le texte des résultats de recherche reste hors registre ; chaque recherche enregistrée porte désormais
  l'empreinte SHA-256 de son texte et sa longueur (`recherches`, `rejeu`). Chaque passage cité par le lecteur est lié à
  l'empreinte du résultat qui le contient (`empreintes_passages`), ou à rien s'il ne figure dans aucun : on pourra
  prouver plus tard qu'un passage venait bien de la recherche, et voir si une page a changé depuis. Aucun effet sur
  aucun p.
- **0.10.55** : **sixième passage ForecastBench (bot 0.10.53)** : 16 lectures chiffrées sur 20 (3 en strate 7, 13
  exploratoires), 1 état nul, 3 refus. Corrigé : un rejet rendu en liste sans clé « carte » devenait « ?0 », que le
  moteur refusait (2 refus) ; la carte est maintenant cherchée sous d'autres noms, ou dans une valeur « ABR@s », et
  un rejet sans carte lisible est ignoré. Une liaison d'une strate posée entre deux strates (« TRC@6 tension POL@7 »)
  est retirée, et la consigne dit quels types vont où. Le dossier refusé est gardé en strate 7 aussi. Monde
  synthétique : protocole 10.
- **0.10.54** : **rejeu et pannes** (d'après un article sur les harnais d'évaluation, décision d'auteur du
  2026-11-12). (1) Chaque ligne du banc garde les lectures brutes du lecteur (la première et les corrections), le
  plan et l'événement (`rejeu`). `python rejeu_banc.py` les repasse par le réparateur et le moteur actuels, sans
  modèle et sans coût : on mesure une correction sur les MÊMES lectures, au lieu de comparer des passages qui n'ont
  aucune question en commun. Limites : le retrait des faits futurs et la boucle de correction ne sont pas rejoués.
  (2) Trois issues au lieu de deux : une panne du harnais (réseau, service, délai, exception du banc) n'est plus un
  « refus » ni un « JSON illisible » ; statut `panne`, écrite pour le diagnostic, exclue des taux, et la question
  sera refaite. Trois pannes de suite arrêtent le banc. Une panne n'est plus reprise sous le motif « JSON invalide ».
- **0.10.53** : **ombre « avec liaisons »** (décision d'auteur du 2026-11-12). Les liaisons du dossier n'atteignaient
  pas le calcul (sauf « averti ») : un transfert déclaré ne changeait rien au p. Quand un dossier chiffré garde des
  liaisons, le bot le recalcule avec toutes (`p_avec_liaisons`, dans `ombre_causale`) : le transfert lève la décote
  entre strates, l'inclusion et le renforcement ne gardent qu'une des cartes redondantes. Le p publié ne change pas ;
  le score compare `C_avec_liaisons` à C sur les mêmes questions. Aucun changement du skill.
- **0.10.52** : **averti** (skill 0.7.75, décision d'auteur du 2026-11-12, `validation.md` §51). Nouvelle liaison
  « A averti B » : observer A renseigne sur B sans agir sur B ; seule liaison qui peut viser l'événement. Elle va au
  moteur (`--liaison`), où elle n'ouvre que l'ombre `mixte_averti` (indices en produit, autres sources en noisy-or) ;
  le p publié ne change pas, et les autres types restent au dossier comme avant. Les liaisons hors liste ne sont plus
  seulement retirées : elles sont gardées à part (`_liaisons_hors_liste`, et `liaisons_hors_liste` dans la ligne du
  banc), pour compter les verbes que le lecteur invente. **Défaut trouvé en chemin** : le moteur exige une preuve par
  liaison (`preuves_liaisons`), que la consigne ne demandait pas ; tout dossier qui gardait une liaison aurait été
  refusé. La consigne la demande ; une liaison sans preuve, ou vers un mot absent de l'état, est retirée (tracé). Les
  preuves suivent leurs liaisons quand une carte est retirée. Monde synthétique : protocole 9 (consigne changée en
  0.10.51 et 0.10.52 ; le passage à 9 manquait en 0.10.51).
- **0.10.51** : **cinquième passage ForecastBench : premiers C exploratoires chiffrés** (7 sur 20), 5 états nuls
  justifiés, 8 refus restants, tous des écarts du lecteur aux règles de forme. Corrigé, par la conséquence écrite de
  chaque règle et dans la consigne : type de liaison hors de la liste (5 refus : « informe », « renforce »,
  « coexiste », « borne », « alimente ») → liaison retirée, liste des types dans la consigne ; « independantes » avec
  une seule source → « unique » ; extrait de plus de 300 caractères → coupé ; garantie dont le support est postérieur
  à la date d'information (B1, une fuite en rétrospectif) → retirée ; strate sans seconde candidate → une voisine de
  la carte ancrée (fiche du skill), « non cherchée » ; toute candidate sans motif de rejet → « non cherchée ».
- **0.10.50** : **TinyFish en relais d'Exa pour les tests rétrospectifs et le banc ForecastBench** (décision d'auteur
  du 2026-11-12 : les crédits peuvent s'arrêter à tout moment). Ordre « exa,tinyfish,gdelt » (variable
  `ALPHABET_RETRO_ORDRE`). TinyFish ne sait pas borner par date : seules ses pages DATÉES et antérieures à la date
  d'information sont gardées (moins de résultats ; petit risque résiduel d'une page antidatée ou mise à jour). Les
  deux scripts démarrent avec Exa OU TinyFish ; chaque ligne du banc trace les moteurs qui ont servi
  (`moteurs_recherche`), pour qu'une mesure de l'étape 2 puisse être séparée selon le moteur.
- **0.10.49** : **consigne du lecteur précisée**, pour que les règles d'ancrage soient respectées à la lecture plutôt
  que réparées après coup (décision d'auteur du 2026-11-12). Écriture des cartes (ABR, strate entière, ABR@strate) ;
  portée OBLIGATOIRE pour chaque mot et sa conséquence A7 en clair ; test parmi les quatre valeurs ; ligne a6 avec la
  liste exacte des VOISINES À PASSER pour chaque candidate (calculée depuis le moteur) ; forme exacte d'une question
  (si_oui ≠ si_non, « indetermine », resolution, justification). Les réparations de la 0.10.48 restent en filet.
  Monde synthétique : protocole 8.
- **0.10.48** : **quatrième passage ForecastBench** : les refus de FORME ont disparu ; ceux qui restaient (18 sur 20)
  venaient des règles d'ancrage du skill, que le lecteur ne respectait pas hors strate 7. `reparer_dossier` applique
  désormais la conséquence ÉCRITE de chaque règle au lieu de faire refuser tout le dossier, et n'affaiblit jamais
  qu'une lecture : A7 (portée absente → mot non retenu ; dominante → rejet ; substantielle sur F → f avec
  force_initiale F ; substantielle sur f → rejet) ; F dont l'A6, le test ou la garantie ne passent pas → f ; test ou
  garantie mal formés sur un f → retirés. Questions de discrimination réparées dans la forme (branches normalisées,
  branche décorative → « indetermine », justification et résolution manquantes inscrites comme « non fournies par le
  lecteur ») ; s'il n'en reste aucune, le bot en pose une sur la carte ancrée, signalée. Vérifié sur les 15 dossiers
  refusés du passage : plus aucune erreur A6/A7.
- **0.10.47** : **troisième passage ForecastBench** : les refus du passage précédent ont disparu, il en restait un seul
  type (15 sur 16) : la vue calculée n'avait pas `ecart_critere`, exigé par le moteur depuis 0.7.44. Ajouté, avec un
  écart honnête pour ACLED (taux stable supposé, rafales des conflits) ; un rejet sans motif devient « non cherchée ».
  Un test vérifie désormais la vue calculée contre la validation du MOTEUR, pas seulement celle du bot. La vue
  calculée est gardée dans chaque ligne (`vue_calculee`) pour vérifier B. Cohérence de B vérifiée : SOFRINDEX, indice
  cumulé toujours croissant, reçoit 0,999 et se résout OUI.
- **0.10.46** : **deuxième passage ForecastBench (20 questions, 0.10.45)** : B calculé par le code pour 19 sur 20 (Brier
  de B 0,26 : des marches aléatoires, à peine mieux que pile ou face, comme attendu), mais les lectures exploratoires
  restaient refusées pour la forme. Corrigé : la vue calculée porte la résolution de la question (4 refus « résolution
  requise ») ; `reparer_dossier` donne la strate de l'événement à une clé qui n'en a pas (4 refus « not enough values
  to unpack »), fait entrer une carte rejetée dans les candidates ou retire son rejet (5 refus « rejets seulement pour
  des candidates »), ajoute une contre-candidate manquante ; FRED sans millésimes ALFRED (SP500) : valeurs actuelles
  bornées à D. Un refus exploratoire garde désormais sa dernière erreur et son dossier, pour être diagnostiqué.
- **0.10.45** : **un événement « programmé » sans qui ni engagement n'est plus refusé** (décision d'auteur du
  2026-11-11 : une question manquée coûte des points ; il faut toujours une proposition, et cohérente). La consigne du
  plan demande `programmation {qui, engagement}` ; sans réponse, la règle du skill (0.7.16) s'applique telle qu'elle
  est écrite : l'événement n'est pas programmé et il est traité comme générique (`programmation_absente` au dossier).
  Avec qui et engagement, il reste programmé ; la vue extérieure du bot étant une référence de domaine, il est chiffré.
- **0.10.44** : **les quatre défauts du premier passage ForecastBench** (décision d'auteur du 2026-11-11 : les régler
  avant d'ouvrir le banc aux questions de marché). (1) **Refus de forme** (8 lectures exploratoires sur 14) : le
  lecteur est normalisé avant validation (`code_carte`, `entier_strate`, `cle_normale` : « POLARITÉ », « POL@6 »,
  « 13_portee » ne font plus d'erreur Python) ; `reparer_dossier` retire les liaisons illisibles, garde l'ancrage d'une
  carte aussi rejetée, complète les candidates d'une strate depuis le plan (rejet « non cherchée », effort 0) ; tout
  est tracé (`_reparations`). Un événement « persiste » sur une carte que le lecteur ne trouve pas devient un état nul
  (pas d'ajustement), non un refus. (2) **B sans vue sur ACLED** : le banc calcule B lui-même à partir de la valeur
  de référence au gel (binomiale négative, Jeffreys). (3) **« carte inconnue : POL@6 »** : la normalisation du plan.
  (4) **Marches aléatoires** : B calculé par le code (part des hausses sur 5 ans pour FRED et DBnomics, 0,5 par
  symétrie pour les paires d'actions) ; C y reste normalement un état nul, ce qui est la bonne réponse. La règle L7
  (C chiffré en strate 7 seulement) ne change pas : hors strate 7, C est exploratoire et scoré à part.
- **0.10.43** : **banc ForecastBench** (décision d'auteur du 2026-11-11). `banc_forecastbench.py` et le workflow
  « Banc ForecastBench » jouent B et C sur des questions ForecastBench (Forecasting Research Institute, CC BY-SA 4.0)
  déjà résolues, tirées de séries (FRED, DBnomics, Yahoo Finance, ACLED, Wikipedia ; environ 145 par jeu au premier
  horizon), à leur date d'information, recherche Exa bornée, sonde de connaissance de l'issue. Les questions de
  marché (cote de la foule au gel) ne sont jamais jouées (§26). Lignes dans `registre/retro.jsonl` (banc
  « forecastbench », coût par question) : le score rétrospectif les compte (biais de C, correction, C contre B,
  `forecastbench` à part) et l'apprentissage des λ les lit. Skill vendu 0.7.74 (valeur attendue de l'information,
  `validation.md` §50).
- **0.10.42** : **skill 0.7.73, freins en ombre** (décision d'auteur du 2026-11-11, `validation.md` §49). Vérification
  faite : les événements calculés du bot et du banc sont tous « SEUIL apparaît », qu'aucun frein ne vise ; les freins
  ne pouvaient presque rien au score. Ils sortent du C publié (qui redevient celui de la 0.10.40) ; l'ombre
  `ombre_causale.avec_freins` les enregistre ; le score `freins` compare C avec freins à C et à B sur les questions où
  ils jouent ; λ_I s'apprend toujours (les freins lus sont comptés). Pour le score, le levier reste C corrigé, l'ombre
  générative et les λ appris.
- **0.10.41** : **skill 0.7.72, les freins** (décision d'auteur du 2026-11-11, `validation.md` §48). Six arêtes
  inhibitrices (λ_I = 0,556) entrent dans le calcul publié : une carte lue peut désormais faire baisser C sous B
  (CONTRAINTE ⊣ CROISSANCE, HIÉRARCHIE ⊣ ÉMERGENCE, TRACE·MÉMOIRE ⊣ TRANSFORMATION et ÉMERGENCE, INCERTITUDE ⊣
  CROISSANCE, POLARITÉ ⊣ COMMUNAUTÉ) ; le produit des λ est borné à [1/10 ; 10]. Bot : λ_I appris comme quatrième
  classe (`apprentissage_lambda.py`) ; score `freins` (gain de C sur B avec et sans frein lu) ; calcul de puissance
  borné des deux côtés.
- **0.10.40** : **puits DBnomics** (décision d'auteur du 2026-11-11, repéré dans FinceptTerminal). Une API gratuite,
  sans clé (Banque de France, Cepremap), pour les séries de près de 80 fournisseurs : FMI, OCDE, BCE, Eurostat, BIS,
  OIT, instituts nationaux — l'OCDE et le FMI, laissés de côté le 8 novembre (SDMX trop lourd), deviennent accessibles.
  `dbnomics` (comptable, `serie` = fournisseur/jeu/code) et `dbnomics_recherche` (trouver le jeu). Bornage à la date
  d'information par retard de publication selon la fréquence ; les projections du FMI (périodes futures) sont écartées.
  Valeurs actuelles, sans millésime. À confirmer par la sonde des puits.
- **0.10.39** : **gain de C selon la marge de B, et partition de Murphy**, descriptifs (d'après Jenkins et Cardei,
  arXiv 2611.10325 : un gain se mesure à la place qui restait). Score : `comparaison.marge_B` (gain normalisé de Hake
  en Brier, (Brier_B − Brier_C) / Brier_B, et gain log de C sur B par tiers de marge de B) et
  `comparaison.partition_murphy` (fiabilité, résolution, incertitude pour A, B, C, sur cinq bacs). Le test principal
  reste le gain apparié C − B ; rien ne change au calcul ni au chiffre posté.
- **0.10.38** : **provenance des F vérifiée hors du modèle**, en ombre (décision d'auteur du 2026-11-11, d'après
  « The Corroboration Illusion », arXiv 2609.22246 : un LLM prend tout texte pertinent pour une preuve forte et ignore
  l'éditeur). La consigne demande, pour chaque F « independantes », `source_urls` (une URL par source, copiée des
  résultats). `alphabet_provenance.py` vérifie sans modèle que chaque URL figure dans les résultats exécutés et que les
  deux viennent de sites différents ; verdicts `verifiee`, `meme_domaine`, `url_hors_resultats`, `une_seule_url`,
  `sans_urls`. Registre : `C.provenance_F` ; score : `provenance_F` (statuts, perte de C selon que toutes les
  provenances sont vérifiées). Rien ne change au calcul ni au chiffre posté. Monde synthétique : protocole 7 (la
  consigne du lecteur a changé).
- **0.10.37** : **veille d'articles**, chaque lundi, sans modèle (décision d'auteur du 2026-11-11).
  `veille_articles.py` interroge arXiv (articles de la semaine, rubriques IA, langage, apprentissage, statistiques,
  économie, réseaux sociaux) et lit la dernière sélection de DAIR.AI « AI Papers of the Week » ; chaque article est noté
  sur son titre et son résumé d'après `veille/mots-cles.txt` (modifiable à la main : expressions fortes à 3 points,
  faibles à 1, 2 dans le titre, retenu à 3) ; les articles déjà signalés ne reviennent pas (`veille/vus.json`). Sortie :
  `veille/semaine-<date>.md` et un ticket GitHub assigné à l'auteur. Rien n'entre dans le bot. Sur 44 semaines de
  DAIR.AI, 8 articles sur 440 auraient été retenus : DAIR reste un complément, arXiv la source principale.
- **0.10.36** : **deux comparaisons de plus dans le monde synthétique** (décision d'auteur du 2026-11-11, d'après
  S. Goedecke, « Is chain-of-thought AI reasoning a mirage? »). (1) **Réflexion** : chaque situation est relue une
  seconde fois par le même lecteur, même consigne, avec la réflexion étendue (Claude : `thinking`, budget 4 000 jetons ;
  autres familles : `reasoning_effort` moyen) ; `perturbations.reflexion` compare sensibilité et faux positifs avec et
  sans. Variable `MONDE_REFLEXION` (« 1 » par défaut). (2) **Référence humaine** : `monde_synthetique.py
  exporter-humain [N]` écrit, sans appel de modèle, un cahier (dépêches + fiches), une grille CSV à remplir et une clé
  à ne pas ouvrir, à partir des situations vérifiées du protocole le plus récent ; `noter-humain <dossier>` compare la
  grille à la vérité vérifiée et au lecteur (sans et avec réflexion). Humain proche du lecteur : les erreurs viennent
  des fiches ou des textes ; humain nettement meilleur : elles viennent du lecteur. Workflow : entrées `reflexion`,
  `action`, `dossier_humain`. Skill vendu 0.7.71.
- **0.10.35** : **relecteur de fidélité du plan**, en ombre (décision d'auteur du 2026-11-11, d'après Humanize,
  arXiv 2610.13632). Un appel de plus par question, au contradicteur s'il existe : il ne voit que la question et sa
  traduction formelle (événement, définition de la carte, sémantique, fenêtre), ni le raisonnement du planificateur ni
  les candidates, et dit si la traduction est fidèle (oui, partiel, non) avec le type d'écart (événement plus facile ou
  plus difficile, autre événement, négation, fenêtre, sémantique). Registre : `C.fidelite_plan` ; score :
  `fidelite_plan` (verdicts, types d'écart, perte de C selon le verdict). Variable `ALPHABET_FIDELITE` (« 1 » par défaut
  dans le workflow). Le nombre de corrections du dossier reste à deux : les refus du registre sont structurels.
- **0.10.34** : **quatre tests de robustesse**, d'après Lv et al. (ICML 2026, « Can Agents Generalize to the Open
  World? »), décision d'auteur du 2026-11-11. (1) Monde synthétique : **effacement des noms**, chaque situation est
  relue avec les cartes renommées en identifiants neutres (C01 à C16), fiches et marqueurs inchangés ; si la lecture
  change, le lecteur s'appuie sur le vocabulaire des noms, pas sur les marqueurs (`MONDE_EFFACEMENT`, « 1 » par
  défaut). (2) Bot : **test de négation**, en ombre, sur 20 % des questions binaires (`ALPHABET_NEGATION_TAUX`) : la
  question est réécrite en son contraire et posée au modèle seul ; p + p_niée devrait valoir 1 (`negation_A` au
  score). (3) Monde synthétique : **dépêches parasites** hors sujet dans la moitié des situations ; sensibilité et
  faux positifs comparés avec et sans. (4) Bot : quand le compte prévu sur une source de données échoue, chaque vue
  extérieure le **sait** (motif fourni) et doit le dire ; la méthode de B devient « vue_modele_compte_echoue » au
  score. `protocole_monde` 6.
- **0.10.33** : **coûts et budget** (bot Metaculus seulement). Chaque question traitée laisse une ligne dans
  `registre/couts.jsonl` (coût estimé par litellm, durée, modèles) ; le passage affiche et note son coût total ; le score
  donne `couts` par modèle et par jour. Budget facultatif : `ALPHABET_BUDGET_USD` depuis `ALPHABET_BUDGET_DEPUIS`
  (variables du dépôt) ; un passage est refusé si le budget est épuisé, et un plafond dur arrête les nouveaux appels en
  cours de passage. Les moteurs de recherche payants hors litellm et les autres workflows (monde synthétique) ne sont
  pas comptés.
- **0.10.32** : décision d'auteur du 2026-11-11 (adoptées sans passage par le juge, à mesurer sur les cas réels),
  d'après un manuel de séries temporelles. Le compte des puits tient compte (1) de la **saisonnalité** des séries
  mensuelles, trimestrielles ou hebdomadaires (composante saisonnière des pas, retenue si R² ≥ 0,2 et F ≥ 2,5, cherchée
  avant le retrait des chocs ; la saison propre à la fenêtre de la question est remise dans les chemins simulés) et
  (2) de la **volatilité groupée** (si les carrés des résidus sont autocorrélés, les pas rejoués sont mis à l'échelle de
  la volatilité récente, qui revient vers la moyenne). Les deux entrent dans le nom de la méthode (« +saison »,
  « +volatilite ») : `B_par_methode` les sépare au score. Juges du banc du compte inchangés (8,15 et 11,14 millinats).
- **0.10.31** : monde synthétique, protocole 5. Chaque dépêche a son média inventé imposé ; pour la moitié des
  cartes présentes, le fait est rapporté par deux médias distincts à deux dates : l'ancrage F (deux sources
  indépendantes) devient possible, et la mesure vérifiée donne la sensibilité séparément pour les faits corroborés et
  à source unique. La réécriture guidée est retirée (elle n'a rien corrigé en trois passages).
- **0.10.30** : skill 0.7.70 (§47, décision d'auteur) : **les λ s'apprennent sur les issues**, en ombre
  (`apprentissage_lambda.py`, chaque lundi après le score, `registre/lambda-appris-<date>.json`). Régression logistique
  à décalage (logit p = logit f + Σ n_classe · ln λ_classe), maximum a posteriori avec un a priori centré sur les λ
  stipulés (écart-type 0,5 en ln λ), sur les questions résolues du bot et du banc alphabet-chaine ; perte log hors
  échantillon comparée. Adoption par décision datée, à 50 questions au moins et gain hors échantillon.
- **0.10.29** : **puissance du test C contre B selon le lecteur** (`puissance_lecteur.py`, sans appel de modèle,
  `registre/puissance-lecteur-<date>.json`), suggestion d'une relecture par Mistral. Monde = programme génératif du
  skill (strate 7), 1 000 questions. Résultat du 2026-11-11 : même si C valait la vraie probabilité du modèle, le gain
  moyen sur B ne serait que de 1,3 point par question (σ ≈ 20) ; le C publié perd même avec un lecteur parfait (−0,2
  point : il n'utilise pas les absences, d'où son biais à la hausse), l'ombre générative gagne de 0,9 à 1,3 point ;
  dans tous les cas, plus de 1 000 questions pour conclure. La sensibilité du lecteur n'est pas le premier goulot :
  c'est la force que le modèle prête aux cartes. Présentation : le README racine décrit le projet (l'ancien est
  gardé dans `README-template-metaculus.md`) ; résumé anglais mis à jour.
- **0.10.28** : skill 0.7.69 (§46 : chaque ligne de marqueurs est une alternative complète, neuf fiches recoupées).
  Monde synthétique : deux États seulement (l'organisation n'entre que si RÉSEAU ou COMMUNAUTÉ doivent être montrés) ;
  dépêche de contexte sans référence au passé ni instance qui préside ou valide ; `protocole_monde` 4.
- **0.10.27** : quatre puits de données repérés dans le projet ShadowBroker (BigBodyCobain), sans clé :
  `front_ukraine` (ligne de front quotidienne depuis 2024-07, archive GitHub cyterat/deepstate-map-data des cartes
  DeepState : surface occupée en km², ou distance en km d'une localité à la zone occupée, 0 = occupée, à compter avec
  seuil 0 et sens « <= ») ; `coupures_internet` (jours d'alerte critique par pays, IODA, Georgia Tech) ; `lancements`
  (lancements spatiaux datés, catalogue SATCAT de CelesTrak, domaine public) ; `sanctions_us` (nouvelles cibles de la
  liste SDN de l'OFAC, via OpenSanctions, CC BY-NC, stock initial retiré). Le fichier unifié du dépôt DeepState a des
  dates vides pour ses 502 premières lignes : le puits lit les fichiers quotidiens, datés par leur nom.
- **0.10.26** : monde synthétique, **narrateur contraint** (décision d'auteur du 2026-11-11 : contraindre le narrateur
  plutôt que changer de modèle). (1) Canevas imposé, tiré de la graine : deux États et une organisation inventés, les
  dates, et pour chaque carte présente UN marqueur précis à remplir ; une dépêche de contexte sans marqueur ; domaine
  imposé (relations entre États et organisations internationales). (2) Réécriture guidée, une fois : le vérificateur
  dit quels marqueurs interdits sont remplis et lesquels manquent, le narrateur corrige, le vérificateur repasse ; le
  lecteur ne lit que la version corrigée. Les erreurs du narrateur avant et après réécriture sont enregistrées.
  `protocole_monde` 3.
- **0.10.25** : (1) **seconde chance pour un JSON illisible** (plan, lecture, correction du dossier, monde synthétique) :
  la consigne est renvoyée avec l'erreur ; le premier échec reste compté (`reprises_json`) dans `sorties_illisibles`.
  (2) Monde synthétique : **vérificateur d'une troisième famille** (entrée `verificateur`, Mistral Large 3 sur
  Bedrock par défaut), sondé avant le passage ; le résultat dit si sa famille diffère de celles du lecteur et du
  narrateur ; le cumul ne mélange pas deux vérificateurs.
- **0.10.24** : monde synthétique, deux coquilles : le workflow ne transmettait pas `ALPHABET_CONTRADICTEUR`, et le
  narrateur « contradicteur » retombait en silence sur le lecteur (passage du 2026-11-11, 03 h 55 UTC) ; un narrateur
  demandé et indisponible arrête désormais le passage. Les passages ne se cumulent qu'à consigne identique
  (`protocole_monde` 2 depuis 0.10.23).
- **0.10.23** : **calibrage du monde synthétique**, après lecture des textes du premier passage. (1) Le narrateur ne
  reçoit plus que les marqueurs observables des cartes (il paraphrasait leurs définitions, ce qui rendait la lecture
  trop facile) ; (2) il raconte une seule situation (mêmes acteurs) et non une dépêche par carte ; (3) il reçoit les
  marqueurs des absentes, qu'aucun fait ne doit remplir ; (4) aucune phrase d'analyse. (5) Un vérificateur
  indépendant (le petit modèle) dit quelles cartes le texte montre vraiment : la `mesure_verifiee` retire les erreurs
  du narrateur, pour ne compter que celles du lecteur.
- **0.10.22** : monde synthétique : narrateur d'une autre famille que le lecteur (entrée `narrateur` du workflow,
  « contradicteur » par défaut, soit DeepSeek V3.2 avec les suites actuelles) ; chaque passage prend des graines
  nouvelles, à la suite des précédents ; le résultat donne aussi le cumul de tous les passages de la strate.
- **0.10.21** : monde synthétique : une carte absente reste toujours hors des candidates pour servir d'événement (le
  premier passage avait perdu 2 situations sur 12, celles à 8 cartes présentes).
- **0.10.20** : **les pièges du taux de base B, traités et surveillés.** (1) Compte des puits : chocs ponctuels retirés,
  retour vers la moyenne (AR(1)), séries bornées déclarées par le modèle (`bornes` : [0, 100] pour un pourcentage),
  croissance relative mieux détectée, bootstrap lissé ; nouveau juge du banc du compte (`banc/compte/juge2.py`, quatre
  pièges) : 53,3 → 10,7 millinats sur la partie cachée. (2) **Alarme de discordance** au registre
  (`B.discordance_A`) : B et A à plus d'un facteur 4 sur les cotes ; pour une question dérivée d'une numérique, le
  seuil est la médiane de A, donc B devrait être près de 0,5. (3) Score : `B_par_methode` (perte de B et B − A par
  méthode d'obtention) et `discordances_B` (qui avait raison quand l'alarme sonne). Rien de posté ne change.
- **0.10.19** : **taux de base d'un seuil de niveau sur une série en croissance.** Le compte des puits rejoue les pas
  RELATIFS (log) quand la série est positive, à tendance nette et que ses pas grandissent avec le niveau : l'écart à
  franchir devient log(seuil / dernière valeur). Cas FYONET (dépenses fédérales, seuil de 8,05 millions de millions) :
  0,56 au lieu de 0,20 (pas absolus) ou 0,11 (vue du modèle, qui comptait les dépassements passés d'un niveau jamais
  atteint). Le juge du banc du compte est inchangé (8,9 millinats). Les consignes de la classe de référence et de la vue
  extérieure portent la même règle pour le cas où le compte ne peut pas tourner.
- **0.10.18** : lecture exploratoire d'une question dérivée : le registre garde le motif de la lecture elle-même
  (il était recouvert par « strate non chiffrée »), la dernière erreur du moteur, le nombre de tentatives et la
  présélection.
- **0.10.17** : **aucune clé d'API dans le registre public.** Les erreurs HTTP des puits masquent les paramètres
  `api_key=`, `token=`, `key=`… de l'URL, et chaque ligne et chaque dossier passent par `sans_cles` avant d'être
  scellés (une clé FRED s'était retrouvée dans une ligne de `journal-autres.jsonl` le 2026-11-11 : clé à régénérer).
  FRED : le millésime ALFRED lu est au plus celui de la veille (UTC), car FRED compte les jours à l'heure de
  Saint-Louis et refusait (erreur 400) un millésime d'« aujourd'hui » encore dans son futur.
- **0.10.16** : **Amazon Bedrock, provisoire** (crédits jusqu'au 23 novembre 2026). Les workflows lisent le secret
  `AWS_BEARER_TOKEN_BEDROCK` (clé d'API Bedrock) et la variable `AWS_REGION_NAME` (us-east-1 par défaut). Suites
  conseillées, Bedrock en tête et Fantasy derrière, en secours :
  `ALPHABET_LLM` = `bedrock/global.anthropic.claude-sonnet-5-5,<suite Fantasy actuelle>` ;
  `ALPHABET_PETIT_LLM` = `bedrock/global.anthropic.claude-haiku-4-5-20251001-v1:0,<suite Fantasy actuelle>` ;
  `ALPHABET_CONTRADICTEUR` = `bedrock/us.deepseek.v3.2,<suite actuelle>` (une autre famille que le principal).
  Changer de modèle ouvre une nouvelle période de score (lire `par_modele`) ; le 23 novembre, retirer les entrées
  `bedrock/` des suites (sinon chaque passage les sonde puis retombe sur Fantasy). Les limitations de débit de Bedrock
  (Throttling) sont traitées comme passagères.
- **0.10.15** : **présélection des cartes par plongement multilingue, en ombre** (`preselection.py`). Un modèle léger
  qui tourne sur CPU dans GitHub Actions (fastembed, `paraphrase-multilingual-MiniLM-L12-v2`, mis en cache) range les
  16 cartes par similarité entre la question (souvent en anglais) et leur définition (en français). Au registre
  (`C.preselection`) : les k premières (k = nombre de cartes retenues par le planificateur), le recouvrement et le
  Jaccard avec ces cartes, le rang de la carte de l'événement ; au score, `preselection_ombre`. Le plan n'est pas
  modifié. Variable `ALPHABET_PRESELECTION` (« 1 » par défaut dans le workflow, « 0 » l'éteint) ; si le modèle ne se
  charge pas, la clé vaut « indisponible » et la question suit son cours.
- **0.10.14** : skill 0.7.66 (§43), d'après LLMMatrix (Prokopets 2026). **Monde synthétique** (`monde_synthetique.py`,
  workflow manuel) : des situations tirées du programme génératif du skill (cartes présentes connues) sont racontées
  en dépêches fictives par un modèle-narrateur, sans nommer les cartes, puis relues par le lecteur ordinaire ;
  sensibilité (F, f) et faux positifs mesurés, à côté des valeurs stipulées du génératif
  (`registre/monde-synthetique-<date>.json`). Borne optimiste : narrateur et lecteur sont de la même famille. Score :
  `sorties_illisibles`, part des sorties de modèle illisibles par modèle principal et par étape (plan, lecture,
  correction, critique, invariance), comptée à part des états nuls.
- **0.10.13** : skill 0.7.65 (§42). Le test d'invariance mesure aussi l'accord au niveau de la FAMILLE (la carte et ses
  voisines A6) : deux vues qui ancrent deux voisines se trompent de carte, pas de famille (`accord_famille_moyen`).
- **0.10.12** : skill 0.7.63 (§40). **Surprise d'une lecture** scellée avec C (`generatif.surprise`) ; le score rend
  `C_selon_surprise` (Brier de C quand la surprise est forte ou faible). **Diversité des lectures** (`diversite_lectures` :
  part des états nuls, états distincts, entropie des cartes ancrées) pour surveiller un lecteur qui « s'effondre ».
- **0.10.11** : skill 0.7.62 (§39), d'après Balestriero & LeCun (2026). **Test d'invariance du lecteur**, en ombre :
  sur une part des questions (`ALPHABET_INVARIANCE_TAUX`, 0,2 par défaut dans le workflow, tirage déterministe par
  question), le même lecteur relit la situation sur deux vues aux SOURCES disjointes (mêmes requêtes, sites séparés).
  Le registre garde les cartes ancrées dans chaque vue ; le score rend `invariance_lecteur` (Jaccard moyen, part des
  lectures identiques, κ sur les candidates). Coût : deux lectures de plus par question testée.
- **0.10.10** : deux puits Epoch AI (CC BY 4.0) pour les questions sur l'IA : `epoch_modeles` (sorties de modèles,
  calcul d'entraînement, filtrables par organisation, domaine, pays, frontière ; lignes modifiées après la date
  d'information comptées et signalées) et `epoch_benchmarks` (scores datés de la sortie du modèle). Score :
  `calibration_queues` (p < 0,1 et p > 0,9, fréquence observée contre p moyen), d'après la méthode bayésienne de l'ECI
  d'Epoch, dont la couverture est la plus faible près des bornes.
- **0.10.9** : skill 0.7.61 (§38, relecture par Murphy, ch. 4, 9, 29, 30). Les catégories de rejet vont au moteur
  (l'ombre générative pèse un rejet selon l'effort de recherche) ; ombre `sans_plafond` au registre et au score
  (`C_sans_plafond_sur_C`) ; export de la matrice d'épisodes N × D (`episodes.py`, `registre/episodes.csv`, chaque
  lundi), entrée des apprentissages futurs.
- **0.10.8** : deux outils tirés de Wong et al. (2023, §4). **Pépinière** (`pepiniere.py`, chaque lundi après le
  score, `registre/pepiniere.json`) : les relations traduites (lien, bloque, exclut) agrégées sur tout le registre ;
  celles absentes de la matrice, affirmées dans 3 questions et 2 sources distinctes au moins, sont candidates à une
  nouvelle arête, qui n'entre que par décision d'auteur datée. Le traducteur donne désormais la source de chaque extrait.
  **Reconstruction** (`reconstruction_matrice.py`, workflow manuel) : un modèle reçoit les seules définitions des 16
  cartes et propose les arêtes ; accord avec la matrice (κ, précision, rappel, forces) et liste des arêtes à réexaminer.
- **0.10.7** : skill 0.7.60 (§37), d'après Wong, Goodman, Tenenbaum et al. (2023). En ombre, si la variable
  `ALPHABET_TRADUCTION` vaut 1 (allumé par défaut dans le workflow ; « 0 » l'éteint) : un TRADUCTEUR (appel séparé, après la lecture, qui ne change donc pas C) traduit ce que
  les textes affirment des liens entre structures en instructions (lien, bloque, exclut), chacune avec un extrait cité ;
  les extraits non retrouvés sont écartés sans modèle ; le moteur en tire `lecture_probabiliste`. Le score compare
  `C_lecture_probabiliste` à C. Les variables `ALPHABET_TRADUCTION` et `ALPHABET_A_ESSAIS` sont lues par le workflow.
- **0.10.6** : skill 0.7.59 (§36). En ombre : `generatif`, un programme génératif conditionné sur la lecture (cartes
  latentes, lecteur bruité, rejets du dossier comptés comme observations, inférence exacte), avec sa bande ; le score
  compare `C_generatif` à C.
- **0.10.5** : skill 0.7.58 (§35), d'après Murphy (2026). En ombre : `tempere` (produit des λ à la puissance α fixée
  d'avance, 0,5 principal) comparé à C ; et, si `ALPHABET_A_ESSAIS` > 1 (1 par défaut, éteint : chaque essai coûte un
  appel au modèle principal), K essais du bras A scellés avec lui, moyenne comparée à A et C comparé à A moyenné. Le
  premier essai reste le bras A publié.
- **0.10.4** : skill 0.7.57 (§34). Deux ombres de plus dans `ombre_causale`, jamais publiées : `p_noisy_or` (les
  cartes lues comme des causes, au lieu d'indices) et `valeur_information` (borne de ce qu'une carte de plus pourrait
  changer ; `arret` vrai si sous 0,02). Le nombre de tours de recherche reste fixe. Le score compare `C_noisy_or` à C et
  donne le Brier de C selon `arret`.
- **0.10.3** : skill 0.7.56 (§33). Deux sondes du moteur enregistrées en ombre (`ombre_causale`), jamais publiées :
  `p_mediation` (règle des médiateurs : une arête lue comme effet total écarte son médiateur) et `ablation` (chaque
  carte retirée seule). Le score compare `C_mediation` au C actuel sur les mêmes questions. L'écart C − B est un
  contraste du dispositif, jamais un contrefactuel.
- **0.10.2** : un mot dont le fait cite une date postérieure à la date d'information, absente des résultats fournis,
  est retiré avant le moteur (`faits_futurs_retires` au registre) : garde contre les fuites temporelles (Paleka et al.,
  ICLR 2026) et contre l'invention de l'issue, observée sur le banc sans texte le 10 novembre.
- **0.10.1** : après la sonde du 10 novembre (16 sources sur 22, les quatre nouvelles comprises) : `sanctions_ue` se
  replie sur la date de publication du règlement quand la date de désignation manque ; `bls` tolère les caractères de
  contrôle de la réponse ; `firms` passe au produit standard (SP) pour une date de plus de 60 jours.
- **0.10.0** : quatre puits de données de plus, sans clé : `gaza` (Tech for Palestine, d'après le ministère de la
  Santé de Gaza et l'OCHA, séries quotidiennes), `sanctions_ue` (liste consolidée des sanctions financières de l'UE,
  une entrée par désignation ; radiations absentes, biais de survie signalé), `oms` (Global Health Observatory,
  indicateurs annuels, retard d'un an), `ecosystemes` (ecosyste.ms, versions datées d'un logiciel open source).
  Noms des champs à confirmer par la sonde des puits.
- **0.9.9** : consigne de lecture précisée (§30, déjà décidé) : les marqueurs d'une fiche sont des alternatives, un
  seul suffit pour f ; l'ancrage d'une carte ne dépend pas de l'objet de la question (le moteur décide de l'effet).
  Constaté sur le banc sans texte : CROISSANCE refusée faute de « limite » alors que trois bougies montaient, ou
  parce que « la question porte sur la réserve, non sur le prix ».
- **0.9.8** : skill 0.7.55 ; les équivalents de données pour les jetons (`donnees-chaine.md`, §32) ne sont chargés
  que si `ALPHABET_EQUIV_DONNEES` est activé (banc `alphabet-chaine`). Le bot Metaculus ne l'active pas : il le fera
  après une décision d'auteur datée (verdict du banc à 200 questions par type, ou équivalents Documentés).
- **0.9.7** : `alphabet()` accepte une vue extérieure fixée et des relevés de données fixés (`vue_fixee`,
  `donnees_fixees`), pour le banc « sans texte » `alphabet-chaine` ; le bot Metaculus ne les passe jamais, son
  comportement est inchangé.
- **0.9.6** : skill 0.7.53 (le marqueur décide de l'intensité) : la définition d'une carte + un marqueur observable
  suffisent pour f, sans la forme complète de l'attendu ; « contredit » distingué de « marqueur non rempli », avec
  exemples (le premier passage exploratoire a fini en état nul sur 16 rejets sur 16 « marqueur non rempli ») ; la
  trace des puits, le compte et les rejets classés figurent dans la lecture exploratoire des questions non binaires.
- **0.9.5** : compte des puits réécrit par la boucle du banc d'essai `banc/compte/` : niveaux jugés depuis la
  dernière valeur (bootstrap des pas observés), événements par taux de Poisson ; partie cachée 275 → 8,7 millinats.
- **0.9.4** : contrôle d'attribution réécrit par la boucle du banc d'essai : ancres indépendantes de la langue
  (nombres, noms propres, unités) ; faux refus de 97 % à 10 % sur la partie cachée, faux acceptés 3,8 %.
- **0.9.3** : contrôle d'attribution sorti dans `alphabet_attribution.py`, sans changement de comportement ; banc
  d'essai `banc/attribution/` (juge et corpus verrouillés) pour l'améliorer.
- **0.9.2** : `MISTRAL_API_KEY` transmise aux workflows : une suite de modèles peut finir par un modèle de l'API
  Mistral (`mistral/mistral-large-latest`), d'un autre fournisseur que la passerelle, en secours quand la clé de la
  passerelle est limitée (le 2026-11-08 au soir, tous ses modèles répondaient « Rate limit exceeded »).
- **0.9.1** : correction symétrique du biais à la hausse (candidates contredites comptées contre), décalage appliqué au
  C exploratoire, questions non binaires lues en exploratoire par une question binaire dérivée.
- **0.9.0** : bras C exploratoire hors strate 7 (skill 0.7.52, `--exploratoire`) : chiffre scellé, jamais posté,
  scoré à part par strate (`C_exploratoire_sur_B`, `statuts_exploratoires`).
- **0.8.3** : une vue qui cite une référence inexistante ([R7] quand quatre résultats ont été fournis) est
  refusée ; le contrôle d'attribution note si l'URL citée par chaque mot figure dans les résultats (`url_retrouvee`).
- **0.8.2** : le moteur « exa » (Exa + petit modèle de synthèse) : une saturation du petit modèle n'est plus comptée
  comme un échec d'Exa ; la synthèse reprend avec les secours des rôles légers, et la seconde clé Exa ne sert plus
  qu'aux erreurs d'Exa (clé, crédits, quota) ; la dernière erreur de chaque moteur est gardée au registre.
- **0.8.1** : premier passage réel de la 0.8.0 : les trois vues d'une question refusées pour une erreur de calcul
  de tête du modèle → la valeur de la formule est retenue (`calcul_corrige`) ; trois vues sur la même source → contrôle
  sans modèle de la reprise de source.
- **0.8.0** : audit d'Azrivo. Intégrité : garde du registre contre toute écriture de test, sceau des dossiers relu
  au score (un dossier écrasé le 2026-11-04 a été trouvé), aucune prévision postée sans sa ligne, passage arrêté
  journalisé, workflows du bot modèle d'origine désarmés. Fuite : tests rétrospectifs filtrés sur l'ouverture, puits
  bornés à la date de publication, fin de mandat future masquée. Bras B : trois sources distinctes, calcul refait par
  le code, compte exact = taux de base, compte proche montré à une seule vue, agrégation typée. Attribution : nombres
  du fait dans les extraits cités, fait retrouvé dans le corpus, décimales lues. Score : diagnostics sur toutes les
  lignes publiées, dernière ligne selon l'horodatage, avertissements (modèles mélangés, erreur familiale, unités).
  Divers : JSON lu par `raw_decode`, deux corrections du plan, délais d'appel réduits.
- **0.7.4** : saturation en cours de passage : le modèle principal est attendu puis ressayé (30 s, 90 s), sans
  changer de codeur ; les rôles légers passent au reste de leur suite, puis au principal (`modèles légers remplacés`
  au bilan). Registre nettoyé : 392 lignes fictives des tests hors ligne (question 4242), publiées par erreur
  de la 0.6.3 à la 0.7.3, retirées ; les tests n'écrivent plus jamais dans le vrai registre.
- **0.7.3** : modèle principal saturé : la suite est ressayée après 60 s puis 120 s avant d'arrêter le passage ;
  trois essais par appel au lieu de deux.
- **0.7.2** : compte « proche » : une série voisine du critère ancre les estimations de B, et le compte est scoré
  en ombre (`compte_sur_B`).
- **0.7.1** : en-tête User-Agent conforme à la politique de Wikimedia (Wikipedia, Wikidata) ; texte des articles
  nettoyé des modèles imbriqués.
- **0.7.0** : puits de données (`alphabet_puits.py`) : 18 bases ouvertes bornées à la date d'information ; compte
  calculé par le code comme vue du bras B ; relevés citables par le lecteur ; sonde par workflow.
- **0.6.3** : TinyFish ajouté à la chaîne de recherche, entre Tavily et GDELT.
- **0.6.2** : Brave Search retiré (carte bancaire exigée).
- **0.6.1** : chaîne de recherche Exa → seconde clé Exa → Brave Search → Tavily → GDELT ; moteur noté pour chaque
  recherche.
- **0.6.0** : suites de modèles avec bascule au début du passage, modèles notés au registre et score par modèle,
  contradicteur en ombre, surveillance toutes les 3 heures, passerelle compatible OpenAI (Fantasy AI, provisoire
  jusqu'au tournoi), toutes les questions traitées par défaut.
- **0.5.2** : contrôle d'attribution déterministe des mots ancrés (extraits et nombres retrouvés dans les résultats),
  idée reprise des contrôles locaux d'EnVrai ; compté par version au score. Les deux autres idées examinées ne sont
  pas reprises : le test de la surprise fait double emploi avec les tests de Van Evera que le dossier porte déjà
  (`pistolet`, `cerceau`, `double`) ; un étage numérique branché sur des séries officielles sortirait du dispositif à
  trois bras et demanderait une source de données par type de question.
- **skill 0.7.51** (bot inchangé) : le skill reprend les changements d'enregistrement et de mesure du bot
  (`alphabet-situationnel/references/validation.md` §28), et son `scorer` publie la même séquence de confiance et le
  même verdict (meilleur / moins bon / indéterminé) que `score_registre.py` : les deux outils ne peuvent plus conclure
  différemment sur le §27.
- **0.5.1** : verdict et séquence de confiance sur le gain moyen ; seuils corrigés pour les comparaisons multiples ;
  commentaire envoyé scellé avec la prévision ; jeu de questions reçu consigné à chaque passage ; passage à blanc
  réservé à la zone de test.
- **0.5.0** : tests rétrospectifs (manuels, rien de posté) pour mesurer le biais de C et apprendre un décalage
  correctif ; C corrigé scellé en ombre dans chaque prévision réelle et scoré à part.
- **0.4.2** : mesure du sens unique de C (`biais_C` : déplacement moyen par rapport à B, gain séparé sur les OUI et
  sur les NON, taux de OUI réel contre B et C moyens), pour trancher sur données la décision d'auteur 9 du skill.
- **0.4.1** : borne structurelle C − B pour le test séquentiel, mise adaptative en plus de la grille, puissance du
  test séquentiel simulée ; sort de la classe figée au registre ; statuts et stabilité de strate par version.
- **0.4.0** : classe de référence définie avant les trois comptages ; source « de mémoire » refusée ; strate choisie
  à l'aveugle ; pour chaque carte écartée, le fait attendu et l'extrait le plus proche (`rejets_details`) ; score :
  test séquentiel valide à tout moment, puissance a priori, grille de plafonds, stabilité de la strate. Pistes tirées
  d'une analyse externe (azrivo), retenues ou écartées une à une.
- **0.3.0** : taux de base estimé trois fois (vue médiane, dispersion mesurée) ; questions Metaculus résolues comme
  classe de référence possible (issues seulement) ; seconde source de recherche facultative ; étude hebdomadaire de
  la recalibration et du plafonnement, avec rappel. Principes inspirés des constats publiés sur les meilleurs bots,
  adaptés au dispositif à trois bras, sans reprise de code.
- **0.2.3** : `dynamique_observee` dans les états nuls (matériau pour une éventuelle carte manquante, hors calcul).
- **0.2.2** : relance ciblée des angles morts avant d'accepter un état nul ; nature de l'état nul au registre et au
  score ; plafond porté à 5 questions par jour ; le Brier apparié reste le critère L7 du skill.
- **0.2.1** : le score logarithmique devient la base du score (règle de Metaculus) ; le Brier passe en contrôle.
- **0.2.0** : correctifs d'un audit externe (bornes 0,001–0,999, questions de groupe, contrôle toutes les 20 minutes,
  une ligne par question au score, champs `publie` et `mode`, dossiers horodatés, recherches coupées tracées,
  temporalité transmise au moteur, tests automatiques). Non appliqués, volontairement : stabilisation de B (sur
  données), changement du bras posté (pas avant la levée de L7), *pastcasting* (le modèle connaît déjà l'issue des
  questions résolues : fuite).
