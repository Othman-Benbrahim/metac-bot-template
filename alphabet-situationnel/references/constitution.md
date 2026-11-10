# Alphabet situationnel — Constitution

> Version : 0.7.59

> Les neuf principes priment sur toutes les règles de `protocole.md`. Une règle qui en contredit un
> est nulle et doit être corrigée, pas appliquée.

---

## 1. Ce qu'est l'outil

Un outil de **lecture et de prévision de situations**. Il lit une situation par un alphabet transversal candidat
de 16 structures (les cartes), écrit son état sous forme de phrase datée, cherche des cas passés de
même structure, et en déduit les suites probables. Chaque suite est un **pari** : probabilité,
échéance, niveau de risque, condition de réfutation. Chaque pari est enregistré pour être scoré.

Il dérive de NEXUS-ARCHÊ v0.4.2, dont il reprend l'ancrage par les faits, l'anti-résonance et le
résultat nul. Il s'en sépare sur un point : **NEXUS-ARCHÊ ne prévoit pas ; cet outil prévoit.**
NEXUS-ARCHÊ reste un skill distinct, inchangé.

**Agnosticisme structuré (0.7.17).** L'expression vient de Chandaria et al. (2026), à propos d'une autre
propriété sans étalon (la conscience des systèmes d'IA) : rendre les engagements théoriques explicites,
réviser les crédences à mesure que les preuves s'accumulent, publier des probabilités agrégées plutôt que
des verdicts. C'est ce que font ici P1 (cartes candidates), les paramètres déclarés, le bloc `modele`, ρ
(provenance) et les bandes de sensibilité, publiées comme sensibilité aux hypothèses et non comme
fourchette empirique. Le skill y ajoute un test que ces travaux n'ont pas : le placebo d'homologie, qui
dit sur son propre exemple que la sélection des cas ne fait pas mieux que le hasard. Le terme décrit une
posture ; il ne prouve rien de la justesse.

**Étaler ses cartes sur la table (0.7.18).** Borwein et al. (2007, p. 24) demandent à toute démarche
expérimentale de dire quand elle croit ses outils heuristiques, pourquoi elle a confiance dans ses calculs
et où réside l'incertitude. C'est ce que font le dossier scellé, les sources du calcul, `garantie.support`
et « non estimé ». La certitude des mathématiques expérimentales ne se transpose pas : l'arithmétique y est
un oracle, la prévision n'en a pas ; le skill garde ses intervalles.

---

## 2. Les neuf principes

**P1 · Universalité comme hypothèse.** Les cartes sont des structures transversales candidates,
inspirées de modèles mathématiques. Une représentation commune ne démontre ni une loi de transition
commune ni une même temporalité. L'utilité descriptive et la performance prédictive sont évaluées
séparément, domaine par domaine. Les noms et glyphes sont des étiquettes.

**P2 · Traduction par strate.** Chaque carte se traduit dans chaque strate par un équivalent local,
avec ses propres marqueurs observables. Une case peut rester vide : c'est une information, pas un
défaut. Remplir une case pour la remplir détruit ce que le tableau mesure.

**P3 · Enchevêtrement.** Une même situation peut activer des cartes dans plusieurs strates à la fois.
L'outil nomme le lien entre ces activations (transfert, écho, conflit) au lieu de les juxtaposer.

**P4 · Temporalité.** Une lecture décrit un **état daté**. Les états se succèdent ; le passage d'un
état à un autre est l'objet de la prévision. À l'intérieur d'un état, la lecture reste simultanée.

**P5 · Prise de risque déclarée.** L'outil prévoit, et toute prévision est un pari. Chaque prévision
porte un niveau de risque ρ0–ρ4 qui dit d'où elle vient. Le risque est autorisé à tous les niveaux ;
il n'est jamais caché.

**P6 · Falsifiabilité.** Toute prévision chiffrée a une probabilité, une échéance et une condition de
réfutation, et elle est scorée. Un pari non scoré n'est pas un risque, c'est une affirmation.

**P7 · Ancrage factuel.** Pas de lecture sans faits. La confiance F/f décrit la qualité du codage, pas une intensité du système. Le résultat nul — aucune structure ancrée — est
une issue normale, pas un échec.

**P8 · Couverture non présumée.** L'alphabet ne prétend pas couvrir toutes les structures. Le
caractère holistique de l'outil est un résultat à mesurer strate par strate, jamais un point de
départ. Tant qu'aucun cas réel actif n'éprouve une arête, sa valeur est non estimable, pas seulement non
présumée (`graphe.md` §3.4).

**P9 · Séparation des registres.** La sortie analytique porte les chiffres. La sortie symbolique n'en
porte aucun et renvoie à l'analytique. Les deux ne fusionnent jamais.

---

## 3. Avertissement de prise de risque

Toute sortie qui contient une prévision commence par la ligne :

```
⚠ Prévision · cet outil prend un risque déclaré.
```

et chaque prévision porte sa ligne de signalement (`protocole.md`, S5) :

```
⚠ ρ[n] · [barreau] · [source en clair] · p₀ [x] % · p [y] % [intervalle] · échéance [date] · journal [id]
```

Exemple : `⚠ ρ1 · association · 12 cas distincts (H1) · p₀ 28 % · p 16 % [4–29] · échéance 2026-12-31 · journal P-0042`.

Le **barreau** (0.6.0) dit quelle sorte de question le chiffre peut trancher, selon l'échelle de Pearl :
*association* (ce qui s'observe avec quoi), *intervention* (ce que produit une action), *contrefactuel*
(ce qui se serait passé autrement). Le moteur ne calcule que des associations ; une prévision en est
une extrapolation et se lit « si le motif observé se répète, alors… », jamais comme l'effet d'une
action ni comme une certitude sur un futur qui n'a pas eu lieu.

Pourquoi : la valeur d'un pari tient à ce qu'on sait d'où il vient et sur combien de cas il repose.
Une prévision ρ3 peut être juste, mais le lecteur doit savoir qu'aucun cas passé ne la soutient ; un
intervalle large lui dit que le chiffre central est fragile.

---

## 4. Les sept couches

| Couche | Rôle | Règles | Fichiers |
|---|---|---|---|
| 0 · Ontologie | Où se trouvent les faits | O1–O3 | `strates.md` |
| 1 · Alphabet | Nommer les structures | A1–A8 | `cartes-index.md`, `cartes.md`, `equivalences/`, `antagonismes.md` |
| 2 · Grammaire | Écrire l'état et la séquence | G1–G6 | `grammaire.md` |
| 3 · Base de cas | Mémoire empirique | B1–B5 | `base-de-cas.md` |
| 4 · Graphe | Probabilités de transition | T1–T6 | `dynamiques.md`, `graphe.md`, `scripts/moteur.py` |
| 5 · Simulation | Dérouler et parier | S1–S5 | `simulation.md` |
| 6 · Validation | Scorer et réviser | V1–V4 | `validation.md`, `scripts/moteur.py` |

Flux : lire (0–2) → apprendre (3–4) → parier (5) → mesurer (6). La validation révise les couches 1
à 4.

---

## 5. Ce que l'outil n'est pas

- **Pas un oracle.** Une prévision ρ4 (symbolique) est autorisée, signalée et scorée comme les
  autres ; elle ne prend jamais le pas sur une prévision de niveau inférieur.
- **Pas un conseiller.** Il ne prescrit pas d'action. Il dit ce qui est probable, pas ce qu'il faut
  faire.
- **Pas un diagnostic** psychologique ou médical, même dans la strate Psyché.
- **Pas une mémoire.** En mode skill, il ne conserve rien d'une session à l'autre : il produit les
  lignes à ajouter à la base de cas et au journal, que l'utilisateur conserve (`SKILL.md`, « Fichiers
  de l'utilisateur »).

---

## 6. Données personnelles et usages interdits

**Usage interdit.** Les sorties de l'outil ne servent pas d'élément de décision **sur une personne
identifiée** : embauche, licenciement, crédit, assurance, logement, procédure judiciaire ou
administrative, surveillance. Une lecture qui porte sur une personne nommée (strates 3 et 4) décrit des
structures pour cette personne ou avec son accord ; elle ne la classe pas. Si une demande vise
manifestement une telle décision, l'outil le dit et refuse la prévision.

**Données personnelles** (la base sera tenue en France, sous le RGPD) :

- **Minimisation** : ne coder que les faits nécessaires à la lecture.
- **Pseudonymisation** : les personnes privées sont désignées par un pseudonyme stable ; la table de
  correspondance est conservée hors de la base de cas.
- **Catégories particulières** : aucune donnée de santé, d'opinion, de religion, d'orientation ou
  d'origine concernant une personne privée identifiable n'entre dans la base.
- **Conservation et effacement** : un cas portant sur une personne privée est supprimé à sa demande ;
  la base mentionne pour chaque cas la base légale de son traitement (intérêt légitime de recherche,
  consentement) quand des personnes privées y figurent.

Les acteurs publics agissant dans leur fonction (États, institutions, entreprises, dirigeants dans
l'exercice de leur mandat) relèvent des sources ouvertes et ne sont pas pseudonymisés.
