# Examen psychométrique des cartes de l'alphabet (préenregistrement, 2026-11-17, 21 h 25)

Écrit AVANT que le banc « jugement : bot standard contre alphabet » (run 44166010892) n'ait rendu ses notes.
Inspiration : pgmj/psychometrics-skill (CC0) : un instrument de mesure se valide par l'unidimensionnalité,
l'indépendance locale, l'invariance et la monotonie, avec des seuils calculés plutôt que des règles empiriques.
Code : `psychometrie_alphabet.py`.

## Règle de l'auteur (2026-11-17, 21 h 14-21 h 15)
« Si on retire et que les questions sont différentes, on n'aura pas forcément besoin des mêmes cartes, et si on les
éloigne, alors on se sépare d'un outil précieux. » Donc : **aucune carte ne sort de l'alphabet** ; les sept restent
notées sur toutes les questions ; chaque carte reçoit un statut PAR TYPE DE QUESTION, revu à chaque nouveau lot :
- **démontrée** : elle aide nettement → elle pèse dans le jugement pour ce type ;
- **non démontrée** : rien de net (ou trop peu de questions) → notée, preuves accumulées ;
- **trompeuse** : elle pousse nettement dans le mauvais sens → notée, mais plus montrée au jugement final pour ce type,
  jusqu'à preuve du contraire.

## Mesures (fixées ici)
1. Monotonie, par carte et par type (élection, échéance, seuil, justice, autre, et tout) : part de « oui » des notes
   3-4 moins celle des notes 1-2 (sens inversé pour les freins) ; p par 2 000 permutations des notes dans le type
   (graine 0) ; seuil 0,05 / 7 par type ; au moins 5 questions dans chaque groupe, sinon « non démontrée (trop peu) ».
2. Redondance : |ρ de Spearman| > 0,7 entre deux cartes, signalée (les deux restent).
3. Unidimensionnalité : part de variance de la première composante principale (freins inversés) ; si elle domine,
   l'alphabet se réduit à un seul jugement « déguisé en sept ».
4. Invariance : les statuts du point 1, type par type.
5. Fiabilité : le même modèle renote 50 questions ; kappa pondéré par carte ; sous 0,4, la carte est « peu fiable »
   quels que soient les points 1 à 4 (coût ≈ 0,50 $, à lancer sur décision d'auteur).

## Réserves écrites d'avance
Environ 150 questions et 20 à 30 % de « oui » : beaucoup de cartes seront « non démontrées » faute de puissance, par
type surtout. C'est attendu : le statut se construit lot après lot. Un statut « démontrée » ou « trompeuse » obtenu sur ce
premier lot sera revérifié sur des questions nouvelles avant de changer le jugement du bot.
