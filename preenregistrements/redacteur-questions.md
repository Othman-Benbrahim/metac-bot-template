# Le modèle du rédacteur de questions (préenregistrement, 2026-11-19, 11 h 35)

Décision d'auteur du 2026-11-19, 11 h 24 : « je valide les 3 points » (point 6 : apprendre, sur les questions
résolues, les régularités de ceux qui écrivent les questions ; banc en ombre, rien dans le bot avant le tournoi).
Origine : décision du 2026-11-19, 6 h 33 (anticiper les attentes des organisateurs, les questions passent par la
perception humaine). Code : `banc_redacteur.py` ; essai `redacteur_questions`. Aucun modèle de langue.

## Idée
Une question n'est pas un tirage neutre : quelqu'un l'a écrite, à un moment, avec un seuil, une échéance, une forme.
Ces choix portent de l'information sur l'issue (le statu quo gagne 4 fois sur 5 sur Metaculus ; « encore », « reste »
annoncent souvent le statu quo ; un seuil choisi près de la valeur du jour, une échéance courte, etc.). Le modèle du
rédacteur apprend le lien entre la FORME de la question et son issue, sans rien lire du monde.

## Données
Celles du banc `jugement_semblables` (`registre/jugement-questions.jsonl`, ForecastBench, CC BY-SA 4.0), même cohorte
complète (clôture prévue passée depuis au moins 30 jours), mêmes garde-fous contre la fuite : pour juger une question
d'un jeu, le modèle n'est entraîné que sur des questions dont la clôture prévue ET la résolution précèdent la date du
jeu ; jamais la même question. Confirmation : jeux de 2026 (comme `jugement_semblables`). La prévision de la foule
n'entre jamais.

## Variables du rédacteur (fixées ici, avant tout passage)
Plateforme ; forme (élection, justice, seuil, échéance, autre, règles de `banc_jugement`) ; tranche d'horizon (≤ 30,
31-90, > 90 j) et log de l'horizon ; présence d'un nombre ; mots du statu quo (remain, still, continue, stay, keep,
maintain) ; mots du changement (first, new, again, resign, leave, launch, release, announce, sign, pass, ban,
ceasefire, deal, agreement, invade, attack) ; négation (not, no, without) ; « at least / more than / exceed » ;
« before / by » ; longueur du titre (log du nombre de mots).
Modèle : régression logistique pénalisée (L2, λ = 1), réapprise à chaque jeu sur le passé admis.
Probabilité finale R = (n·p_logit + 5·R1) / (n + 5) n'est PAS utilisée : R est la sortie brute du modèle, bornée à
[0,02 ; 0,98].

## Critère (un seul regard)
Perte log R − S (S = questions semblables, la référence adoptée comme départ) sur les questions de confirmation ;
bootstrap par question ; risque `es.risque_corrige(1)`. R meilleur si la borne haute < 0. Rapportés aussi : R contre
R1 (plateforme × forme × horizon), discrimination, par plateforme (Metaculus à part, c'est notre terrain), la moyenne
(R + S) / 2 en descriptif seulement.

## Attendu (Claude, avant le passage)
R bat R1 (il voit plus de traits) ; contre S, pas de gain net : S voit déjà les mots via le TF-IDF, et le rédacteur
n'ajoute que des traits grossiers. Un gain, s'il existe, viendra de Metaculus, où le statu quo domine.

## Sort
Quel que soit le verdict, rien n'entre dans le bot avant le tournoi (condition de l'auteur) ; un verdict favorable
serait proposé à l'auteur pour après.
