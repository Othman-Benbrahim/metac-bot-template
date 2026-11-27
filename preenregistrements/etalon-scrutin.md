# La brique « scrutin » : étalons de l'écosystème électoral (préenregistrement, 2026-11-19, 20 h 25)

Décisions de l'auteur du 2026-11-19 :
- 20 h 09 : chaque écosystème a ses propres variables, à connaître avant de les appliquer ; lire une situation n'est pas forcément la mesurer, surtout sans le bon étalon.
- 20 h 12 : fixer les étalons précisément et tester que la règle s'applique avant de l'inscrire dans une fiche.
- 20 h 17 : la règle doit être une brique réutilisable dans les cas HOMOLOGUES (même structure, et non simple ressemblance : analogie ≠ homologie), et le test doit être reproductible et automatisable.

Essai `etalon_scrutin`. Ombre : rien dans le bot, rien côté Metaculus avant le tournoi.

## 1. La brique (définie par sa structure, pas par sa géographie)

Une question relève de la brique quand sa STRUCTURE est celle d'un scrutin. Le pays, la région ou le nom du candidat ne décident de rien. Classes homologues :

| Classe | Règle du scrutin | Formes de question admises |
|---|---|---|
| S1 | majoritaire à deux tours : > 50 % au premier tour pour gagner, sinon les deux premiers au second tour | gagne ; se qualifie pour le second tour ; finit au rang k au premier tour |
| S2 | majoritaire à un tour (le premier gagne) | gagne ; finit au rang k |
| S3 | primaire ou investiture d'un parti | est investi |

Toute autre forme (sièges à la proportionnelle, coalitions, dates d'annonce) est hors brique : la brique s'abstient, et la question reste à la lecture.

## 2. Étalons (variables propres de l'écosystème)

- **E1 · Règle** : la classe S1, S2 ou S3 et son seuil. Table écrite à la main par pays et par type d'élection (`etalons/scrutins.csv`), sourcée (loi électorale ou page Wikipédia de l'élection).
- **E2 · Sondages** : moyenne des sondages publiés dans les 30 jours qui précèdent la date de la question, lue sur la page Wikipédia « Opinion polling for … » **dans sa version à cette date** (historique des versions, identifiant de version archivé). Sans sondage dans les 30 jours : abstention.
- **E3 · Erreur habituelle** : écart-type de l'erreur sur la part d'un candidat, σ₀ = 2,5 points à la veille du vote (ordre de grandeur de Jennings et Wlezien, 2018), élargi selon le temps restant : σ(t) = σ₀ · √(1 + t / 30), t en jours avant le vote. Fixé ici, jamais ajusté sur les issues.
- **E4 · Temps restant** : jours entre la date de la question et le scrutin (calendrier électoral du registre ou date de la page).

E5 (sortant) et E6 (économie du pays) sont déclarés comme variables de l'écosystème, mais **hors de ce test**. On les teste ensuite, un par un, comme corrections.

## 3. Calcul (déterministe)
Tirages de Monte-Carlo (20 000, graine fixe 0) : part de chaque candidat = moyenne des sondages + erreur normale σ(t), indépendante par candidat, parts renormalisées à 100 % ; on applique la règle E1 et on compte la fréquence de l'événement demandé. Probabilité bornée à [0,02 ; 0,98].

## 4. Reproductibilité et automatisation
- Chaque entrée est archivée au registre : identifiant de version Wikipédia, table extraite en CSV, date. Une seconde exécution sur les mêmes archives doit donner les mêmes probabilités (empreinte SHA-256 publiée).
- Le rattachement d'une question à la brique se fait par règles écrites (formes de question, table des pays), sans modèle de langue. Une question non reconnue est hors brique.

