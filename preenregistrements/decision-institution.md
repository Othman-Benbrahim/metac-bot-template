# Décision d'une institution avant une échéance : outil adapté au cadre institutionnel (préenregistrement, 2026-11-21, 9 h 30)

Décisions de l'auteur (2026-11-21) : adapter l'outil au cadre institutionnel plutôt que revérifier M (8 h 55) ; le
tester rétrospectivement comme M (8 h 58) ; l'outil répond toujours, sans abstention qui gaspillerait des crédits, avec un
coupe-circuit (9 h 02-9 h 04, « OUI »).

## Pourquoi
La forme la plus fréquente du flux réel du bot sans mécanisme propre (`registre/questions-bot-cadre.md`, 7 questions sur
38) : un sénat, un conseil des ministres, une banque centrale, deux parties qui doivent signer, avant une date. Les
cartes de M sont génériques (mêmes sept questions pour un cessez-le-feu et pour un vote) ; ici le cadre est mécanique.
Déjà établi chez nous : compter les accords requis n'apporte rien seul (`accords-requis.md`) ; les engagements rapportés
surestiment l'issue (`signaux-couteux.md`, β ≈ −0,49) ; sur 10 jours le statu quo domine.

## L'outil (fixé)
Le modèle n'estime AUCUNE probabilité : il relève des faits datés dans la recherche bornée à la date de la question
(gpt-5-mini, comme le banc de M) :
- `etape_avant_echeance` : une séance, un vote, une réunion ou une signature capable de produire le OUI est-elle fixée
  avant l'échéance (prevue / aucune / inconnu) ;
- `regle` : décideur seul, majorité, majorité qualifiée, consensus, deux parties (inconnue sinon) ;
- `soutien` : le soutien requis par cette règle est-il acquis (acquis / insuffisant / inconnu) ;
- `confirmation` : un accord ou une intention déclarés par les deux parties, par une seule, par aucune (ou sans objet) ;
- `deja_decide` : une décision qui suffit à la résolution est-elle déjà prise avant la date (oui / non / inconnu).
Le code les traduit en six indicateurs (+1/−1/0 pour l'étape, le soutien, la règle ; 0/1 pour la confirmation par les
deux, par une seule, et la décision déjà prise) et les combine par une régression logistique dont le point de départ est
le taux de départ des semblables : logit(p) = logit(p_S) + Σ β·x, a priori normal (0, 1) sur chaque β, estimée en
validation croisée à 10 blocs fixés par empreinte (chaque question est prévue par un modèle qui ne l'a pas vue). Aucun
fait trouvé : p = p_S. Pas d'abstention.

## Données (fixées)
Questions de jugement résolues de ForecastBench (`registre/jugement-questions.jsonl`, cohorte complète), titre reconnu
comme décision d'institution par le motif de `decision_institution.MOTIF`, forme « élection » exclue (mécanisme propre).
Une ligne par question (le jeu déjà cherché pour M s'il existe, sinon le premier par empreinte) : 102 questions
distinctes (65 Polymarket, 25 Metaculus, 7 Manifold, 5 INFER ; 26 oui). Les cotes et prévisions de foule ne sont jamais
lues ni transmises. Recherche gelée partagée avec le banc de M (pas de nouvelle recherche pour ses questions).
Exclusion : le modèle dit connaître l'issue.

## Coupe-circuit (fixé)
Après les 20 premières questions traitées, arrêt si plus de la moitié n'a donné aucun fait utilisable.

## Critère (fixé)
Perte log de l'outil (validation croisée) contre p_S, une ligne par question, toutes les lignes en un regard
(`score_registre.critere_ombre_b`, essai `decision_institution`, bootstrap par question, risque corrigé pour les essais
ouverts). Adopté si l'intervalle corrigé est entièrement sous 0 ; le critère nominal est affiché. Descriptif : β appris sur
tout l'échantillon (quels faits portent), comparaison avec M sur les questions communes, détail Fed / hors Fed.
Lancé une fois (`banc_decision_institution.py`, workflow `banc_decision_institution.yaml`), crédits Azure, plafond 3 $.

## Limite connue d'avance
Les décisions de la Fed (réunions fixées, décideur collégial à majorité) pèsent lourd dans l'échantillon (Polymarket) ;
le détail hors Fed est rapporté. Une centaine de questions : seul un effet net se verra.
