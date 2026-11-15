# Pré-enregistrement — l'alphabet pour organiser et comparer : classes de référence par signature (2026-11-15)

**Décision d'auteur du 2026-11-15.** L'alphabet ne remplace pas le texte ; il sert à organiser et comparer les
situations. Mesure de cette plus-value : retrouver, parmi les questions déjà résolues, celles qui ont la même signature
de lecture, et s'en servir comme classe de référence.

## Règle (fixée ici, avant tout calcul)
- **Signature** d'une question lue par l'alphabet (registre du banc, `retro.jsonl`) : (carte de l'événement, type
  d'événement, strate de l'événement), tirés du plan.
- **B_signature** : pour une question du jeu J, parmi les questions des jeux ANTÉRIEURS à J ayant la même signature,
  k OUI sur n : B_sig = (k + 10·B) / (n + 10). Le pseudo-compte 10 est un choix d'auteur fixé ici, non ajusté : avec peu
  de cas comparables, B_sig reste près de B ; avec beaucoup, il suit les cas.
- Une ligne par question (la plus ancienne lecture), lecteurs confondus pour la signature (limite déclarée : la
  signature dépend du lecteur).

## Critère
Questions des jeux 2026-10-11 et 2026-10-25 (apprentissage sur les jeux antérieurs), ordre entrelacé entre jeux et
sources. Sur les 100 premières avec au moins un cas comparable : perte log de B_sig inférieure à celle de B, intervalle
de l'écart (bootstrap par blocs « jeu × source ») entièrement sous 0 au niveau corrigé. Ces jeux ont été vus pour
d'autres questions, jamais pour celle-ci. Si le critère tient : l'alphabet a une plus-value mesurée comme organisateur de
la mémoire des cas ; décision d'auteur datée sur son usage pour B.
