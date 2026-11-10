# Alphabet situationnel — Sources françaises par thème et par strate

> Version : 0.7.63

> Où trouver, pour une situation française, les **faits** qui ancrent une carte (A5), la **source de
> résolution** d'une prévision (S1) et les **séries chiffrées** qui servent de grandeur à « s'intensifie »
> ou de fréquence externe (`--references`). Charger ce fichier quand la situation est française et
> que l'on cherche une source, pas pour lire une situation.
>
> **Origine.** Adapté du projet EnVrai? (fact-checking des débats politiques français),
> `docs/puits.md` et `backend/src/sensors/catalogue.ts`, © 2026 envrai, licence MIT (notice
> reproduite dans `LICENCES-TIERS.md`). Les accès marqués ✓ y ont été vérifiés le 25/10/2026 sur la
> documentation officielle, ceux marqués ~ restent à confirmer. Les lignes marquées **[ajout]** ne
> viennent pas d'EnVrai et restent à vérifier avant usage.

---

## 1. Règles de choix d'une source

1. **Producteur officiel du domaine d'abord**, puis sources harmonisées (Eurostat, OCDE) dès qu'une
   comparaison entre pays est en jeu : seules elles garantissent des périmètres comparables.
2. **Ordre de préférence par nature** : texte officiel (Journal officiel, Légifrance, EUR-Lex) >
   donnée officielle (INSEE, Eurostat, OCDE, RTE) > vérification publiée (AFP Factuel, Les Décodeurs,
   CheckNews) > publication scientifique > presse > encyclopédie (Wikipédia, Wikidata) > agrégateur
   (GDELT). Ordre seulement : aucun poids chiffré n'est repris, ceux d'EnVrai étant déclarés non
   calibrés par leurs auteurs.
3. **Une dépêche reprise par plusieurs titres est une seule source.** Plusieurs articles qui s'appuient
   sur un même communiqué ne s'additionnent pas (A5, A7).
4. **Pour une résolution (S1)**, choisir une source qui publie la grandeur du marqueur local, à une date
   connue, et **la garder jusqu'à l'échéance** : changer de source en cours de route change la
   grandeur mesurée. Un comptage contesté (manifestants : ministère de l'Intérieur contre
   organisateurs) se résout sur **une** des deux séries, nommée à l'avance.
5. **Un document n'est pas une série.** Un rapport en PDF (Cour des comptes, COR, Haut Conseil pour le
   climat) peut ancrer un fait daté ; il ne fournit pas de fréquence de référence.
6. **Chercher sans présupposer** (0.7.2, `protocole.md` A7) : requêtes sur le phénomène, l'objet et la
   période, pas sur le nom d'une carte ; une requête d'observation, une de discrimination, une de
   contradiction ; conserver la requête neutre avant toute reformulation. Un document pertinent qui
   contredit la lecture reste au dossier.

---

## 2. Politique intérieure (strate 13) et droit public (strate 8)

| Besoin | Sources | Accès | Strate |
|---|---|---|---|
| votes nominatifs, scrutins, amendements, dossiers législatifs, motions | **Assemblée nationale** (`data.assemblee-nationale.fr`), **Sénat** (open data, relayé sur data.gouv.fr) ; pas d'API REST officielle à l'Assemblée | `FICH` ✓ | 13 |
| élus et mandats | **Répertoire national des élus** (data.gouv.fr), Wikidata | `TAB` ✓ · `API` ✓ | 13 |
| résultats électoraux | ministère de l'Intérieur | `FICH` | 13 |
| financement des partis, déclarations des élus | CNCCFP, HATVP | `TAB` HATVP ✓ | 13 |
| chronologie des réformes, « qui a fait quoi, quand » | vie-publique.fr, Légifrance (dates des lois), votes AN, Sénat et Parlement européen | `SCRP` vie-publique · `API+` Légifrance ✓ | 13, 8 |
| textes en vigueur, décrets, ordonnances | **Légifrance** et **Judilibre** via PISTE (une inscription, un jeton) | `API+` ✓ | 8 |
| décisions sur la constitutionnalité des lois | Conseil constitutionnel | `SCRP` | 8 |
| couvre-feux, interdictions de manifester, arrêtés de police | **[ajout]** recueils des actes administratifs des préfectures ; communiqués préfectoraux | `PDF`/`SCRP` | 8 |
| comptage des manifestations | **[ajout]** ministère de l'Intérieur et organisateurs, deux séries distinctes (règle 4) | communiqués | 13 |
| sondages publiés | **[ajout]** notices de la Commission des sondages | `SCRP` | 13 (fait sur la mesure publiée) |
| fact-checks déjà publiés | **Google Fact Check Tools** (ClaimReview), clé API | `API+` ✓ | toute strate |

