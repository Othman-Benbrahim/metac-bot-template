# Bot Metaculus de l'alphabet situationnel

Version 0.1.5 · skill alphabet-situationnel 0.7.49 · auteur Othman Ben Brahim · licence MIT pour les fichiers du bot
(`LICENSE-alphabet` : `alphabet_*.py`, `score_registre.py`, `tests/`, `run_alphabet_bot.yaml`) ; le reste du dépôt
est le modèle de Metaculus, sous ses propres conditions

Un bot pour le tournoi FutureEval de Metaculus. Il fait tourner le skill **alphabet situationnel** sur les questions
binaires et publie chaque prévision chez un tiers horodaté, avant l'échéance : c'est la condition des tests prospectifs
du skill (`validation.md` §14).

## Ce que fait le bot

Pour chaque **question binaire**, trois bras, dans cet ordre :

| Bras | Ce qui produit la probabilité | Rôle |
|---|---|---|
| **A** | le modèle seul, sans le skill (raisonnement du bot modèle de Metaculus) | calculé et **scellé avant** toute carte |
| **B** | la classe de référence seule (vue extérieure du dossier) | le taux de base |
| **C** | l'alphabet : `moteur.py calculer --dossier`, la fréquence de B passée en référence | C − B = l'apport des cartes |

Le bot **poste le bras C** quand le moteur l'estime. Si aucune carte n'est ancrée (**état nul**, lecture légitime :
« aucune structure lue »), il poste le **bras B**, le taux de base non ajusté. Dans les autres cas (question sans
événement de carte, pas de taux de base honnête, lecture refusée par le moteur), il poste le bras A et le dit dans le
commentaire. Pour les **autres types de questions** (numériques, choix multiples, dates), il se comporte exactement
comme le bot modèle de Metaculus : bras A.

Étapes des bras B et C :
1. **Plan** : le modèle choisit les strates, l'événement de carte qui correspond au OUI, et 2 à 4 candidates par strate
   (dont une contre-candidate). Pour un événement « apparait », au moins deux candidates sont **tirées de la matrice des
   dynamiques du skill** : les cartes qui, selon elle, font apparaître la carte visée (les seules qui peuvent déplacer le
   taux de base) ; la carte visée n'est jamais candidate. Un plan qui ne respecte pas cette règle est renvoyé une fois au
   modèle, puis refusé. Le plan fixe aussi la sémantique, 1 à 3 requêtes sur le **taux de base**, et les requêtes de lecture (trois
   familles par candidate, une discrimination par paire), formées sur le phénomène, jamais sur le nom d'une carte.
2. **Vue extérieure d'abord** (bras B) : le bot lance les requêtes de taux de base ; le modèle en tire une fréquence, ou
   d'un registre historique notoire qu'il nomme, sans chiffre inventé. Le bot construit lui-même la partie « événement »
   du dossier : les corrections ne peuvent plus l'effacer.
3. **Lecture** (bras C) : le bot lance les requêtes de lecture (12 au plus) ; le modèle écrit les mots ancrés à partir des
   seuls résultats, avec les fiches des candidates et les équivalents des strates. Un état nul est admis.
4. **Moteur** : `calculer --dossier`. Un refus est renvoyé au modèle pour correction (2 fois au plus), avec la consigne
   de descendre à f ou de retirer un mot plutôt que d'inventer. Le moteur reste juge : aucun chiffre n'est fabriqué.

**Strates chiffrées (décision L7 du skill).** Le moteur ne chiffre aujourd'hui que la strate 7 (géopolitique). Hors de
cette strate, le bot pose la vue extérieure (bras B, enregistrée), ne lance pas la lecture, et poste le bras A. Avec la
variable `ALPHABET_LECTURE_HORS_STRATE` = `1`, il fait quand même la lecture et la scelle sans chiffre : elle pourra être
chiffrée après une levée de L7 (critère : `alphabet-situationnel/references/validation.md` §27). Un refus structurel du
moteur n'est jamais renvoyé en correction.

Chaque question binaire laisse une ligne scellée (SHA-256) dans `registre/journal-bot.jsonl` et son dossier dans
`registre/dossiers/`. Le workflow les enregistre dans le dépôt après chaque passage.

## Installation

Ce dépôt est déjà prêt : fork de `Metaculus/metac-bot-template`, fichiers du bot à la racine, skill 0.7.48 dans
`alphabet-situationnel/` (copie exacte du dépôt `Othman-Benbrahim/alphabet-situationnel`, contrôlée par `moteur.py audit`).
Les planifications des workflows d'origine (tournoi, Metaculus Cup, revue hebdomadaire) sont désactivées : ils ne se
lancent plus qu'à la main, pour que deux bots ne postent pas sur le même compte.

Reste à faire :
1. Créer le compte bot sur <https://www.metaculus.com/futureeval/participate/>, copier le jeton, remplir le formulaire de
   participation (obligatoire ; demande de crédits au même endroit).
