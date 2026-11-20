# Les questions réelles du bot : cadre sur les quatre axes, écosystème et leviers (2026-11-20)

Demande de l'auteur (19 h 12) : situer chaque question du journal sur les quatre variables (espace, temps, vitesse,
taille), dans son écosystème, pour voir où sont les leviers. Source : `registre/journal-bot.jsonl` et
`registre/journal-autres.jsonl`, 38 questions distinctes, dont 28 se résolvent en 8 à 14 jours. Observation, aucun calcul.

Temps : « conj. » = conjoncturel (un cas, une échéance proche) ; « struct. » = structurel.

## 1. Prix de marché à une date (8 questions, 10 jours)
| Question | Espace | Temps | Vitesse | Taille | Écosystème | Levier |
|---|---|---|---|---|---|---|
| Strategy (MSTR) sous 100 $ le 27/11 | marché mondial | conj., 10 j | minutes | macro | aucune fiche (marchés) | distance au seuil / volatilité ; bitcoin |
| Brent au-dessus de 100 $ le 27/11 | marché mondial | conj., 10 j | minutes | macro | energie-mondiale (prix, contrats Brent), ormuz | distance au seuil / volatilité ; Ormuz, OPEP+ du 29/11 |
| Nasdaq le 27/11 ; Nvidia le 27/11 ; Anthropic le 27/11 | marché mondial | conj., 10 j | minutes | macro | aucune fiche ; sciences-techniques (capitaux) | volatilité ; résultats et annonces dans la fenêtre |
| Laquelle de Nvidia, AMD, Broadcom, Micron monte le plus | marché mondial | conj., 14 j | minutes | macro | aucune fiche | 1 sur N, puis volatilités relatives |
| Nombre d'entreprises à mille milliards le 18/12 | marché mondial | conj., 1 mois | jours | macro | aucune fiche | distance des candidates au seuil |

## 2. Chiffre publié par une institution à une date (10 questions, 10 à 14 jours)
| Question | Espace | Temps | Vitesse | Taille | Écosystème | Levier |
|---|---|---|---|---|---|---|
| Inflation sous-jacente de Tokyo, novembre | Tokyo | conj., publication du 26/11 | mois | macro | inflation-mondiale | dernier chiffre et inertie ; calendrier de publication |
| Cas de rougeole aux États-Unis au 27/11 (CDC) | pays | conj., mise à jour hebdomadaire | semaine | macro | epidemies (lien us_rougeole_decompte_cdc) | dernier total + rythme hebdomadaire ; jour de publication |
| Popularité de Lee Jae-myung (Gallup Korea) | pays | conj., sondage hebdomadaire | semaine | macro | aucune fiche (Corée) | dernière valeur et marge de bruit du sondage |
| Votes par correspondance admis (Correos, Espagne) | pays | conj., élection du 29/11 | jours | macro | aucune fiche (élections Europe) | dernier chiffre publié et rythme |
| Indice de précipitations de la Sierra du Nord au 26/11 | région | conj., cumul saisonnier | jours | méso | climat-extremes ; oceans-et-fleuves | cumul actuel + prévision météo à 7 jours |
| Chiffre d'affaires de Snowflake ; BPA de Salesforce | entreprise | conj., publication trimestrielle | trimestre | méso | aucune fiche (entreprises) | prévisions de l'entreprise, historique des écarts |
| Audience de MasterChef Celebrity (Telefe) | pays | conj., émission du 26/11 | semaine | méso | competitions-culture | audiences des semaines précédentes |
| Remise maximale sur childrensplace.com au Black Friday | entreprise | conj., 27/11 | jour | micro | aucune fiche | remises des années passées ; entreprise en faillite |