---

## 3. Thèmes de débat → strates → sources

Volumes relevés par EnVrai sur 29 débats politiques français (4 713 affirmations) : ils indiquent les
thèmes où une situation politique française a le plus de chances de se jouer.

| Thème | Strate(s) | Sources principales | Accès |
|---|---|---|---|
| institutions (442) | 13, 8 | Assemblée nationale, Sénat, RNE, résultats (Intérieur), Conseil constitutionnel, CNCCFP, Wikidata | `FICH` ✓ · `TAB` ✓ · `API` ✓ |
| fiscalité (359) | 6, 8 | DGFiP, annexe « Voies et moyens » du PLF, Conseil des prélèvements obligatoires, barèmes IPP, OpenFisca, OCDE, Eurostat `gov_10a_taxag` | `SDMX` ✓ · `ODS` ✓ · `PDF` |
| Europe (291) | 7, 8 | HowTheyVote.eu, open data du Parlement européen, EUR-Lex, budget de l'UE, BCE, Eurostat | `FICH` ✓ · `API` ✓ · `SDMX` ✓ |
| international (278) | 7 | Wikidata, ONU, CPI, presse, fact-checks publiés | `API` ✓ · `PDF`/`SCRP` |
| immigration (277) | 13, 8 | DGEF (ministère de l'Intérieur), OFPRA, INSEE, Eurostat `migr_*`, OIM, Frontex | `SDMX` ✓ · `TAB` ✓ · `PDF` |
| énergie (243) | 10, 6 | RTE eCO2mix et ODRÉ, CRE, SDES, Eurostat `nrg_*`, prix des carburants | `ODS` ✓ · `SDMX` ✓ · `TAB` ✓ |
| sécurité (211) | 8, 13 | SSMSI (Interstats), enquête de victimation, ministère de l'Intérieur | `TAB` ✓ · `PDF` |
| éducation (196) | 5, 9 | DEPP, OCDE (PISA), Eurostat, ministère de l'Enseignement supérieur | `ODS` ✓ · `SDMX` ✓ |
| bilan d'un gouvernement (169) | 13, 8 | vie-publique.fr, Légifrance, votes AN, Sénat et Parlement européen | `API+` ✓ · `FICH` ✓ |
| emploi (163) | 6 | INSEE (chômage BIT), DARES, France Travail, Eurostat `une_rt_a` | `SDMX` ✓ · `API+` ✓ |
| justice (159) | 8 | SDSE, statistiques pénitentiaires, CEPEJ, Judilibre, Légifrance | `API+` ✓ · `PDF` |
| retraites (153) | 6, 8 | COR, DREES, CNAV, OCDE | `ODS` ✓ · `SDMX` ✓ · `PDF` |
| santé (150) | 2, 6 | DREES, Assurance maladie, ATIH, Santé publique France, OCDE | `ODS` ✓ · `SDMX` ✓ |
| économie (127) | 6 | INSEE, Banque de France (Webstat), Eurostat, FMI | `SDMX` ✓ · `API+` ✓ |
| dette et déficit (122) | 6 | INSEE, Agence France Trésor, Banque de France, Eurostat `gov_10dd_edpt1`, BCE | `SDMX` ✓ · `API+` ✓ |
| défense (117) | 7 | SIPRI, ministère des Armées, OTAN, Légifrance (LPM) | `FICH` ✓ · `PDF` |
| protection sociale (107) | 6, 8 | DREES, CAF, URSSAF, Commission des comptes de la Sécurité sociale, Cour des comptes | `ODS` ✓ · `PDF` |
| laïcité et religion (85) | 9, 8 | INED et INSEE (TeO), Légifrance, Conseil d'État | `API+` ✓ · `PDF` |
| climat et environnement (84) | 11 | CITEPA, Haut Conseil pour le climat, SDES, AEE, Eurostat `env_air_gge` | `SDMX` ✓ · `PDF` |
| territoires (59) | 13, 6 | INSEE (populations légales), Observatoire des territoires, OFGL, IEDOM | `ODS` ✓ · `API+` ✓ |

Les autres thèmes d'EnVrai (salaires, travail, entreprises, industrie, dépense publique, agriculture,
logement, pauvreté, transports, culture et médias, recherche, numérique) relèvent des strates 6, 9 ou
10 et de producteurs du même type (INSEE, DARES, SDES, Eurostat).

