sources: registre/banc-credibilite.json, registre/banc-acteur-nomme.json
constantes: 90; 30; 0,693
# Résultat : crédibilité par catégorie d'acteurs (2026-11-18)

Run 44373402637, bot 0.10.286, préenregistrement preenregistrements/credibilite-acteurs.md. Aucun modèle, coût nul.
Piste « confiance » de la confrontation Complex Systems Frameworks.

- 163 questions distinctes de 2026 dont l'acteur est reconnu (58 oui).
- Perte log : R1 (forme × horizon) 0,818 ; S (semblables) 0,771 ; C (catégorie d'acteur × genre d'acte) 0,736.
- C contre R1 : écart −0,082, intervalle 90 % [−0,155 ; −0,004] (sous zéro), corrigé (18 essais) [−0,211 ; +0,045] :
  critère NOMINAL seulement. C contre S : −0,035, non atteint. Essai clos, non adopté.

## Lecture
Le gain est un gain de CALIBRAGE, pas de discrimination : fiabilité 0,055 (R1) → 0,029 (C), résolution 0,007 →
0,008. Les questions qui nomment un acteur se résolvent OUI plus souvent (36 %) que ne le dit le taux de base général
(R1 rate 54 oui sous 30 %, C 41). C ne sépare pas mieux les acteurs crédibles des autres ; il corrige un niveau.
Les trois restent pires que pile ou face (0,693) sur ce sous-ensemble.
Cellules (descriptif, petits nombres) : exécutif ~47 % de oui, parlement/tribunal 37 %, entreprise 36 %, banque
centrale 39 % ; « annonce » plus rare que « acte ».

## Suite : « la question nomme un acteur », testée sur 2025 — NON reproduite
Préenregistrement acteur-nomme.md (idée née des données de 2026, donc jugée sur 2025), run 44374695099 :
- 174 questions distinctes de 2025 avec acteur : N 0,463 contre R1 0,443 (PIRE, +0,020 ; intervalle corrigé
  [−0,018 ; +0,057]) ; S 0,439. Toutes questions de 2025 (863) : +0,002.
- En 2025, ces questions se résolvent OUI à 17 % seulement (36 % en 2026). L'effet vu en 2026 tenait à la période
  (composition des questions de 2026), pas au fait de nommer un acteur. Essai clos.
- Leçon de méthode confirmée : une idée trouvée en regardant les données doit être rejugée ailleurs ; ici elle
  s'effondre.
