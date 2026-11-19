# Réseaux et influence : ce qui est établi, et notre modèle

Demande de l'auteur du 2026-11-19 (13 h 44) : simuler, à l'échelle de la planète, qui interagit avec qui et à quel niveau
(proches, connaissances, connaissances de connaissances), avec des forces de lien selon le statut, et le croiser avec
l'influence des masses par convergence éditoriale et algorithmique.

## Ce qui est établi (sources vérifiées le 2026-11-19)
- **Degrés de séparation** : sur 721 millions de comptes Facebook (69 milliards de liens), la distance moyenne est de
  4,74, contre 5,28 en 2008 ; 92 % des paires sont à 5 pas ou moins (Backstrom et al., « Four Degrees of Separation »,
  2012, arXiv:1111.4570).
- **Couches de Dunbar** : couches emboîtées d'environ 5, 15, 50 et 150 personnes, rapport ≈ 3, retrouvées sur Facebook
  et Twitter (arXiv:2205.13980).
- **Liens faibles** : le test causal sur 20 millions de membres de LinkedIn confirme leur force pour l'emploi, avec une
  courbe en U inversé : les liens modérément faibles sont les plus utiles (Rajkumar et al., *Science*, 2022).
- **Contagion par les proches** : expérience sur 61 millions d'électeurs. Le message social a augmenté la participation
  de 0,39 point. Environ 60 000 votes sont venus directement, 280 000 par contagion. Les amis proches (environ 7 % des
  liens) portent toute la contagion mesurable, avec un effet estimé à environ quatre fois celui du message (Bond et al.,
  *Nature*, 2012).
- **Les « influents »** : dans les modèles à seuils, les grandes cascades viennent surtout de gens facilement
  influençables qui en entraînent d'autres, pas d'influents. La « diffusion en deux étapes » reste mal établie (Watts et
  Dodds, 2007).
- **Les « trois degrés d'influence »** (Christakis et Fowler) sont contestés : il est difficile de séparer contagion et
  ressemblance (homophilie) (Lyons, 2011).
- **Amplification algorithmique** : expérience sur près de 2 millions de comptes de contrôle. Le fil personnalisé
  amplifie la droite modérée plus que la gauche dans 6 pays sur 7 (Huszár et al., *PNAS*, 2022) ; des écarts de 43 % à
  176 % de portée en plus.
- **Fil chronologique** : pendant trois mois en 2020, il a réduit le temps passé et changé l'exposition (plus de
  politique, plus de sources peu fiables, moins d'incivilités), sans changer la polarisation ni les attitudes (Guess et
  al., *Science*, 2023).
- **Propriété des médias** : en France, d'après Le Monde diplomatique et Acrimed (décembre 2025), 41 titres
  d'information recensés sur 53 appartiennent à un milliardaire ou à une famille. Pour les autres pays, le Media
  Ownership Monitor de RSF couvre une vingtaine de pays.

## Notre modèle (`reseau_influence.py`, synthétique, aucune personne réelle)
- **La population** : 20 000 individus en communautés de 150, liens par couches de Dunbar, une part de liens lointains.
  Le statut suit une loi de Pareto et pèse sur l'influence.
- **Les médias** : 50 titres d'audience très inégale, répartis entre 25 propriétaires. Les trois premiers propriétaires
  totalisent 70 % de l'audience.
- **Les plateformes** : une amplification algorithmique des liens faibles et des hauts statuts.
- **La règle de diffusion** : chacun adopte quand l'exposition (proches pondérés et médias suivis) dépasse son seuil.
- **Contrôle de vraisemblance** : avec 20 % de liens lointains, la distance extrapolée à 8,1 milliards d'habitants est
  de 4,56, proche des 4,74 mesurés sur Facebook.

Premier passage, population de résistance moyenne (seuil moyen 0,5) :

| Configuration | Adoptants |
|---|---|
| Proches seuls, départ au hasard | 0,5 % (rien ne bouge) |
| Proches seuls, départ par des influents | 4 % |
| Proches seuls, départ par des influents, amplification ×2,7 | 12 % |
| 1 propriétaire aligné, départ par des influents | 50 % |
| 1 propriétaire aligné, départ par des influents, amplification | 68 % |
| 3 propriétaires alignés, sans liens lointains, départ par des influents | 55 % |
| 3 propriétaires alignés, 20 % de liens lointains, départ par des influents | 98 % |
| Les mêmes, départ au hasard | 28 à 35 % |

Toutes les lignes « propriétaires alignés » ont 20 % de liens lointains, sauf celle qui dit le contraire.

Population résistante (seuil 0,65) : même avec 3 propriétaires, l'amplification et des influents, au plus 30 %.

**Lecture.** Les médias seuls convainquent très peu, environ 1,6 % de la population directement. Leur effet passe par
l'abaissement du seuil de tous, et c'est le tissu des liens qui fait la cascade : influence et connexion se renforcent
au lieu de s'additionner. La concentration des propriétaires compte parce qu'elle aligne plusieurs titres à la fois. La
résistance de la population (son seuil) décide de tout : à seuil haut, rien ne prend.

**Limites.**
- Ce sont des paramètres supposés : poids des médias 0,3, seuils normaux, statut multiplicatif.
- Dans ce modèle, les influents comptent plus que chez Watts et Dodds, parce que le statut pondère l'exposition par
  construction.
- Un seul message, une seule adoption : il n'y a pas de messages concurrents.

À calibrer sur des cascades réelles datées, par exemple la vitesse et l'ampleur d'une mobilisation mesurées par GDELT.

## Dans la carte (fiche humain, bot 0.10.347)
- **Compartiments** : liens, convergence_editoriale, amplification_algorithmique.
- **La convergence éditoriale** ne convainc pas directement : elle abaisse le seuil du passage de l'opinion privée à
  l'opinion publique (modulation). Elle alimente aussi la disponibilité.
- **L'amplification** alimente le marché cognitif et la disponibilité. Son effet sur la polarisation est marqué
  « contesté », d'après Guess et al. 2023.
- **Les liens** alimentent l'opinion publique et le passage à l'acte.
- **Les personnes** : uniquement des propriétaires, par leurs faits publics de propriété. Aucun cercle personnel n'est
  cartographié.
