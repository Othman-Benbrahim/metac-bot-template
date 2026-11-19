# Kahneman — Système 1 / Système 2

## Référence
Daniel Kahneman, *Thinking, Fast and Slow*, 2011 ; trad. fr. Raymond Clarinard, *Système 1 / Système 2. Les deux
vitesses de la pensée*, Flammarion, coll. Champs, nouvelle édition. Lu en epub (envoyé par l'auteur le 2026-11-19),
38 chapitres en cinq parties. Mémo dans nos mots.

## Thèse en trois phrases
Le jugement humain repose sur deux modes : un système rapide, automatique et associatif (système 1), qui répond
souvent à une question plus facile que celle posée, et un système lent et coûteux (système 2), paresseux, qui valide
le plus souvent ce que propose le premier. De là des biais systématiques et prévisibles : disponibilité, ancrage,
oubli des fréquences de base, excès de confiance, récit qui fabrique de la cohérence, oubli du retour vers la moyenne.
Face au risque, on juge en gains et pertes par rapport à un point de référence, les pertes pèsent environ deux fois
plus que les gains, et les probabilités extrêmes sont déformées (le possible et le certain surpondérés).

## Mécanismes retenus
Format : phrase · niveau · relation (fiche `humain`) ou code · paramètres · trace.

1. **Disponibilité et cascades.** On juge la fréquence à la facilité de se rappeler ; un événement vif et récent gonfle
   la probabilité perçue ; la couverture et l'inquiétude se nourrissent. · psychologique · compartiment
   disponibilite ; passage_acte → disponibilite (+), disponibilite → disponibilite (+, saturation), symboles →
   disponibilite (+) · — · attention publique par sujet (à brancher).
2. **Poids des probabilités (schéma quadrangulaire, événements rares).** · psychologique · compartiment risque_percu ;
   disponibilite → risque_percu (+, saturation) · — · anticipations (T10YIE, UMCSENT).
3. **Aversion aux pertes et point de référence.** Une perte pèse environ deux fois un gain ; le point de référence est
   l'état habituel. · tous niveaux humains · `carte.asymetrie` : paramètres de relation `lambda_pertes` (départ 2) et
   `sens_perte` ; posés sur stress_chronique → attente, attente → passage_acte, stress_chronique → opinion_privee ; le
   point de référence de la carte est l'habitude de chaque série (le z est un écart à l'habitude) · λ mesuré par
   `calibrer.mesurer_asymetrie` (pente du côté perte contre côté gain, testée) · séries des deux bouts.
4. **Peur et frontière.** risque_percu → nous_eux (+), risque_percu → attente (−). · psychologique · — · —
5. **Retour vers la moyenne.** Une valeur extrême est suivie d'une valeur plus proche de la moyenne, sans cause à
   chercher. · tous niveaux · `calibrer.persistance` : AR(1) par compartiment, tendance retirée, φ et temps
   caractéristique τ ; `Carte.simuler` utilise τ mesuré à la place du temps propre écrit · — · toute série branchée
   (112 compartiments mesurés au premier passage).
6. **Ce qu'on voit est tout ce qui existe ; vision externe ; formules contre intuition.** · observateur · pont
   disponibilite → observateur-mesure:biais (les questions naissent des événements saillants : la saillance gonfle
   la probabilité perçue au-delà de la fréquence de base) · — · côté bot, déjà en place : classe de référence, base
   rates, juges aveugles ; rien de nouveau dans le bot avant le tournoi (condition de l'auteur).

## Ce qui a été écrit dans le programme (bot 0.10.328)
- `ecosystemes/humain.yaml` : compartiments disponibilite et risque_percu ; 6 relations ; 3 asymétries de pertes ;
  2 ponts.
- `carte.py` : `asymetrie` (dans la propagation et la simulation) ; persistance mesurée dans `simuler`.
- `calibrer.py` : `mesurer_asymetrie`, `persistance` ; section « compartiments » de `registre/calibration.json`.
- Tests : asymétrie retrouvée sur données simulées (λ = 2), φ et τ retrouvés, fiche.

## Limites et critiques connues
- Plusieurs résultats de la première partie (amorçage social, épuisement de l'ego) ne se sont pas répliqués ; Kahneman
  l'a reconnu publiquement pour l'amorçage. Rien n'en est entré dans la carte.
- Les coefficients de l'aversion aux pertes varient beaucoup selon les enjeux et les populations ; 2 n'est qu'une
  valeur de départ, mesurée ensuite.
- Biais mesurés surtout en laboratoire sur des choix individuels ; leur agrégation en comportements de population est
  notre hypothèse.
