# Sapolsky — Behave

## Référence
Robert M. Sapolsky, *Behave: The Biology of Humans at Our Best and Worst*, Penguin Press, 2017. Lu dans une traduction
française non officielle (PDF envoyé par l'auteur le 2026-11-19), 17 chapitres, un épilogue et une annexe de
neurosciences. Mémo écrit dans nos mots, sans citation longue.

## Thèse en trois phrases
Un acte humain ne s'explique par aucune cause seule : il faut remonter, en couches emboîtées, de la seconde qui le
précède (le système nerveux), aux minutes (les indices du milieu), aux heures (les hormones), aux mois (le stress, la
plasticité), à l'adolescence, à l'enfance et à la vie prénatale, aux gènes, à la culture et à l'écologie d'origine,
puis à l'évolution. Les facteurs biologiques modulent plus qu'ils ne causent : ils abaissent les seuils auxquels le
milieu déclenche un comportement, et leur effet dépend du contexte. Le même appareil qui trace en un instant la
frontière entre nous et eux sait aussi l'effacer : trêves, contact, buts communs et temps rendent les haines passées
incompréhensibles.

## Mécanismes retenus
Format : phrase · niveau d'organisation · relation (fiche `humain`) · paramètres · trace.

1. **L'emboîtement des échelles de temps.** Chaque couche agit à sa vitesse ; la carte les ordonne de la seconde
   (instant) au millénaire (culture_ecologie). · corps → ideologie · structure de la fiche (ordre des compartiments,
   axe vitesse) · aucun · —
2. **La modulation de seuil (le cœur du livre).** Une hormone ne cause pas l'acte : elle abaisse le seuil auquel une
   alerte le déclenche ; la précarité fait de même pour la frontière de groupe. · corps, psychologique · relations
   `module` : hormones ⇢ (instant → passage_acte), indices ⇢ (instant → passage_acte), stress_chronique ⇢
   (nous_eux → passage_acte) · `seuil` (départ 2,0 en |z|), `gain` (0,5 ; 0,3 ; 0,4) · le gain se mesure quand les
   trois séries existent (corrélation de la relation visée, modulateur haut contre bas).
3. **La seconde avant.** Détection de menace avant la conscience ; peur et agression partagent leurs circuits ; le
   frein frontal faiblit sous fatigue, faim, stress. · corps · indices → instant (+, seuil), instant → passage_acte
   (+, seuil) · `seuil` · aucune trace directe (compartiment fermé, lu par ses effets).
4. **Les indices du milieu.** Chaleur, bruit, foule, marqueurs d'un autre groupe raccourcissent la patience et amorcent
   la réaction. · psychologique · indices → instant ; indices ⇢ seuil du passage à l'acte · `gain` · anomalies de
   température NASA POWER (`meteo:delhi`, `meteo:houston`).
5. **Stress aigu contre stress chronique.** Le premier mobilise, le second use (courbe en U inversé) ; l'imprévisibilité
   et la perte de contrôle pèsent plus que la privation. · corps · stress_chronique → hormones (+, saturation) ·
   règle mesurée · `fred:UNRATE`, `fred:PFOODINDEXM:var12`.
6. **L'attente plutôt que la récompense.** Le système de récompense est tourné vers l'anticipation ; une attente qui
   s'effondre mobilise plus qu'une misère attendue. · psychologique · stress_chronique → attente (−), attente →
   passage_acte (−, seuil), attente → hierarchie (− : contestation) · `seuil` · `fred:UMCSENT` (ajoutée à la collecte
   FRED), `fred:T10YIE`.
7. **Adolescence.** Le cortex frontal mûrit le dernier ; prise de risque surtout sous le regard des pairs ; besoin
   d'appartenance. · societe · jeunesse → passage_acte (+, proportionnelle) · pente · structure par âge (à brancher).
8. **Enfance et vie prénatale.** L'adversité précoce marque la réactivité au stress pour la vie, parfois sur plusieurs
   générations ; en partie réversible, d'autant moins qu'on tarde. · corps · passage_acte → enfance (+, hystérésis),
   enfance → stress_chronique (+, décennie, hystérésis), enfance → genes_milieu (±) · aucun calibrable à la semaine ·
   exposition cumulée d'une génération (UCDP par décennie, à brancher).
9. **Gènes en interaction.** Un gène est un potentiel ou une vulnérabilité dont l'effet change de signe selon le milieu.
   · corps · genes_milieu → hormones (±) · — · fermé (aucune trace non intrusive).
10. **Culture et écologie d'origine.** Riziculture et interdépendance, pastoralisme et culture de l'honneur, désert et
    monothéisme ; inégalité et confiance. · ideologie · culture_ecologie → morale (+), culture_ecologie →
    passage_acte (±, seuil : affront public) · — · enquêtes de valeurs (à brancher).
11. **Parentèle et réciprocité.** Aide d'abord aux siens ; donnant-donnant avec pardon ; la réputation permet la
    réciprocité entre inconnus. · societe · reciprocite → treve (+, donnant-donnant) · retard et force · dyades GDELT
    (`dyade:UKR:RUS` → `dyade:RUS:UKR`), en lien avec `banc_reciprocite.py`.
12. **Nous contre eux.** Frontière tracée en un instant sur des marqueurs arbitraires ; une menace extérieure resserre
    le nous ; la frontière s'entretient elle-même ; les camps changent de eux. · psychologique · nous_eux → nous_eux
    (+, saturation), nous_eux → empathie (−), nous_eux → passage_acte (+, seuil), passage_acte → nous_eux (+, boucle
    rancunière) · `seuil`, paire imposée `telegram:tout` ↔ `hostilites:UA` · volume des canaux suivis.
13. **Hiérarchie et obéissance.** Une hiérarchie stable stresse le bas, contestée elle stresse le haut ; l'obéissance
    croît avec la proximité et la légitimité de l'autorité, chute dès qu'un dissident est visible. · statut ·
    hierarchie → hormones (±, seuil), hierarchie → passage_acte (±) · — · proximité d'élection (compte à rebours,
    exclu de la calibration : c'est un calendrier, pas une intensité).
14. **Morale intuitive.** Jugement rapide, justification après ; règles pour les nôtres. · ideologie · morale →
    passage_acte (±) · — · enquêtes d'opinion (à brancher).
15. **Empathie.** Ressentir n'est pas agir ; la victime identifiée mobilise plus que le nombre ; l'empathie se fatigue.
    · psychologique · empathie → passage_acte (−, faible) · — · attention publique (à brancher).
16. **Métaphores et valeurs sacrées.** Le cerveau traite une métaphore de dégoût comme un dégoût réel (vermine,
    souillure → déshumanisation) ; sur une valeur sacrée, une offre matérielle aggrave le refus, un geste symbolique
    peut débloquer. · convention · symboles → nous_eux (+, seuil), symboles → treve (±, seuil) · `seuil` · récits
    suivis (`recit_russe`, `telegram`).
17. **Guerre et paix.** Trêves spontanées entre unités face à face ; hostilité la plus forte loin du front ; contact
    égal et but commun ; le temps efface. · societe · treve → nous_eux (−), treve → passage_acte (−) · retard ·
    ton Goldstein `dyade:RUS:UKR`, contre `hostilites:UA`.
18. **Tout est moyenne.** Presque chaque fait est une moyenne avec une large variation individuelle. · — · inscrit dans
    la déclaration de la fiche : la carte ne vaut que pour des populations.

## Ce qui a été écrit dans le programme (bot 0.10.325)
- `ecosystemes/niveaux.yaml` : nouveau niveau **corps** (rang 3, inertie 0,3), avec ses relations propres.
- `ecosystemes/humain.yaml` : fiche générique, 17 compartiments dans l'ordre des échelles de Sapolsky (instant,
  indices, hormones, stress_chronique, attente, jeunesse, enfance, genes_milieu, culture_ecologie, reciprocite,
  nous_eux, hierarchie, morale, empathie, symboles, passage_acte, treve), 30 relations dont 3 de modulation,
  11 ponts sortants (influences ; « meme » seulement pour la structure par âge) ; 6 ponts entrants ajoutés aux fiches
  climat-extremes, inflation-mondiale, alimentation-mondiale, information-cyber, guerre-levant, russie-ukraine.
