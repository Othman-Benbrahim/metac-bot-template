# Brique « produits » — procédure écrite avant le calcul

Décision de l'auteur, 2026-11-24, 16 h 52 : « On commence » (… annonces et produits) ; l'auteur est absent.
Découpage matriochka. Une passe ; sans retour. Lus avant : les titres de la famille et les effectifs par sous-famille
(modèles d'IA 13, grand public 11, culture 9, finance 7, espace 3), sans leurs issues.

## Règle (produits_regle.py)
Sous-familles par le titre : course entre deux événements (« X avant Y ») exclue ; modele_ia ; culture (jeux, films,
livres, musique) ; espace (Starship) ; finance (introduction en bourse, jeton) ; grand_public (appareils, véhicules,
logiciels). Polarité inversée (« not », « doesn't », « no ») exclue.
Mesure faute de série extérieure pour l'instant (Epoch AI, collecteur prêt, servira à un essai séparé sur modele_ia) :
- niveau 1 : part de oui de la famille hors groupe, tirée vers la référence (poids 5) ;
- niveau 2 : part de oui de la sous-famille hors groupe, tirée vers le niveau 1 (poids 5).

## Évaluation (une passe)
Référence = part de oui de tout le corpus résolu hors groupe ; mélange d'un quart plafonné à 15 points ; un niveau passe
si (1) règle < référence, (2) mélange < référence, (3) règle < référence sur 2026 ; on branche le niveau le plus fin qui
passe (ecosystemes/produits-taux.json) ; dans le bot, même mélange, même plafond, journal scellé.
