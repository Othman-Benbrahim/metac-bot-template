sources: registre/banc-gdelt-complement.json
# Résultat : titres GDELT (BigQuery) en complément de la recherche de M (2026-11-18)

Run 44358972727, bot 0.10.280, préenregistrement preenregistrements/gdelt-complement.md. [journal: coût 0,41 $] (gpt-5-mini).

- 75 questions distinctes (celles qui ont des titres GDELT ET des notes de cartes au banc), 16 oui.
- Perte log : SANS titres 0,4634 ; AVEC titres 0,4735. Écart +0,010 (les titres aggravent un peu).
- Intervalle par question [−0,016 ; +0,038] ; corrigé (17 essais) [−0,031 ; +0,056]. Critère non atteint.
- Profil : moins de ratés (oui prévus sous 30 % : 11 → 8 ; fausses alertes 2 → 1), meilleure fiabilité
  (0,031 → 0,008), mais résolution plus faible (0,046 → 0,027) : avec les titres, M sépare moins bien les oui des non.

Verdict : non retenu. Les titres GDELT restent un relais, utilisés seulement quand les autres moteurs ne trouvent rien.
Essai clos en 0.10.282. Correctif au passage : un banc à regard unique n'annonce plus de « second regard ».
