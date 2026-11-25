# L'actualité d'un compartiment coïncide-t-elle avec un mouvement anormal de ses séries ? (préenregistrement, 2026-11-25, 17 h 15)

Décision de l'auteur : « Oui, vas-y » (17 h 11), sur la proposition d'un étage 3 au recoupement chiffré des briefs
(`recoupement_briefs.py`, étages 1 et 2). Procédure écrite AVANT tout calcul : au moment de l'écrire, le journal compte
10 briefs d'un seul jour et une seule série terrain touchée ; aucun résultat n'a été regardé. Calcul fait une fois, à la
date d'arrêt ci-dessous, par un script écrit à ce moment-là (`etage3_briefs.py`), qui suit ce texte sans le changer.

## Question
Quand un brief rattache une nouvelle à un compartiment de la carte, les séries chiffrées de ce compartiment montrent-elles
plus souvent qu'à l'ordinaire un mouvement anormal (a) juste avant le brief (l'actualité suit le monde), (b) dans les
semaines qui suivent (l'actualité annonce le monde) ? Une sonde vaut quelque chose si (a) ou (b) dépasse le taux de base.

## Unités (fixées)
- Une unité = (compartiment, série terrain) touchée par un brief ok du journal `briefs/journal.jsonl`.
- Série terrain = trace « collecte » avec adaptateur, HORS séries d'attention (`recoupement_briefs.ATTENTION` : rss,
  rss_famille, rss_matiere, rss_region, rss_villes, recit_russe, telegram, wikipedia, openmeasures).
- Dépendance : plusieurs briefs sur le même sujet ne font qu'une unité. Regroupement par (compartiment, série, semaine
  ISO du brief) ; la date retenue est celle du premier brief de la semaine ; la famille et le média sont ceux de ce
  premier brief.
- Exclues : séries de moins de 9 points connus à la date du brief ; série dont l'écart absolu médian des variations
  passées est nul.

## Mesure (fixée)
- Variation = différence entre deux points successifs de la série. Écart robuste z = (variation − médiane des variations
  passées) / (1,4826 × écart absolu médian des variations passées), les « passées » étant celles dont le point d'arrivée
  est STRICTEMENT antérieur au point testé. Anormal : |z| ≥ 2.
- (a) Coïncidence : la dernière variation dont le point d'arrivée tombe dans [J − 45 j, J] est anormale.
- (b) Anticipation : au moins une variation anormale parmi celles dont le point d'arrivée tombe dans ]J, J + 60 j].
  Calculée seulement quand J + 60 j ≤ date d'arrêt.
- Taux de base de l'unité, p : part des variations anormales (même règle, chacune jugée sur son seul passé) parmi
  celles de la série dans les 730 jours avant J. Pour (b), p_b = 1 − (1 − p)^k, k = nombre de variations de la série
  dans ]J, J + 60 j] (au moins 1). p borné à [0,01 ; 0,9].

## Test (fixé)
- E-valeur par pari, unité par unité, alternative fixée d'avance : q = min(2p, 0,95). Pour une unité observée x (1 si
  anormal, 0 sinon) : e = (q/p)^x × ((1 − q)/(1 − p))^(1 − x). E-valeur du test = produit des e.
- Seuil : E ≥ 20 → le taux observé dépasse le taux de base (risque d'erreur ≤ 5 %, sans hypothèse sur l'ordre des
  unités). E ≤ 1/20 → la sonde fait PIRE que le hasard (moins d'anomalies qu'attendu). Entre les deux : non conclu.
- (a) et (b) sont deux tests : seuil 40 pour chacun (correction pour deux tests).
- Par famille de flux et par classe de média : description seulement (taux observé, taux attendu, effectifs). Un test
  par groupe n'est fait que si le groupe a au moins 50 unités, au seuil 20 × nombre de groupes testés.

## Arrêt (fixé)
Calcul unique le premier jour où l'une des deux conditions est remplie : 150 unités pour (a), ou le 2027-02-25 (trois
mois). Si moins de 30 unités le 2027-02-25 : pas de test, seul l'inventaire est rapporté (les séries manquent ; c'est
alors le résultat). Aucun regard intermédiaire sur les taux ; le nombre d'unités peut être compté sans les taux.

## Ce qui sera rapporté
Taux observé et attendu pour (a) et (b), E-valeurs, effectifs, table par famille et par classe de média, liste des
séries qui portent l'essentiel des anomalies (une série qui domine est un biais à signaler), et l'inventaire des
compartiments touchés sans série (`registre/briefs-recoupement-inventaire.json`).

## Limites connues avant le calcul
- Peu de compartiments ont une série terrain fraîche (1 sur 15 le 2026-11-25) : l'échantillon dépendra des séries
  branchées d'ici là, et donc de nos choix de branchement (biais de sélection à signaler).
- Les séries à pas mensuel ou annuel ne peuvent répondre à (b) qu'avec un point dans les 60 jours.
- Un brief rattaché à tort à un compartiment dilue l'effet ; on ne corrige pas les rattachements après coup.
