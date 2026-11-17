# Questions de jugement : semblables contre statu quo (préenregistrement, 2026-11-17, 21 h 00)

Décisions d'auteur du 2026-11-17 : changer de terrain d'après le diagnostic des pertes (20 h 33) ; outils standards
comme RÉFÉRENCE, puis ce qui peut nous distinguer (20 h 40-20 h 47 ; mise en garde de l'auteur contre le piège de la
médiane) ; cadre validé à 20 h 53. Code : `banc_jugement.py` ; essai `jugement_semblables`. Aucun modèle de langue.

## Données
Questions de jugement résolues redistribuées par ForecastBench (Metaculus, Manifold, Polymarket, INFER ; CC BY-SA 4.0),
jeux depuis juillet 2024, une ligne par (question, jeu). La prévision de la foule n'entre jamais dans un calcul ; elle
n'est lue qu'à la fin pour situer la foule, sans être enregistrée.

## Garde-fous contre la fuite
- Horizon = date de clôture prévue − date du jeu ; jamais la date réelle de résolution (une résolution anticipée trahit
  souvent un « oui »).
- Une voisine (ou une question comptée dans R0, R1) doit avoir été résolue AVANT la date du jeu ; jamais la même question.

## Référence et candidat
- R0 : part de « oui » de la plateforme, lissée (k + 1) / (n + 2).
- R1 (référence) : plateforme × forme × horizon, (k + 5·R0) / (n + 5). Formes par règles fixes (élection, justice,
  seuil, échéance, autre) ; horizons ≤ 30 j, 31-90 j, > 90 j.
- SEMBLABLES : 50 plus proches voisines par TF-IDF (cosinus), toutes plateformes, pondérées par le cosinus ;
  p = (Σ w·issue + 5·R1) / (Σ w + 5).

## Jugement
Perte log SEMBLABLES − R1 sur les questions des jeux de 2026 ; bootstrap par question (une question reposée dans
plusieurs jeux forme un bloc) ; risque `es.risque_corrige(1)` ; meilleur si la borne haute < 0. Rapportés : R0, la
discrimination (moyenne de p sur les « oui » moins sur les « non »), par plateforme, par forme, la foule (descriptif).

## Attendu (Claude, avant le passage)
R1 bat nettement R0 (la forme et l'horizon comptent). SEMBLABLES : gain modeste mais réel sur la discrimination, car les
questions d'une même série (le même événement à des dates différentes, le même type d'annonce) se ressemblent par le
texte ; risque : des voisines de même texte mais d'issue indépendante n'apportent que du bruit.

## Correction du 2026-11-17 (21 h 10), après le premier passage et AVANT le second : biais de censure
Premier passage (local, 21 h 00) : 40 % de « oui » sur les questions de 2026 contre 5 à 14 % en 2025, et des références
pires que pile ou face (R0 : 0,84). Cause : parmi les questions récentes, seules celles qui ont fini « oui » tôt sont
déjà résolues ; les « non » attendent leur échéance. Ce premier passage est NUL (son verdict, « semblables meilleures »,
n'est pas retenu). Règle ajoutée, rien d'autre ne change :
- seules les questions dont la clôture prévue (date du jeu + horizon) est passée depuis au moins 30 jours entrent ;
- une question ne sert de voisine ou au calcul de R0 et R1 que si sa clôture prévue ET sa résolution précèdent la date
  du jeu de la question jugée.
