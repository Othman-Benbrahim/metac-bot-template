# Bot Metaculus de l'alphabet situationnel

Version 0.4.2 · skill alphabet-situationnel 0.7.49 · auteur Othman Ben Brahim · licence MIT pour les fichiers du bot
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
   fois** (ce qui compte pour un cas, sur quelle population, quelle période) ; puis le comptage est fait **trois fois,
   indépendamment, sur cette même classe**. B est la vue médiane (une vraie vue, avec sa source : aucune moyenne
   fabriquée), et l'écart entre les trois est enregistré : c'est alors un écart de mesure, non un changement de classe.
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

## Quand il tourne et ce qu'il coûte

- **Toutes les 20 minutes**, il regarde s'il y a des questions nouvelles (elles ne restent ouvertes que 3 heures, à
  heure aléatoire). Un contrôle sans question nouvelle ne coûte rien et n'écrit rien.
- **5 questions nouvelles par jour au plus** (variable `ALPHABET_MAX_QUESTIONS`), comptées dans
  `registre/passages.jsonl` avant toute prévision.
- **Lancement manuel** (*Actions → Bot alphabet situationnel → Run workflow*) : son propre plafond (champ
  `max_questions`), hors quota quotidien. Le mode `test_questions` (zone de test de Metaculus) est enregistré comme essai
  et n'entre pas dans le score.
- Par question binaire : environ cinq appels au modèle principal (dont trois estimations du taux de base), quelques
  appels au petit modèle, jusqu'à quinze recherches (doublées si une seconde source est configurée), quelques appels
  gratuits à l'API de Metaculus, plus le bras A.

## Comment il est jugé

Metaculus classe les participants au **score logarithmique** (les scores de pair sont des différences de scores log).
Le registre est donc scoré de la même façon (`score_registre.py`, chaque lundi par le workflow « Score du bot
alphabet ») :

- **par bras** : perte log, et score de référence de Metaculus (100 × (log₂ p + 1) ; 0 = pile ou face) ;
- **comparaison appariée**, sur les questions où les trois bras existent : **gain de C sur B** et de C sur A, en points
  de score de pair (100 × écart de ln p sur l'issue réelle ; positif = C meilleur), questions gagnées et perdues ;
- **un test séquentiel** (`test_sequentiel`) : une valeur e pour « C fait mieux » et une pour « C fait moins bien ».
  Au-delà de 20, l'écart est établi au niveau 5 %, **quel que soit le moment où l'on regarde** : on peut lire le score
  chaque semaine sans fausser la conclusion. En dessous, rien n'est établi ;
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
| `registre/journal-bot.jsonl` | une ligne scellée par question binaire : bras A, B, C, bras posté, statut, `publie`, `mode` |
| `registre/dossiers/` | le dossier de lecture de chaque question, nommé `<question>-<horodatage>.json` |
| `registre/journal-autres.jsonl` | une ligne scellée par question non binaire (bras A) |
| `registre/passages.jsonl` | une ligne par passage : date, déclencheur, questions trouvées et envoyées |
| `registre/issues.jsonl`, `registre/issues-autres.jsonl` | les issues constatées, jamais réécrites |
| `registre/score.json` | le dernier score calculé |

L'historique Git date chaque écriture : c'est ce qui rend les prévisions vérifiables après coup.

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
3. *Actions* : lancer d'abord en mode `test_questions`, vérifier sur Metaculus et dans `registre/`.

Au démarrage, le bot vérifie sa configuration et s'arrête en rouge si elle ne peut rien poster ; à la fin, il affiche
un bilan du passage. En local : `cp .env.template .env`, remplir, puis
`uv run python alphabet_bot.py --mode test_questions --sans-publier`.

## Tests

```
ALPHABET_SKILL_DIR=alphabet-situationnel python -m unittest discover -s tests
```

Modèle et recherche simulés, vrai moteur du skill. Ils tournent, avec l'audit du skill, à chaque modification du dépôt
(workflow « Contrôle du bot alphabet »).

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
