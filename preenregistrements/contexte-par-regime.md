# Le contexte d'une série selon son régime causal (brouillon de conception, 2026-11-15, 16 h 33)

**Statut : plan, pas encore un pré-enregistrement.** Chaque ligne deviendra un essai quand ses questions existeront
en nombre et que sa source de contexte aura été vérifiée.

## Thèse de l'auteur
« Une série non contextualisée ne donne pas de résultat, car elle ne contient pas le contexte précis qui pourrait
expliquer la raison de la série. Le contexte indique les conditions de la série (l'ambiant). Les règles de causalité
doivent être reliées à ce contexte pour déterminer dans quel sens va influer la série. »

## Ce que les bancs ont déjà montré (2026-11-15)
Sans contexte, rien ne bat B : B autorégressif, saisonnier, récent, Chronos-2 (modèle de fondation). Sur les
températures, B et Chronos-2 font 0,692, le score de pile ou face (0,693). Le contexte « articles de presse » donné au
modèle de langue n'a rien apporté non plus sur les séries (A = B) : ce n'était pas le bon contexte.

## Trois régimes, trois contextes
| Régime | Exemples | Le contexte qui porte la cause | Source gratuite | État |
|---|---|---|---|---|
| Physique | températures Météo-France | état de l'atmosphère, modèles de prévision | Open-Meteo, prévisions archivées avec échéance | **essai `contexte_meteo` ouvert** |
| Macroéconomique | inscriptions au chômage, inflation, PIB, emploi | estimations en temps réel (nowcasts), calendrier des publications, jours fériés et saisons | GDPNow (Fed d'Atlanta), nowcast d'inflation (Fed de Cleveland), calendrier BLS | **en attente** : ~11 questions macro seulement dans les jeux (inscriptions au chômage) ; à reprendre quand elles seront assez nombreuses |
| Marchés | taux, écarts de crédit, changes, indices | l'information publique est déjà dans le prix ; reste l'information **de niche**, peu suivie : signaux faibles, micro-causalités, petits événements à grosses conséquences (ex. commandes de pizzas autour du Pentagone), à trouver par l'OSINT | à chercher indicateur par indicateur | **par induction** : chaque indicateur de niche passe par l'observatoire inductif (`induction.py`, même sens dans 3 lots sur 4) puis par un pré-enregistrement à sens fixé |

## Règles communes (préenregistrements/README.md)
Rasoir d'Ockham avant tout essai ; pas d'extrapolation ; mesure stable ; formes trivialement solubles décrites à part.
Pour les marchés, réserve de l'auteur notée : un signal de niche s'épuise quand il devient connu, et joue surtout
autour d'événements (crises, annonces) plutôt que sur la variation d'une semaine ordinaire.
