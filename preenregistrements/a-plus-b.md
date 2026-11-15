# Pré-enregistrement — bras A et combinaison A + B (bot 0.10.106)

**Décision d'auteur du 2026-11-15** : après la clôture des essais sur B (banc du taux de base), mesurer la marge du
jugement du modèle (A) et de sa combinaison avec le taux de base. Commité AVANT tout passage du banc du bras A.

## Dispositif (`banc_a.py`)
- Questions : séries ForecastBench résolues (FRED, DBnomics, ACLED) des jeux postérieurs au 2026-07-01, hors jeux déjà
  vus par le banc de l'alphabet (2026-09-27, 10-11, 10-25), avec un B calculé par le code ; ordre : jeu le plus ancien
  d'abord, puis identifiant de question.
- A voit les mêmes données que B (taux de base et son calcul, 30 derniers points de la série avant la date
  d'information) et une recherche bornée à cette date. Une question dont un modèle déclare connaître l'issue est exclue.
- Une série par jeu de modèles (`modeles_A`) ; plusieurs modèles : moyenne des logits. Premier jeu : gpt-5-mini seul.
- Combinaison fixée ici, jamais ajustée sur les issues : logit(AB) = ½·logit(A) + ½·logit(B).

## Critère (`score_registre.critere_ombre_b`, essai `a_plus_b`)
Sur les **100 premières questions** d'une même série : perte log de AB inférieure à celle de B, et intervalle de l'écart
(bootstrap par blocs « jeu × source », 2 000 tirages, graine 0) entièrement sous 0 au niveau corrigé de la règle
d'adoption commune. Second regard possible sur les 200 premières, au risque partagé. A seul contre B est rapporté sans
verdict. Si le critère tient : décision d'auteur datée sur ce que poste le bot.

## Amendement (2026-11-15, après le premier passage de 10 questions, exécution 43655369673)
L'ordre « jeu le plus ancien, puis identifiant » mettait en tête les questions ACLED d'un seul jeu : les 100 premières
auraient formé un ou deux blocs « jeu × source », et le bootstrap par blocs n'aurait rien voulu dire. Les 10 premières
lectures étaient toutes ACLED du 2026-07-05. **Nouvel ordre** : entrelacé entre les jeux (rang de la question dans son
jeu selon l'empreinte SHA-1 de son identifiant, puis jeu). **Seules les lignes à partir de la version 0.10.107
comptent pour le critère** ; les 10 lectures du premier passage sont rapportées à part et ne seront pas relues. Le
critère lui-même (combinaison, seuil, niveau corrigé, regards) ne change pas. Constat descriptif de ces 10 lectures, qui
ne motive pas l'amendement : A recopie B sur 9 questions sur 10.

## Verdict et décision (2026-11-15)
Second regard (200 premières questions de la série gpt-5-mini, 18 blocs) : écart ½A + ½B − B = −0,013 ; intervalle
corrigé (98,75 %) [−0,027 ; −0,0006], entièrement sous 0. **Critère atteint.** Par source : ACLED A 0,480, B 0,526,
AB 0,494 ; DBnomics et FRED sans écart notable.
**Décision d'auteur du 2026-11-15 (option prudente, « au cas par cas, selon les sources »)** : le bot Metaculus poste
½A + ½B seulement pour les événements humains couverts par la presse (événement en strate 7 ou 13, avec un taux de
base) ; ailleurs, la règle précédente (bot 0.10.111). Extension éventuelle après le verdict de l'aiguillage.
