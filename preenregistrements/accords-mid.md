# Tenue des trêves : couche « affrontements armés entre États » (MID 5.0, depuis 1946) — procédure écrite avant le calcul

Décisions de l'auteur, 2026-11-24 : 16 h 38 (« ne les éludes pas ») ; 16 h 46 (séries depuis 1946 ; seconde couche MID).
Nouvel essai sur la sous-famille « tenue » seule ; une passe ; sans retour. Lus avant : en-têtes et nombre de lignes
(2 436 disputes, 5 883 participations) ; aucun taux, aucune issue de question.

## Règle (accords_mid.py)
- Guerre de type « inter » : disputes MID de niveau d'hostilité 4 ou 5 commencées en 1946 ou après ; pour chaque paire
  d'États opposés, trêve = fin de la dispute ; échec = nouvelle dispute retenue entre les deux mêmes États ; censure au
  2014-12-31 ; tranches < 90 jours, 90-364, ≥ 365 ; P(échec avant h) = 1 − exp(−Σ λ·jours) ; « continues » = 1 − P.
- Guerre de type « interne » : tenue ETH/PRIO inchangée (preenregistrements/accords-cessez.md).
- Limites déclarées : une dispute MID d'emploi de la force est plus large qu'une guerre (la « rupture » Metaculus est
  souvent de ce niveau) ; série arrêtée en 2014.

## Évaluation (une passe)
Mêmes questions « tenue », même référence, même mélange plafonné, mêmes trois critères. Branchement écrit dans
ecosystemes/accords-mid-branchees.json ; dans le bot, même mélange, même plafond, journal scellé.
