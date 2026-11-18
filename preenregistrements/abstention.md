# Préenregistrement : règle d'abstention (« pas de recherche, pas de jugement du modèle »)
2026-11-18, bot 0.10.263, écrit avant le premier passage de banc_abstention.py.

Décision d'auteur du 2026-11-18, 12 h 57 : les trois règles (interrupteur, abstention, disjoncteur) et le banc de
l'abstention. Source : Khmelinskaya (Q10, sortie « je m'abstiens ») ; trace du 2026-11-18 (21 % des questions du banc
sans aucune recherche, jugées à l'aveugle).

## Questions
Les 309 questions du banc jugement_alphabet dont la recherche gelée est vide (bras_m.recherche_vide : rien, panne,
« aucun résultat », ou moins de 200 caractères utiles). Leur nombre n'est connu qu'au passage.

## Comparaison
M de gpt-5-mini (notes puis jugement final, consignes du banc) avec ce qu'il a réellement (aucune recherche), contre
le taux des questions semblables (p_B du banc, aucune recherche nécessaire).

## Règle (la charge de la preuve est sur le modèle)
- Si le modèle aveugle bat les semblables, intervalle 90 % par blocs entièrement sous zéro : abstention rejetée.
- Sinon : abstention adoptable ; l'allumer (variable du dépôt ALPHABET_ABSTENTION = « oui ») reste une décision datée
  de l'auteur. La règle la plus simple (le code) l'emporte quand le modèle ne prouve pas qu'il fait mieux.
- Pas de second regard : l'échantillon est celui qui existe.

## Rapporté sans être jugé
M du banc d'origine sur ces mêmes questions (il avait peut-être une recherche à l'époque : repère seulement).
