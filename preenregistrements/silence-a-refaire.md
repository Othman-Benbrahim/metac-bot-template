# Silence de la presse — à refaire avec B corrigé : distinguer trois silences (brouillon, 2026-11-15, 13 h 35)

**Statut : brouillon de conception, pas encore un pré-enregistrement.** Il deviendra l'essai `silence` refait quand
le banc du bras A (sources `acled`, B corrigé, 0.10.127+) aura fourni des questions d'apprentissage ; les paramètres
seront alors figés sur elles et jugés sur des questions fraîches, comme d'habitude.

## Pourquoi refaire
L'essai du 2026-11-15 (11 h 27) est caduc : ses paramètres venaient d'un A ancré sur le B ACLED faux
(`erreur-b-acled-2026-11-15.md`). Décision d'auteur du 2026-11-15 (13 h 12) : refaire.

## Ce qui manquait : tous les silences ne se valent pas
Idée de l'auteur : « le calme précède la tempête ». Objection tirée du 7 octobre 2023 (Opex News, 2026) : un calme
peut être **fabriqué** ; le Hamas a cloisonné sa préparation et le silence apparent était une manœuvre. L'ancien essai
mettait dans le même sac trois situations opposées :

1. **Angle mort** : personne ne regarde (petit territoire, langue peu indexée, moteur de recherche qui ne couvre pas).
   Le silence ne dit rien de la situation.
2. **Calme réel** : on regarde, et il ne se passe rien. Le silence annonce plutôt moins d'événements.
3. **Silence suspect** : la presse se tait, mais des signes indirects bougent (coupures d'internet, conseils aux
   voyageurs durcis, attention du public qui monte, black-out des communications officielles). Le silence peut
   annoncer plus d'événements.

## Mesures envisagées (toutes avant la date d'information, sans modèle de langue sauf l'extraction existante)
- Silence : aucun extrait de presse trouvé (banc du langage) ou nombre d'extraits nettement sous l'habituel du pays.
- Couverture habituelle du pays (pour l'angle mort) : vues moyennes de l'article Wikipedia du pays sur 90 jours
  (niveau absolu, pas seulement la variation), et nombre d'événements GDELT habituels du pays (`gdelt_comptes.py`).
- Signes indirects (pour le silence suspect) : alertes IODA sur 30 jours, changement de sécurité des conseils aux
  voyageurs, hausse de l'attention Wikipedia.
- Classement fixé d'avance : silence + couverture faible → angle mort ; silence + couverture normale + signes
  indirects calmes → calme réel ; silence + au moins un signe indirect actif → suspect.

## Hypothèse à tester (sens fixé d'avance)
Par rapport à B corrigé : calme réel → probabilité plus basse ; silence suspect → plus haute ; angle mort → aucun
effet. Le gain attendu vient de ne plus mélanger les trois.

## Limites connues
Les silences suspects seront rares sur ForecastBench (questions sur tous les pays, surtout ordinaires) : peu de
puissance. La couverture GDELT et Wikipedia penche vers les pays anglophones.
