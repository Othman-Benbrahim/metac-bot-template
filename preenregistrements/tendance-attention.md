# Préenregistrement : tendance de l'attention GDELT (piste « l'avenir déjà présent »)
2026-11-18, bot 0.10.281, écrit avant toute requête des comptes et tout calcul sur les issues.

Décision d'auteur du 2026-11-18, 18 h 25 (« fais les trois »). Origine : confrontation avec la collection Complex
Systems Frameworks (Three Horizons : le futur existe déjà dans le présent sous forme marginale), document de projet
claude/confrontation-complex-systems-frameworks-2026-11-18.md. Aucun appel à un modèle.

## Données
- Comptes : `gdelt_bq.py --mode comptes`, mêmes questions distinctes et même filtre que le mode bancs (noms propres
  exigés, au moins un autre mot), titres en double retirés, NOMBRE d'articles par jour sur les 90 jours qui précèdent
  la date de jeu (J−90 à J−1). Dates sûres : jour où GDELT a vu l'article.
- Prévisions : M de registre/banc-jugement-alphabet.jsonl, une ligne par question distincte (la première date de jeu
  qui n'est pas antérieure à celle des comptes).

## Mesure (fixée ici)
tendance = ln((articles des 10 derniers jours / 10 + 0,1) / (articles des 80 jours précédents / 80 + 0,1)) ;
0 quand la question n'a aucun article (pas d'ajustement).

## Règle et comparaison
- p' = σ(logit(p_M) + β·tendance), β choisi sur la grille −1 à 1 (pas 0,05) en LAISSANT DE CÔTÉ la question jugée
  (ex æquo : |β| le plus petit).
- Écart = perte log de p' − perte log de M ; intervalle par question (bloc_par="question"), un seul regard sur toutes
  les questions (tout_juger), risque corrigé des essais ouverts (essai tendance_attention).
- Si l'intervalle corrigé est entièrement sous zéro : la tendance est proposée comme ajustement de M dans le bot
  (décision datée de l'auteur). Sinon : non retenue ; la mesure reste calculée et affichée.
- Rapportés aussi : corrélation de rang tendance / issue (descriptive), β appris sur tout, profil des erreurs.

## Limites connues
- Environ 120 questions, dont une partie sans article : seul un effet net sera détectable.
- Une attention qui monte peut précéder un NON autant qu'un OUI (on parle d'un sommet qui échoue) ; le signe de β
  n'est pas imposé.
