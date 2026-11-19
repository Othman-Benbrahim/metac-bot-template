# Simon — la rationalité limitée (article de Claude Parthenay)

## Référence
Claude Parthenay, « Herbert Simon : rationalité limitée, théorie des organisations et sciences de l'artificiel »,
chapitre de synthèse (CEPN, Paris XIII, et Université de Cergy-Pontoise), 28 pages ; PDF envoyé par l'auteur le
2026-11-19. Il présente l'œuvre de Simon (Administrative Behavior 1947, « A Behavioral Model of Rational Choice »
1955, Organizations avec March 1958, The Sciences of the Artificial 1969, Models of Bounded Rationality 1997). Mémo dans
nos mots. Le point 6 ci-dessous (quasi-décomposabilité) vient de Simon 1962 et n'est pas traité dans l'article.

## Thèse en trois phrases
Les gens ont des raisons à ce qu'ils font, mais leur capacité à traiter l'information est limitée : ils ne cherchent
pas la meilleure solution, ils s'arrêtent à la première qui atteint leur niveau d'aspiration, lequel suit
l'expérience. Il faut donc étudier la rationalité procédurale (comment la décision se fabrique : attention, recherche,
heuristiques) plutôt que la rationalité du résultat. Les organisations prolongent ces limites et les compensent :
routines, division des décisions, autorité acceptée dans une zone, identification aux buts communs.

## Mécanismes retenus
Format : phrase · niveau · relation (fiche `humain`) ou code · paramètres · trace.

1. **Satisfaction plutôt qu'optimum, aspiration adaptative.** L'aspiration monte avec les succès, baisse avec les
   échecs, avec retard ; l'insatisfaction est l'écart entre l'obtenu et l'aspiration. · psychologique · compartiment
   aspiration ; attente → aspiration (+, mois), aspiration → passage_acte (+), aspiration → opinion_privee (+) ; avec
   attente → passage_acte (−) déjà posée, passage_acte suit l'écart aspiration − attente, et la simulation pas à pas
   montre l'écart qui se referme quand l'aspiration rattrape · retards · attentes des ménages à 1 et 5 ans (à brancher).
2. **L'attention, ressource rare.** Un stimulus attire l'attention sur un aspect plutôt qu'un autre ; une organisation
   ne traite que quelques problèmes à la fois. · statut · compartiment agenda ; disponibilite → agenda (+, seuil),
   passage_acte → agenda (+), agenda → agenda (−, éviction) ; pont entrant calendriers-echeances:dates_limites → agenda
   · `seuil` · actes présidentiels au Federal Register.
3. **Routines et recherche déclenchée par l'échec.** Hors crise, l'organisation suit ses programmes ; elle ne cherche
   du nouveau que sous son aspiration. · statut · éléments du compartiment agenda · — · —
4. **Autorité et zone d'acceptation ; identification.** · statut · éléments du compartiment agenda ; relation déjà
   posée hierarchie → passage_acte (±) · — · —
5. **Rationalité procédurale et programmes comme modèles testables.** Un programme qui reproduit une procédure de
   décision est une théorie qu'on peut tester. · méthode · c'est le statut de la carte : `Carte.simuler` est une
   procédure explicite, testée (tests/test_calibrer.py), calibrée sur données · — · —
6. **Quasi-décomposabilité (Simon 1962).** Un système complexe se compose de sous-systèmes aux liens internes forts et
   rapides, aux liens externes faibles et lents. · architecture · déjà au cœur de la carte (fiches, niveaux, inertie,
   ponts partiels) ; désormais TESTÉ : `calibrer.py` mesure aussi les ponts entre fiches et compare |r| moyen dedans
   et entre ; un pont « influence » mesuré significatif reçoit son sens, sa force et son délai mesurés · — · toutes
   les séries. Premier passage (2026-11-19) : |r| moyen 0,216 dedans (51 mesures) contre 0,245 entre (23) — la
   quasi-décomposabilité n'est PAS confirmée sur nos séries à ce stade (peu de mesures ; plusieurs ponts relient des
   séries proches) ; à relire quand les collectes auront grandi.

## Ce qui a été écrit dans le programme (bot 0.10.329)
- `ecosystemes/humain.yaml` : compartiments aspiration et agenda ; 6 relations ; 2 ponts sortants ; 1 pont entrant.
- `calibrer.py` : mesure des ponts (« pont:de>vers ») et bilan de décomposabilité.
- `carte.py` : un pont d'influence calibré significatif prend le sens, la force et le délai mesurés.
- Tests : l'aspiration suit une chute de l'attente avec retard ; un pont calibré donne son sens.

## Limites
- Source secondaire : un article de synthèse, pas Simon lui-même ; les mécanismes retenus sont ceux que l'article
  expose avec références précises.
- Le niveau d'aspiration est rarement observable directement ; la partie lente des attentes n'en est qu'un indice.
