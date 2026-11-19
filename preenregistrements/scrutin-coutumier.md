# Brique « scrutin » coutumière (préenregistrement, 2026-11-19)

Décisions de l'auteur du 2026-11-19 : écrire les règles coutumières propres à chaque échelle, ne pas déduire, s'abstenir sans source ; les intégrer au programme écosystémique avec les règles déjà mises à jour ; tester une seule fois sur des cas réels.

Essai `scrutin_coutumier`. Ombre : rien dans le bot, rien côté Metaculus avant le tournoi.

## 1. Ce qui change par rapport à `etalon_scrutin`

Les deux règles inventées de `banc_scrutin.py` sont retirées :
- le second tour « approximé » (le premier gagne) devient la règle sourcée `second_tour_retournement` : le premier du premier tour gagne le second avec 1 − r, le deuxième avec r, r par région (Europe 0,316 ; Amérique latine 0,24 ; Afrique 0,216 ; moins de 30 seconds tours → monde 0,293) ;
- σ(t) = σ₀·√(1 + t/30) devient : erreur par type d'élection (`sondages_erreur_comparee` hors États-Unis, dernière semaine ; `us_erreur_sondages_par_echelle` aux États-Unis, 21 jours), multipliée par le rapport des erreurs selon le temps restant (`us_erreur_selon_temps_restant` : 2 la veille, 3 à 50 jours, 4 à 150 jours et plus ; interpolation linéaire).
Seules conversions ajoutées, arithmétiques : écart = 2 × part à deux candidats ; erreur moyenne absolue = 0,8 σ.

## 2. Abstentions (règle manquante → pas de probabilité)

Primaires d'État américaines (`us_erreur_primaires_d_etat`, absence) ; investitures présidentielles (délégués) ; élections municipales et infranationales hors États-Unis ; questions de sièges (pas de règle voix → sièges) ; pays ou mode de scrutin absents des tables ; Géorgie et Louisiane en élection générale. Le motif de chaque abstention est publié.

## 3. Couverture mesurée avant le test, sans lire les issues

`python brique_coutumiere.py --couverture` le 2026-11-19 : **3 questions jugées sur 329** (116 hors forme, 62 pays ou échelle absents des tables, 53 sans sondage dans les 30 jours, 42 primaires d'État, 22 municipales, 17 sièges, 6 investitures, 4 sans archive, 4 modes non inscrits).

## 4. Test décisif (une seule exécution, par l'auteur)

- Questions : toutes les questions électorales résolues des archives de `banc_scrutin` (toutes années), hors réseau.
- Critère (risque corrigé d'`essais.py`) : brique coutumière contre semblables, perte log, intervalle de l'écart entièrement sous 0 ; en dessous de 30 questions jugées, verdict « insuffisant ». En descriptif : contre l'ancienne brique sur les questions communes, et par mode (un tour, deux tours).
- **Condition de lancement** : au moins 30 questions jugées à la couverture (§ 3). Elle n'est pas remplie aujourd'hui ; lancer le test maintenant donnerait « insuffisant » à coup sûr. Les règles qui ouvriraient le plus de questions sont l'erreur des sondages à l'échelle infranationale (États brésiliens, Länder, primaires d'État) et le passage voix → sièges.
