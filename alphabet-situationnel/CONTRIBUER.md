# Contribuer à l'alphabet situationnel

Le projet n'a pas besoin de nouvelles idées. Il a besoin de **mesures**, et une mesure exige plus d'une personne :
deux codeurs qui ne se concertent pas, un relecteur qui n'a pas écrit le protocole, un tiers qui horodate. Voici où
vous pouvez aider, en une heure ou en un mois.

## 1. En dix minutes : vérifier que tout tourne

```bash
python3 scripts/moteur.py audit
python3 scripts/moteur.py autotest
```

Python 3.8 ou plus récent suffit, sans aucune dépendance. Si l'un des deux échoue sur votre système, c'est déjà une
contribution : ouvrez une *issue* sur GitHub avec la sortie complète, le système et la version de Python.

## 2. Choisir un rôle

| Rôle | Ce que vous faites | Temps | À lire d'abord |
|---|---|---|---|
| **Second codeur** | coder les mêmes situations que l'auteur, sans voir son codage, pour mesurer l'accord | 2 à 4 h par cas | `references/protocole.md` A1–A8, `references/equivalences/strate-07.md` |
| **Relecteur de sources** | vérifier qu'une référence citée dans un équivalent dit bien ce qu'on lui fait dire | 30 min par référence | `references/equivalences.md` §2 |
| **Méthodologue extérieur** | relire le protocole de validation avant le premier épisode, et publier votre avis | une demi-journée | `references/validation.md` §11 à §15 |
| **Tiers horodateur** | recevoir les fiches TEST avant leur échéance, et attester leur date | quelques minutes par fiche | `references/validation.md` §11.7 et §14 |
| **Développeur** | tests, portabilité, outils d'acquisition des données | variable | `scripts/moteur.py`, `CHANGELOG.md` |

La priorité actuelle : **des seconds codeurs pour la strate 7** (géopolitique). Sans eux, aucune structure n'a
d'accord mesuré et la validation ne peut pas commencer.

## 3. Pour un second codeur

Lire A1–A8 et la grammaire ; recevoir uniquement les faits et dates de disponibilité, jamais le
premier codage. Coder indépendamment, nommer l'objet de chaque ancrage, documenter les alternatives.
Vérifier les sources des équivalents avant F. Valider la fiche puis examiner l'accord par carte.
Le nombre de codeurs déclaré ne prouve ni leur indépendance ni la valeur de κ ; au moins un humain.
`moteur.py export-codeur --base B --cas ID` produit cette vue : faits, sources et dates, mélangés, sans
mots, cartes, forces, strates ni questions ; les faits restent ceux qu'a retenus le premier codeur, et le
mieux est de partir du dossier de sources complet. Déclarer `signe_suffisant` avant de coder. Mesurer l'accord
carte par carte avec `moteur.py accord` ; avec deux fichiers de codage complets, `moteur.py depouiller` calcule
l'accord de toutes les cartes à la fois.

## 4. Les règles qui ne se discutent pas

- **Indépendance.** Un second codeur ne voit jamais le premier codage, et les deux ne se concertent pas avant la
  mesure. Un modèle de langage peut être l'un des deux codeurs, jamais les deux.
- **Faits sourcés et datés.** Un fait sans source vérifiable n'ancre rien. Une impression n'est pas un fait.
- **Rien ne se retire.** Une correction s'ajoute à côté du texte qu'elle corrige.
- **Une modification qui change une probabilité est une version à part**, annoncée comme telle et vérifiée par
  `conservativite`.
- **Pas d'interface web, pas d'API, pas de modèle de langage branché sur le moteur.**
- **Le projet est gelé** : une règle nouvelle n'entre qu'avec des données réelles qui la justifient.

## 5. Proposer une contribution

1. Ouvrir une *issue* qui dit ce que vous voulez faire, et quel rôle vous prenez.
2. Pour du code ou de la documentation : une *pull request* où `audit` et `autotest` passent, et une entrée au
   `CHANGELOG.md`.
3. Pour un codage : le fichier JSONL de vos fiches, **sans** avoir consulté celles de l'auteur ; l'accord se
   calcule ensuite, et se publie quel qu'il soit.

Tout résultat se publie, y compris un accord faible ou une prévision ratée. C'est ce qui donnera de la valeur au
projet.
