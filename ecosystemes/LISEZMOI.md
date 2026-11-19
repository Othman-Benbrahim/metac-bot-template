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
    traces:                       # comment on le lit sans rien d'intrusif
      - {source: ..., statut: collecte | a_brancher | fermee | inconnue, fichier: collecte_x.py}
relations:
  - de: compartiment source
    vers: compartiment cible
    effet: "+" | "-" | "0" | "±"  # effet de la source sur la cible
    retour: "+" | "-" | "0" | "±" # effet en retour sur la source ; absent = influence à sens unique (forçage)
    forme: (facultatif) competition | predation | mutualisme | commensalisme | amensalisme | neutralisme | forcage | contrainte | ambivalent
    style: (facultatif, éléments qui se répondent) donnant-donnant | rancunier | conciliant | indifferent | inconnu
    delai: délai typique de transmission
    force: faible | moyenne | forte | inconnue
    coupure: où et quand le lien se coupe
    statut: a_verifier | verifie | conteste
    source: (si vérifié) la source relue
    texte: une phrase
ponts:
  - {depuis: compartiment, vers: autre-theme:compartiment, nature: une phrase}
```
Sans forme écrite, la forme est déduite des deux effets (− / − compétition, + / + mutualisme, + / − prédation,
+ / 0 commensalisme, − / 0 amensalisme, 0 / 0 neutralisme ; sans retour : forçage).
