# Règle d'adoption commune — compter, corriger, regarder à date fixe (bot 0.10.98)

**Décision d'auteur du 2026-11-14**, commit `5f0840b`. Source : Elliot Tower, *AI for Science × Philosophy of Science*
(Zenodo, 2026), ch. 2 « Forking Paths » et ch. 3 « Stopping and Evidence ».

## Pourquoi
- **Chemins qui bifurquent** (Gelman et Loken 2013) : l'erreur dépend aussi des analyses qu'on *aurait* faites avec
  d'autres données. Plusieurs ombres, chacune avec un critère propre, laissent attendre des adoptions par hasard.
  Bonferroni (Dunn 1961) ne marche que si l'on compte les essais.
- **Arrêt** (Mayo) : regarder à chaque passe et s'arrêter au premier passage favorable gonfle l'erreur.
- **Réutilisation de l'ensemble de contrôle** (Dwork et al. 2015) : relire sans cesse le même tiers de jugement l'use.

## La règle (`essais.py`)
1. **Compter.** Tout essai qui peut changer ce qui est posté ou calculé officiellement est inscrit, avec son critère et
   sa date, avant son premier regard, et son pré-enregistrement est commité dans ce dossier.
2. **Corriger.** Critère à intervalle (« intervalle à 90 % de l'écart sous 0 », risque unilatéral 5 %) : jugé au
   risque 5 % / k, k = nombre d'essais ouverts de ce type. Le critère nominal reste affiché à côté.
3. **Regarder à date fixe.** Verdict sur les N premières lignes admissibles. Un « indécis » donne droit à un second
   regard sur les 2N premières, au risque partagé. Au-delà : clos sans adoption, ou repris sous un critère neuf.
4. **Apprentissage des liens** : jugé une seule fois, à la fin.

Ne fait que durcir l'adoption ; ne touche ni la lecture ni le p posté.
