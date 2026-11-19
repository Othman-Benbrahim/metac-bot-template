sources: registre/banc-couverture-alphabet.json, registre/couverture-alphabet-restes-regroupes.json
constantes: 16; 80; 60; 0,4; 0,2
# Résultat : couverture de l'alphabet sur des situations non vues (idée Axiom CFSG) (2026-11-19)

Run 44433995614, bot 0.10.310, préenregistrement preenregistrements/couverture-alphabet.md. Descriptif, rien dans le
bot. 99 titres de questions de 2026 jamais vus par un banc de l'alphabet, codés par gpt-5-mini et Claude Haiku 4.5
sans qu'ils se voient ; une carte ne compte que si un passage du titre l'ancre mot pour mot. [journal: coût 0,53 $
Azure et 0,20 $ Bedrock].

## Chiffres
- Couverture (aucun reste essentiel) : gpt 26,3 % ; Haiku 4 % ; les deux à la fois 3 %.
- Cartes ancrées par situation : gpt 4,63 ; Haiku 2,57. Aucune situation sans carte.
- Charge : INCERTITUDE est ancrée presque partout (gpt 96, Haiku 93 sur 99) : sur des questions de prévision elle est
  vraie par construction et ne discrimine rien. Une seule carte suffit donc à « couvrir » 80 % : la mesure est
  écrasée par INC. Ensuite gpt : CONTRAINTE 76, HIÉRARCHIE 58, PÉRIODICITÉ 51 ; Haiku : SEUIL 69, CONTRAINTE 55.
- Jamais utilisée : RÉSONANCE (par les deux). Haiku n'emploie que 11 des 16 cartes.
- Accord entre codeurs : κ moyen 0,127 ; Jaccard moyen 0,382. Le plus haut : CROISSANCE 0,373, CONTRAINTE 0,334.

## Lecture préenregistrée
Couverture sous 60 % et κ sous 0,2 : « il manque des pièces, ou les cartes sont lues trop différemment pour servir
d'alphabet commun ». Les deux sont vrais ici. C'est le résultat le plus net de la nuit contre l'alphabet tel qu'il est.

## Les restes (regroupés à la main APRÈS lecture, par mots-clés ; descriptif)
Cinq structures manquantes passent la règle (chaque codeur dans au moins 5 % des situations) :
1. **Compétition, rivalité, jeu stratégique** (élections, sport, prix, dissuasion) : gpt 20, Haiku 40, les deux 14.
   De loin la première. L'alphabet a la RÉCIPROCITÉ et la COMMUNAUTÉ, mais aucune carte pour l'affrontement.
2. **Intention, décision discrétionnaire d'un acteur** : gpt 10, Haiku 23.
3. **Capacité** (militaire, technique, logistique) : gpt 7, Haiku 12.
4. **Marché, prix, offre et demande** : gpt 9, Haiku 7.
5. **Convention et mesure** (statistique officielle, légitimité, définition, attribution) : gpt 5, Haiku 11.
Le regroupement par mots-clés est grossier ; il est écrit après lecture, donc indicatif.

## Limites
Les titres sont courts ; le jeu est riche en élections et en sport (Polymarket, Manifold), ce qui gonfle la
compétition. Un seul tirage.

## Ce qui est soumis à l'auteur (aucune carte ajoutée par ce banc)
Une 17e carte candidate : la COMPÉTITION (rivalité pour une ressource ou une position, à somme nulle ou non). En
écologie, c'est l'une des interactions fondamentales entre éléments, à côté de la prédation et du mutualisme : le lien
entre ce banc et la carte des interrelations est direct. Les candidates 2 et 5 rejoignent les remarques de l'auteur sur
la personne qui décide et sur les statuts conventionnels.