## 3. Décision d'une institution dans une séance ou un délai (7 questions, 10 jours à 1 mois)
| Question | Espace | Temps | Vitesse | Taille | Écosystème | Levier |
|---|---|---|---|---|---|---|
| Sénat argentin : primaires PASO le 26/11 | pays | conj., une séance | jour | méso | elections-amerique-latine (Sénat argentin) | ordre du jour ; majorité requise ; qui doit dire oui |
| Conseil des ministres libanais : renvoi au Conseil judiciaire | pays | conj., 12 j | semaine | méso | liban-institutions | consensus entre blocs (droit de blocage) ; séances |
| Banque centrale du Paraguay : date de paiement (banque ueno) | pays | conj., 10 j | semaine | méso | crises-bancaires | annonces de la banque centrale ; calendrier légal |
| État belge et Engie : accord sur le nucléaire avant le 14/12 | pays | conj., 1 mois | mois | méso | energie-mondiale (nucléaire civil) | état des négociations déclaré ; deux parties qui doivent dire oui |
| GPS (Sarawak) : parti du candidat à Bawang Assan | circonscription | conj., jour du dépôt 28/11 | jours | micro | aucune fiche (Malaisie) | 1 sur N, puis sortant et partage des sièges de la coalition |
| Delhi (SIR) : date limite des réclamations | ville | conj., 10 j | jours | méso | aucune fiche (Inde) | calendrier publié par la commission électorale ; prolongations passées |
| Comité des créanciers (Children's Place) : sept membres ou plus | entreprise | conj., 10 j | jours | micro | aucune fiche (faillites) | dépôts au tribunal ; pratique du Trustee |

## 4. Événement à confirmer dans un délai (3 questions)
| Question | Espace | Temps | Vitesse | Taille | Écosystème | Levier |
|---|---|---|---|---|---|---|
| Mexique : les neuf colis radioactifs récupérés avant le 27/11 | région | conj., 3 semaines après le vol | jours | micro | nucleaire-radiologique | annonces des autorités ; délais habituels de récupération |
| Nigeria : une des deux sources Ir-192 récupérée avant le 28/11 | région | conj., 10 j | jours | micro | nucleaire-radiologique | idem |
| Zelensky en personne au Conseil européen des 26-27/11 | ville | conj., une réunion | jours | micro | russie-ukraine, securite-europeenne | agenda annoncé ; habitudes de présence ; sécurité |

## 5. Compétition (1 question)
| Étoile d'or du festival de Marrakech | ville | conj., 29/11 | jour | micro | competitions-culture | 1 sur N (10 films) ; peu d'information |

## 6. Horizon long (9 questions, 2027 à 2029)
| Question | Temps | Écosystème | Levier |
|---|---|---|---|
| Fortune du président (×4) ; popularité nette au 31/12 ; départs parmi 15 hauts responsables | struct. et conj. | politique-americaine | tendance, rythme des départs passés |
| Un pays fondateur quitte l'UE avant 2027 | struct. | securite-europeenne | procédure de l'article 50 (deux ans) : quasi impossible dans le délai |
| Levée de la loi martiale sur les 3/4 de l'Ukraine | struct. + cycle de 90 jours | russie-ukraine (ua_loi_martiale_prolongee_par_la_rada) | cycle de prolongation ; négociation (ru_ua_negociation_reprise) |
| Taux moyen de la dette fédérale ; dépenses fédérales 2028 | struct. | politique-americaine (budget) | trajectoire des taux, projections du CBO |
| Parti vainqueur de la présidentielle 2028 | struct. | politique-americaine | taux de base historiques d'alternance |
| Nouveaux prévisionnistes par jour (méta-question) | struct. | aucune | rythme observé sur Metaculus |

## Où sont les leviers
1. **28 questions sur 38 se résolvent en 8 à 14 jours.** Sur un horizon si court, le statu quo domine : un prix reste
   près de sa valeur, un chiffre publié reste près du précédent, une institution décide rarement hors de son agenda.
2. **Quatre leviers reviennent** :
   - la **distance au seuil rapportée à la volatilité** (prix de marché, chiffres publiés) ;
   - le **calendrier** : date de séance, de publication, de dépôt, de mise à jour ;
   - **qui doit dire oui** (décisions d'institution : majorité, consensus, deux parties) ;
   - **1 sur N** (choix entre candidats, films, entreprises).
3. **Écosystèmes** : la moitié des questions tombe dans des domaines sans fiche (marchés, entreprises, faillites,
   élections hors Amérique latine, Asie). Les fiches géopolitiques ne servent qu'à une poignée de questions.
