# Cessez-le-feu et tenue : couche « guerres entre États » (COW, depuis 1946) — procédure écrite avant le calcul

Décisions de l'auteur, 2026-11-24 : 16 h 38 (« ne les éludes pas ») ; 16 h 46 (« 1817-2007, c'est un peu vieux comme
série » → guerres commencées en 1946 ou après). Nouvel essai ; une passe ; sans retour. Lus avant : en-têtes et
décomptes descriptifs (38 guerres depuis 1946, 2 avec un second épisode) ; aucun taux, aucune issue de question.

## Règle (accords_etats.py)
- Guerre de type « inter » (table sourcée) : COW Inter-State War v4.0, guerres commencées en 1946 ou après.
  - cessez_le_feu, guerre en cours depuis a jours : taux de fin de guerre (dernier combat de tous les participants,
    toutes issues) par tranche d'âge (< 365 jours, ≥ 365) ; guerres non finies censurées (au plus 2007-12-31).
  - tenue, trêve en vigueur depuis a jours : pour chaque paire d'États opposés, trêve = fin du premier épisode ; échec =
    second épisode de la même guerre ou nouvelle guerre COW entre les mêmes États ; censure au 2007-12-31 ; tranches
    < 90 jours, 90-364, ≥ 365.
- Guerre de type « interne » : mesure ETH/PRIO inchangée (accords_cessez.py, preenregistrements/accords-cessez.md).
- Limites déclarées : 38 guerres seulement ; série arrêtée en 2007 ; la fin d'une guerre COW n'est pas toujours un
  cessez-le-feu négocié (victoire comprise).

## Évaluation (une passe)
Mêmes questions, même référence, même mélange plafonné, mêmes trois critères par sous-famille que
preenregistrements/accords-cessez.md. Branchées écrites dans ecosystemes/accords-etats-branchees.json ; dans le bot,
même mélange, même plafond, journal scellé.