- `ecosystemes.py` : clés de relation `module` (de>vers, visant une relation à seuil), `parametres` (valeurs de départ
  à calibrer), `series` (paire de séries imposée pour mesurer le même lieu aux deux bouts), validées.
- `carte.py` : les modulations abaissent le seuil des relations visées (seuil − gain × intensité, plancher 0,5) ; la
  carte lit `registre/calibration.json` (une mesure significative qui concorde remplace force, délai et règle ; une
  mesure de signe contraire marque la relation « contredite » sans la retourner) ; un effet fort arrivé tard n'est
  plus masqué par un effet faible arrivé tôt.
- `calibrer.py` : mesure délai, signe, poids, règle et gain de modulation sur toutes les relations dont les deux bouts
  ont une série ; méthode fixée dans son en-tête avant tout résultat. Comptes à rebours exclus.
- `collecte_fred.py` : série UMCSENT (confiance des ménages) ajoutée.
- Tests : `tests/test_calibrer.py`.

## Limites et critiques connues
- Une partie des expériences de psychologie sociale citées (amorçage, certains effets de l'ocytocine et de la
  testostérone, « épuisement de la volonté ») n'a pas résisté aux tentatives de réplication depuis ; nous n'avons
  retenu que des mécanismes qui se testent sur nos séries agrégées, et ils entrent tous « à vérifier ».
- Les études en neuro-imagerie et en laboratoire portent sur de petits échantillons, souvent d'étudiants occidentaux ;
  le passage à des populations entières est notre hypothèse, pas celle des études.
- Le livre plaide contre le libre arbitre (ch. 16) ; c'est une position philosophique que la carte n'a pas à trancher.
- Les liens écologie → culture (riz et blé, pastoralisme et honneur) sont des corrélations entre sociétés, discutées.
