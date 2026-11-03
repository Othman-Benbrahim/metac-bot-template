# Bot Metaculus de l'alphabet situationnel

Version 0.1.0 · skill alphabet-situationnel 0.7.48 · auteur Othman Ben Brahim · licence MIT pour les fichiers du bot
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

Le bot **poste le bras C** quand le moteur l'estime. Sinon (question sans événement de carte, dossier refusé par le moteur,
probabilité « non estimée »), il poste le bras A et le dit dans le commentaire. Pour les **autres types de questions**
(numériques, choix multiples, dates), il se comporte exactement comme le bot modèle de Metaculus : bras A.

Étapes du bras C :
1. **Plan** : le modèle choisit les strates, 2 à 4 candidates par strate (dont une contre-candidate), l'événement de carte
   qui correspond au OUI de la question, sa sémantique, et les requêtes (trois familles par candidate, une
   discrimination par paire), formées sur le phénomène, jamais sur le nom d'une carte.
2. **Recherches** : le bot lance lui-même chaque requête (12 au plus) ; seules celles lancées par un vrai moteur de
   recherche comptent comme exécutées.
3. **Dossier** : le modèle écrit le dossier de lecture à partir des seuls résultats, avec les fiches des candidates et les
   équivalents des strates ; le bot remplit lui-même l'état daté, la date de disponibilité et les recherches.
4. **Moteur** : `calculer --dossier`. Un refus est renvoyé au modèle pour correction (2 fois au plus), avec la consigne
   de descendre à f ou de retirer un mot plutôt que d'inventer. Le moteur reste juge : aucun chiffre n'est fabriqué.

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
   - onglet **Secrets** : `METACULUS_TOKEN` ; si tu en as, `OPENROUTER_API_KEY` (ou `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`),
     `ASKNEWS_CLIENT_ID` et `ASKNEWS_SECRET` (ou `PERPLEXITY_API_KEY`). Avec le seul jeton Metaculus, la bibliothèque
     utilise les modèles du proxy Metaculus (`metaculus/gpt-4o`…), sous réserve des crédits accordés ;
   - onglet **Variables** (facultatif) : `ALPHABET_LLM` (modèle du raisonnement, format litellm), `ALPHABET_CHERCHEUR`
     (par exemple `asknews/news-summaries`).
3. Onglet **Actions** : autoriser les workflows, puis **Bot alphabet situationnel → Run workflow**, mode `test_questions`.
   Vérifier sur Metaculus (compte bot) et dans `registre/`. Puis mode `minibench`.
4. Une fois les essais concluants, activer la planification dans `.github/workflows/run_alphabet_bot.yaml` (retirer les
   « # » devant `schedule`).

En local : `cp .env.template .env`, remplir, puis `uv run python alphabet_bot.py --mode test_questions --sans-publier`.

## Scorer

```
python score_registre.py --metaculus
```

Brier et score logarithmique de chaque bras, et la comparaison **appariée** sur les questions où les trois bras existent :
C − B (l'apport des cartes) et C − A (l'alphabet contre le modèle seul). Les lignes dont le sceau ne correspond plus sont
écartées et listées. Sur quelques dizaines de questions, aucune conclusion : le nombre de questions décide de ce qu'on
peut dire.

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
