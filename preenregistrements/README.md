# Pré-enregistrements

Un critère ne vaut que s'il précède les données qui le jugent. Un texte ne le prouve plus par lui-même : il se rédige en
une minute, à n'importe quel moment (Sean Goedecke, « Writing is no longer proof of work », 2026). Ce qui le prouve ici,
c'est la **date du commit** qui l'a introduit, et le **code** qui calcule le verdict.

## Règle (2026-11-14)

Tout nouvel essai susceptible de changer ce qui est posté ou calculé officiellement :
1. a son pré-enregistrement dans ce dossier, dans un commit **antérieur à son premier regard** ;
2. est inscrit dans `essais.py` (registre des essais ouverts, règle d'adoption commune) ;
3. a son verdict calculé par du code (`score_registre.py`, `apprentissage_liens.py`), jamais à la main.

Toute modification d'un pré-enregistrement passe par un commit daté qui dit ce qui change et pourquoi ; l'historique git
garde l'ancienne version.

## Ce qui fait foi pour les essais ouverts au 2026-11-14

Ces documents ont été rédigés d'abord dans les notes du projet, puis copiés ici le 2026-11-14 au soir : la date de
copie ne prouve donc rien pour eux. Ce qui prouve l'antériorité, c'est le commit où le critère est entré **dans le code** :

| Essai | Document | Critère entré dans le code | Commit (date) |
|---|---|---|---|
| Ombre « absence » (états nuls) | `ombre-absence.md` | bot 0.10.70 | `b2be8b8` (2026-11-13 19:50) |
| Apprentissage des liens | `apprentissage-liens.md` | bot 0.10.80 ; découpage 0.10.89 | `6396b72` (2026-11-14 01:24) ; `c0cefd2` (13:41) |
| Plan et lecture sans matrice | `sans-matrice.md` | bot 0.10.91 | `3e4efa5` (2026-11-14 14:15) |
| B autorégressif (séries) | `b-autoregressif.md` | règle 0.10.92 ; critère 0.10.97 | `8394e21` (14:39) ; `84ab44f` (17:17) |
| Règle d'adoption commune | `regle-adoption.md` | bot 0.10.98 | `5f0840b` (2026-11-14 17:53) |

Les premières lectures « sans matrice » ont été faites après `3e4efa5` ; les premières questions nouvelles du B
autorégressif viendront après `84ab44f`.

## Rasoir d'Ockham avant tout essai (décision d'auteur du 2026-11-15, 15 h 25)

« Les idées simples et vraies battent en général les systèmes complexes. » Avant d'être testée, chaque hypothèse passe
cinq questions, dont les réponses ouvrent son pré-enregistrement (section « Rasoir d'Ockham ») :

1. **Une phrase** : le mécanisme tient-il en une phrase ?
2. **Paramètres** : combien de nombres faut-il apprendre ? Zéro ou un ; au-delà, dire pourquoi.
3. **Sens fixé d'avance** : dans quel sens l'effet doit-il aller, et pourquoi (bon sens, littérature) ?
4. **Domaine** : à quelle classe de questions s'applique-t-elle, et seulement à elle ?
5. **Plus simple ?** : une explication plus simple rend-elle compte des mêmes cas ?

Une hypothèse qui échoue est écartée ou simplifiée avant tout passage. Deux garde-fous s'ajoutent, tirés de l'échec
de `indicateurs-pertinents.md` (2026-11-15) :
- **pas d'extrapolation** : une variable est bornée à l'étendue vue à l'apprentissage (ou réduite à son sens :
  au-dessus / au-dessous de la normale) ;
- **mesure stable** : une mesure qui peut diverger (division par un écart-type quasi nul, régions sèches) est bornée
  ou écartée avant le test.
- **simulation a priori** (décision d'auteur du 2026-11-21, 12 h 31) : tout outil qui apprend des poids passe
  `verification_a_priori.simuler` avant son banc (aucun appel de modèle). Si l'a priori, sans aucune donnée, déplace la
  prévision de plus de 0,5 logit en médiane ou ajoute plus de 10 points de prévisions extrêmes, on prend l'écart-type
  conseillé (`sd_conseille`) ou on retire des indicateurs. Cas d'origine : « décision d'institution » (alerte : 0,80 logit,
  extrêmes 1 % → 14 %, sd conseillé 0,52 au lieu de 1).
- **taille nécessaire** (décision d'auteur du 2026-11-21, 12 h 53) : avant tout essai, `verification_a_priori.puissance`
  ou `taille_necessaire` dit quel écart le banc peut voir à sa taille. Mesuré sur nos bancs : σ ≈ 0,2 à 0,3 de perte log
  par question ; une centaine de questions ne voit qu'un écart de 0,05 à 0,07 ; un gain de 0,01 en demande plusieurs
  milliers. Un essai trop petit pour l'écart visé est décrit comme tel avant d'être lancé.
- **découpage temporel** (même date) : un outil qui apprend des poids apprend sur le passé et se juge sur la suite
  (`verification_a_priori.blocs_chronologiques`), jamais par blocs tirés au hasard.
- **placebo** (même date) : une règle candidate à devenir brique passe `placebo.placebo` : elle doit aider sur les
  questions dont l'événement est son objet, et pas au-dehors ; une règle qui aide autant au-dehors est « générique »
  (rétrécissement déguisé) et ne s'inscrit pas comme brique de mécanisme.

## Le piège des tests trivialement solubles (décisions d'auteur du 2026-11-15, 16 h 33 et 16 h 43)
Avertissement de Hoover, Blayney et Whittington (« Classical Energies Learn to Reason 1,000x Faster than Looped
Models », arXiv, 12 nov. 2026) : une méthode jugée sur des épreuves trivialement solubles paraît meilleure qu'elle
n'est, et les écarts entre méthodes disparaissent dans la moyenne. Chez nous : les questions ACLED « dix fois plus »
(0 oui sur 74, toute méthode correcte y obtient environ 0,001) formaient la moitié des questions de conflits.
Règles :
1. les verdicts sur les conflits ACLED portent sur la forme « une fois » seulement ; la forme « dix fois plus » est
   décrite à part, jamais mêlée au critère ;
2. avant d'écrire un critère, regarder quelle part des questions est jouée d'avance (B sous 2 % ou au-dessus de
   98 %, ou une forme dont la réponse est presque toujours la même) et l'exclure ou la décrire à part ;
3. un score s'annonce toujours à côté de la référence « pile ou face » (0,693) et de B, pour qu'on voie la marge
   réelle et non un chiffre flatteur.
