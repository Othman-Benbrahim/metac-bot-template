# Calibration après coup (méthode de Platt) des prévisions binaires publiées (préenregistrement, 2026-11-28)

Décision de l'auteur (00 h 28) : « ça ne coûte rien, on le fait ». Rédigé **avant toute donnée** : au 28/11, le registre compte 21 questions publiées et aucune issue enregistrée.

Origine : l'analyse de calibration de Metaculus (Q1 et Q2) trouve un score de Brier amélioré de 0,016 sur les questions binaires (p < 0,001) grâce à la méthode de Platt (voir `claude/analyses-metaculus-reglages-2026-11-28.md`, relayé). C'est le seul effet de ces analyses mesuré sur les données plutôt que par enquête.

Une passe. Aucun modèle de langue, aucun crédit.

## Question
Une recalibration de Platt, apprise sur nos propres questions Metaculus résolues, améliore-t-elle nos prévisions binaires sur des questions plus récentes, qu'elle n'a pas vues ?

## Déclenchement
- Le test a lieu **une seule fois**, dès que le registre compte **au moins 100 questions binaires résolues** répondant aux conditions ci-dessous. Le décompte est fait par le code chaque nuit (score) ; aucune issue n'est regardée avant.
- Si le critère n'est pas atteint, un **second et dernier passage** a lieu à 200 questions, avec la même procédure.

## Données
- **Questions retenues** : les questions binaires des tournois Metaculus (MiniBench, FutureEval) sur lesquelles le bot a **publié** une prévision (`registre/journal-bot.jsonl` : `publie` vrai, mode autre que `test_questions`), et résolues par OUI ou NON (`registre/issues.jsonl`). Les questions annulées ou ambiguës sont exclues et comptées.
- **Prévision retenue** : la dernière probabilité publiée avant la clôture de la question, bornée à [0,01 ; 0,99].
- **Ordre** : les questions sont triées par date de publication de cette prévision.

## Découpage
- **Apprentissage** : les 60 % les plus anciennes.
- **Épreuve** : les 40 % les plus récentes. Aucun réglage n'utilise l'épreuve.

## Méthode
- **Platt à deux paramètres** : p' = σ(a · logit(p) + b), avec a et b estimés par maximum de vraisemblance (régression logistique de l'issue sur logit(p)) sur la seule partie d'apprentissage. Il n'y a pas de régularisation, et p' est bornée à [0,01 ; 0,99].
- **Comparaison** : sur l'épreuve, la perte logarithmique de p' est comparée à celle de p (les prévisions brutes publiées).

## Critère
- **Perte logarithmique moyenne (Platt − brut) < 0, avec un intervalle à 90 % qui exclut 0.** L'intervalle est obtenu par rééchantillonnage des questions de l'épreuve, 10 000 tirages, graine 20261128.
- Rapportés sans effet sur le critère :
  - le score de Brier ;
  - les valeurs de a et b (a < 1 signifie des prévisions trop tranchées, a > 1 trop timides ; b ≠ 0 signale un penchant vers OUI ou vers NON) ;
  - le détail selon l'origine de la prévision finale (brique de base, mélange, modèle seul) ;
  - le diagramme de fiabilité en 5 tranches.

## Conséquence prévue
- **Critère atteint** : la recalibration devient la **dernière étape** des prévisions binaires, après le juge et le garde-fou, juste avant la publication. Elle est réapprise chaque mois sur toutes les questions résolues (fenêtre qui s'agrandit). La décision de brancher revient à l'auteur au vu du résultat.
- **Critère non atteint** : rien ne change.
- Les questions à choix multiples et numériques ne sont pas concernées ; une procédure à part sera rédigée si l'auteur le souhaite.

## Limites déclarées
- **Peu de questions** : 100 questions, dont 40 à l'épreuve, donnent un test de faible puissance. Le second passage à 200 est prévu pour cela.
- **Les questions changent avec le temps** (thèmes, rédaction par une IA depuis le 1er juin 2026), et le bot aussi (nouvelles briques, changement de modèle). Une calibration apprise sur une période peut ne plus valoir sur la suivante. Le découpage chronologique sert justement à mesurer ce risque.
- **La recalibration corrige un biais d'ensemble**, pas une erreur question par question.

Conflit d'intérêts déclaré : la procédure est rédigée par un modèle d'Anthropic.
