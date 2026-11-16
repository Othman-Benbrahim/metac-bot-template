# Catalogue des mécanismes (ouvert le 2026-11-16)

**Décision d'auteur du 2026-11-16 (10 h 49)** : « Je valide tout » (catalogue reconstruit). Origine : l'idée de l'auteur
du 2026-11-15 d'explorer l'événementiel **cas par cas, « en grappillant »**, avec des critères **fixés à l'avance et
automatisables** plutôt que des jugements subjectifs d'IA, et de raisonner **par induction** (un motif doit revenir lot
après lot).

**Statut : registre, pas un pré-enregistrement.** Une fiche n'est qu'une hypothèse. Elle ne touche à aucune prévision
tant qu'elle n'a pas franchi, dans l'ordre :
1. le **rasoir d'Ockham** (`README.md` de ce dossier : une phrase, paramètres, sens fixé d'avance, domaine, plus
   simple ?) ;
2. l'**observatoire inductif** (`induction.py` : même sens dans au moins 3 lots sur 4, au moins 4 lots, 20 questions),
   quand l'indicateur y est branché ;
3. un **pré-enregistrement** à sens et force fixés, jugé par la règle d'adoption commune ;
4. une **décision d'auteur datée** pour passer de l'ombre à la prévision postée.

Un modèle de langue peut **proposer** une fiche (usage n° 3 des crédits Bedrock : mécanismes suggérés sur les plus
grosses erreurs) ; il ne la juge jamais. Une fiche proposée par un modèle porte « origine : modèle » et passe les mêmes
étapes.

## Gabarit d'une fiche
- **Mécanisme** (une phrase) ;
- **Indicateur** observable AVANT la date de la question, et sa source ;
- **Sens** fixé d'avance (+ / −) et, si possible, ordre de grandeur ;
- **Domaine** : familles de questions concernées (et celles exclues) ;
- **Échelle de temps** ;
- **Origine** : événement ou constat qui l'a suggéré (auteur, banc, littérature, modèle), date ;
- **État** : proposé → observatoire → pré-enregistré → adopté / rejeté / caduc, avec renvoi.

## Fiches

