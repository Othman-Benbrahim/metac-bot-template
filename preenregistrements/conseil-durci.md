# Pré-enregistrement — conseil aux voyageurs durci, violence (bot 0.10.133)

**Décision d'auteur du 2026-11-15 (15 h 31)** : « Je garderai cette variable principalement et officiellement ».
Commité AVANT toute question des jeux à venir.

## Rasoir d'Ockham
1. **Une phrase** : quand le Royaume-Uni durcit son conseil aux voyageurs pour raison de sécurité dans le mois, c'est
   que la situation se dégrade ; la violence du mois suivant est un peu plus probable.
2. **Paramètres** : aucun appris. Force fixée d'avance : +0,5 en logit (30 % → 41 %).
3. **Sens fixé d'avance** : vers le haut, par le bon sens (un conseil se durcit quand le danger monte).
4. **Domaine** : questions ACLED « une fois » de la famille violence (combats, explosions, violences contre les
   civils, morts), conseil mesuré ; ailleurs, B inchangé.
5. **Plus simple ?** : réduite à « durci / inchangé », pas de compte ni de pente (pas d'extrapolation).

## Ce qu'on sait déjà (honnêteté)
Sur les questions déjà vues, l'effet s'annule : moins de violence après un conseil durci dans l'exploration (76
questions), plus dans le test frais (199 questions : 50 % de oui contre 28 %) ; réunies (126 questions de violence
mesurées), le coefficient appris vaut −0,04. Le test dira si le bon sens tient sur des questions nouvelles.

## Questions
Questions ACLED « une fois » des jeux à venir, traitées par `banc_indicateurs_frais.py` à partir de la version
0.10.133 (aucune ligne existante ne compte), ordre entrelacé fixé d'avance.

## Critère (règle d'adoption commune, niveau corrigé ; second regard à 200)
**`conseil_durci`** : sur les 100 premières questions, perte log de B + règle inférieure à celle de B corrigé,
intervalle de l'écart (bootstrap par blocs « jeu ») entièrement sous 0. Seules les questions touchées font varier
l'écart : il faudra plusieurs jeux.
