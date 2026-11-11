# Bot Metaculus de l'alphabet situationnel

Version 0.10.16 · skill alphabet-situationnel 0.7.66 · auteur Othman Ben Brahim · licence MIT pour les fichiers du bot
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

- **0.10.16** : **Amazon Bedrock, provisoire** (crédits jusqu'au 23 novembre 2026). Les workflows lisent le secret
  `AWS_BEARER_TOKEN_BEDROCK` (clé d'API Bedrock) et la variable `AWS_REGION_NAME` (us-east-1 par défaut). Suites
  conseillées, Bedrock en tête et Fantasy derrière, en secours :
  `ALPHABET_LLM` = `bedrock/global.anthropic.claude-opus-5-5,<suite Fantasy actuelle>` ;
  `ALPHABET_PETIT_LLM` = `bedrock/global.anthropic.claude-haiku-4-5-20251001-v1:0,<suite Fantasy actuelle>` ;
  `ALPHABET_CONTRADICTEUR` = `bedrock/global.anthropic.claude-sonnet-5-5,<suite actuelle>`.
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
