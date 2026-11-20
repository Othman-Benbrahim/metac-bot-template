# Acteurs de veto et questions « procédure » (préenregistrement, 2026-11-20, plan A)

Décisions de l'auteur : cadre méthodologique du 2026-11-20 (16 h 50, `cadre-methodologique.md`) ; piste validée à 16 h 53 ; plan A validé à 16 h 58. Première mesure du réseau et de l'influence sur des cas réels. L'auteur précise (16 h 58) que le réseau et l'influence agissent sur tout l'écosystème : à reprendre après cette étude, hors de ce cas.

## Fondement (recherche existante)
- Tsebelis, *Veto Players: How Political Institutions Work*, Princeton University Press, 2002 ; synthèse : Tsebelis, « Decision Making in Political Systems », *British Journal of Political Science*, 1995. Un acteur de veto est un acteur dont l'accord est nécessaire pour changer le statu quo (institutionnel ou partisan, règle d'absorption). Plus d'acteurs de veto, plus éloignés, majorité plus exigeante : plus de stabilité.
- Preuves : Tsebelis, *APSR* 1999 (législation du travail, 16 pays européens) ; Kreppel (Italie) ; Warwick (durée des coalitions). Résultat contraire ou nuancé aux États-Unis : Mayhew (pas de différence entre gouvernement uni et divisé) ; Binder (le gouvernement divisé réduit la part de lois importantes).
- Mesure : DPI 2023, variable CHECKS (Scartascini, Cruz, Keefer, Banque interaméricaine de développement, CC BY 4.0), pays × année, 1975-2023 ; collecte `collecte_dpi.py`, extrait `registre/dpi/dpi-2023-veto.csv`.

## Hypothèse
À structure égale (question « procédure » : une décision, un vote, un accord avant une date), une question dont le pays a plus d'acteurs de veto se résout OUI moins souvent.

## Questions (règles fixées avant toute lecture des issues)
- Échantillon de mise au point (`registre/mise-au-point/questions.jsonl`), Metaculus et GJOpen, structure « procédure (décision, vote, accord) » (`structures_questions.structure`), questions combinées exclues.
- Pays : noms de pays de la DPI (`countryname`), plus une table d'alias fixée d'avance (démonymes ; « Congress », « Senate », « Supreme Court », « White House » → États-Unis ; « Bundestag » → Allemagne ; « Knesset » → Israël ; « Duma » → Russie ; « Westminster », « House of Commons » → Royaume-Uni ; « Rada » → Ukraine). Une question entre dans l'essai si **un seul** pays est reconnu.
- CHECKS de ce pays pour l'année de la date jugée (année ≤ 2023 ; au-delà, valeur de 2023).
- La couverture (nombre de questions retenues) sera comptée avant tout calcul et rapportée à l'auteur.

## Calcul (fixé)
- Témoin I : prévision actuelle de mise au point (80 % semblables + 20 % taux de base, en log-cotes), comme `classes_homologues_essai.py`.
- Variante V : le taux de base est remplacé par le taux de OUI des questions « procédure » PASSÉES (résolues avant la date jugée) de la même tranche de CHECKS, rétréci vers le taux de base (poids 5) ; tranches fixées d'avance : 1-2, 3-4, 5 et plus ; au moins 30 questions passées dans la tranche, sinon témoin.
- Perte log ; intervalle à 90 % par question (rééchantillonnage).
- Descriptif, sans effet sur le critère : taux de OUI par tranche (le sens prédit par Tsebelis est décroissant).

## Critère
- Candidat si V − I < 0 et l'intervalle à 90 % exclut 0.
- Confirmation (cadre méthodologique, point 1.3) : contre la sortie réelle du bot, sur les questions « procédure » du journal d'ombre résolues après le 2026-11-20, suivi séquentiel (e-processus, α = 5 %), comme `journal-cadre.md`.
- Si le sens observé est contraire à la théorie : essai clos, rien n'est adopté.

## Limites connues
- CHECKS est une mesure par pays, pas par question : une question sur une agence (FDA, banque centrale) relève d'un décideur unique, quel que soit le pays. Le plan B (compte des acteurs requis question par question, par le réseau d'acteurs) traitera ce point.
- La DPI s'arrête en 2023.
- Les États-Unis pèsent lourd dans Metaculus, et c'est là que la preuve publiée est la plus discutée (Mayhew contre Binder).
