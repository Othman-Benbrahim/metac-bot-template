# Préenregistrement : « la question nomme un acteur », correctif de niveau du taux de base
2026-11-18, bot 0.10.288, écrit avant tout calcul sur les questions de 2025.

Décision d'auteur du 2026-11-18, 19 h 49 (« ok, on le fait »). Idée née APRÈS les données du banc de la crédibilité
(run 44373402637) : les questions de 2026 qui nomment un acteur se résolvent OUI plus souvent que ne le dit R1, et le
gain de C était un gain de calibrage, pas de discrimination. Une idée née des données ne se juge pas sur ces données :
elle est jugée sur les questions de 2025, qu'aucun banc de la crédibilité n'a utilisées.

## Règle (banc_acteur_nomme.py, fixée ici)
- Deux classes : acteur reconnu (mots du titre, banc_credibilite.categorie ≠ « aucun ») ou non.
- p_N = (oui des questions de la même classe, closes et résolues avant la date de jeu + 5·R1) / (n + 5) ; sans fuite.

## Comparaison
- Questions jugées : questions distinctes jouées en 2025 (première date de jeu), dont l'acteur est reconnu.
- Écart = perte log de N − perte log de R1 ; intervalle par question, un seul regard (tout_juger), risque corrigé des
  essais ouverts (essai acteur_nomme). Secondaire, affiché : toutes les questions de 2025 (avec ou sans acteur).
- Si l'intervalle corrigé est entièrement sous zéro : la classe « acteur nommé » est proposée comme correctif du taux
  de base R1 dans le bot, APRÈS le tournoi et sur décision datée de l'auteur (décision de 19 h 40 : rien ne change
  côté Metaculus avant). Sinon : non retenue.

## Limite connue
2025 n'a pas forcément le même mélange de plateformes que 2026 ; le correctif peut tenir à la composition plutôt
qu'à l'acteur. Rapportés : part de oui par période, profil des erreurs.
