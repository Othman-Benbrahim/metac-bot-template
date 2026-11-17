# Questions de jugement Metaculus : bot standard contre bot passé par l'alphabet (préenregistrement, 2026-11-17, 21 h 15)

Décision d'auteur du 2026-11-17 (21 h 05) : « on peut commencer par là, c'est un début » ; la même décision adopte les
questions semblables comme taux de base de DÉPART sur les questions de jugement (en ombre). Question de l'auteur :
l'alphabet apporte-t-il une plus-value, même minime, au-dessus de ce que fait la médiane des bots ?
Code : `banc_jugement_alphabet.py` ; essai `jugement_alphabet`.

## Questions
Metaculus, du banc des questions de jugement, cohorte complète (clôture prévue passée depuis 30 jours), jeux de 2026
(398 questions), dans un ordre fixé par une empreinte de l'identifiant. La prévision de la communauté n'est jamais lue
ni transmise au modèle.

## Les deux bras, sur les mêmes entrées (une recherche bornée avant la date du jeu, même modèle gpt-5-mini)
- A, le bot standard : question, critères, contexte, échéance, taux de base (semblables), recherche → probabilité.
- M, l'alphabet en matriochka : sept notes de 1 à 4, une par carte (CROISSANCE : tendance ; RÉCIPROCITÉ : engagements
  datés ; HIÉRARCHIE : position des décideurs ; SEUIL : déclencheur prévu ; CONTRAINTE : freins ; PÉRIODICITÉ : temps
  restant contre temps nécessaire ; PROPORTION : distance à la résolution), sans probabilité ; puis le jugement final,
  qui voit le taux de base, les notes et un extrait plus court des recherches, avec la consigne de s'écarter franchement
  du taux de base quand plusieurs situations convergent (pour viser la faiblesse collective des bots : la
  discrimination).

## Critère
Perte log M − A, 150 premières questions non exclues (second regard à 300), critère des ombres
(`critere_ombre_b`, blocs par jeu), au risque corrigé ; exclues : les questions dont le modèle dit connaître l'issue.
Rapportés : B (semblables), discrimination de A et de M.

## Attendu (Claude)
A bat nettement B (l'information du moment compte sur ce terrain). M contre A : incertain ; si l'alphabet aide, ce sera
par la discrimination (des probabilités plus franches quand les situations convergent), au risque d'erreurs sûres
d'elles. Coût estimé : 3 appels et une recherche par question, environ 4 $ pour 150 questions.
