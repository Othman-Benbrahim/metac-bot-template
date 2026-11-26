# Brique du maintien : signal de crise (procédure écrite avant tout calcul)

Décision de l'auteur, 2026-11-26, 15 h 01 : « on met en place la procédure, pour éviter de perdre des points bêtement ».

## Constat (audit du 2026-11-26)
Sur 20 questions de maintien résolues, les trois pires pertes sont des départs que les tables disaient très
improbables : Khamenei écarté avant fin mars 2026 (0,5 %), Khamenei avant 2027 (4,8 %), le pape François en 2025
(4,5 %). Les tables (Archigos, ancienneté ; mortalité selon l'âge) valent en temps normal et ne voient pas un
changement de régime, comme l'Elo ne voyait pas la blessure de Sinner. Les 20 questions sont trop peu nombreuses pour
juger : le test porte sur l'historique des dirigeants.

## Données (sources déjà validées)
- Archigos 4.1 (dirigeants, entrées et sorties ; validé le 2026-11-24, 15 h 23), par le paquet peacesciencer.
- UCDP/PRIO Armed Conflict Dataset (conflits armés par pays et par année), par le même paquet ; UCDP est déjà la
  source de l'état des conflits du bot (ucdp_mois).

## Signal de crise
Au 1er janvier de l'année t, le pays du dirigeant (lieu du conflit) a connu dans l'année t−1 :
- **guerre** : un conflit d'intensité 2 (au moins 1 000 morts liés aux combats dans l'année) ;
- **conflit** : un conflit d'intensité 1 seulement (25 à 999 morts).
Les manifestations (GDELT) ne sont pas dans ce test : pas d'historique comparable ; déclaré.

## Modèle
Pour chaque dirigeant-année de 1990 à 2015 (exposition en fraction d'année), risque de départ attendu par les tables
de la brique : irrégulier + régulier selon l'ancienneté (ecosystemes/archigos-risques.csv), plus mortalité selon l'âge
(SSA 2023) si l'année de naissance est connue. Départ observé : sortie d'Archigos dans l'année (hors « Still in
Office »). Pour chaque niveau de signal, multiplicateur m = départs observés / départs attendus.

## Évaluation (une passe)
- Apprentissage 1990-2005, test 2006-2015.
- Perte log par dirigeant-année, sur le test : tables seules contre tables × m (m appris sur 1990-2005).
- **Retenue si** la perte baisse sur le test ET si m(guerre) > 1 avec un intervalle à 90 % (Poisson exact sur les
  départs observés) qui exclut 1. Le multiplicateur « conflit » n'est appliqué que s'il remplit la même condition.
- Rapport secondaire (sans effet sur la décision) : les 20 questions de maintien résolues, avec et sans multiplicateur,
  le signal étant lu dans l'état UCDP récent du bot à la date de la question.

## Branchement si retenue (décision de l'auteur ensuite)
Dans `maintien_regle.py` : si l'état UCDP du pays montre une guerre dans les 12 mois précédant la question, le risque
de départ (hors mortalité) est multiplié par m(guerre) ; de même pour « conflit » si retenu.

## Limites déclarées
Lieu du conflit et pays du dirigeant : un dirigeant en guerre hors de son territoire n'est pas signalé (cas de
l'Iran frappé chez lui en 2026 : signalé ; cas d'une guerre menée à l'étranger : non). Le pape n'est pas concerné.

## Correction avant tout résultat (2026-11-26, 15 h 10)
Le premier passage s'est arrêté sur les données, avant tout calcul : la version de l'UCDP/PRIO fournie par
peacesciencer n'a pas de colonne de lieu (gwno_loc). Le signal se lit donc sur les **parties principales** du conflit
(gwno_a, gwno_b ; alliés exclus). Conséquence : un État partie principale d'une guerre menée hors de son territoire
est signalé (cela remplace la limite déclarée plus haut). Archigos et l'UCDP utilisent tous deux les codes
Gleditsch-Ward : aucune conversion.
