# Préenregistrement : accord du lecteur de l'alphabet (stabilité et accord entre modèles), sur dossiers complets
2026-11-22, commit 0.10.427, écrit avant tout calcul.

Décision d'auteur du 2026-11-22, 5 h 10 : « on s'occupe du problème des cartes et de l'accord entre codeurs, dans
l'ordre que tu souhaites, et on avance ». Origine : l'audit extérieur du dépôt (22 novembre) et le banc de couverture
du 19 novembre (κ moyen 0,127, mesuré sur des TITRES seuls, avec ancrage mot pour mot). Ce banc-là jugeait une carte
sur une ligne de texte ; l'auteur a jugé ensuite les codeurs « trop instables pour trancher » (19 novembre, 4 h 25).
Ici, on mesure le lecteur RÉELLEMENT employé (les sept notes de la matriochka M, postée au tournoi) sur des DOSSIERS
COMPLETS, et on sépare deux causes de désaccord : un modèle qui se contredit lui-même (instabilité), et deux modèles
qui lisent différemment (pas de langage commun).

## Banc DESCRIPTIF
Aucune issue utilisée pour juger, aucune adoption, rien dans le bot ni dans le skill ; aucune carte ajoutée ni retirée.

## Situations
Les questions Metaculus du banc jugement_alphabet (registre/banc-jugement-alphabet.jsonl) : non exclues, avec les sept
notes et p_M ; dans l'ordre fixé de ce banc (empreinte de l'identifiant) ; les 60 premières dont la recherche gelée
existe (cache/recherche-jugement, restauré du cache des Actions). Aucune recherche neuve : une question sans recherche
gelée est sautée, et le nombre de sautées est rapporté.

## Entrées identiques pour tous les codeurs
Question, critères, contexte, échéance, taux de base, recherche gelée filtrée : exactement la consigne
banc_jugement_alphabet.consigne_notes (sept critères notés de 1 à 4 : CROISSANCE, RÉCIPROCITÉ, HIÉRARCHIE, SEUIL,
CONTRAINTE, PÉRIODICITÉ, PROPORTION). Température 0,2, comme au banc d'origine.

## Codages
- R1 et R2 : gpt-5-mini (Azure), deux appels indépendants sur la même entrée (stabilité test-retest) ;
- X : Claude Haiku 4.5 (Bedrock), un appel (accord entre modèles ; R1 contre X) ;
- pour R1 et R2 seulement, le jugement final (consigne_finale) qui donne p_M : écart de probabilité dû à la seule
  relecture.
Les notes du banc d'origine (R0, gpt-5-mini, 0.10.243) sont comparées à R1 à titre descriptif.

## Mesures (fixées)
1. Par critère et en moyenne : κ pondéré quadratique (notes ordinales 1 à 4) pour R1-R2 (stabilité) et R1-X (accord) ;
   part d'accord exact ; écart absolu moyen des notes.
2. Part des notes « 2 » par codeur et par critère (la consigne impose 2 quand l'information manque : un critère figé
   sur 2 s'accorde avec lui-même sans rien lire).
3. Probabilité : écart absolu moyen |p_M(R1) − p_M(R2)|, part des écarts de plus de 0,10.

## Lecture prévue (seuils de lecture, pas d'adoption)
- Stabilité : κ pondéré moyen R1-R2 d'au moins 0,6 = lecteur stable ; sous 0,4 = instable.
- Accord : κ pondéré moyen R1-X d'au moins 0,4 = lecture commune ; sous 0,2 = pas de langage commun.
- Un critère dont la stabilité est sous 0,4 est signalé à l'auteur comme à reformuler ; aucun changement n'est fait par
  ce banc.
- Si la stabilité est bonne et l'accord faible, le désaccord vient des modèles, pas des cartes ; si la stabilité est
  faible, aucun accord entre modèles ne peut être interprété.

## Suite prévue (préenregistrement séparé, après lecture de ce banc)
Les structures manquantes (compétition, intention, capacité, marché, convention) : on testera d'abord si elles
s'écrivent comme COMPOSITIONS de cartes existantes (décision de l'auteur, 5 h 07 : pas de nouvelle lettre qui ne
relève pas des universaux ; une carte n'entre que si elle prouve son utilité dans le lecteur).

## Limites connues
60 questions, une seule passe par codeur ; deux modèles seulement ; les crédits Bedrock expirent le 23 novembre.
Budget : Azure 3 $, Bedrock 1 $ au plus.
