# Graphe des types (ontologie, étape 1)

Tiré tel quel des règles coutumières : un type de situation mène à un type d'événement par une règle. Rien n'est inventé ni fusionné.

- 58 types de situation, 60 types d'événement, 60 règles reliées
- 29 manques, 4 doublons probables (à trancher par l'auteur)

## Doublons probables (formulations proches)

- « élection américaine à venir, avec des sondages publiés » / « élection nationale à venir, avec des sondages publiés » (0.9) — règles ['us_erreur_sondages_par_echelle'] / ['us_erreur_selon_temps_restant', 'sondages_erreur_comparee']
- « chef d'État ou de gouvernement au pouvoir » / « ancien chef d'État ou de gouvernement sorti du pouvoir » (0.84) — règles ['chefs_d_etat_sortie_irreguliere'] / ['anciens_dirigeants_sort']
- « résultat d'une élection américaine prévu d'après les sondages » / « résultat d'une élection nationale prévu d'après les sondages » (0.91) — règles ['us_erreur_sondages_par_echelle'] / ['sondages_erreur_comparee']
- « résultat d'une élection nationale prévu d'après les sondages, selon le temps restant avant le vote » / « résultat d'une élection nationale prévu d'après les sondages » (0.76) — règles ['us_erreur_selon_temps_restant'] / ['sondages_erreur_comparee']

## Manques

- us_erreur_primaires_d_etat : situation ou événement non écrit (statut absence)
- regimes_fermes_inertie : situation ou événement non écrit (statut auteur)
- regimes_fermes_contestation : aucun compartiment : la situation ne peut pas être reconnue dans les situations observées (statut source)
- afrique_limites_de_mandat : aucun compartiment : la situation ne peut pas être reconnue dans les situations observées (statut source)
- afrique_reelection_sortants : situation ou événement non écrit (statut absence)
- sondages_erreur_comparee : aucun compartiment : la situation ne peut pas être reconnue dans les situations observées (statut source)
- france_legislatives : aucun compartiment : la situation ne peut pas être reconnue dans les situations observées (statut source)
- seuils_parlements_nationaux_europe : aucun compartiment : la situation ne peut pas être reconnue dans les situations observées (statut source)
- seuils_elections_europeennes : aucun compartiment : la situation ne peut pas être reconnue dans les situations observées (statut source)
- ue_majorite_qualifiee : aucun compartiment : la situation ne peut pas être reconnue dans les situations observées (statut source)
- ue_sanctions_russie : aucun compartiment : la situation ne peut pas être reconnue dans les situations observées (statut source)
- europe_formation_gouvernement : aucun compartiment : la situation ne peut pas être reconnue dans les situations observées (statut source)
- voix_vers_sieges : aucun compartiment : la situation ne peut pas être reconnue dans les situations observées (statut source)
- afrique_lecture_auteur : situation ou événement non écrit (statut auteur)
- afrique_frontieres_coloniales : aucun compartiment : la situation ne peut pas être reconnue dans les situations observées (statut source)
- afrique_mines_conflits : aucun compartiment : la situation ne peut pas être reconnue dans les situations observées (statut source)
- afrique_flux_financiers_illicites : aucun compartiment : la situation ne peut pas être reconnue dans les situations observées (statut source)
- presidentielles_mode_de_scrutin : aucun compartiment : la situation ne peut pas être reconnue dans les situations observées (statut source)
- indonesie_presidentielle : aucun compartiment : la situation ne peut pas être reconnue dans les situations observées (statut source)
- japon_chambre_basse : aucun compartiment : la situation ne peut pas être reconnue dans les situations observées (statut source)
- australie_vote_preferentiel : aucun compartiment : la situation ne peut pas être reconnue dans les situations observées (statut source)
- inde_scrutin_uninominal : aucun compartiment : la situation ne peut pas être reconnue dans les situations observées (statut source)
- chine_maintien : situation ou événement non écrit (statut absence)
- onu_conseil_securite_vote : aucun compartiment : la situation ne peut pas être reconnue dans les situations observées (statut source)
- second_tour_retournement : aucun compartiment : la situation ne peut pas être reconnue dans les situations observées (statut source)
- parlements_mode_de_scrutin : aucun compartiment : la situation ne peut pas être reconnue dans les situations observées (statut source)
- bresil_gouverneurs_senat : aucun compartiment : la situation ne peut pas être reconnue dans les situations observées (statut source)
- erreur_infranationale_mesuree : situation ou événement non écrit (statut absence)
- papes_voyages : aucun compartiment : la situation ne peut pas être reconnue dans les situations observées (statut source)

## Arêtes

| type de situation | → type d'événement | règle | structure | compartiments |
|---|---|---|---|---|
| campagne présidentielle américaine avant le vote du collège électoral | issue de l'élection présidentielle américaine (collège électoral) | us_president_college | course | politique-americaine:regles_electorales |
| primaire américaine en cours dans un État qui prévoit un second tour | issue d'une primaire américaine qui prévoit un second tour | us_primaires_second_tour | course | politique-americaine:regles_electorales |
| primaire non partisane ou scrutin préférentiel prévu dans un État américain | issue d'une primaire non partisane ou d'un vote préférentiel dans un État américain | us_primaires_systemes_speciaux | course | politique-americaine:regles_electorales |
| élection américaine à venir, avec des sondages publiés | résultat d'une élection américaine prévu d'après les sondages | us_erreur_sondages_par_echelle | course | politique-americaine:elections |
| élection nationale à venir, avec des sondages publiés | résultat d'une élection nationale prévu d'après les sondages, selon le temps restant avant le vote | us_erreur_selon_temps_restant | course | politique-americaine:elections, calendriers-echeances:elections |
| membre sortant du Congrès américain candidat à sa réélection | réélection d'un sortant au Congrès américain | us_avantage_sortant_congres | maintien | politique-americaine:elections |
| campagne de contestation non violente en cours contre un régime | succès d'une campagne de contestation non violente qui vise un changement de régime | regimes_fermes_contestation | evenement_rare |  |
| dirigeant africain au pouvoir face à une limite de mandat | maintien au pouvoir d'un dirigeant africain au-delà des limites de mandat | afrique_limites_de_mandat | maintien |  |
| élection nationale à venir, avec des sondages publiés | résultat d'une élection nationale prévu d'après les sondages | sondages_erreur_comparee | course |  |
| élections législatives françaises convoquées | élection d'un député ou issue des élections législatives françaises | france_legislatives | course |  |
| élections législatives à venir dans un pays européen | entrée d'un parti au parlement national ou répartition des sièges, dans un pays européen | seuils_parlements_nationaux_europe | course |  |
| élections européennes à venir | sièges obtenus par une liste aux élections européennes | seuils_elections_europeennes | course |  |
| proposition soumise au vote du Conseil de l'Union européenne | adoption d'une décision par le Conseil de l'Union européenne | ue_majorite_qualifiee | procedure |  |
| sanctions de l'Union européenne contre la Russie en vigueur ou proposées | adoption ou renouvellement des sanctions de l'Union européenne contre la Russie | ue_sanctions_russie | procedure |  |
| élections législatives tenues ou prévues dans une démocratie parlementaire | formation d'un gouvernement après des législatives dans une démocratie parlementaire | europe_formation_gouvernement | procedure |  |
| élection législative à venir | conversion des voix en sièges dans une élection législative | voix_vers_sieges | course |  |
| territoire ethnique africain coupé ou non par une frontière coloniale | violence politique dans un territoire ethnique africain | afrique_frontieres_coloniales | evenement_rare |  |
| zone minière africaine face à une variation des prix des minerais | conflit local dans une zone minière africaine | afrique_mines_conflits | evenement_rare |  |
| économies africaines (flux financiers mesurés sur plusieurs années) | montant des sorties financières illicites d'Afrique | afrique_flux_financiers_illicites | contexte |  |
| élection présidentielle prévue ou en cours | déroulement ou issue d'une élection présidentielle (à un ou deux tours) | presidentielles_mode_de_scrutin | course |  |
| élection présidentielle indonésienne prévue | issue de l'élection présidentielle indonésienne | indonesie_presidentielle | course |  |
| élection de la Chambre des représentants du Japon prévue | majorité à la Chambre des représentants du Japon | japon_chambre_basse | course |  |
| élection fédérale australienne prévue | élection d'un député ou majorité à la Chambre des représentants australienne | australie_vote_preferentiel | course |  |
| élection de la Lok Sabha prévue | élection d'un député ou majorité à la Lok Sabha | inde_scrutin_uninominal | course |  |
| texte de loi ou nomination soumis au Sénat américain | adoption d'une loi ou confirmation d'une nomination par le Sénat américain | us_senat_cloture | procedure | politique-americaine:congres |
| Congrès américain en session | nombre de lois adoptées par le Congrès américain | us_congres_productivite | procedure | politique-americaine:congres |
| projet de résolution soumis au Conseil de sécurité de l'ONU | adoption d'une résolution par le Conseil de sécurité de l'ONU | onu_conseil_securite_vote | procedure |  |
| pays exposé à une tentative de coup d'État (taux mondial ou régional) | tentative ou réussite d'un coup d'État | coups_d_etat_frequence | evenement_rare | humain:hierarchie |
| chef d'État ou de gouvernement au pouvoir | départ forcé (coup, révolte, assassinat) ou maintien au pouvoir d'un chef d'État ou de gouvernement | chefs_d_etat_sortie_irreguliere | maintien | humain:hierarchie |
| présidentielle à deux tours dont le premier tour est connu | vainqueur du second tour d'une présidentielle à deux tours | second_tour_retournement | course |  |
| élection législative à venir | issue d'une élection législative selon son mode de scrutin | parlements_mode_de_scrutin | course |  |
| élections brésiliennes des gouverneurs ou des sénateurs prévues | élection d'un gouverneur ou d'un sénateur au Brésil | bresil_gouverneurs_senat | course |  |
| politique monétaire américaine entre deux réunions du FOMC | décision de taux de la Réserve fédérale américaine | us_fed_calendrier | procedure | politique-americaine:reserve_federale, calendriers-echeances:banques_centrales |
| affaire ou pourvoi pendant devant la Cour suprême américaine | décision, ordonnance ou acceptation d'un pourvoi par la Cour suprême américaine | us_cour_supreme_calendrier | procedure | politique-americaine:tribunaux, calendriers-echeances:dates_limites |
| projet budgétaire au Congrès américain | adoption d'une loi de réconciliation budgétaire par le Congrès américain | us_reconciliation_budgetaire | procedure | politique-americaine:congres, politique-americaine:budget |
| exercice budgétaire fédéral américain sans lois de crédits annuelles adoptées | vote d'une loi de finances provisoire (continuing resolution) ou fermeture du gouvernement fédéral américain | us_lois_de_finances_provisoires | maintien | politique-americaine:congres, politique-americaine:budget, calendriers-echeances:dates_limites |
| membre de la Chambre des représentants américaine en fonction | censure, réprimande ou exclusion d'un membre de la Chambre des représentants américaine | us_chambre_sanctions_disciplinaires | evenement_rare | politique-americaine:congres |
| accord USMCA en vigueur, avant ou pendant sa révision conjointe | prolongation, révision ou retrait de l'accord États-Unis–Mexique–Canada (USMCA) | usmca_revision_conjointe | procedure | politique-americaine:commerce, calendriers-echeances:dates_limites |
| négociation en cours avec une date limite connue | conclusion d'un accord négocié avant une date limite | effet_d_echeance_negociation | contexte | calendriers-echeances:dates_limites, calendriers-echeances:anticipations |
| campagne référendaire en cours sur un changement | victoire du changement à un référendum | referendums_retour_statu_quo | contexte | humain:risque_percu, calendriers-echeances:elections |
| nomination présidentielle américaine transmise au Sénat | confirmation par le Sénat d'une nomination présidentielle américaine | us_confirmations_delais | procedure | politique-americaine:congres, politique-americaine:executif |
| conseiller principal de la Maison-Blanche ou membre du cabinet américain en fonction | départ d'un conseiller principal de la Maison-Blanche ou d'un membre du cabinet américain | us_entourage_rotation | evenement_rare | politique-americaine:entourage, politique-americaine:executif |
| programme de sanctions du Trésor américain en vigueur | nouvelles désignations de sanctions par le Trésor américain (OFAC) | us_sanctions_frequence | maintien | politique-americaine:sanctions |
| élu ou responsable public américain, en fonction ou ancien, non inculpé | inculpation ou arrestation d'un élu ou d'un responsable public américain, en fonction ou ancien | us_inculpation_personnalites | evenement_rare | politique-americaine:tribunaux, politique-americaine:executif |
| projet, chantier ou lancement annoncé avec une date prévue | achèvement ou mise en service d'un projet annoncé à la date prévue | calendriers_annonces_glissent | contexte | calendriers-echeances:anticipations, calendriers-echeances:dates_limites |
| programme nucléaire nord-coréen sans essai depuis septembre 2017 | essai nucléaire nord-coréen | coree_du_nord_essais_nucleaires | evenement_rare | non-proliferation:etats_du_seuil, non-proliferation:dissuasion |
| saison cyclonique atlantique en cours ou à venir | atterrissage d'un ouragan sur le territoire continental des États-Unis | us_ouragans_atterrissage | evenement_rare | climat-extremes:tempetes, climat-extremes:saisons |
| surveillance satellitaire des explosions de bolides dans l'atmosphère | explosion dans l'atmosphère d'un bolide d'une énergie donnée | bolides_frequence | evenement_rare | soleil-espace:meteorites |
| série de températures mondiale ou régionale proche de son record | record mensuel ou journalier de température de l'air ou de la mer | records_temperature_persistance | maintien | climat-extremes:tendance, climat-extremes:oceans |
| phase finale de la Coupe du monde à venir ou en cours, avec ses équipes qualifiées | vainqueur ou parcours d'une équipe à la Coupe du monde de football | coupe_du_monde_vainqueurs_hotes | course | competitions-culture:forme, competitions-culture:public |
| ancien chef d'État ou de gouvernement sorti du pouvoir | exil, emprisonnement ou poursuite d'un ancien chef d'État ou de gouvernement | anciens_dirigeants_sort | evenement_rare | humain:hierarchie, securite-publique:justice |
| composition du Dow Jones Industrial Average en vigueur | changement de composition du Dow Jones Industrial Average | dow_jones_changements | evenement_rare | calendriers-echeances:marches |
| niveau national de menace terroriste du Royaume-Uni en vigueur | changement du niveau national de menace terroriste du Royaume-Uni | royaume_uni_niveau_menace | maintien | securite-publique:alertes |
| contrôle temporaire aux frontières intérieures de Schengen en vigueur ou notifié | levée ou prolongation d'un contrôle temporaire aux frontières intérieures de Schengen | schengen_controles_interieurs | procedure | securite-publique:frontieres |
| pays membre de l'OPEP | départ ou suspension d'un pays membre de l'OPEP | opep_departs | evenement_rare | energie-mondiale:decisions |
| tarifs de Royal Mail en vigueur | hausse des tarifs des lettres ou colis de Royal Mail | royal_mail_hausses_tarifs | maintien | inflation-mondiale:prix_conso |
| pape en fonction | voyage d'un pape à l'étranger | papes_voyages | maintien |  |
| présidents américain et russe en fonction, sans sommet annoncé | rencontre en personne entre les présidents américain et russe | sommets_etats_unis_russie | evenement_rare | russie-ukraine:negociations |
| saison de culture en cours (mars-août pour le maïs et le soja, avril-octobre pour le coton) avec des journées chaudes | rendement d'une récolte de maïs, de soja ou de coton aux États-Unis selon les températures de la saison | seuil_chaleur_mais_soja_coton | seuil | alimentation-mondiale:cultures, alimentation-mondiale:climat |
| blé en fin de cycle (floraison, remplissage du grain) exposé à des maxima élevés | rendement d'une récolte de blé selon les températures maximales de la saison | seuil_chaleur_ble | seuil | alimentation-mondiale:cultures, alimentation-mondiale:climat |
