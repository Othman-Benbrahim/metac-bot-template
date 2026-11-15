# Pré-enregistrement — aiguillage par régime causal, séries (bot 0.10.113)

**Décision d'auteur du 2026-11-15.** Idée de l'auteur : différencier les types de causalité et en déduire des principes
actifs ; classés par mécanisme mesurable plutôt que par domaine (note `claude/regimes-causaux-principes-actifs.md` du
projet). Premier test, gratuit, sur les séries. Commité AVANT tout calcul.

## Mesures, avant la date d'information (`banc_b.proprietes`)
- **Saisonnalité** : moyennes mensuelles sur 10 ans, pas d'un mois au suivant ; part de variance expliquée par le mois
  de l'année, retenue avec la règle déjà fixée dans le bot (0.10.32) : au moins 3 pas par mois, R² ≥ 0,2 et F ≥ 2,5.
- **Inertie** : φ de l'AR(1) sur les différences (celui du B autorégressif), retenue s'il sort de la bande de
  Bartlett ±2/√n (n = points sur 5 ans).
- **Entropie de permutation** (Bandt et Pompe, ordre 3) : rapportée, sans rôle dans la règle.

## Règle d'aiguillage (fixée ici)
Saisonnalité forte → B saisonnier ; sinon inertie forte → B autorégressif ; sinon → B.

## Questions et critère
Séries FRED et DBnomics résolues, lues par le banc du taux de base à partir de la version 0.10.113, hors jeux vus
(2026-09-27, 10-11, 10-25) ; les 400 questions de juillet-août déjà lues sont exclues (version antérieure). Ordre
entrelacé entre les jeux (empreinte SHA-1). Sur les 100 premières : perte log de l'aiguillage inférieure à celle de B,
intervalle de l'écart (bootstrap par blocs « jeu × source ») entièrement sous 0 au niveau corrigé. Second regard à 200.
Essai `regimes_causaux`.

## Attente déclarée
Le B saisonnier a perdu sur FRED et gagné sur DBnomics ; une règle qui ne l'applique que là où la saison est mesurée
devrait garder le gain et éviter la perte. Le B autorégressif n'a pas gagné : l'inertie risque de ne rien apporter.
