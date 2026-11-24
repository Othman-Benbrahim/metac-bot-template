# Brique « justice » (Supreme Court Database) — procédure écrite avant le calcul

Décision de l'auteur, 2026-11-24, 18 h 19 (« la suite ? ») ; banc SCDB passé à 18 h 24 (scdb.wustl.edu ; le site de
Penn State refuse le robot, refus respecté). Une passe ; sans retour. Lus avant : les en-têtes et les titres des
questions de justice, sans leurs issues. Questions couvertes : 2 (« rule in favor of Monsanto », départ d'un juge) ;
les autres restent au bot (camp du « oui » non lisible mécaniquement, acceptation d'une affaire, autre tribunal,
personnes privées).

## Règle (justice_regle.py)
- « rule in favor of X in X v. Y » : part des affaires tranchées au fond (decisionType 1, 6, 7) gagnées par le
  demandeur (partyWinning = 1), 20 dernières sessions closes avant la question, (k + 0,5)/(n + 1).
- « any justice announce their retirement before <date> » : (départs + 0,5) / années, de 1946 à la dernière session
  close ; tout motif (décès compris : la base ne donne pas le motif) ; P = 1 − exp(−λ·h).
- Limites déclarées : la part générale des victoires du demandeur ignore l'affaire elle-même ; les départs ne tiennent
  pas compte de la saison (annonces surtout au printemps).

## Évaluation (une passe)
Référence = part de oui de tout le corpus résolu hors groupe ; mélange d'un quart plafonné à 15 points ; branchement si
(1) règle < référence, (2) mélange < référence, (3) règle < référence sur 2026 (ecosystemes/justice-branchee.json) ;
dans le bot, même mélange, même plafond, journal scellé.
