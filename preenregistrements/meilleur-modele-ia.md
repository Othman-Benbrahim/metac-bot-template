# Brique « meilleur modèle d'IA à une date » : BROUILLON, à valider par l'auteur avant tout calcul

Écrit le 2026-11-26 vers 13 h, pendant la pause de l'auteur (« continue »). Rien n'est calculé ; aucune issue lue.

## Pourquoi
C'est la plus grande famille de questions sur l'IA du corpus : 132 questions « Will X have the top / best AI model
on <date> ? » (Polymarket, CC BY-SA via ForecastBench), sur 15 échéances mensuelles distinctes (novembre 2025 à
octobre 2026). Elles se tranchent sur le classement texte de LMArena, source NON validée : la brique ne la lit pas.

## Mécanisme (fiche sciences-techniques, sorties des modèles de pointe)
Le premier rang change par sauts, à la sortie d'un modèle de pointe ; entre deux sorties, le leader reste. D'où :
- si X est le leader connu à la date de la question : P = taux de maintien du leader d'une échéance à la suivante ;
- sinon : P = (1 − taux de maintien) × part de X parmi les nouveaux leaders passés (repli : part égale entre les
  laboratoires de pointe).

## Données, sans source nouvelle
L'historique des leaders se lit dans les issues des questions résolues elles-mêmes (une seule réponse « oui » par
échéance et par rang). Le leader « connu » à la date d'une question est celui de la dernière échéance résolue avant
cette date (décalage déclaré : il peut avoir changé depuis ; le contradicteur, en ombre, couvre le terrain).

## Évaluation proposée (une passe)
- Questions : celles dont l'échéance précédente est résolue avant leur date de jeu.
- Référence : part de oui de la famille hors groupe ; critères habituels (règle < référence sur l'ensemble et sur 2026).
- Limite déclarée : une quinzaine d'échéances seulement, donc une douzaine de transitions ; le taux de maintien sera
  imprécis. Si moins de 8 transitions sont exploitables, on ne calcule pas.

## À décider par l'auteur
1. Lancer ce passage unique.
2. Plus tard, éventuellement : valider LMArena comme source (lecture du leader du jour, sans regard vers l'avant).
