# Socle du programme écosystémique

Règles coutumières : {'source': 31, 'absence': 3, 'auteur': 2} ; valables partout : us_erreur_selon_temps_restant, regimes_fermes_inertie, regimes_fermes_contestation, sondages_erreur_comparee, voix_vers_sieges, presidentielles_mode_de_scrutin, onu_conseil_securite_vote, coups_d_etat_frequence, chefs_d_etat_sortie_irreguliere, second_tour_retournement, parlements_mode_de_scrutin. Briques : seuil (vitesse) valide, course (taille) non tranché.

| Fiche | Espaces des règles | Règles (dont absences) | Inconnus | Natures des traces |
|---|---|---|---|---|
| alimentation-mondiale | asie, amerique_latine | 4 (1) | absence 8 | stock 2, flux 6, potentiel 1, gradient 2 |
| calendriers-echeances | — | 0 (0) | absence 2 | phase 3, gradient 1, potentiel 1 |
| climat-extremes | — | 0 (0) | absence 6 | gradient 8, stock 3, flux 4 |
| competitions-culture | — | 0 (0) | absence 7 | — |
| crises-bancaires | — | 0 (0) | absence 1 | flux 1, potentiel 5 |
| cycles-biogeochimiques | — | 0 (0) | absence 6 | flux 2, gradient 2, potentiel 2 |
| dette-emergents | — | 0 (0) | absence 6 | potentiel 3, flux 5, phase 1 |
| eau-moyen-orient | afrique, asie | 10 (2) | absence 10 | gradient 3, flux 3, stock 1 |
| economie-chinoise | asie | 4 (1) | absence 6, conflictuel 1 | flux 9, phase 3, gradient 3 |
| elections-amerique-latine | amerique_latine | 0 (0) | absence 5, confusion 1 | potentiel 1, flux 1 |
| energie-mondiale | — | 0 (0) | absence 2 | flux 6, stock 1, potentiel 1, gradient 3 |
| epidemies | — | 0 (0) | absence 6 | gradient 1, flux 2 |
| foret-et-sols-vivants | — | 0 (0) | absence 13 | — |
| guerre-levant | asie | 4 (1) | absence 4 | flux 17 |
| humain | — | 0 (0) | absence 23, tabou 3, conflictuel 1 | gradient 5, stock 1, flux 14, déclaration 1, phase 4 |
| inflation-mondiale | amerique_du_nord, asie | 12 (2) | absence 2 | potentiel 5, flux 5, stock 1, gradient 2, phase 1 |
| information-cyber | — | 0 (0) | absence 1 | flux 7, stock 1 |
| infrastructures-critiques | — | 0 (0) | absence 2 | flux 4, potentiel 1, gradient 1 |
| iran-nucleaire | asie | 4 (1) | absence 4 | flux 9, phase 1, potentiel 1, gradient 1, stock 1 |
| liban-institutions | — | 0 (0) | absence 3 | flux 4 |
| migrations-demographie | — | 0 (0) | absence 5 | stock 2, flux 1, gradient 1 |
| non-proliferation | — | 0 (0) | absence 5 | flux 4 |
| nucleaire-radiologique | — | 0 (0) | absence 7 | — |
| observateur-mesure | — | 0 (0) | absence 2 | flux 2 |
| oceans-et-fleuves | — | 0 (0) | absence 6 | gradient 3, stock 1, flux 2 |
| ormuz | — | 0 (0) | absence 2 | gradient 2, flux 9, potentiel 1, stock 1 |
| politique-americaine | amerique_du_nord | 8 (1) | absence 1 | flux 20, phase 1, potentiel 3, gradient 2 |
| relief-et-montagnes | — | 0 (0) | absence 7 | gradient 2, flux 3 |
| rivalite-sino-americaine | asie | 4 (1) | absence 1 | flux 14, potentiel 2 |
| russie-ukraine | europe | 6 (0) | absence 3 | flux 17, stock 2, potentiel 1, phase 1 |
| sciences-techniques | — | 0 (0) | absence 1 | flux 3, potentiel 2, gradient 1 |
| securite-europeenne | europe | 6 (0) | absence 4 | flux 4, potentiel 1 |
| securite-publique | — | 0 (0) | absence 5 | flux 1 |
| soleil-espace | — | 0 (0) | absence 7 | flux 1 |
| transport-maritime | asie | 4 (1) | absence 6 | flux 8 |

Parlements (IPU Parline) : 281 chambres, 71 non élues au suffrage direct ; suspendues (inertie des régimes fermés) : Afghanistan, Kazakhstan, Koweït, Mauritanie, Myanmar, Soudan, Turkménistan.

## Mécanismes à connaître (non mesurables) et leur garde

- **reprise des dépêches (amont commun de la presse)** : deux sources indépendantes au minimum ; presse ↔ presse et GDELT ↔ UCDP marqués « amont partagé » (ecart_dit_compte.py)
- **le sondage révèle aussi son émetteur** : un sondage est classé déclaration (classer_series.py), jamais mesure
- **la note de qualité n'est pas une mesure (Goldstein, gestuelle)** : comptes de gestes à la place du ton (adaptateur gestes:) ; test de garde sur la nature des traces
- **l'État n'est pas au-dessus** : statistiques et rapports d'État classés selon ce qu'ils comptent, avec leur émetteur
- **lecture à froid (effet Barnum)** : une lecture sans probabilité notée sur l'issue réelle ne compte pas
- **prédiction précise en apparence, probable en réalité** : juger sur le registre complet des prévisions notées
- **les deux poches (multiple outs)** : préenregistrement ; risque corrigé selon le nombre d'essais ouverts ; un test lancé une fois
- **le forçage (choix illusoire)** : forme de la question lue avant l'issue ; brique qui s'abstient hors forme
- **la communication volontaire** : écart dit / compté, personnalités publiques et institutions seulement
- **le détournement d'attention (distraction prévisible)** : fêtes programmées, pas commémorations ; premier test sans effet visible
- **l'éloquence n'est pas la justesse** : la confiance verbale d'un modèle n'est jamais une probabilité
