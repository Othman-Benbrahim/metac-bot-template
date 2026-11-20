# Seuils de prix : calibrage du modèle log-normal sur des questions résolues (préenregistrement, 2026-11-20)

Référence : `seuils-de-prix-reference.md`. Module : `seuils_prix.py` (0.10.398). Décision de l'auteur (19 h 21) : Claude
sert de filet sur ce point technique ; le test est annoncé avant calcul et lancé une fois, quand les séries FRED des
indices seront collectées.

## Questions (règles fixées avant toute lecture des issues)
- Registre de jugement et échantillon de mise au point, toutes sources (Polymarket, Manifold, Metaculus, INFER, GJOpen).
- Un seul actif reconnu par `seuils_prix.actif` (bitcoin, éther, Brent, Nasdaq, S&P 500, Dow Jones) et un montant dans le
  titre ; recensement : 187 questions, dont 84 « atteint avant », 61 « à la date », 42 de forme non reconnue (exclues).
- Type : « atteint avant » si le titre contient reach, hit, touch, dip, drop, fall, trade above/below, at any point,
  again ; sinon « à la date » si close, closing, settle, be above/below ; sinon exclue.
- Sens : au-dessus si above, over, higher, reach, hit ; au-dessous si below, under, lower, dip, drop, fall.
- Seuil : premier montant du titre (k = mille, m = million).
- Date de fin : date de jeu + horizon (jours) ; prix et volatilité pris strictement avant la date de jeu.

## Calcul (fixé)
- M : probabilité log-normale sans dérive (`p_a_la_date` ou `p_atteint_avant`), σ sur 30 rendements quotidiens.
- Témoin I : taux de base des questions de prix déjà résolues avant la date de jeu (même type), rétréci vers 0,5 (poids 5).
- Rapportés sans effet sur le critère : M avec σ sur 90 jours ; M avec σ × 1,5 (queues épaisses) ; calibrage de M par
  tranches de 10 points ; part de questions où le seuil était déjà franchi au départ.
- Perte log, probabilités bornées à [0,01 ; 0,99] ; intervalle à 90 % par question.

## Critère
M est retenu comme mécanisme des questions de seuil de prix si M − I < 0 et l'intervalle à 90 % exclut 0. Ensuite
seulement : branchement dans le bot pour ces questions, avec la règle de l'auteur (mécanisme vérifié à son niveau
d'application → introduit ; sortie brute scellée).

## Résultat (2026-11-20, 19 h 45)
Premier passage invalide (fichier conservé : `registre/mise-au-point/seuils-prix-passage1-errone.json`), pour trois
erreurs de MESURE trouvées en relisant les questions, corrigées avant le second passage :
1. « NASDAQ Ticker: $NVDA » rangé dans l'indice Nasdaq (7 questions sur des actions) : motif resserré ;
2. « atteint avant » : le sens était déduit du mot reach, alors que le seuil peut être en dessous du prix (« reach $14k »
   depuis 19 000) ; la probabilité de toucher est désormais symétrique ;
3. l'horizon du registre est le délai jusqu'à la RÉSOLUTION, raccourci quand un seuil est touché tôt (fuite de l'issue) :
   l'échéance est lue dans le titre quand elle y figure (66 questions sur 138 ; les autres gardent l'horizon, ce qui
   pénalise le modèle, donc joue contre lui).
Second passage : 138 questions (131 distinctes). Perte : témoin 0,6216 ; M (σ 30 j) 0,4154 ; σ 90 j 0,4320 ;
σ × 1,5 0,4385. **M − I = −0,2062, intervalle à 90 % [−0,2677 ; −0,1356] : critère atteint.**
« À la date » : M 0,574 contre 0,697 (54) ; « atteint avant » : M 0,314 contre 0,573 (84). Bitcoin 0,458 contre 0,630 ;
éther 0,334 contre 0,604. Calibrage : 0-10 % → 8,5 % de oui (47) ; 50-60 % → 81 % (16) ; 60-70 % → 83 % (12).
Le σ × 1,5 ne fait pas mieux : pas de correction de queues épaisses à ce stade.
Réserve : la comparaison est faite contre le taux de base, pas contre le bot.
