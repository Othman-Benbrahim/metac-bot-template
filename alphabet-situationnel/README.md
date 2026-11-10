# Alphabet situationnel

**Lire une situation complexe avec un petit alphabet de structures, puis mettre ses prévisions à l'épreuve.**

Auteur : Othman Ben Brahim · Licence MIT (`LICENSE`) · Skill Claude, moteur Python sans dépendance

Version 0.7.63 · historique complet dans `CHANGELOG.md`

---

## Ce que fait l'outil

L'alphabet situationnel décrit une situation réelle (une crise diplomatique, un conflit social, un marché) avec
**16 structures transversales candidates** : SEUIL, POLARITÉ, RÉSEAU, CONTRAINTE, TRACE·MÉMOIRE… Il les lit dans
**13 strates** (géopolitique, politique intérieure, économie, droit…). Chaque structure retenue doit être ancrée
dans un fait daté et sourcé, opposée à sa rivale la plus proche, et soumise à une contre-observation.

Sur cette lecture, un moteur Python calcule des **probabilités conditionnelles** : « sachant cet état, quelle
chance qu'un franchissement de seuil survienne d'ici trois mois ? ». Chaque prévision s'enregistre, se scelle, puis
se compare à ce qui s'est réellement produit.

Quatre usages :

| Mode | Pour quoi |
|---|---|
| **LIRE** | décrire une situation, sans aucun chiffre |
| **PRÉVOIR** | poser une question datée, obtenir une probabilité ou un refus motivé, et une fiche TEST |
| **CODER** | transformer un épisode passé en cas documenté |
| **SCORER** | confronter les prévisions à leurs issues (fiche RÉSULTAT, Brier, comparateurs) |

## Où en est le projet, honnêtement

- **L'instrument est construit, la mesure n'a pas commencé.** Aucun cas réel n'est encore actif, et aucune
  prévision n'a été scorée.
- **Les probabilités ne sont pas calibrées.** Les paramètres du moteur sont posés à la main ; chaque sortie le dit.
- **La prévision chiffrée est limitée à la strate 7** (géopolitique), la seule dont 13 structures sur 16 sont
  sourcées. Les autres strates se lisent, sans chiffre.
- **Le projet est gelé** depuis la 0.7.34 : plus de règle nouvelle tant qu'il n'y a pas de données réelles.

C'est précisément pour cela que nous cherchons des participants : voir `CONTRIBUER.md`.

## Démarrer

Prérequis : Python 3.8 ou plus récent, bibliothèque standard seule.

```bash
python3 scripts/moteur.py audit        # intégrité du paquet et cohérence des fichiers
python3 scripts/moteur.py autotest     # tests de régression
python3 scripts/moteur.py calculer --demo --base assets/base-de-cas.exemple.jsonl \
  --etat "[2026-09 | 3 mois] POLARITÉ@7[F] + CONTRAINTE@6[F]" \
  --evenement "SEUIL@7 apparait" --temporalite generique
python3 scripts/moteur.py equivalences --carte SEUIL    # ce que SEUIL veut dire dans chaque strate
```

`--demo` signale une base **fictive** : ses chiffres décrivent la mécanique du calcul, jamais le monde. Hors
`--demo`, `calculer` exige un dossier de lecture (`--dossier`, modèle `assets/dossier.exemple.json`).

Dans Claude, le skill s'utilise en conversation : « lis cette situation », « que peut-il se passer d'ici
décembre ? ». La procédure est dans `SKILL.md`.

**Vos données vivent hors du skill**, par exemple dans un dossier `alphabet-donnees/` : journal des prévisions,
registre des tests (copie de `assets/registre-tests.md`), carnet de faits. Le paquet est contrôlé par
`SHA256SUMS` et remplacé à chaque mise à jour.

## Limites

- Il ne certifie pas la vérité des sources, ne diagnostique pas et ne décide rien sur une personne.
- Il ne valide pas ses propres probabilités : seule une série de prévisions prospectives, scellées chez un tiers
  avant leur échéance, le peut (`references/validation.md` §11).
- Les 16 structures sont des **hypothèses** ; leur caractère transversal reste à démontrer.
- Un accord entre un humain et un modèle de langage ne vaut pas un accord entre deux humains.

## Contribuer

Le projet a besoin de **seconds codeurs**, d'un **méthodologue extérieur**, de **relecteurs de sources** et d'un
**tiers** pour horodater les prévisions. Le parcours tient en une page : `CONTRIBUER.md`.

## Organisation

```
README.md                   cette page
CONTRIBUER.md               parcours contributeur
SKILL.md                    procédure du skill, mode par mode
CHANGELOG.md                historique de toutes les versions (et ancien README, en annexe)
LICENSE, LICENCES-TIERS.md  licences
references/                 constitution, cartes, strates, grammaire, graphe, validation, feuille de route…
references/equivalences/    les 16 structures traduites dans chacune des 13 strates
scripts/moteur.py           moteur, validateur, scoreur, autotests
assets/parametres.json      tous les paramètres du moteur
assets/*.exemple.*          données fictives de démonstration
assets/registre-tests.md    modèle vide du registre des tests
SHA256SUMS                  empreinte de chaque fichier livré
```

## Intégrité

`sha256sum -c SHA256SUMS` ou `python3 scripts/moteur.py audit` refusent un fichier modifié, ajouté ou retiré.
Sur GitHub, chaque version a son étiquette `vX.Y.Z` et sa release, avec `SHA256SUMS` en pièce jointe. Le zip livré se
nomme `alphabet-situationnel-0.7.63.zip`.
