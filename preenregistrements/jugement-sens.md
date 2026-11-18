# Préenregistrement : questions semblables par le sens (embeddings) contre par les mots (TF-IDF)
2026-11-18, bot 0.10.259, écrit avant le premier calcul.

Décision d'auteur du 2026-11-18, 12 h 20, après lecture du dépôt lioneldreyfuss-ui/recherche_semantique.
Hypothèse : des voisines trouvées par le sens (même idée, autres mots : « ceasefire » et « end of hostilities »)
donnent un meilleur taux de départ que des voisines trouvées par les mots communs.

## Ce qui est comparé
- Référence : p_S (adopté le 2026-11-17 comme taux de départ, en ombre), TF-IDF.
- Variante : p_SE, exactement le même calcul (50 voisines, poids = similarité bornée à 0, retour vers R1 avec M = 5,
  voisines closes et résolues avant le jeu, cohorte complète), la similarité étant le cosinus des embeddings du
  modèle BAAI/bge-small-en-v1.5 (local, aucun appel payant). Aucun réglage choisi après coup.

## Règle
- Jugement principal : questions de 2026 (même coupure que l'essai des semblables), toutes sources ; écart = perte
  de p_SE − perte de p_S ; bootstrap par question, risque corrigé de l'essai (1 regard, pas de second).
- Condition supplémentaire, apprise de l'essai des doublons (qui gagnait en 2026 et ne se répliquait pas en 2025) :
  l'écart moyen doit aussi être négatif sur les questions de 2025 (réplique), sans exigence d'intervalle.
- Retenu en ombre si les deux conditions sont remplies ; sinon non retenu. Adoption : décision datée de l'auteur.
- Rapporté sans être jugé : écart par source (Metaculus, Manifold, Polymarket, INFER).

## Ajout du 2026-11-18, 12 h 45, après le résultat (run 44294691789), avant tout calcul par source sur 2025
Question de l'auteur : se servir du sens sur les seules questions Polymarket (seule source gagnante en 2026, −0,029).
Ce sous-groupe a été trouvé APRÈS coup, parmi quatre sources : il ne vaut que s'il se reproduit. Règle : le sens est
retenu pour Polymarket si, sur les questions Polymarket de 2025, l'écart est négatif avec un intervalle (risque
0,05/4, quatre sources regardées) entièrement sous zéro. Sinon, non retenu.
