# Préenregistrement : observatoire Telegram par les métadonnées (2026-11-18, bot 0.10.250)

Écrit et poussé **avant la première collecte** (aucune donnée Telegram n'existe au registre à cette date).
Décisions d'auteur : principe des métadonnées (2026-11-18 4 h 36) ; observatoire et liste auto-mise à jour (4 h 43).

## Ce qui est recueilli
Métadonnées seulement (collecte_telegram.py) : chaîne, numéro, heure UTC, vues, chaîne relayée, chaînes citées.
Aucun texte. Le pays vient du groupe de la chaîne (liste registre/telegram-chaines.csv), jamais du contenu.
Les chaînes sont partisanes et non vérifiées : on mesure leur **activité**, jamais la vérité de leurs affirmations.

## Groupes jugés et issue
- UKRAINE → pays UCDP : Ukraine, Russie. MOYEN-ORIENT → Israël, Palestine, Liban, Syrie, Iran, Yémen, Irak.
- ASIE et MONDE : décrits seulement, non jugés (UCDP n'y a pas d'issue adaptée aux sujets suivis).
- Issue, chaque jour J et pour chaque groupe : les événements UCDP (Candidate) des pays du groupe sur J+1…J+7
  sont-ils **plus nombreux** que sur J−6…J ? (forme « plus qu'avant » de banc_cr_sources.)
- Référence : B_noyau (classe de référence pondérée adoptée le 2026-11-17), calculée sur les seuls comptes UCDP.

## Signaux (fixés ici, aucun autre ne sera jugé dans cet essai)
Calculés sur les chaînes **actives** du groupe, avec les seules données connues à J (heure ≤ J 23:59 UTC).
1. **rythme** : ln((messages du groupe à J + 1) / (médiane des 28 jours précédents + 1)).
2. **synchronie** : part des chaînes du groupe au-dessus de leur propre médiane sur 28 jours, à J.
3. **horaire** : part des messages du groupe publiés entre 22 h et 5 h (heure de Kyiv pour UKRAINE, de Jérusalem
   pour MOYEN-ORIENT), écart à sa médiane sur 28 jours.
4. **silence** : nombre de chaînes du groupe à 0 message sur 48 h alors que leur médiane sur 28 jours est ≥ 3 par jour.
5. **vues** : ln(médiane des vues des messages de J / médiane des 28 jours précédents). Les vues sont mesurées à des
   âges différents selon les passages : signal le plus fragile, noté comme tel.
Une chaîne entrée par la mise à jour mensuelle ne compte qu'après 28 jours de présence.

## Prévision concurrente
Pour chaque signal s : la même classe de référence pondérée que B_noyau, avec une dimension de plus dans le noyau,
w = max(0,005 ; exp(−½Δz² − ½Δm² − ½Δs²)), s étant standardisé sur l'historique disponible à J. Rien d'autre
n'est ajusté (pas de régression, pas de seuil choisi après coup).

## Calendrier et règle
- Démarrage : premier jour avec 28 jours d'historique Telegram. Jugement : quand **90 jours** d'issues sont connues
  (UCDP Candidate paraît avec environ un mois de retard : jugement vers la fin février 2027 au plus tôt).
- Critère : différence de Brier (signal − B_noyau) sur les deux groupes réunis ; intervalle bootstrap par blocs de
  7 jours (les issues se chevauchent) ; seuil corrigé 0,05/5. Un signal est **retenu en ombre** si la borne haute
  est < 0. Sinon : non démontré, et la carte correspondante garde son statut « non démontrée » pour ce type.
- Puissance : environ 180 issues fortement corrélées ; un effet de l'ordre de −0,01 ne sera pas détectable. Un
  « non démontré » ne vaudra donc pas réfutation ; il sera écrit ainsi.
- Pas d'adoption sans décision datée de l'auteur. Pas de second regard prévu ; s'il en faut un, il sera
  préenregistré avant de regarder les 90 jours suivants.

## Ce qui invaliderait l'essai
- Plus de 30 % des passages en échec (blocage, changement de format des aperçus) : essai déclaré nul, pas jugé.
- Pages pleines fréquentes (plus de 20 messages par jour pour une chaîne) : le rythme de cette chaîne est censuré ;
  elle sera exclue des signaux 1 à 3, liste écrite avant le jugement.
