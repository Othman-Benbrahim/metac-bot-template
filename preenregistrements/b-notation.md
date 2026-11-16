# B notation : les notes souveraines ne bougent qu'aux dates annoncées (brouillon, 2026-11-16)

**Décision d'auteur du 2026-11-16 (10 h 49)** : « Je valide tout » (B notation compris). **Statut : brouillon de
pré-enregistrement.** Il ne deviendra un essai qu'après les deux conditions de la fin de ce texte.

## Rasoir d'Ockham
1. **Une phrase** : dans l'Union européenne, une agence ne change la note d'un État qu'aux dates de révision qu'elle a
   publiées d'avance ; sans date dans la fenêtre, presque rien ne bouge.
2. **Paramètres** : aucun appris sur les questions jugées. Fréquences de changement lues dans l'historique des
   décisions ANTÉRIEURES à la période de jugement.
3. **Sens fixé d'avance** : pas de date → probabilité basse ; une date et une perspective négative → probabilité
   d'abaissement plus haute qu'avec une perspective stable.
4. **Domaine** : questions « l'agence X / une agence abaissera-t-elle (relèvera-t-elle) la note de l'État Y avant la
   date D ? », États notés depuis l'UE (règlement (CE) n° 1060/2009, art. 8 bis : calendrier publié fin décembre pour
   l'année suivante, au plus trois révisions non sollicitées par an et par État, écarts motivés).
5. **Plus simple ?** : B par comptage brut (part des questions de notation résolues « oui ») ; c'est la référence.

## Règle
- **Calendrier** : `registre/calendrier-notation.csv` (agence, État, date de révision prévue), saisi depuis les
  calendriers officiels de l'année (Fitch, Moody's, S&P, Morningstar DBRS, Scope). Les pages des agences sont rendues
  par JavaScript ; le calendrier est saisi une fois par an (fin décembre), à la main ou par un navigateur sans tête, et
  daté.
- **Perspective** au jour de la question : négative, stable, positive, sous surveillance, tirée du dernier communiqué
  de l'agence antérieur à la question.
- **Probabilité** d'un changement dans le sens demandé, par agence :
  - aucune date de révision dans la fenêtre : p₀ = 0,02 (révision hors calendrier, rare et motivée) ;
  - une date ou plus : fréquence historique (Jeffreys) du changement dans ce sens à une révision, selon la perspective ;
  - plusieurs agences visées (« une agence ») : 1 − Π(1 − pₐ).
- Bornée à 0,01–0,99.

## Critère (règle d'adoption commune ; second regard à 2N)
Essai **`b_notation`** : sur les N premières questions de notation souveraine résolues après l'ouverture, perte log
de B notation inférieure à celle de B, intervalle (bootstrap par blocs) entièrement sous 0. N fixé à l'ouverture.

## Conditions avant d'ouvrir l'essai
1. **Assez de questions.** La récolte Metaculus (`recolte_metaculus.py`) dira combien de questions résolues portent
   sur une note souveraine. Moins d'une trentaine : l'essai ne serait jamais jugé ; on s'arrête là (Ockham : ne pas
   construire un outil pour des questions qui n'existent pas).
2. **Sources vérifiées.** Un historique gratuit des décisions par État (dates, sens, perspective) pour les fréquences,
   et les calendriers lisibles. Non vérifiés au 2026-11-16 : les pages d'S&P et de Scope ne se lisent qu'avec
   JavaScript ; la compilation de MNI (cinq agences) n'est pas lisible sans compte.

## Pistes de sources (à vérifier)
- S&P Global Ratings, page réglementaire « Calendar of Publication Dates For Sovereign, Regional & Local Government
  Ratings » ; Scope Ratings, calendrier PDF annuel ; communiqués de Morningstar DBRS annonçant leur calendrier.
- Les agences de la dette des États (Finlande, Lituanie, Allemagne, Serbie…) publient l'historique de leurs notes.
- La famille RSS dérivée « notation » (0.10.160) repère les décisions dans la presse économique, au fil de l'eau.
