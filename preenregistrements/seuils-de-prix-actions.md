# Seuils de prix : calibrage sur les actions (préenregistrement, 2026-11-20, 19 h 55)

Suite de `seuils-de-prix-calibrage.md` (critère atteint sur cryptomonnaies, Brent et indices, −0,206). Décision de
l'auteur (19 h 49, option 1) : cours d'actions lus chez Twelve Data avec sa clé, sans écrire de cours brut dans le dépôt.

- Questions : mêmes règles de lecture (`mise_au_point/seuils_prix_essai.py --actions`), actifs de `seuils_prix.ACTIONS` ;
  recensement : 55 questions (Tesla 31, Apple 10, Nvidia 5, Microsoft 3, AMD 2, autres 4 ; « à la date » 33,
  « atteint avant » 22 ; Manifold 48).
- Calcul, témoin et critère : identiques au passage d'origine (M − I < 0, intervalle à 90 % excluant 0).
- Si le critère est atteint : `ACTIONS_DANS_LE_BOT = True` (règle de l'auteur : vérifié à son niveau → introduit).
- Lancé une fois, dans GitHub (workflow banc_seuils_actions.yaml) ; seul le fichier de résultats est enregistré.