2. *Settings → Secrets and variables → Actions* :
   - onglet **Secrets** : `METACULUS_TOKEN` ; une clé de modèle (`ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY` ou
     `OPENAI_API_KEY`) ; une recherche web : `EXA_API_KEY` (niveau gratuit d'Exa) ou une clé AskNews
     (`ASKNEWS_API_KEY`, ou `ASKNEWS_CLIENT_ID` et `ASKNEWS_SECRET`). **Le proxy de modèles de Metaculus n'existe plus** :
     sans clé de modèle, le bot s'arrête en rouge ;
   - onglet **Variables** : `ALPHABET_LLM` (plan et dossier, ex. `anthropic/claude-sonnet-5-5`), `ALPHABET_PETIT_LLM`
     (lecture des réponses et résumés, ex. `anthropic/claude-haiku-5-5` ; par défaut, `ALPHABET_LLM`),
     `ALPHABET_CHERCHEUR` (ex. `smart-searcher/anthropic/claude-haiku-5-5` avec Exa, ou `asknews/news-summaries`).
     Avec une clé Anthropic seule, ces variables sont **nécessaires** : les modèles par défaut de la bibliothèque sont
     anciens, et sa recherche par défaut passe par le proxy disparu.
3. Onglet **Actions** : autoriser les workflows, puis **Bot alphabet situationnel → Run workflow**, mode `test_questions`.
   Vérifier sur Metaculus (compte bot) et dans `registre/`. Puis mode `minibench`.
4. La planification est active depuis le 2026-11-04 : mode `minibench`, toutes les 4 heures. Pour la suspendre :
   *Actions → Bot alphabet situationnel → ⋯ → Disable workflow*.

En local : `cp .env.template .env`, remplir, puis `uv run python alphabet_bot.py --mode test_questions --sans-publier`.

## Ce que dit un passage

Au démarrage, le bot vérifie le jeton, la clé de modèle et la recherche : une configuration qui ne peut rien poster
s'arrête en rouge avec la liste des problèmes. À la fin, un **BILAN DU PASSAGE** donne les questions traitées, les
prévisions postées, les questions binaires journalisées (bras C ou A posté) et les statuts de l'alphabet. Le passage
échoue en rouge si des questions ont été trouvées et qu'aucune n'a pu être prévue.

## Ce que garde le registre

| Fichier | Contenu | Écrit par |
|---|---|---|
| `registre/journal-bot.jsonl` | une ligne scellée par question binaire : bras A, B et C, bras posté, statut de l'alphabet | chaque passage du bot |
| `registre/dossiers/` | le dossier de lecture de chaque question | chaque passage du bot |
| `registre/journal-autres.jsonl` | une ligne scellée par question non binaire (numérique, choix multiple, date, conditionnelle) : la prévision postée (bras A) et l'empreinte du raisonnement | chaque passage du bot |
| `registre/issues-autres.jsonl` | l'issue brute de ces questions, telle que Metaculus la donne, jamais réécrite | le workflow « Score du bot alphabet » |
| `registre/issues.jsonl` | l'issue de chaque question résolue (0 ou 1), jamais réécrite | le workflow « Score du bot alphabet », chaque lundi |
| `registre/score.json` | Brier et score logarithmique par bras, comparaison appariée C − B et C − A | le même workflow |

Ce sont ces fichiers qui serviront à calibrer : ils restent dans le dépôt, datés par l'historique Git.

## Scorer

```
python score_registre.py --metaculus
```

Brier et score logarithmique de chaque bras, et la comparaison **appariée** sur les questions où les trois bras existent :
C − B (l'apport des cartes) et C − A (l'alphabet contre le modèle seul). Les lignes dont le sceau ne correspond plus sont
écartées et listées. Sur quelques dizaines de questions, aucune conclusion : le nombre de questions décide de ce qu'on
peut dire.

## Motifs de rejet classés

Chaque candidate écartée porte une catégorie, gardée au registre (`rejets_classes`) et comptée par le bilan et par
`score_registre.py` (`motifs_rejet`) :

| Catégorie | Ce qu'elle dit |
|---|---|
| `aucun_fait` | aucun fait pertinent dans les résultats : un problème de **recherche** |
| `marqueur_non_rempli` | des faits existent mais ne remplissent pas le marqueur : un problème de **marqueur**, ou une vraie absence |
| `contredit` | un fait de la situation contredit la carte : une **vraie absence de structure** |

Seule la dernière renseigne sur l'alphabet lui-même ; les deux autres renseignent d'abord sur l'outil.

## Points ouverts

- **Stabilité du bras B** (décidé le 2026-11-04 : ne rien changer avant d'avoir des données). Sur la même question, la vue
  extérieure a donné 2,5 % puis 8 % d'un passage à l'autre. Les passages répétés en `test_questions` fournissent
  gratuitement des estimations répétées de B pour les mêmes questions : quand il y en aura assez, mesurer la dispersion,
  puis choisir entre une classe de référence plus contrainte et une médiane de plusieurs estimations.

## Limites, à dire avec les résultats

- **Pas d'humain dans la boucle.** Le codeur est un modèle de langage seul : le bot mesure « le skill joué par un modèle »,
  pas le skill avec le codage humain qu'exige A4. Les tests du codeur du §25 (noms neutres, recouvrement lexical) se font
  à part, sur les dossiers du registre.
- **Le moteur n'a encore aucun cas réel actif** (`validation.md` §23) : les multiplicateurs des cartes sont hypothétiques.
  C diffère de B par ces seuls multiplicateurs ; c'est précisément ce que le bot éprouve.
- **Seuls les événements « apparait », « persiste » et « disparait »** sont pris en charge ; les événements composés
  (« s'intensifie », qui exigent des références séparées) et les questions nominatives passent au bras A.
- **Prévisions humaines** : les consignes du bras C interdisent cotes de marché et prévisions publiées (§26), mais la
  recherche peut en ramener ; le bras A, celui du bot modèle, n'a pas cette consigne.
- **Le commentaire public est en anglais**, avec les drapeaux du moteur en français.
- **Coût** : environ trois appels au modèle et jusqu'à douze recherches par question binaire, plus le bras A.

## Tests hors ligne

```
ALPHABET_SKILL_DIR=alphabet-situationnel python -m unittest discover -s tests
```

Modèle et recherche simulés, vrai moteur : bras C posté, correction après refus, refus définitif (bras A, B conservé),
question hors alphabet, réponse illisible, événement incompatible avec l'état, sceau du journal, score apparié.
