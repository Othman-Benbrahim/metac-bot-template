# Cessez-le-feu conclus en pleine guerre et leur tenue (ETH/PRIO) — procédure écrite avant le calcul

Décision de l'auteur, 2026-11-24, 16 h 38 : « Il y a deux sous familles qui n'ont pas eu de réponses satisfaisantes, ne
les éludes pas. Cherche ETH/PRIO ». Nouvel essai sur cessez_le_feu et tenue (échecs précédents : PA-X générique,
UCDP fin des conflits). Procédure versée avant tout calcul ; une passe ; sans retour. Seuls ont été lus avant : les
en-têtes et les décomptes descriptifs (2 203 cessez-le-feu, 1 234 bilatéraux ou multilatéraux, issue « incertaine »
pour 46 %) ; aucun taux, aucune issue de question.

## Données
ETH/PRIO Civil Conflict Ceasefire Dataset (ceasefireproject.org, octobre 2022 ; Clayton et al. 2023), colonnes codées
seulement ; UCDP Conflict Termination v4-2024 pour les années de conflit actif.

## Mesures (accords_cessez.py)
- cessez_le_feu, guerre en cours depuis a jours : λ par tranche d'âge de l'épisode (< 365 jours, ≥ 365) = cessez-le-feu
  bilatéraux ou multilatéraux déclarés pendant une année active du même conflit, par jour d'année active (1989-2020).
- tenue, cessez-le-feu en vigueur depuis a jours : échec = « ended 2 » (déclaré échoué par les parties ou un acteur
  international) ; autres fins datées = censure ; en cours = censure au 2020-12-31 ; jamais entré en vigueur ou date
  de fin inconnue = exclu ; tranches < 90 jours, 90-364, ≥ 365.
- P = 1 − exp(−Σ λ·jours de chaque tranche pendant h) ; « continues » = 1 − P(échec).
- État de la guerre : table sourcée (accords_guerre.etat), sans les relevés automatiques (ils datent d'après les
  questions).
- Limites déclarées : guerres civiles seulement (appliqué aussi aux guerres entre États, faute de mieux ; l'âge porte) ;
  46 % d'issues « incertaines » (traitées comme sorties sans échec quand elles sont datées : le taux d'échec peut être
  sous-estimé) ; couverture 1989-2020.

## Évaluation (une passe)
Mêmes questions, même référence (part de oui de toute la famille accords hors groupe), même mélange plafonné, mêmes trois
critères par sous-famille que preenregistrements/accords-guerre.md. Sous-familles branchées écrites dans
ecosystemes/accords-cessez-branchees.json ; dans le bot, même mélange avec sa prévision, même plafond, journal scellé.
