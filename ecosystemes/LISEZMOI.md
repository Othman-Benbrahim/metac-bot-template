# Fiches d'écosystèmes

Une fiche par thème (`<theme>.yaml`). Chaque fiche est UN écosystème : un découpage déclaré par un observateur pour un
but, pas L'écosystème. Les compartiments sont propres à chaque thème ; les fiches se relient par des ponts.
`python ecosystemes.py` valide toutes les fiches et assemble le schéma global (registre/ecosystemes-schema.json) et la
liste de travail (registre/ecosystemes-a-faire.md).

## Format
```yaml
theme: identifiant-court          # sert dans les ponts : theme:compartiment
nom: Nom lisible
declaration:                      # obligatoire : un écosystème est un découpage déclaré
  but: pour quelle situation ou quelle question on découpe ainsi
  limites: ce qui est dedans, ce qui est laissé dehors
  observateur: qui découpe, d'où (nos sources, notre point de vue)
  date: AAAA-MM-JJ
  espace: étendue regardée
  temps: calendrier, période, mémoire prise en compte
  vitesse: rythmes regardés (de l'heure au siècle)
  taille: échelles regardées (du micro au macro)
compartiments:
  - id: identifiant
    nom: Nom lisible
    elements: [ce qui compose le compartiment]
    niveau: {espace: ..., temps: ..., vitesse: ..., taille: ...}   # son niveau d'action propre
    acteurs:                      # chacun à SON échelle (taille obligatoire : micro, méso, macro)
      - {nom: ..., taille: micro | méso | macro, espace: ..., vitesse: ...}
    traces:                       # comment on le lit sans rien d'intrusif
      - {source: ..., statut: collecte | a_brancher | fermee | inconnue, fichier: collecte_x.py, adaptateur: "type:paramètres"}
relations:
  - de: compartiment source
    vers: compartiment cible
    effet: "+" | "-" | "0" | "±"  # effet de la source sur la cible
    retour: "+" | "-" | "0" | "±" # effet en retour sur la source ; absent = influence à sens unique (forçage)
    forme: (facultatif) competition | predation | mutualisme | commensalisme | amensalisme | neutralisme | forcage | contrainte | ambivalent
    style: (facultatif, éléments qui se répondent) donnant-donnant | rancunier | conciliant | indifferent | inconnu
    delai: délai typique de transmission
    force: faible | moyenne | forte | inconnue   # ce que la relation transmet d'ordinaire
    intensite:                    # (facultatif) la force varie avec l'intensité du moment
      mesure: ce qui dit l'intensité (une trace : tension, chaleur, rareté, attention…)
      regle: proportionnelle | seuil | saturation | hysteresis | inconnue
    coupure: où et quand le lien se coupe
    statut: a_verifier | verifie | conteste
    source: (si vérifié) la source relue
    texte: une phrase
ponts:
  - {depuis: compartiment, vers: autre-theme:compartiment, nature: une phrase, type: meme | influence | voisinage}
    # meme : les deux fiches lisent le même phénomène (transmission entière, dans les deux sens)
    # influence (par défaut) : CAUSE — le compartiment agit sur l'autre fiche, flèche de la cause vers l'effet
    #   (carte : « cause ») ; partielle, avec retard
    # voisinage : les deux se touchent (partie d'un tout, lieu, calendrier) sans cause établie (carte : « lien de
    #   voisinage ») ; sert à naviguer, ne transmet rien en simulation ; meme s'affiche « même chose »
```
Sans forme écrite, la forme est déduite des deux effets (− / − compétition, + / + mutualisme, + / − prédation,
+ / 0 commensalisme, − / 0 amensalisme, 0 / 0 neutralisme ; sans retour : forçage).

## L'intensité (idée de l'auteur, 2026-11-19)
La force d'une relation n'est pas fixe : plus l'intensité du moment est forte, plus la relation transmet. Exemples :
en temps calme, une menace verbale sur Ormuz bouge à peine les prix ; en pleine crise, la même phrase les fait bondir.
La règle dit comment : proportionnelle (plus d'intensité, plus de transmission), seuil (rien puis tout), saturation
(la transmission plafonne), hystérésis (elle ne redescend pas par le même chemin qu'elle est montée).

## Les quatre axes lus par le code (0.10.317)
`ecosystemes.axes()` lit chaque niveau en grandeurs : taille 1 (micro) à 3 (macro), espace 1 (site) à 5 (monde),
vitesse en jours (temps caractéristique de changement), le temps restant en mots. Une plage quand le texte en donne une
(« micro à macro »). La taille est obligatoire et doit être lisible, pour les compartiments comme pour les acteurs.
Dans la carte vivante (carte.py), un effet qui MONTE d'échelle (du micro vers le macro) s'atténue, sauf relation à
seuil ; un effet qui DESCEND s'impose ; un compartiment lent met plus de temps à montrer un changement.

## Attention aux virgules
Dans une ligne `{ … }`, une virgule sépare les clés : un texte qui contient une virgule doit être entre guillemets
(`texte: "saisies, menaces et mines"`). Le validateur refuse toute clé inconnue, signe d'une virgule non protégée.

## Niveaux d'organisation et facettes (0.10.320, ecosystemes/niveaux.yaml)
Chaque compartiment et chaque acteur peut déclarer son niveau d'organisation (`organisation:` minéral, climat, météo,
eau, sol vivant, végétal, animal, personne, entourage, statut, idéologie, société, économie, technique, géopolitique).
Chaque niveau a ses relations PROPRES et son INERTIE : un effet venu d'un autre niveau n'y passe entier que s'il est
assez fort pour y provoquer un changement (sinon un cinquième). Un acteur public peut apparaître sous trois facettes
(`facette:` personne, statut, idéologie), chacune à son niveau : la personne n'est pas son statut, ni son idéologie.
Le climat (régime de long terme, adaptateur `climat:<point>`) est distinct de la météo (`meteo:<point>`).
