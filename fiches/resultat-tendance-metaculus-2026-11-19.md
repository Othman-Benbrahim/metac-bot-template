sources: registre/banc-tendance-metaculus.json
# Résultat : tendance de l'attention GDELT, apprise sur Metaculus 2026, testée sur Metaculus d'avant 2026 (2026-11-19)

Run 44428107762, bot 0.10.304, préenregistrement preenregistrements/tendance-metaculus.md. Aucun appel à un modèle.
Origine : au banc large, la tendance aidait un peu sur les seules questions Metaculus [journal: −0,010, vu après coup,
fiche resultat-attention-gdelt]. Test hors échantillon : β appris sur les 127 questions Metaculus de 2026, appliqué tel
quel aux 109 questions Metaculus d'avant 2026 (67 avec au moins un article GDELT).

- β appris sur 2026 : 0,6.
- Perte log : S 0,5329 ; S ajusté 0,5478. Écart +0,015 (la tendance aggrave).
- Intervalle par question [−0,021 ; +0,057] ; corrigé [−0,041 ; +0,086]. Critère non atteint.
- Profil : oui prévus sous 30 % : 4 → 7 ; fausses alertes 1 → 5. La correction pousse à tort dans les deux sens.
- Rang tendance / issue sur le test : 0,059 (presque nul).

Verdict : non reproduit. Le petit gain vu sur Metaculus 2026 était du bruit d'échantillon. La tendance GDELT est close
sur toutes les plateformes ; elle n'entre pas dans le bot. Essai tendance_metaculus clos en 0.10.306.