## 5. Test décisif
- **Questions** : toutes les questions électorales résolues de la cohorte des questions de jugement (239 repérées, dont 180 en confirmation), quel que soit le pays.
- **Comparaison** sur les mêmes questions : semblables (p_S, taux de base actuel) contre brique. En descriptif : la carte actuelle.
- **Critère** (risque corrigé d'`essais.py`) : la brique est retenue si la perte log de la brique est plus basse que celle des semblables, avec un intervalle de l'écart entièrement sous 0, sur les questions où la brique ne s'abstient pas. Le taux d'abstention est publié.
- **Homologie** : on publie le résultat par classe (S1, S2, S3) et par région. Une brique qui gagne en Amérique latine mais perd ailleurs, dans la même classe, n'est pas une brique : c'est une analogie.
- Même en cas de succès, l'inscription dans les fiches et le passage dans le bot sont des décisions d'auteur datées, après le tournoi pour le bot.

## Amendement du 2026-11-27 (13 h 05) : relance pour dysfonctionnement avéré, avant tout nouveau score
Le passage de novembre a conclu « trop peu de questions jugées » : 25 questions jugées sur 329, et le critère n'a pas été évalué.

**Cause trouvée sans regarder aucune issue :** 183 archives sur 340 n'ont trouvé aucune page de sondages. Pourtant, le diagnostic en lecture seule du 27/11 (run 45995542185) montre que la recherche de l'API Wikimedia renvoie aujourd'hui la bonne page en première position, par exemple « Opinion polling for the 2026 Brazilian presidential election » ou « Opinion polling for the 46th Canadian federal election ». Les échecs de novembre étaient donc très probablement des refus passagers (429), traités comme « aucune page ».

**Correctif :**
- La collecte fait cinq essais avec une attente croissante, et signale tout échec répété.
- Les archives sans page sont reprises, comme le prévoyait déjà `lire_archives`.

**Inchangé :**
- Le calcul de la brique et le critère, perte logarithmique contre les semblables, avec un intervalle de l'écart entièrement sous 0, publié par classe S1, S2, S3.
- La cohorte : elle comprend désormais aussi les élections tranchées depuis le 19/11.
- Rappel du principe de la matriochka : une classe qui perd (S1 en novembre) n'est pas branchée, même si l'ensemble gagne.

Ce relancement est décidé pour un dysfonctionnement de collecte, pas au vu d'un résultat.

## Résultat de la relance (run 45995971880, 2026-11-27, 13 h 09)
**Ma correction d'abord.** Seuls 10 couples restaient à archiver dans la cohorte (178 questions de 2026). Les 183 archives sans page appartenaient presque toutes aux années d'avant 2026, collectées avec `--tout`, hors de la cohorte du test. L'amendement a donc peu changé la matière. Le vrai frein de la cohorte est ailleurs : la page est lue, mais le sujet n'est pas trouvé dans les tableaux, ou aucun sondage ne date des 30 jours précédents (118 questions).

**Résultats :**
- 342 questions électorales, 260 en confirmation.
- **30 questions jugées** : 9 S2, 14 S3, 7 S1.
- Abstentions : 118 sans sondage du sujet dans les 30 jours, 82 hors forme, 30 sans archive ni tableau.
- Perte : brique 0,380 contre 0,781 pour les semblables. Écart −0,401, intervalle corrigé [−0,829 ; +0,007].
- **Verdict : non tranché, de justesse.** La brique n'est pas branchée.

| Classe | Questions | Brique | Semblables |
|---|---|---|---|
| S1 (deux tours) | 7 | 1,083 | 0,617 |
| S2 (un tour) | 9 | 0,093 | 0,974 |
| S3 (primaires) | 14 | 0,213 | 0,739 |

**Pas de nouveau passage sur ces questions.** Restreindre le critère à S2 et S3 après avoir vu ces chiffres serait un choix fait après coup. Toute suite (critère par classe, lecteur des sujets amélioré) se pré-enregistre maintenant et s'éprouve sur des élections tranchées APRÈS aujourd'hui.
