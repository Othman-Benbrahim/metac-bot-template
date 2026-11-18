# Préenregistrement : crédibilité par catégorie d'acteurs (piste « confiance »)
2026-11-18, bot 0.10.281, écrit avant tout calcul sur les issues (seule la répartition des titres par cellule a été
regardée, sans les issues).

Décision d'auteur du 2026-11-18, 18 h 25. Origine : Process of Building Trust / Types of Trust, confrontation Complex
Systems Frameworks. Aucun appel à un modèle ; aucune cote ni prévision de foule : titres et issues seulement.

## Ce qui est testé (et ce qui ne l'est pas)
La crédibilité au sens propre (cet acteur tient-il SES promesses ?) demanderait l'historique de chaque acteur : trop
peu de questions par acteur nommé. On teste une version grossière : savoir QUI agit et QUEL GENRE d'acte est attendu
apporte-t-il quelque chose au taux de base forme × horizon (R1) ?

## Mesure (fixée ici, banc_credibilite.py)
- Catégorie d'acteur par mots du titre, dans cet ordre : banque centrale, organisation internationale, entreprise,
  parlement ou tribunal, exécutif ; sinon « aucun ». Genre d'acte : annonce, acte concret, autre.
- Répartition des titres de 2026 (lignes, avant toute issue) : 71 % « aucun » ; environ 550 lignes avec un acteur.
- p_C = (oui de la même cellule + 5·R1) / (questions de la cellule + 5), sur les questions CLOSES ET RÉSOLUES avant
  la date de jeu (sans fuite par construction).

## Règle et comparaison
- Questions jugées : questions distinctes de 2026 (première date de jeu) dont l'acteur est reconnu.
- Écart = perte log de C − perte log de R1 ; intervalle par question, un seul regard (tout_juger), risque corrigé
  (essai credibilite_acteurs). Secondaire : C contre S (semblables).
- Si l'intervalle corrigé est entièrement sous zéro : la cellule acteur × acte est proposée comme classe de référence
  du bot, et une version fine (promesses tenues par acteur nommé, extraites avec citation vérifiée comme les cartes
  ancrées) sera préenregistrée. Sinon : non retenue.

## Limites connues
Les essais de classe de référence et de semblables ont déjà échoué ; le résultat attendu est nul. Le test coûte zéro.
