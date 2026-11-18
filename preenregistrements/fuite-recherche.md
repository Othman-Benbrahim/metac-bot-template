# Préenregistrement : fuite des recherches rétrospectives dans nos bancs de jugement
2026-11-18, bot 0.10.296, écrit avant le premier passage de banc_fuite_recherche.py.

Décision d'auteur du 2026-11-18, 22 h 04 (« j'accepte les deux, à appliquer »). Origine : ForecastGym (Tao, Li, Fan,
arXiv 2611.23045) : une recherche refaite après la résolution, même filtrée par date, laisse deviner l'issue pour
jusqu'à 92 % des questions. Nos bancs de jugement (A contre M, variantes, abstention, attention…) reposent tous sur
une recherche rétrospective bornée par date (Exa, TinyFish), gelée ensuite.

## Mesure
- Lignes : celles du banc jugement_alphabet (309 lignes, 119 questions distinctes), recherche gelée identique à celle
  des bras A et M.
- Lecteur : Claude Haiku 4.5 (Bedrock), qui connaît l'issue réelle et la date de la question. Il dit si le texte
  contient une information postérieure à la date de la question qui révèle l'issue ou la laisse fortement deviner,
  et recopie la phrase. Le code vérifie que la phrase figure mot pour mot dans la recherche.
- Fuite = « oui » ET citation vérifiée. « Oui » sans citation vérifiée : compté à part, pas comme fuite.

## Ce qu'on en tire (fixé ici)
- Part des lignes et des questions distinctes avec fuite.
- Perte de A et de M sur les lignes avec fuite et sur les lignes propres ; M contre A recalculé sur les lignes propres
  (intervalle par question), en DESCRIPTIF : la décision de poster M appartient à l'auteur et n'est pas rejugée ici.
- Si au moins 10 % des questions distinctes ont une fuite : tout verdict des bancs de jugement est rapporté aussi sur
  les lignes propres, et la capture en direct (capture-recherche.md) devient la base des bancs futurs.

## Limites connues
Haiku peut manquer une fuite subtile (une phrase qui ne dit pas l'issue mais la rend évidente) ou en voir une qui
n'en est pas une ; la citation vérifiée limite la seconde erreur, pas la première. La part mesurée est donc un
minimum.
