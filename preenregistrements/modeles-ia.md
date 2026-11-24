# Modèles d'IA : échelle des versions par laboratoire (Epoch AI) — procédure écrite avant le calcul

Décisions de l'auteur, 2026-11-24 : source Epoch validée (14 h 35) ; « On commence » (16 h 52) ; banc Epoch lancé
(17 h 56). Nouvel essai sur la sous-famille modele_ia (l'essai « produits » par parts de oui a échoué). Une passe ; sans
retour. Lus avant : la liste des versions dans Epoch et les cibles lues dans les titres, sans les issues.

## Règle (modeles_ia_regle.py)
Échelle des versions par famille (GPT/OpenAI, Claude/Anthropic, Gemini/Google, Grok/xAI, Llama/Meta), date de première
sortie dans Epoch (organisation vérifiée). Version entière visée : échelle des versions entières ; décimale : toutes les
versions. Âge = jours depuis le barreau précédent. Taux par tranche d'âge (< 180 j, 180-364 j, ≥ 365 j) sur les écarts
de toutes les familles avant la date de la question (écart en cours censuré). P = 1 − exp(−Σ λ·jours). Version déjà
sortie avant la question = 1. Abstention : variante (Flash, Pro, mini…), sans numéro, « claim », comparaison (« than »),
course entre deux événements, échéance illisible.
Limite déclarée : Epoch date la publication ; une sortie limitée peut différer d'une « sortie publique » au sens de la
question.

## Évaluation (une passe)
Référence = part de oui de tout le corpus résolu hors groupe ; mélange d'un quart plafonné à 15 points ; branchement si
(1) règle < référence, (2) mélange < référence, (3) règle < référence sur 2026 (ecosystemes/modeles-ia-branchee.json) ;
dans le bot, même mélange avec sa prévision, même plafond, journal scellé.
