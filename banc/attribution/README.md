# Banc d'essai du contrôle d'attribution

Boucle d'amélioration sur le modèle d'*autoresearch* (A. Karpathy, 2026) : un juge verrouillé, un seul fichier
modifiable, chaque essai mesuré, gardé s'il améliore le score, annulé sinon.

| Rôle | Fichier | Règle |
|---|---|---|
| modifiable | `alphabet_attribution.py` (racine du dépôt) | le seul fichier que la boucle change |
| juge | `banc/attribution/juge.py` | verrouillé |
| corpus | `articles.json`, `paraphrases.json`, `construire.py` → `corpus-travail.json`, `corpus-cache.json` | verrouillé ; la partie cachée ne sert qu'à la vérification finale |

**Score** (à faire baisser) : taux de faits non attribuables acceptés, tant que les faits attribuables refusés restent
≤ 10 % ; sinon 1 + faux refus.

**Corpus** : 50 articles réels de la BBC (2004-2005), une phrase chiffrée par article, paraphrasée fidèlement en français
comme le fait la lecture du bot (faits en français, extraits verbatim en anglais). Six cas par article, étiquetés par
construction : P1, P2 attribuables (avec, sans extrait) ; N1 nombre changé ; N2 nom propre remplacé ; N3, N4 fait d'un
autre article (avec un extrait réel, sans extrait). 188 cas de travail (articles 0-34), 83 cachés (35-49).

**Point de départ (0.9.3)** : 0 % de faux acceptés, mais **97 % de faux refus** : le contrôle rejette presque tous les
vrais faits, parce qu'il cherche les mots du fait français dans des résultats anglais. Score 1,97 (travail), 1,97
(caché).