### M1. Le beau temps du jour fait descendre dans la rue
- Indicateur : pluie le jour J et les jours précédents (Open-Meteo), au lieu de la question.
- Sens : pluie → moins de manifestations et d'émeutes (−), à **court terme** (le jour même, quelques jours).
- Domaine : ACLED « manifestations », « émeutes ». Pas la violence armée.
- Origine : auteur, 2026-11-15 (« on ne manifeste et on n'est violent que quand il fait beau ») ; effet documenté
  pour les manifestations (la pluie vide la rue).
- État : **rejeté sous sa forme saisonnière** (essai `indicateurs_pertinents`, z de pluie sur 90 jours instable dans
  les régions sèches, signes inversés sur questions fraîches) ; la forme **courte** (jours, pas saison) n'a pas été
  testée. Suivie dans l'observatoire (état « pluie »).

### M2. Une saison humide entretient la violence politique
- Indicateur : cumul de pluie sur la saison (90 jours) rapporté à la normale.
- Sens : année humide → plus de violence politique (+) ; échelle de la saison.
- Domaine : ACLED « violence » (affrontements, violence contre les civils).
- Origine : littérature (Hendrix et Salehyan, *Journal of Peace Research* 2012 ; Salehyan et Hendrix, *Global
  Environmental Change* 2014), relevée le 2026-11-15 en vérifiant M1.
- État : **rejeté avec M1** (même modèle figé, même mesure instable) ; à reprendre seulement avec une mesure stable
  (anomalie relative bornée, pas un z sur une série presque nulle).

### M3. Un conseil aux voyageurs durci annonce de la violence
- Indicateur : durcissement du conseil aux voyageurs britannique (FCDO) dans les 14 jours avant la date.
- Sens : + 0,5 logit sur B, fixé d'avance.
- Domaine : ACLED « violence ». Pas les manifestations.
- Origine : banc des indicateurs (2026-11-15) ; décision d'auteur de le garder « principalement et officiellement ».
- État : **pré-enregistré**, essai ouvert `conseil_durci` (`conseil-durci.md`).

### M4. B surestime les émeutes (surdispersion)
- Indicateur : aucun signal extérieur ; c'est la forme de la loi de comptage. Les émeutes viennent par rafales rares :
  la moyenne des 12 derniers mois annonce trop de mois « avec émeute ».
- Sens : − sur B pour la famille « émeutes ».
- Domaine : ACLED « émeutes ».
- Origine : observatoire inductif, premier passage (2026-11-15) : 5 « oui » pour 9,7 attendus ; les deux candidates de
  l'observatoire s'expliquent par ce seul fait.
- État : **observatoire** ; à confirmer lot après lot avant tout pré-enregistrement.

### M5. Les acteurs font ce qu'ils annoncent (actes de langage)
- Indicateur : engagements datés relevés dans les sources (« X frappera si… », « le vote aura lieu le… »).
- Sens : engagement public daté → probabilité de l'acte plus haute (+).
- Domaine : conflits, décisions politiques programmées.
- Origine : banc du langage (2026-11-15) ; Merton (1948) pour l'effet des annonces.
- État : **pré-enregistré**, essai ouvert `langage_acte` (`langage.md`).

### M6. Le silence est une information
- Indicateur : aucune mention du pays dans la presse lue, ou état « structure absente » de l'alphabet.
- Sens : − sur B (cote divisée par 2 pour les états nuls d'absence).
- Domaine : questions d'occurrence d'événement.
- Origine : banc ForecastBench du 2026-10-25 (11 états nuls, 1 « oui » pour 3,9 attendus).
- État : **pré-enregistré**, essai ouvert `ombre_absence` (`ombre-absence.md`) ; la variante « silence de la presse »
  est à refaire (`silence-a-refaire.md`).

### M7. Le contexte physique décide d'une série physique
- Indicateur : prévisions météo archivées, à même échéance, de cinq modèles.
- Sens : écart prévu entre J+7 et J → sens de la variation.
- Domaine : températures (Météo-France, DBnomics).
- Origine : auteur, 2026-11-15 (« une série non contextualisée ne donne pas de résultat ») ; premier passage 0,645
  contre 0,694 pour B.
- État : **pré-enregistré**, essai ouvert `contexte_meteo_v2` (`contexte-meteo.md`).

### M8. Les signaux de niche précèdent la presse
- Indicateurs (branchés en ombre, dans l'observatoire) : emballement des canaux Telegram validés, modifications de la
  page Wikipédia du pays, prix alimentaires (PAM), arrivées aériennes (OpenSky), brouillage GPS (gpsjam), incidents
  graves (Violations Watch), comptes RSS par famille (presse, officiel, santé, Parlement européen, renseignement,
  Global Voices, think tanks, économie, notation).
- Sens : **non fixé** ; c'est l'observatoire qui dira si un sens revient lot après lot. Aucun sens ne sera choisi
  après avoir vu les issues.
- Domaine : par famille de questions, à l'observatoire.
- Origine : auteur, 2026-11-15 (indice des pizzas du Pentagone ; « tu sous-estimes les signaux faibles »).
- Réserve de l'auteur : un signal de niche s'épuise quand il devient connu, et joue surtout autour d'événements.
- État : **observatoire** ; premières mesures RSS et Violations Watch après 14 jours de collecte (vers le 30 novembre).

### M9. Les notes souveraines ne bougent qu'aux dates annoncées
- Indicateur : calendrier de révision publié d'avance par chaque agence (obligation européenne) ; perspective en cours
  (négative, stable, positive).
- Sens : aucune date dans la fenêtre → probabilité de changement quasi nulle ; une date → fréquence historique selon la
  perspective.
- Domaine : notes souveraines des pays de l'UE (et pays tiers notés depuis l'UE quand le calendrier les couvre).
- Origine : recherche des flux des agences, 2026-11-15 ; décision d'auteur du 2026-11-16.
- État : **à pré-enregistrer** (`b-notation.md`).

### M10. Une élection nationale proche attise les tensions
- Indicateur : élection nationale ou référendum du pays (Wikidata) dans les 30 jours avant la date ; à part, prévue
  dans les 30 jours après (fuite possible pour une élection anticipée annoncée plus tard, déclarée).
- Sens fixé d'avance : élection proche → plus de manifestations, d'émeutes, de coupures d'internet (+).
- Domaine : ACLED « manifestations », « émeutes » ; coupures (Radar, OONI).
- Origine : recherche d'un calendrier électoral, 2026-11-16 ; décision d'auteur du même jour.
- État : **observatoire** (indicateur `elections`, 0.10.179).

### M11. Les troubles des pays voisins gagnent le pays (diffusion spatiale)
- Indicateur : manifestations et émeutes de GDELT dans les pays frontaliers (table GeoNames), 14 jours avant la date
  contre les 14 précédents (`voisins`, 0.10.186).
- Sens fixé d'avance : voisins qui s'embrasent → manifestations et émeutes plus probables dans le pays (+).
- Domaine : ACLED « manifestations », « émeutes ».
- Origine : géographie de la diffusion (Hägerstrand ; Hypergéo, « diffusion spatiale », Th. Saint-Julien : contagion
  de proximité, décroissance avec la distance, barrières) ; appui empirique : manifestations contagieuses entre pays
  (LSE, 200 pays, 2000–2020) et corrélation spatiale des troubles (arXiv 2306.08698, Moran I = 0,15–0,19).
  Analyse de la page « liens utiles » de Géoconfluences, 2026-11-16 ; décision d'auteur du même jour.
- Réserve : un signal positif ne distingue pas la contagion d'une cause commune aux voisins (économie, culture).
- État : **observatoire** ; jugeable sur les questions résolues dès le rattrapage de GDELT.

### M12. Le récit monte avant l'acte
- Indicateur : articles de sources russes qui nomment le pays (GDELT DOC 2.0, `sourcecountry:russia`), 14 jours avant
  la date contre les 14 précédents (`recit_russe`, 0.10.202) ; variante « alibi informationnel » : part de ces articles
  qui parlent de provocation, de mise en scène ou de faux drapeau (`part_alibi_14j`).
- Sens fixé d'avance : récit russe en hausse → action russe visant le pays plus probable (frappes, sabotages,
  incursions, coupures, ruptures diplomatiques) (+) ; part « alibi » en hausse, même sens.
- Domaine : questions sur une action de la Russie contre un pays ; exclues : questions sans acteur russe.
- Échelle de temps : semaines.
- Origine : Anderson et Bajarūnas, *Cognitive Warfare: A Democratic Defence* (KAS, 2026), vol. 2, chapitre Ukraine :
  StopFake dit avoir anticipé la date et l'ampleur de l'invasion de 2022 en suivant le volume des récits russes ;
  affirmation de praticiens, non vérifiée. Alibi informationnel : MH17, Skripal (même rapport, annexe B). Décision
  d'auteur du 2026-11-16 (18 h 56).
- Réserve : l'API ne remonte qu'à trois mois ; l'historique se construit au fil des passages. Les requêtes portent sur
  la traduction anglaise des articles russes faite par GDELT.
- État : **observatoire** (indicateur `recit_russe`).

### M13. La réponse s'use à la répétition (« mundanisation »)
- Indicateur : actes hostiles d'un acteur russe dans le pays (GDELT, Actor1CountryCode = RUS, racines CAMEO 18, 19, 20)
  dans les 12 mois avant la date, par catégorie (registre `gdelt-hostilites-ru.csv`, 0.10.202).
- Sens fixé d'avance : plus la même catégorie de transgression s'est répétée, moins une réponse occidentale forte
  (sanctions nouvelles, mesures diplomatiques) est probable (−).
- Domaine : questions « les États-Unis, le Royaume-Uni ou l'UE répondront-ils par des sanctions ou des mesures après
  X ? » ; réponses mesurées par nos registres de sanctions (OFAC, Royaume-Uni). Exclues : toutes les autres.
- Échelle de temps : mois.
- Origine : même rapport, chapitre 4 et annexe B (« mundanisation ») ; décision d'auteur du 2026-11-16.
- Réserve : peu de questions de ce type ; le jugement attendra 20 questions résolues du domaine. Rattrapage de GDELT
  nécessaire sur 12 mois (collecte GDELT avec « depuis »).
- État : **proposé** ; données collectées, pas d'état d'observatoire (domaine trop étroit pour les questions du banc).

### M14. Les dates de mémoire attisent les tensions
- Indicateur : date de mémoire du calendrier fixe (`registre/dates-memoire.csv` : 9 mai, déportations de 1941 et 1949,
  ruban noir du 23 août, légion lettone du 16 mars, Nuit de bronze, 13 janvier, Kirkenes…) dans les 14 jours à partir
  de la date (`dates_memoire`, 0.10.202). Calendrier connu d'avance : aucune fuite.
- Sens fixé d'avance : date de mémoire proche → manifestations, incidents, opérations d'influence et cyberattaques
  plus probables dans le pays (+).
- Domaine : pays du calendrier (baltes, Russie, Biélorussie, Ukraine, Moldavie, Géorgie, Pologne, Norvège).
- Échelle de temps : jours.
- Origine : même rapport (annexe B, « memory politics » : Soldat de bronze, Tallinn 2007 ; mémorial de Kirkenes) ;
  rangé par l'auteur parmi les signaux faibles et angles morts ; décision d'auteur du 2026-11-16 (18 h 56).
- Réserve : calendrier établi le 2026-11-16 à partir de connaissances générales, à relire par l'auteur ; dates à jour
  fixe seulement (pas le Holodomor, quatrième samedi de novembre).
- État : **observatoire** (indicateur `dates_memoire`).

### M15. Le silence statistique annonce une mauvaise nouvelle
- Indicateur : publications du Bureau national des statistiques chinois prévues par son calendrier officiel annuel
  et parues en retard (plus de 3 jours) ou pas du tout, dans les 30 jours avant la date (`silence_statistique`,
  0.10.209 ; calendrier `registre/calendrier-nbs.csv`, observations `registre/publications-nbs.csv`).
- Sens fixé d'avance : publication manquante ou retardée → mauvaise nouvelle économique ou politique en Chine plus
  probable (chiffre suspendu, crise interne, décision sensible) (+).
- Domaine : questions sur l'économie chinoise et la stabilité intérieure de la Chine ; exclues : toutes les autres.
- Échelle de temps : semaines.
- Origine : suspension de la publication du chômage des jeunes (été 2023) ; logique de l'ombre « absence » appliquée
  à une administration fermée ; décision d'auteur du 2026-11-16 (22 h 19).
- Réserve : le site anglais publie avec un ou deux jours de décalage (tolérance de 3 jours) ; un motif de titre qui
  change ferait passer une publication pour absente (à surveiller dans le registre) ; calendrier à renouveler chaque
  année.
- État : **observatoire** (indicateur `silence_statistique`).

## Ce que ce catalogue n'est pas
Ni une liste de « causes » démontrées, ni un réservoir où l'on choisit après coup la fiche qui aurait marché. Le
nombre de fiches augmente le risque de trouver une régularité par hasard ; c'est pourquoi le sens est fixé avant
l'observatoire, et la règle d'adoption corrige pour le nombre d'essais ouverts.
