sources: registre/banc-abstention.json, registre/trace-recherche-jugement.json
constantes: 90
# Résultat : règle d'abstention (2026-11-18)

Run 44384289376 ([journal: 50 min]), bot 0.10.292, préenregistrement preenregistrements/abstention.md.
Question : quand la recherche est vide, faut-il laisser le modèle juger « à l'aveugle » (M aveugle, gpt-5-mini) ou
poster simplement le taux des questions semblables (abstention) ? Règle préenregistrée : abstention adoptée SAUF si
le modèle aveugle gagne (intervalle à 90 % entièrement sous zéro).

- 21 lignes sans recherche dans la recherche gelée ([journal: contre 40] avant les correctifs de la recherche), 20 jugées,
  soit 11 questions distinctes seulement, 3 oui.
- Perte log : semblables 0,411 ; M aveugle 0,382 (écart −0,028, intervalle [−0,099 ; +0,053], corrigé
  [−0,149 ; +0,116]). Le modèle aveugle ne gagne pas au sens du critère.
- Verdict préenregistré : abstention ADOPTABLE. Mais les données ne prouvent rien dans un sens ni dans l'autre ;
  elles penchent même légèrement vers le modèle aveugle. Le choix par défaut tient au principe (ne pas laisser juger
  un modèle qui n'a rien lu), pas à la preuve.
- Profil : M aveugle mieux résolu (0,090 contre 0,016) mais moins fiable (0,078 contre 0,012).

Décision : l'abstention reste désactivée (variable ALPHABET_ABSTENTION) ; rien ne change côté Metaculus avant le
tournoi (décision de l'auteur, 2026-11-18, 19 h 40). À reconsidérer après le tournoi, avec plus de questions sans
recherche.
