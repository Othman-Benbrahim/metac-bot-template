# Règle : mise au point et confirmation séparées (décision de l'auteur, 2026-11-20, 02 h 36)

Constat de la nuit du 19 au 20 novembre 2026 : une trentaine d'essais ont été jugés sur le même échantillon de confirmation (questions de 2026 du registre de jugement). À force de le consulter, on finit par y trouver quelque chose par hasard (mécanisme 7, les deux poches, à l'échelle du projet) ; le risque corrigé ne suffit plus.

1. **Mise au point** : tout ce qui existe au 2026-11-20 — le registre de jugement jusqu'à cette date et l'échantillon `registre/mise-au-point/questions.jsonl` (forecasting_raw, 2015-2023 : Metaculus, Good Judgment Open, CSET). On y essaie librement ; rien n'y est un verdict.
2. **Confirmation** : uniquement les questions ForecastBench dont la date du jeu est **postérieure au 2026-11-20** (`essais.CONFIRMATION_DEPUIS`), résolues et closes depuis au moins 30 jours. Chaque brique n'y passe **qu'une fois**, préenregistrée ; aucune n'y est mise au point.
3. Le test du journal d'ombre (`preenregistrements/journal-cadre.md`) n'est pas concerné : ses questions sont postérieures par construction.
