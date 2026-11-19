# Préenregistrement : couverture de l'alphabet sur des situations non vues (idée d'Axiom, corpus CFSG)
2026-11-19, bot 0.10.308, écrit avant toute lecture de ces situations par un modèle.

Décision d'auteur du 2026-11-19, 1 h 46 (« oui, ce serait cool »). Source de l'idée : Axiom, *Beyond the
classification: what the CFSG corpus unlocks* : la valeur d'une bibliothèque se mesure à ce qu'elle porte HORS de
l'ouvrage qui l'a fait naître (30 résultats extérieurs, plus de 99 % du travail déjà dans le corpus, un théorème qui en
porte dix). Question transposée : les 16 cartes suffisent-elles à coder des situations qu'elles n'ont jamais vues, et
lesquelles portent le plus ?

## Banc DESCRIPTIF
Aucune issue utilisée, aucun essai, aucune adoption, rien dans le bot. Il mesure la couverture, pas la prévision.

## Situations
Questions distinctes de 2026 du jeu de données (registre/jugement-questions.jsonl), titres seuls, JAMAIS passées par un
banc de l'alphabet (exclues : toutes celles du banc jugement_alphabet). Tirage au hasard, graine 0, au plus 30 par
plateforme (INFER : toutes, moins de 30), soit environ 100 situations.

## Codage (deux codeurs indépendants, sans se voir)
gpt-5-mini (Azure) et Claude Haiku 4.5 (Bedrock), température 0,2, même consigne : les 16 définitions de cartes
(cartes-index.md, via preselection.textes_cartes), puis la situation. Réponse JSON :
- « cartes » : les cartes dont la STRUCTURE est présente, chacune avec le passage du titre qui l'ancre ;
- « reste » : une structure essentielle à la situation qu'aucune carte ne saisit, ou null ;
- « reste_essentiel » : vrai si, sans ce reste, le codage manque l'essentiel.
Une carte ne compte que si son passage figure mot pour mot dans le titre (cartes_ancrees.citation_verifiee) : pas de
carte par simple résonance. Aucune carte est une réponse admise.

## Mesures (fixées)
1. Couverture : part des situations sans reste essentiel, par codeur et pour les deux à la fois.
2. Charge des cartes : fréquence d'usage ancré de chaque carte ; nombre minimal de cartes qui couvrent 80 % des
   situations codées (glouton) ; cartes jamais utilisées.
3. Accord : κ de Cohen par carte entre les deux codeurs ; Jaccard moyen des ensembles de cartes.
4. Restes : liste brute. Une structure manquante est CANDIDATE à une 17e carte seulement si les deux codeurs la nomment,
   chacun dans au moins 5 % des situations ; la lecture et le regroupement des restes sont faits à la main, puis soumis
   à l'auteur. Aucune carte n'est ajoutée ni retirée par ce banc.
5. Part des situations sans aucune carte ancrée.

## Lecture prévue
Couverture des deux codeurs ≥ 80 % et accord moyen κ ≥ 0,4 : l'alphabet est une bibliothèque réutilisable sur ce
terrain. Couverture < 60 % ou κ < 0,2 : il manque des pièces, ou les cartes sont lues trop différemment pour servir
d'alphabet commun. Entre les deux : à affiner. Seuils de lecture, pas d'adoption.

## Limites connues
Les titres sont courts : une structure réelle mais non écrite dans le titre ne peut pas être ancrée (la couverture
sera sous-estimée, de la même façon pour les deux codeurs). Le terrain reste celui des questions de prévision ; une
extension à des situations d'autres disciplines (l'arbre de la connaissance) viendra ensuite. Budget : Azure 1 $,
Bedrock 1 $ au plus.
