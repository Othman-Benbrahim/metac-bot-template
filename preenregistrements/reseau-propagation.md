# Propagation dans le réseau d'acteurs, sur des questions neuves (préenregistrement, 2026-11-20, 18 h 50)

Décisions de l'auteur : observation du réseau (18 h 31) ; test sur un échantillon séparé (18 h 41) ; couverture complétée
avant le test, « avec le moins de biais possible » (18 h 45). Cadre méthodologique : observer (fait), expliquer (fait :
`registre/mise-au-point/reseau-observation-lecture.md`), tester une fois.

## Observation d'origine (échantillon de mise au point, Metaculus, GJOpen, CSET, jeux jusqu'au 2023-12-21)
Part de OUI d'une question selon la part de OUI des questions récentes (180 jours) sur les acteurs LIÉS (lien vu au moins
3 fois) : peu (< 20 %) 30,7 % ; moyen 25,4 % ; beaucoup (≥ 40 %) 19,5 %. Sens inverse dans les écosystèmes de conflit,
même sens en politique américaine.

## Questions (fixées sans regarder les issues)
Registre des questions de jugement, Metaculus et INFER, jeu à partir du 2024-01-01 (aucune n'a servi à l'observation),
au moins un acteur reconnu (`reseau_observation.acteurs`), questions combinées exclues (`fenetre_variantes.charger`).
Type par `couverture_reseau.type_question` (règles mécaniques, voir le fichier) ; recensement : conflit 297 (fiche 220,
réseau 27, extension UCDP 50) ; politique 143 (fiche 77, réseau 66) ; sans sens prédit : 83 (exclues).
Réservoir des questions passées : celles de l'échantillon de mise au point et du registre (mêmes sources), résolues
avant la date jugée.

## Calcul (fixé)
- Témoin I : 80 % semblables + 20 % taux de base (log-cotes), comme `classes_homologues_essai.py`.
- Variante P : log-cotes du témoin + s × 0,3 × b, avec b = +1 si les OUI récents liés sont < 20 %, 0 entre 20 et 40 %,
  −1 au-delà de 40 % (au moins 3 questions liées, sinon b = 0) ; s = +1 pour « conflit », −1 pour « politique ».
  0,3 vient de l'observation d'origine (écarts de log-cotes entre tranches : 0,27 et 0,34), fixé avant le test.
- Perte log ; intervalle à 90 % par question (rééchantillonnage).

## Critère
Confirmé si P − I < 0 et l'intervalle à 90 % exclut 0 (ensemble des questions jugées). Rapportés à part, sans effet sur
le critère : conflit seul, politique seul, extension UCDP seule, Polymarket et Manifold (descriptif).
Non confirmé : le motif était propre à l'échantillon d'origine ; on le garde comme observation, rien n'entre dans le bot.
Confirmé : candidat pour le bot, à vérifier contre sa sortie réelle sur le journal (cadre, point 1.3).

## Résultat (2026-11-20, 19 h 00) : non confirmé
399 questions jugées (Metaculus, INFER, 2024-2026), 258 ajustées. P − I = +0,0129, intervalle à 90 % [−0,0048 ; +0,0279] :
la propagation ne fait pas mieux que le témoin (plutôt moins bien). Part de OUI : peu de OUI liés récents 11,3 % (257),
moyen 14,9 % (141), beaucoup 1 question seulement. Le motif d'origine ne se retrouve pas : sur la période 2024-2026,
presque aucune question ne suit une vague de OUI liés, et celles qui suivent peu de OUI se résolvent MOINS souvent OUI.
Conflit seul : +0,0231 [−0,0005 ; +0,0405] ; politique seule : −0,0147 [−0,0332 ; +0,0101] (non tranché) ; extension
UCDP : +0,0083 ; Polymarket et Manifold (descriptif) : −0,0019 [−0,0142 ; +0,0093].
Lecture : le motif observé sur 2015-2023 tenait surtout à la période (2021-2022, vague d'événements et questions sur le
pire) ; il ne se transpose pas. Gardé comme observation ; rien n'entre dans le bot. Fichier :
`registre/mise-au-point/reseau-propagation.json`.
