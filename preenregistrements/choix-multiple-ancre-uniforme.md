# Choix multiple : ancrer la répartition du bot sur 1/N (préenregistrement, 2026-11-20)

Décision de l'auteur, 2026-11-20, 15 h 58 : « si les résultats sont bons, on les introduira sur le bot Metaculus comme un mécanisme de fonctionnement ; il reste une marge d'erreur, mais c'est un pari ».

## Origine
- Mise au point `candidat-parmi-n.md` (commit 8260cc0) : sur 30 groupes Metaculus à gagnant unique (347 questions), partir de 1/N fait beaucoup mieux que le taux de base de la couche structurelle (−0,205 de perte log par question, intervalle à 90 % [−0,242 ; −0,156]). Ce test compare 1/N à notre couche structurelle, **pas** au bot.
- Lecture du code (2026-11-20) : pour les questions à choix multiple, le bot (`main.py`, `_run_forecast_on_multiple_choice`, repris tel quel par `alphabet_bot.py`) ne fait aucun ancrage explicite sur la répartition égale ; la consigne demande seulement de « laisser une probabilité modérée sur la plupart des options ».
- Journal d'ombre (`registre/journal-autres.jsonl`, au 2026-11-20) : 21 prévisions à choix multiple, 6 questions distinctes, aucune résolue. Sur la question du festival de Marrakech (10 films), le bot donne au favori entre 0,22 et 0,605 selon les passages, et jusqu'à 0,001 à certains films : répartition instable et parfois très concentrée là où l'information est faible.

## Mécanisme testé (fixé)
Pour chaque question à choix multiple à N options : p_final(option) = (1 − w) × p_bot(option) + w × 1/N, avec **w = 0,15**. La somme reste 1. Calculé après coup à partir de la prévision scellée du journal : aucun changement du bot pour ce test.

## Questions
Prévisions à choix multiple du journal d'ombre, scellées ; une par question (la dernière avant la date de résolution prévue) ; issues relevées sur Metaculus à la résolution. Questions annulées exclues.

## Suivi et critère
- Écart par question d = perte log(mélange) − perte log(bot), sur l'option gagnante ; probabilités bornées à [0,001 ; 0,999].
- Suivi séquentiel valable à tout instant : e-processus par pari (Waudby-Smith et Ramdas, 2024), comme `journal-cadre.md` ; **α = 5 %** ; verdict positif dès que la richesse atteint 20 ; arrêt sans verdict à 100 questions résolues.
- Hypothèse unique, déclarée d'avance ; échantillon à part (le journal à choix multiple ne sert à aucun autre essai).
- Si le verdict est positif, l'auteur décide de l'introduction dans le bot (mécanisme de fonctionnement), avec w = 0,15, sans réglage sur les issues.

## Limites connues
- Peu de questions à choix multiple dans le journal (6 en trois semaines) : le verdict peut prendre longtemps, ou ne jamais arriver.
- Le mélange coûte un peu quand le bot a raison avec un favori net ; il protège quand le bot écrase une option qui finit par gagner. Le pari porte sur le second effet.
