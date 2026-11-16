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

## Ce que ce catalogue n'est pas
Ni une liste de « causes » démontrées, ni un réservoir où l'on choisit après coup la fiche qui aurait marché. Le
nombre de fiches augmente le risque de trouver une régularité par hasard ; c'est pourquoi le sens est fixé avant
l'observatoire, et la règle d'adoption corrige pour le nombre d'essais ouverts.
