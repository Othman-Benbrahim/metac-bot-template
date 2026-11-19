# Préenregistrement : cinq cartes candidates en ombre, banc de couverture refait sur des situations neuves
2026-11-19, bot 0.10.311, écrit avant tout codage avec ces cartes.

Décision d'auteur du 2026-11-19, 3 h 00 : « mets-les en ombre ; si elles passent, on s'en rendra compte ». Origine :
banc de couverture (fiche resultat-couverture-alphabet-2026-11-19), restes nommés par les deux codeurs. Aucune carte
n'entre dans le bot, dans le skill ni dans la matrice ; elles n'existent que dans ce banc.

## Les cinq définitions (fixées ici, sur le modèle des 16 : définition, puis structure formelle)
- CMP COMPÉTITION : plusieurs parties visent une même ressource ou une même position qui ne peut pas revenir à toutes ;
  ce que l'une obtient réduit ce que les autres peuvent obtenir, selon une règle d'attribution (vote, score, classement,
  combat, enchère) (compétition au sens écologique ; jeux à somme nulle ou constante).
- ITN INTENTION : l'issue dépend du choix discrétionnaire d'un acteur identifiable qui a le pouvoir de la produire ou
  de l'empêcher, et que les règles en place ne dictent pas (théorie de la décision ; choix sous contrainte).
- CAP CAPACITÉ : l'issue dépend des moyens d'un acteur — forces, ressources, compétences, logistique — rapportés à ce
  que l'action exige (rapport moyens / exigences ; fonction de production).
- MAR MARCHÉ : une valeur se forme par la rencontre décentralisée d'offres et de demandes et s'ajuste aux chocs et aux
  anticipations (équilibre offre-demande ; formation des prix).
- CNV CONVENTION : un fait n'existe que parce qu'une collectivité ou une autorité l'accepte ou le déclare (statut,
  titre, statistique officielle, frontière, reconnaissance) ; il peut changer par décision sans que rien de matériel ne
  bouge (faits institutionnels : « X compte comme Y dans le contexte C », Searle 1995).

## Plan
- Situations NEUVES : questions distinctes de 2025 et 2026 du jeu de données, jamais vues par un banc de l'alphabet ni
  par le premier banc de couverture ; tirage au hasard, graine 1, au plus 30 par plateforme.
- Mêmes deux codeurs (gpt-5-mini, Haiku 4.5), même consigne, même ancrage mot pour mot (3 caractères au moins).
  Chaque codeur code CHAQUE situation deux fois, par deux appels indépendants : avec les 16 cartes, puis avec les
  21 (16 + 5 candidates, mêlées dans l'ordre alphabétique des abréviations).

## Lecture (fixée)
Une candidate « passe » si : (a) les deux codeurs l'ancrent chacun dans au moins 5 % des situations ; (b) son κ entre
codeurs est d'au moins 0,2. L'ensemble « passe » si, avec 21 cartes, la couverture monte pour LES DEUX codeurs et le
κ moyen ne baisse pas. Ce qui passe est proposé à l'auteur ; rien n'est ajouté par ce banc. INCERTITUDE est rapportée
à part (vraie par construction sur des questions de prévision). Budget : Azure 2 $, Bedrock 1 $ au plus.
