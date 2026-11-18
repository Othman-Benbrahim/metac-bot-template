sources: registre/banc-attention-gdelt.json, registre/banc-tendance-large.json
constantes: 10; 80; 90; 30
# Résultat : tendance et sursauts de l'attention GDELT (2026-11-18)

Run 44373600462, bot 0.10.286 ; comptes quotidiens par BigQuery (run 44373174438, [journal: 42,7 Go, 130 questions, 92 avec
articles]). Préenregistrements tendance-attention.md et sursauts-attention.md (avec l'amendement du filtre des pics
isolés). Aucun modèle, coût nul. Pistes « avenir déjà présent » (Three Horizons) et « réponse aux chocs » (Taleb) de
la confrontation Complex Systems Frameworks.

119 questions distinctes avec une prévision M (87 avec articles), 27 oui. M seul : perte 0,4473.

## Tendance (10 derniers jours contre les 80 précédents) : non adoptée, mais signal dans le sens attendu
- M ajusté 0,4405 ; écart −0,007, intervalle corrigé [−0,050 ; +0,036].
- Rang tendance / issue 0,18 ; β appris sur toutes les questions +0,55 (attention qui monte → OUI plus probable) ;
  ratés (OUI prévus sous 30 %) 15 → 13 ; fiabilité 0,019 → 0,014.

## Tendance à grande échelle (run 44383204002, préenregistrement tendance-attention-large.md)
Décision d'auteur (« grappiller ; tester à plus grande échelle »). Comptes BigQuery (run 44381992980, [journal: 46,1 Go]) des 892
questions distinctes de 2026 des quatre plateformes, 628 avec articles ; base sans modèle : taux des semblables S.
- S ajusté 0,6572 contre S 0,6588 : écart −0,002, intervalle corrigé [−0,010 ; +0,007]. Non adopté, essai clos.
- Même sens qu'au premier banc : β appris positif (+0,25 sur S, +0,35 sur R1), rang tendance / issue 0,09.
  Le signal existe probablement, mais il est très faible.
- Par plateforme (vu APRÈS coup, non jugé) : Metaculus 0,5667 → 0,5564 ([calc: 0,5564 - 0,5667 = -0,010]), Manifold [calc: 0,6361 - 0,6452 = -0,009], INFER [calc: 0,8984 - 0,9525 = -0,054]
  (10 questions), Polymarket [calc: 0,6799 - 0,6769 = +0,003] (sport et crypto, mal couverts par GDELT). Sur R1 : Metaculus [calc: 0,5679 - 0,5819 = -0,014].
- Piste ouverte : un essai limité à Metaculus, préenregistré, jugé sur d'AUTRES questions Metaculus (2025, comptes à
  récupérer, [estimation: 70 à 90 Go]).

## Sursauts (indice de Goh-Barabási après retrait des pics isolés) : non adoptés, légèrement nuisibles
- M éloigné des extrêmes 0,4521 ; écart +0,005, intervalle corrigé [+0,002 ; +0,008], entièrement au-dessus de zéro.
- λ appris sur tout = 0,05 : la règle n'est presque pas utilisée ; ce qui reste est du bruit d'apprentissage.
- Rang sursaut / issue 0,06 (brut 0,05) ; sursaut moyen des ratés 0,51 contre 0,45 pour les autres.
- Filtre des pics : 25 jours retirés sur 13 questions ; il ne change pas la conclusion.
