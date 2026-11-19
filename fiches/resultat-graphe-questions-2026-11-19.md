sources: registre/banc-graphe-questions.json
constantes: 180; 3
# Résultat : le graphe des questions en correction finale à porte (idée GraFT) (2026-11-19)

Run 44433157311, bot 0.10.308, préenregistrement preenregistrements/graphe-questions.md. Aucun appel à un modèle.
1878 questions distinctes, toutes années ; 647 ont au moins une voisine (même entité nommée, résolue dans les 180 jours
avant le jeu). Signal : erreurs récentes de S sur ces voisines, rétrécies (K = 3), derrière une porte α.

- Perte log : S 0,5374 ; S corrigé 0,5368. Écart −0,0006.
- Intervalle par question [−0,003 ; +0,002] ; corrigé [−0,005 ; +0,003]. Critère non atteint.
- Sur les 647 questions qui ont des voisines (descriptif) : 0,5405 → 0,5387.
- Porte apprise sur tout : α = −1,8. Elle s'ouvre, mais À L'ENVERS de l'hypothèse : quand S a sous-estimé le oui sur
  les voisines récentes, la question suivante sur la même entité penche plutôt vers le non, et inversement.
- Par plateforme (vu après coup) : Metaculus 0,5511 → 0,5428 ; Manifold 0,6049 → 0,5982 ; Polymarket 0,5183 → 0,5205.
  Même motif qu'au banc de la tendance large (gain Metaculus et Manifold, perte Polymarket), et ce gain Metaculus-là ne
  s'était pas reproduit hors échantillon : prudence.

Lecture (non testée) : pas de « régime » qui persiste ; plutôt un rappel. Une chose arrivée à un acteur (inculpation,
démission, accord) se reproduit moins dans les mois suivants que ses semblables ne le laissent croire. Hypothèse à
ne prendre au sérieux que si elle se reproduit sur des questions futures.

Verdict : non retenu (gain trop petit pour être distingué de zéro). Essai graphe_questions clos en 0.10.309.
