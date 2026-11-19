sources: registre/banc-wikipedia.json
constantes: 90
# Résultat : tendance des pages vues Wikipédia et protections d'articles (2026-11-19)

Run 44428639555, bot 0.10.304, préenregistrement preenregistrements/wikipedia.md. Aucun appel à un modèle, aucune clé.
892 questions distinctes de 2026, 859 avec au moins un article Wikipédia (en) trouvé pour leurs entités.

- Perte log : S 0,6588 ; S ajusté par la tendance des pages vues 0,6587. Écart nul (−0,0001).
- Intervalle par question [−0,005 ; +0,005] ; corrigé [−0,008 ; +0,008]. Critère non atteint.
- β appris sur tout : −0,25 (de sens opposé à GDELT) ; rang tendance / issue −0,008.
- Par plateforme (vu après coup) : Manifold 0,6452 → 0,635 ; Metaculus 0,5667 → 0,5737 ; Polymarket 0,6769 → 0,6786.
- Lien avec GDELT : rang 0,348 entre les deux tendances. Wikipédia mesure en partie la même attention, en partie autre
  chose, et cette autre chose ne prédit pas non plus l'issue.

Descriptif, non jugé : 116 questions dont un article a été protégé dans les 90 jours avant le jeu. Oui dans 35,3 % des
cas, contre 28,9 % sans protection, pour un S moyen presque égal (0,182 contre 0,175). S sous-estime un peu plus le oui
quand un article est verrouillé ; sur 116 questions, cet écart reste dans le bruit. Piste à garder, pas un résultat.

Verdict : non retenu. L'attention du public, qu'on la mesure par la presse (GDELT) ou par Wikipédia, ne déplace pas la
prévision au-delà des semblables. Essai tendance_wikipedia clos en 0.10.307.
