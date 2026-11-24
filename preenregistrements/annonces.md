# Brique « annonces » — procédure écrite avant le calcul

Décision de l'auteur, 2026-11-24, 16 h 52 : « On commence » (… puis annonces et produits) ; l'auteur est absent.
Découpage matriochka. Une passe ; sans retour. Lus avant : les 35 titres contenant « announce », sans leurs issues.

## Mécanisme
Calendriers promis qui glissent ; le questionneur pose la question quand l'annonce paraît possible, elle arrive moins
souvent. Pas de mesure extérieure propre aux annonces : la mesure est la part de oui des questions semblables du corpus,
hors groupe (biais du questionneur, par forme puis par annonceur).

## Règle
- Questions : titre contenant « announce » ; polarité inversée (« not », « refrain ») exclue.
- Annonceur (annonces_regle.py) : nomination (casting, présidence de la Fed, ministre…), entreprise (OpenAI, Apple,
  TikTok…), gouvernement (le reste).
- Niveau 1 : part de oui des questions « announce » hors groupe, tirée vers la référence (poids 5).
- Niveau 2 : part de oui de l'annonceur hors groupe, tirée vers le niveau 1 (poids 5).

## Évaluation (une passe)
Référence = part de oui de tout le corpus résolu hors groupe. Mélange d'un quart plafonné à 15 points. Un niveau passe
si (1) règle < référence, (2) mélange < référence, (3) règle < référence sur 2026. On branche le niveau le plus fin qui
passe (ecosystemes/annonces-taux.json) ; dans le bot, même mélange avec sa prévision, même plafond, journal scellé.
