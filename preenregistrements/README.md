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
