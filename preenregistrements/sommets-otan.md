# Présence du président américain à un sommet de l'OTAN — procédure écrite avant le calcul

Décision de l'auteur, 2026-11-24, 18 h 15 : « Tu peux faire l'OTAN ». Une passe ; sans retour. Lus avant : la liste
officielle des sommets (nato.int) et le contrôle de concordance avec COLT (voyages du président américain), sans les
issues des questions.

## Règle (sommets_regle.py)
Sommets officiels en personne (virtuel de février 2022 exclu). Présent : sommet tenu aux États-Unis (hôte), ou voyage
du président américain dans le pays hôte pendant le sommet (± 3 jours), à défaut la même année (Londres 1990, Rome
1991, Madrid 1997 : dates de la page officielle discordantes, voyages COLT en juillet 1990, novembre 1991, juillet 1997).
P = (présences + 0,5) / (sommets + 1), sommets clos avant la date de la question et couverts par COLT (jusqu'en 2025).
Limite déclarée : mesure de la fonction (le président américain), pas de la personne.

## Évaluation (une passe)
Questions reconnues (« Trump … attend … NATO summit »). Référence = part de oui de tout le corpus résolu hors groupe ;
mélange d'un quart plafonné à 15 points ; branchement si (1) règle < référence, (2) mélange < référence, (3) règle <
référence sur 2026 (ecosystemes/sommets-otan-branchee.json) ; dans le bot, même mélange, même plafond, journal scellé.