---

## 4. Voies d'accès

| Code | Famille | Points d'entrée principaux |
|---|---|---|
| `SDMX` | statistiques harmonisées | Eurostat (sans clé), OCDE (sans clé ; l'ordre des dimensions change d'un flux à l'autre), INSEE Melodi (compte), Banque de France Webstat (clé) ; **DBnomics** les réunit derrière une seule requête |
| `ODS` | portails Opendatasoft (API Explore v2.1) | ODRÉ, data.economie, DREES, DEPP, Ens. sup., CAF, URSSAF, Arcep, SNCF, data.culture, Observatoire des territoires, OFGL |
| `TAB` | data.gouv.fr, API tabulaire (beta) | interroge l'intérieur des fichiers publiés (SSMSI, RNE, HATVP, DVF, Sitadel, RPLS, ONISR, DGEF, carburants) |
| `API+` | PISTE (DILA) | Légifrance, Judilibre |
| `API` | SPARQL | Wikidata, EUR-Lex (Cellar) |
| `FICH` | fichiers en masse | Assemblée nationale, Sénat, HowTheyVote, SIPRI |
| `PDF` | documents | Cour des comptes, COR, HCC, CITEPA, OFPRA, Agreste, CRE |
| `SCRP` | pages HTML seulement | à éviter : fragile |

---

## 5. Séries chiffrées : grandeurs pour « s'intensifie » et fréquences externes

Une série officielle donne la grandeur, l'unité et les dates exigées par une résolution de
`s'intensifie` (`graphe.md` §2.2). Toutes celles-ci sont des séries Eurostat, harmonisées.

| Grandeur | Jeu Eurostat | Unité | Strate |
|---|---|---|---|
| taux de chômage au sens du BIT | `une_rt_a` | % | 6 |
| taux d'emploi des 20-64 ans | `lfsi_emp_a` | % | 6 |
| inflation annuelle (IPCH) | `prc_hicp_aind` | % | 6 |
| croissance du PIB en volume | `tec00115` | % | 6 |
| dette publique brute (% du PIB) | `gov_10dd_edpt1` | % | 6 |
| capacité ou besoin de financement des administrations | `gov_10dd_edpt1` | % du PIB | 6 |
| recettes fiscales et sociales (% du PIB) | `gov_10a_taxag` | % | 6 |
| population au 1er janvier | `demo_gind` | personnes | 2 |
| premiers titres de séjour délivrés | `migr_resfirst` | personnes | 13, 8 |
| demandes d'asile (primo-demandeurs) | `migr_asyappctza` | personnes | 13, 8 |
| part des renouvelables dans la consommation finale | `nrg_ind_ren` | % | 10 |
| émissions nettes de gaz à effet de serre | `env_air_gge` | unité de la série, à lire avant usage | 11 |
| dépenses courantes de santé (% du PIB) | `hlth_sha11_hf` | % | 6 |
| dépenses publiques d'éducation (% du PIB) | `gov_10a_exp` | % | 6 |
| taux de risque de pauvreté | `ilc_li02` | % | 6 |

**Avant de faire dire quelque chose à une série** (0.7.2) : qu'est-ce qui est compté (une série
« engagements » peut mêler annonces, autorisations et réalisations) ; unité ; période et date de
publication (disponible à la date d'information ?) ; périmètre géographique et institutionnel, et ses
changements ; traitement des valeurs manquantes (un zéro n'est pas une absence de donnée) ; niveau
d'agrégation ; révisions ultérieures. Lire la notice et quelques valeurs avant d'ancrer un marqueur
ou de fixer une résolution. Une requête ou un calcul qui s'exécute sans erreur peut répondre à une
autre question.

Ces séries sont **annuelles** : elles conviennent à une fenêtre d'un an, pas à une semaine. Pour une
crise d'ordre public à l'horizon de quelques jours, la grandeur se construit à partir de comptages
publiés et datés, définis avant l'échéance (exemple 11 : communes sous couvre-feu, interpellations
d'une journée d'action selon le ministère de l'Intérieur).
