sources: registre/banc-fuite-recherche.json
constantes: 90; 10; 92
# Résultat : fuite des recherches rétrospectives dans le banc du jugement (2026-11-18)

Run 44399511327 ([journal: 20 min]), Claude Haiku 4.5 (Bedrock), préenregistrement preenregistrements/fuite-recherche.md.
Origine : ForecastGym (arXiv 2611.23045, jusqu'à 92 % de questions qui fuient en recherche rétrospective).

## Mesure préenregistrée (Haiku, citation vérifiée par le code)
- 291 lignes lues pour 117 questions distinctes ; fuite citée et vérifiée sur 111 lignes (part 0,381), 58 questions.
- Le seuil préenregistré (10 % des questions) est franchi : les verdicts des bancs de jugement doivent aussi être
  donnés sur les lignes propres.
- Lignes propres (180 lignes, 86 questions, 14 oui) : A 0,3813, M 0,335 ; M contre A écart −0,0463, intervalle 90 %
  [−0,079 ; −0,013], corrigé [−0,099 ; +0,005] : critère nominal seulement.
- Lignes avec fuite : A 0,3826, M 0,3992.

## Relecture stricte (définie APRÈS le premier passage, descriptive)
En lisant les citations, Haiku a souvent compté des faits ANTÉRIEURS à la question (consigne non respectée). Relecture
stricte : une date postérieure à la date de la question doit figurer dans la citation ou l'explication.
- 74 lignes, 47 questions avec une fuite stricte (des pages mises à jour après coup : « Update, September 2026 » sur
  une page de 2025 ; un tableau de prix d'octobre-novembre 2026 ; un article de novembre 2026).
- Questions touchées : A 0,3648, M 0,3593. Questions sans fuite stricte (150 lignes) : A 0,3977, M 0,3597.

## Lecture
1. La fuite est réelle et fréquente dans nos recherches rétrospectives, comme l'annonçait ForecastGym : environ 40 %
   des questions ont au moins une ligne qui contient une information postérieure.
2. Elle n'explique pas l'avance de M sur A : l'avance est plus nette là où il n'y a PAS de fuite (écart
   [calc: 0,3597 - 0,3977 = -0,038] sur les questions sans fuite stricte, presque nul sur les questions touchées). La décision de poster M ne
   repose donc pas sur une fuite.
3. Les modèles ne semblent pas exploiter les fuites : les pertes ne sont pas meilleures sur les lignes qui fuient.
4. Conséquence : les bancs futurs s'appuieront sur la capture en direct (preenregistrements/capture-recherche.md) ;
   pour les bancs rétrospectifs, la relecture des fuites devient une étape du protocole.
