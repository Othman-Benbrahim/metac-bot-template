# Accords selon l'état de la guerre — procédure écrite avant le calcul

Décision de l'auteur, 2026-11-24, 16 h 28 : découpage « matriochka » des accords après l'échec de la règle PA-X
générique (preenregistrements/accords.md). Nouvel essai, pas une retouche. Procédure versée avant tout calcul ;
une passe ; sans retour. Seuls les en-têtes du fichier UCDP ont été lus avant (aucune issue de question, aucun taux).

## État de la guerre (ecosystemes/guerres-suivies.csv, une source par date)
Six guerres : Russie–Ukraine, Israël–Hamas, Yémen–Houthis, États-Unis–Houthis, Israël–Iran, États-Unis–Iran.
Le titre désigne la guerre (règles de correspondance dans accords_guerre.py). Dernier événement avant la date de la
question : début ou rupture → « guerre en cours », âge = jours depuis cet événement ; cessez-le-feu → « cessez-le-feu en
vigueur », âge = jours depuis. Type (inter / interne) de la table.

## Mesure : UCDP Conflict Termination Dataset v4-2024 (niveau conflit, 1946-2023)
Épisode : c_epid ; début = start_date2 ; fin = c_ependdate quand c_epterm = 1 ; issue = c_outcome ; extra-systémiques
exclus ; type 2 = inter, 3 et 4 = interne. Tranches d'âge : moins de 365 jours, 365 jours et plus.
- cessez_le_feu, guerre en cours : taux des fins par issue 1 ou 2, par tranche, pour le type ; autres fins sans
  événement ; épisodes en cours censurés à la date de la question (au plus tard 2023-12-31).
- accord_paix, guerre en cours : issue 1 seule.
- tenue, cessez-le-feu en vigueur : après un épisode terminé par l'issue 2, reprise = début de l'épisode suivant du même
  conflit ; taux par tranche de temps depuis la fin ; tous types réunis.
- P = 1 − exp(−Σ λ·jours de chaque tranche parcourus pendant h) ; « continues » = 1 − P(rupture).
- Abstention : guerre non trouvée ; « conclure » pendant un cessez-le-feu, « tenue » pendant une guerre ; échéance
  illisible (lecture de accords_regle.echeance).
- Limites déclarées : une reprise UCDP exige 25 morts dans l'année (seuil plus haut qu'une « rupture » Metaculus) ;
  l'accord nucléaire n'est pas une fin de guerre (pris tel quel quand une guerre est en cours).

## Évaluation (une passe)
Référence = part de oui de toute la famille accords hors groupe (comme l'essai précédent). Mélange d'un quart plafonné à
15 points. Branchement par sous-famille si (1) règle < référence, (2) mélange < référence, (3) règle < référence sur
les questions de 2026. Sous-familles branchées écrites dans ecosystemes/accords-guerre-branchees.json ; dans le bot,
même mélange avec sa prévision, même plafond, journal scellé.
