# Préenregistrement : sursauts de l'attention GDELT (piste « réponse aux chocs »)
2026-11-18, bot 0.10.281, écrit avant toute requête des comptes et tout calcul sur les issues.

Décision d'auteur du 2026-11-18, 18 h 25. Origine : Fragile to Antifragile (Taleb), confrontation Complex Systems
Frameworks. Aucun appel à un modèle.

## Pourquoi pas les séries chiffrées
Proposé d'abord sur les séries (FRED, DBnomics). Vérification avant écriture (registre/banc-b.jsonl, 832 questions) :
le taux de base B des séries est presque toujours proche de 0,5 (26 prévisions sous 0,15 ou au-dessus de 0,85, une
seule surprise). Il n'y a rien à corriger là. Les ratés (OUI prévus sous 30 %) sont dans les questions Metaculus,
sans série. La « fragilité » est donc mesurée sur l'attention médiatique du sujet de la question.

## Mesure (fixée ici)
Mêmes comptes quotidiens que tendance-attention.md (90 jours avant le jeu). Indice de sursaut de Goh et Barabási :
b = (σ − μ) / (σ + μ) des comptes quotidiens, de −1 (régulier) à 1 (rafales). Sans article : pas d'ajustement.

## Règle et comparaison
- p' = 0,5 + (p_M − 0,5)·(1 − λ·max(0, b)), λ choisi sur la grille 0 à 1 (pas 0,05) en laissant de côté la question
  jugée (ex æquo : λ le plus petit). La règle ne fait qu'éloigner M des extrêmes ; elle ne change jamais son sens.
- Écart, intervalle, regard, risque : comme tendance-attention.md (essai sursauts_attention).
- Adoption seulement si l'intervalle corrigé est entièrement sous zéro, puis décision datée de l'auteur.
- Rapportés aussi : indice moyen des ratés (OUI prévus sous 30 %) contre les autres, profil des erreurs.

## Limites connues
Même échantillon que la tendance. L'indice dépend du volume : un sujet peu couvert paraît « en rafales » ; on le dit
si les ratés sont surtout des questions à très peu d'articles.

## Amendement du 2026-11-18, 19 h 16 (avant toute requête des comptes)
Décision d'auteur (« oui, évidemment »), sur le modèle du filtre de cohérence de J. Landrevie (physical-tracking) :
l'indice est calculé APRÈS retrait des pics isolés. Un jour intérieur au-dessus de 5 × base (base = max(médiane des
90 jours, 1)), dont la veille ET le lendemain restent sous 2 × base, est ramené à la médiane ; les deux jours du bord
ne sont pas touchés. Seul l'indice filtré est jugé (essai sursauts_attention inchangé) ; l'indice brut et le nombre
de pics retirés sont affichés, sans jugement. La tendance (tendance-attention.md) n'est pas filtrée.
Réserve écrite avant les données : l'analogie avec le sport est imparfaite. Un sprint d'une seule image est
physiquement impossible ; un jour d'actualité isolé est souvent un VRAI événement (les doublons de titres sont déjà
retirés par la requête). Le filtre peut donc effacer du signal autant que du bruit ; l'affichage de l'indice brut
permet de le voir.
