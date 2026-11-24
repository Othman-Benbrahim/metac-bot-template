# Sondes de l'écosystème (« sonder, percevoir, répondre ») — procédure écrite avant tout branchement

Décisions de l'auteur, 2026-11-24 : 21 h 14 (on ne compare pas le passé avec le même étalon que le présent : c'est une
question de cycle) ; 21 h 22 (« Oui, on peut essayer ») sur trois sondes parallèles à la manière de Snowden ; 21 h 24 :
le sens des ponts ne se décide pas par jugement (« trop subjectif […] ce n'est pas à moi de décider »), il se mesure ;
« Tu peux commencer à les construire ».

Constat qui motive : la couche écosystème calée sur l'avant-2026 poussait dans le bon sens avant 2026 et à contresens en
2026 ; recalée sur 2026 seule, son coefficient vaut 0 (version 1) et −0,1 (version « objet »).

## Principe
Plusieurs petites sondes en parallèle, chacune sans danger si elle échoue (plafond bas), chacune avec son étalon recalé
sur le cycle présent et sa règle d'arrêt écrite ici. Le terrain dit laquelle « prend » ; elle seule est amplifiée.
Les sondes ne s'appliquent qu'aux questions où AUCUNE brique mesurée n'a répondu (pas de double lecture).

## Les trois sondes (sondes.py)
1. **relations** : couche des relations internes (ecosysteme_couche.py) avec les échelles temps, vitesse, espace,
   taille et l'échelle « objet », corrigée : l'objet d'une série météo est le phénomène (chaleur, froid, sécheresse,
   pluie, mousson…) ET le lieu, pas le lieu seul.
2. **ponts** : ponts « influence » entrants dans les compartiments de la question, quand les deux bouts ont une série.
   Sens MESURÉ, jamais décidé : signe de la corrélation des variations mensuelles des deux séries sur les 12 mois
   précédant la date ; retenu si |r| ≥ 0,3 et au moins 8 mois communs, sinon le pont se tait. État de l'amont : z sur
   30 jours (même calcul que la couche) ; échelle « objet » appliquée à la série amont. d = moyenne de signe × g(z).
3. **phase** : cycles décrits dans les fiches (7) dont un compartiment est rattaché à la question ; mois de la « phase
   vulnérable » lus dans leur texte ; d = part des jours de l'horizon qui tombent dans ces mois ; sens = +1 (que
   l'événement arrive). Le signe de l'effet est laissé à l'étalon.

## Étalon glissant (sondes_etat.py)
Pour chaque sonde, k (seul paramètre) est recalculé à chaque passage sur les questions résolues du corpus dont la date
de résolution tombe dans les 182 jours précédents, et que la sonde lit (grille −3 à 3, pas 0,1 ; maximum de
vraisemblance autour de la part de oui hors groupe). k peut être nul ou négatif : c'est le cycle présent qui le dit.

## Application dans le bot
Pour une question sans brique : p_s = σ(logit p + k_s·d_s·sens_s) pour chaque sonde active ; déplacement de chaque
sonde borné à son plafond ; somme des déplacements bornée au plus grand plafond actif. Plafond de départ : 5 points.
Journal scellé : registre/journal-sondes.jsonl (p de base, p_s de chaque sonde, d, k, lecture).

## Règle d'arrêt et d'amplification (e-valeurs, écrite avant le premier branchement)
Pour chaque sonde, sur les questions résolues où elle a joué (dernière prévision publiée de chaque question) :
log E = Σ log( p_s(issue) / p_base(issue) ).
- log E ≤ −ln 20 : la sonde est débranchée (elle ne revient que par décision de l'auteur).
- log E ≥ ln 20 : plafond porté à 10 points ; log E ≥ ln 400 : 15 points.
- Entre les deux : la sonde continue au plafond courant.
Calculé à chaque relevé des issues (workflow « Score du bot alphabet ») ; état dans registre/sondes-etat.json.

## Limites déclarées
Le corpus de résolution récent vient surtout de ForecastBench (questions de marché, de séries, d'actualité) ; les
sondes peuvent rester muettes faute de questions lues sur six mois ; une sonde à k = 0 ne fait rien (c'est voulu).
