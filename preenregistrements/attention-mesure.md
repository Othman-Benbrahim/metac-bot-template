# Préenregistrement SUSPENDU : l'attention précède-t-elle la mesure ?

Suspendu le 2026-11-22 (décision de l'auteur, 1 h 13 - 1 h 16) : compter des termes isolés est une faute ; un terme n'a de
sens que dans sa situation (écosystème, quatre variables, acteurs, émetteur, temps T). Le collecteur enregistre
désormais des situations (lecteur-local, comptes/situations.jsonl) ; un test sera réécrit sur cette base.

2026-11-22, écrit avant toute requête et tout calcul. Décisions de l'auteur du 2026-11-22 : 0 h 50 (exploitation n° 2 :
confronter l'attention à la mesure), 1 h 03 (« oui et oui » : collecteur de nuit dans lecteur-local, et test commencé
en parallèle sur GDELT). Aucun appel à un modèle.

## Ce qui a déjà été mesuré (ne pas le refaire)
La TENDANCE de l'attention GDELT comme ajustement des prévisions de questions est close : non adoptée au banc de 119
questions, ni au banc large de 892 (écart −0,002, intervalle corrigé [−0,010 ; +0,007]), et non reproduite hors
échantillon sur Metaculus (écart +0,015) [fiches resultat-attention-gdelt-2026-11-18, resultat-tendance-metaculus-
2026-11-19]. Le présent test pose une AUTRE question : non pas « l'attention prédit-elle l'issue d'une question ? »,
mais « l'attention d'un compartiment prédit-elle la MESURE de ce compartiment mieux que la mesure ne se prédit seule ? ».
Le résultat passé incite à attendre peu ; il ne tranche pas cette question-ci.

## Paires (attention → mesure), toutes des compartiments des fiches
| compartiment | attention (GDELT, titres anglais) | mesure | pas |
|---|---|---|---|
| climat-extremes:secheresses | termes validés du compartiment + nom de l'État américain | US Drought Monitor, part de l'État en D2 ou plus (registre/secheresse-usdm.csv) | semaine |
| information-cyber:cyber | termes validés du compartiment | failles ajoutées au catalogue KEV (registre/cyber-kev.csv) | semaine |
| inflation-mondiale:anticipations | termes validés de inflation-mondiale:* | inflation anticipée à 10 ans (FRED T10YIE), variation | semaine |
| energie-mondiale:prix | termes validés de energie-mondiale:* et ormuz:* | Brent (FRED DCOILBRENTEU), variation absolue | semaine |

Attention = nombre d'articles par semaine dont le titre contient au moins un des termes, vus par GDELT (BigQuery,
table gkg_partitioned, filtrage chez Google, garde-fous du quota de gdelt_bq.py). Termes : ceux de lecteur-local
listes/valides.txt en anglais, figés au commit du lancement. Période : du 2023-01-02 à la dernière semaine complète.

## Méthode (fixée ici)
- A : la mesure de la semaine t+1 prévue par ses 4 dernières semaines (régression linéaire).
- B : A + l'attention des 4 dernières semaines (en log(1 + articles)).
- Origine glissante : apprentissage sur toutes les semaines antérieures (104 au minimum), prévision de la semaine
  suivante, jamais d'information future. Erreur absolue moyenne hors échantillon.
- Sens inverse : même calcul en échangeant les rôles (la mesure prédit-elle l'attention ?).
- Hasard : 500 permutations par blocs de 4 semaines de la série d'attention ; p = part des permutations où B fait au
  moins aussi bien qu'avec l'attention réelle.

## Critère (fixé ici, un seul passage)
- Une paire « apporte » si B bat A hors échantillon avec p < 0,05 (correction de Holm sur les 4 paires).
- L'attention est dite utile à la prévision si au moins 3 paires sur 4 apportent. Alors : proposition de brancher
  l'attention comme trace des compartiments concernés, sur décision datée de l'auteur. Sinon : non retenue, noté tel
  quel ; le collecteur continue (les séries servent aussi aux autres exploitations).
- Rapportés : gain par paire, sens inverse, délais.

## Prérequis avant lancement
- Les registres de la sécheresse (collecte_agro) et du catalogue KEV (collecte_cyber) n'existent pas encore : les deux
  collectes doivent tourner une fois.
- Coût BigQuery estimé : environ 0,11 Go par jour de titres, soit environ 140 Go pour la période ; sous le plafond
  mensuel (800 Go).
