# Plan de transition entre fournisseurs d'IA

**Contrainte d'auteur du 2026-11-14 :** le projet utilisera plusieurs IA chez plusieurs fournisseurs, au gré des
crédits disponibles, dans cet ordre : **Amazon Bedrock → Microsoft Azure → OVHcloud → Google**. Aucune dépense sur un
compte personnel hors crédits. Chaque passage d'un fournisseur au suivant se prépare à l'avance, rôle par rôle.

## Rôles et modèles

| Rôle | Variable | Aujourd'hui (2026-11-14) | Microsoft (dès l'abonnement) | Après Bedrock (23 novembre) | OVH | Google |
|---|---|---|---|---|---|---|
| Lecteur principal (plan, lecture, bras A) | `ALPHABET_LLM` | Mistral Medium, API Mistral (compte personnel, **arrêté** : limite atteinte) | **gpt-5-mini** (version 2025-08-07), Azure AI Foundry, `azure_ai/gpt-5-mini` — Mistral Medium indisponible sur l'abonnement gratuit | Azure | à choisir dans le catalogue OVH | à choisir dans Vertex AI |
| Petites tâches (résumés, analyse) | `ALPHABET_PETIT_LLM` | Claude Haiku 4.5, Bedrock | Bedrock tant qu'il reste des crédits, Azure en secours | Azure | OVH | Google |
| Chercheur (requêtes web) | `ALPHABET_CHERCHEUR` | smart-searcher avec Claude Haiku 4.5, Bedrock | idem | Azure (modèle équivalent du catalogue) | OVH | Google |

Les cases « à choisir » se remplissent avant la bascule, après une sonde (workflow « Santé des modèles »).

## Règles

1. **Le lecteur, c'est le modèle et sa version, pas le fournisseur.** Le bot relève la version exacte servie à
   chaque appel (`modeles_servis` dans le registre du banc et dans le bilan de chaque passage, bot 0.10.100). Le même
   modèle à la même version chez un autre fournisseur continue la même série ; une autre version ou un autre modèle est
   un autre lecteur.
2. **Une série d'essai ne mélange jamais deux lecteurs.** Chaque essai inscrit dans `essais.py` dit sur quel lecteur
   il se juge (champ `lecteur`) ; les lignes d'un autre lecteur sont comptées à part (`autres_lecteurs`).
3. **Contrôle de continuité à chaque changement de fournisseur pour un même modèle.** Relire 10 questions déjà lues
   (champ « relire les mêmes questions » du banc) et comparer les cartes ancrées (alpha de Krippendorff, déjà dans
   `score_registre`). Si l'accord est nettement plus bas qu'entre deux lectures du même point d'accès, on traite le
   nouveau point d'accès comme un autre lecteur.
4. **Chevauchement plutôt que coupure.** Pendant la transition, le nouveau fournisseur passe en tête de la suite de
   modèles (variables du dépôt, modèles séparés par des virgules) et l'ancien reste en secours jusqu'à la fin de ses
   crédits. Une bascule automatique sur le secours change le codeur : elle est écrite dans chaque ligne du registre.
5. **Avant chaque bascule :** sonde des modèles, secrets en place, une passe courte du banc (10 questions) pour
   vérifier format, coût par question et refus.
6. **Plafond par passage** (`--budget`) maintenu à chaque fournisseur, calé sur ses crédits restants.

## Secrets par fournisseur

| Fournisseur | Secrets du dépôt | Forme du nom de modèle |
|---|---|---|
| Amazon Bedrock | `AWS_BEARER_TOKEN_BEDROCK` (+ variable `AWS_REGION_NAME`) | `bedrock/<profil d'inférence>` |
| Microsoft Azure AI Foundry | `AZURE_AI_API_KEY`, `AZURE_AI_API_BASE` (= `https://<ressource>.services.ai.azure.com/openai/v1`) | `azure_ai/<nom du déploiement>` ; le bot l'appelle par l'API OpenAI v1 de Foundry (0.10.101) |
| OVHcloud AI Endpoints | à ajouter à la bascule | à fixer |
| Google Vertex AI | à ajouter à la bascule | à fixer |

## Calendrier

| Date | Événement |
|---|---|
| 2026-11-14 | Compte Mistral personnel arrêté (limite atteinte). Décision : abonnement Microsoft dès maintenant, chevauchement avec Bedrock accepté. |
| 2026-11-14 | Mistral Medium 3.5 et DeepSeek indisponibles sur l'abonnement Azure gratuit (pas de demande de quota possible). Déploiement de **gpt-5-mini** (Global Standard). C'est un **nouveau lecteur** (règle 1) : nouvelles séries ; les essais jugés sur Mistral Medium restent sur leurs lignes Mistral. |
| à la mise en service d'Azure | Secrets Azure ; sonde ; contrôle de continuité (règle 3) ; le lecteur principal passe sur Azure. |
| 2026-11-23 | Fin des crédits Bedrock : petites tâches et chercheur passent sur Azure. |
| à fixer | Passage à OVH, puis à Google, avec les mêmes étapes. |
