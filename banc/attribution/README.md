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

**Première boucle (2026-11-10, 10 essais, journal : `resultats.tsv`).** Le recouvrement des mots du fait (qui dépend de
la langue) est retiré ; le contrôle s'appuie sur ce qui ne se traduit pas : nombres (tous dans les résultats, au moins
un dans l'extrait cité), noms propres (lexique générique des pays, villes, mois et partis ; noms composés gardés
entiers ; sigles courts et noms de ministères ignorés), nombres liés à une unité (« 7 % », « 5 mai » = « 5 May ») ; sans
extrait, au moins une ancre spécifique (ni une année, ni un pays).

| | faux acceptés | faux refus | score |
|---|---|---|---|
| travail, départ | 0 % | 97 % | 1,97 |
| travail, après | 0 % | 5,7 % | 0 |
| **caché, départ** | 0 % | 97 % | 1,97 |
| **caché, après** | **3,8 %** | **10 %** | **0,038** |

Sur la partie cachée, l'écart avec la partie de travail (0 % → 3,8 % ; 5,7 % → 10 %) est le sur-ajustement attendu :
il reste modéré. Le juge ne récompense pas une baisse des faux refus à faux acceptés égaux : c'est sa limite.
