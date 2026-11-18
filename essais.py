"""Registre des essais ouverts et règle d'adoption commune (0.10.98, décision d'auteur du 2026-11-14).

Lecture d'Elliot Tower, « AI for Science × Philosophy of Science », ch. 2 (Forking Paths) et 3 (Stopping and Evidence) :
un critère propre pris seul ne protège pas d'un ensemble d'essais menés en parallèle (Gelman et Loken : « had the data
turned out differently, they could have done other analyses »), ni d'un regard répété qui s'arrête au premier passage
favorable (Mayo : « significance will be attained erroneously with high probability »). Trois règles :

1. COMPTER. Tout essai qui peut aboutir à un changement de ce qui est posté ou calculé officiellement est inscrit ici,
   avec son critère et sa date d'ouverture, AVANT son premier regard, et son pré-enregistrement est commité dans
   preenregistrements/ (la date du commit fait foi, pas le texte). Le rapport de score dit combien sont ouverts.
2. CORRIGER. Un critère fondé sur un intervalle (« l'intervalle à 90 % de l'écart reste sous 0 », soit un risque
   unilatéral de 5 %) est jugé au risque 5 % / k, k = nombre d'essais ouverts de ce type (Bonferroni, Dunn 1961) :
   l'intervalle bilatéral correspondant est à 1 − 2 × 0,05 / k. Le critère nominal reste affiché à côté.
3. REGARDER À DATE FIXE. Le verdict se calcule sur les N PREMIÈRES lignes admissibles (N fixé au critère), pas sur tout ce
   qui s'accumule : regarder à chaque passe et s'arrêter au premier passage favorable gonfle l'erreur. Un verdict
   « indécis » donne droit à UN second regard, sur les 2N premières lignes, au risque partagé (moitié à chaque regard).
   Au-delà, l'essai est clos sans adoption, ou repris sous un nouveau critère inscrit avant le premier regard.

Ces règles ne font que durcir l'adoption ; elles ne touchent ni la lecture ni le p posté.
"""
from __future__ import annotations

RISQUE = 0.05          # unilatéral, celui de « l'intervalle à 90 % sous 0 »

# id → ouverture, objet, type de critère (« intervalle » : soumis à la correction ; « seuil » : critère descriptif),
# N du premier regard, pré-enregistrement.
ESSAIS = {
    "liens_empiriques": {"ouvert_le": "2026-11-14", "type": "intervalle", "n": 100, "statut": "clos",
                         "clos_le": "2026-11-14", "verdict": "non adopté (C empirique = B sur le jugement)",
                         "objet": "C empirique (liens appris) à la place de la matrice",
                         "doc": "preenregistrements/apprentissage-liens.md"},
    "b_autoregressif": {"ouvert_le": "2026-11-14", "type": "intervalle", "n": 100, "statut": "clos",
                        "clos_le": "2026-11-15", "verdict": "non adopté (banc du taux de base : pas de gain aux deux regards)",
                        "objet": "B autorégressif à la place de B pour les séries",
                        "doc": "preenregistrements/b-autoregressif.md"},
    "b_saisonnier": {"ouvert_le": "2026-11-15", "type": "intervalle", "n": 100, "statut": "clos",
                     "clos_le": "2026-11-15", "verdict": "non adopté (pire que B sur FRED ; gain sur DBnomics seul, hors critère)",
                     "objet": "B saisonnier (même période du calendrier) à la place de B pour les séries",
                     "doc": "preenregistrements/b-saisonnier.md"},
    "a_plus_b": {"ouvert_le": "2026-11-15", "type": "intervalle", "n": 100, "statut": "clos",
                "clos_le": "2026-11-15", "verdict": "adoption suspendue le 2026-11-15 (preuve en partie due à l'erreur du B ACLED) ; à réévaluer avec B corrigé",
                 "objet": "combinaison ½ A + ½ B (logit) à la place de B, sur les séries",
                 "doc": "preenregistrements/a-plus-b.md"},
    "motifs_ordinaux": {"ouvert_le": "2026-11-15", "type": "intervalle", "n": 100, "statut": "clos",
                        "clos_le": "2026-11-15", "verdict": "non adopté (moins bon que B aux deux regards)",
                        "objet": "taux de hausse conditionné au motif ordinal (transversal) à la place de B, séries",
                        "doc": "preenregistrements/motifs-ordinaux.md"},
    "combo_abo": {"ouvert_le": "2026-11-15", "type": "intervalle", "n": 100, "statut": "clos",
                  "clos_le": "2026-11-15", "verdict": "clos avant son regard, sans adoption (décision d'auteur : les motifs ont échoué seuls)",
                  "objet": "combinaison ⅓A + ⅓B + ⅓O à la place de ½A + ½B, séries",
                  "doc": "preenregistrements/motifs-ordinaux.md"},
    "aiguillage": {"ouvert_le": "2026-11-15", "type": "intervalle", "n": 100, "statut": "clos",
                  "clos_le": "2026-11-15", "verdict": "caduc (critère jugé contre le B ACLED faux) ; à refaire avec B corrigé",
                   "objet": "A sur les questions ACLED (événements humains), B ailleurs",
                   "doc": "preenregistrements/aiguillage.md"},
    "classes_signature": {"ouvert_le": "2026-11-15", "type": "intervalle", "n": 100, "statut": "ouvert",
                          "objet": "classe de référence par signature de l'alphabet (B_sig) à la place de B",
                          "doc": "preenregistrements/classes-par-signature.md"},
    "langage_acte": {"ouvert_le": "2026-11-15", "type": "intervalle", "n": 100, "statut": "ouvert",
                     "objet": "A corrigé par les actes de langage (engagements) des sources, conflits",
                     "doc": "preenregistrements/langage.md"},
    "desaccord": {"ouvert_le": "2026-11-15", "type": "intervalle", "n": 100, "statut": "clos",
                 "clos_le": "2026-11-15", "verdict": "non adopté (aucun effet du désaccord entre sources)",
                  "objet": "A rapproché de B selon le désaccord entre sources, conflits",
                  "doc": "preenregistrements/langage.md"},
    "regimes_causaux": {"ouvert_le": "2026-11-15", "type": "intervalle", "n": 100, "statut": "ouvert",
                        "objet": "méthode choisie selon le régime causal mesuré (saison, inertie) à la place de B, séries",
                        "doc": "preenregistrements/regimes-causaux.md"},
    "signaux_couteux": {"ouvert_le": "2026-11-15", "type": "intervalle", "n": 100, "statut": "clos",
                       "clos_le": "2026-11-15", "verdict": "non adopté (critère non atteint)",
                        "objet": "A corrigé par les actes gratuits et coûteux séparément, conflits",
                        "doc": "preenregistrements/signaux-couteux.md"},
    "indicateurs": {"ouvert_le": "2026-11-15", "type": "intervalle", "n": 100, "statut": "clos",
                    "clos_le": "2026-11-15", "verdict": "non atteint, puis caduc (référence A recalibré sur le B ACLED faux) ; remplacé par indicateurs_pertinents",
                    "objet": "A recalibré plus indicateurs indirects (Wikipedia, IODA, conseils aux voyageurs, pluie), conflits",
                    "doc": "preenregistrements/indicateurs.md"},
    "recalibrage_conflits": {"ouvert_le": "2026-11-15", "type": "intervalle", "n": 100, "statut": "clos",
                            "clos_le": "2026-11-15", "verdict": "caduc (erreur du B ACLED « dix fois », paramètres figés sur un A faussé) ; à refaire, décision d'auteur du 2026-11-15",
                             "objet": "A recalibré (Platt figé) à la place de A, conflits",
                             "doc": "preenregistrements/silence-et-calibrage.md"},
    "silence": {"ouvert_le": "2026-11-15", "type": "intervalle", "n": 100, "statut": "clos",
               "clos_le": "2026-11-15", "verdict": "caduc (erreur du B ACLED « dix fois », paramètres figés sur un A faussé) ; à refaire, décision d'auteur du 2026-11-15",
                "objet": "A recalibré corrigé par le silence de la presse (aucun extrait), conflits",
                "doc": "preenregistrements/silence-et-calibrage.md"},
    "b_tendance": {"ouvert_le": "2026-11-15", "type": "intervalle", "n": 100, "statut": "clos",
                  "clos_le": "2026-11-15", "verdict": "non adopté (650 questions : B récent 0,681 contre B 0,679 ; non atteint aux deux regards)",
                   "objet": "B pondéré vers les semaines récentes (demi-vie 90 j) à la place de B, séries fréquentes",
                   "doc": "preenregistrements/b-tendance.md"},
    "b_chronos": {"ouvert_le": "2026-11-15", "type": "intervalle", "n": 100, "statut": "clos",
                 "clos_le": "2026-11-15", "verdict": "non adopté (832 questions : Chronos 0,709 contre B 0,688 ; températures 0,692 = pile ou face)",
                  "objet": "B lu sur la distribution prévue par Chronos-2 (modèle de fondation) à la place de B, séries",
                  "doc": "preenregistrements/b-chronos.md"},
    "conseil_durci": {"ouvert_le": "2026-11-15", "type": "intervalle", "n": 100, "statut": "ouvert",
                      "objet": "B + 0,5 logit si conseil aux voyageurs durci (violence), sens et force fixés d'avance",
                      "doc": "preenregistrements/conseil-durci.md"},
    "contexte_meteo": {"ouvert_le": "2026-11-15", "type": "intervalle", "n": 100, "statut": "clos",
                       "clos_le": "2026-11-15", "verdict": "non atteint au second regard (0,645 contre B 0,694 ; 5 lots sur 7 gagnants) ; remplacé par contexte_meteo_v2",
                       "objet": "prévision météo archivée (contexte physique) à la place de B, températures Météo-France à 7 jours",
                       "doc": "preenregistrements/contexte-meteo.md"},
    "contexte_meteo_v2": {"ouvert_le": "2026-11-15", "type": "intervalle", "n": 100, "statut": "ouvert",
                          "objet": "prévision météo, 5 modèles, même échéance, incertitude selon le désaccord, jeux après le 2026-09-27",
                          "doc": "preenregistrements/contexte-meteo.md"},
    "indicateurs_pertinents": {"ouvert_le": "2026-11-15", "type": "intervalle", "n": 100, "statut": "clos",
                              "clos_le": "2026-11-15", "verdict": "non adopté (199 questions fraîches : 0,644 contre B 0,492 ; sens retournés)",
                               "objet": "B corrigé + conseils aux voyageurs (violence) et pluie (mobilisation), modèle figé, conflits « une fois »",
                               "doc": "preenregistrements/indicateurs-pertinents.md"},
    "jugements_intermediaires": {"ouvert_le": "2026-11-15", "type": "intervalle", "n": 100, "statut": "ouvert",
                                 "objet": "jugement final après sept notes séparées (cartes) à la place de A, conflits",
                                 "doc": "preenregistrements/jugements-intermediaires.md"},
    "ombre_absence": {"ouvert_le": "2026-11-13", "type": "intervalle", "n": 30, "statut": "ouvert",
                      "objet": "cote de B divisée par 2 pour les états nuls d'absence",
                      "doc": "preenregistrements/ombre-absence.md"},
    "combinaisons": {"ouvert_le": "2026-11-17", "type": "intervalle", "n": 10, "statut": "ouvert",
                     "objet": "combinaisons de deux mécanismes (grille de bon sens) : δ fixé sur l'exploration (avant 2026), "
                              "jugé sur la confirmation (2026) ; correction interne supplémentaire par le nombre de paires jugées",
                     "doc": "preenregistrements/combinaisons-bon-sens.md"},
    "jugement_aveugle": {"ouvert_le": "2026-11-17", "type": "intervalle", "n": 100, "statut": "ouvert",
                         "objet": "jugement du modèle sans voir B, combiné mécaniquement à B, contre A qui voit B (conflits)",
                         "doc": "preenregistrements/jugement-aveugle.md"},
    "conflictforecast": {"ouvert_le": "2026-11-17", "type": "intervalle", "n": 10, "statut": "clos",
                         "clos_le": "2026-11-17", "verdict": "non adopté (12 cases jugées, aucune confirmée ; violence, "
                                                           "escalade prévue : δ +0,32 en exploration, écart +0,004 en confirmation)",
                         "objet": "ConflictForecast lu comme indicateur (escalade prévue, toute violence probable) : δ par "
                                  "état fixé avant 2026, jugé sur 2026 ; version utilisable le 25 du mois suivant ses données",
                         "doc": "preenregistrements/conflictforecast.md"},
    "classe_reference": {"ouvert_le": "2026-11-17", "type": "intervalle", "n": 30, "statut": "clos",
                         "clos_le": "2026-11-17", "verdict": "adopté (décision d'auteur du 2026-11-17, 19 h 10) comme B du "
                                                            "banc GDELT : meilleur que B à 7, 30 et 90 jours ; non adopté "
                                                            "sur les séries (essai b_noyau)",
                         "objet": "B par classe de référence pondérée par la ressemblance (tous pays, noyau fixé d'avance) "
                                  "contre B, questions fabriquées GDELT",
                         "doc": "preenregistrements/classe-reference.md"},
    "b_noyau": {"ouvert_le": "2026-11-17", "type": "intervalle", "n": 100, "statut": "clos",
                "clos_le": "2026-11-17", "verdict": "non adopté (séries réelles : écart +0,004 sur les 200 premières, "
                                                  "intervalle corrigé [−0,052 ; +0,052] ; gain descriptif sur DBnomics hors critère)",
                "objet": "B des séries pondéré par la ressemblance (position dans l'année, élan sur h jours) contre B, "
                         "questions réelles FRED et DBnomics",
                "doc": "preenregistrements/classe-reference.md"},
    "classe_reference_sources": {"ouvert_le": "2026-11-17", "type": "intervalle", "n": 30, "statut": "clos",
                                 "clos_le": "2026-11-17",
                                 "verdict": "UCDP meilleur que B, tenu sans les pays tronqués (écart −0,043, intervalle "
                                            "corrigé [−0,073 ; −0,018]) ; IODA non tranché, OFAC non jugé (28 questions) ; "
                                            "domaine retenu par l'auteur : UCDP, OFAC, IODA (19 h 35) ; entrée dans le bot "
                                            "après le test sur la forme des questions Metaculus",
                                 "objet": "classe de référence pondérée contre B sur les sources d'événements du bot "
                                          "(UCDP, IODA, USGS, GDACS, lancements, OFAC), par source, à 30 jours",
                                 "doc": "preenregistrements/classe-reference.md"},
    "classe_reference_metaculus": {"ouvert_le": "2026-11-17", "type": "intervalle", "n": 30, "statut": "clos",
                                   "clos_le": "2026-11-17",
                                   "verdict": "non adopté : UCDP même gain qu'avant mais non tranché (−0,043, [−0,085 ; "
                                              "+0,027]) ; OFAC PIRE que le taux du bot (+0,089, [+0,011 ; +0,151]) ; IODA rien",
                                   "objet": "classe de référence pondérée contre le taux du bot, questions « au moins N "
                                            "événements ? » (UCDP, OFAC, IODA), par source, à 30 jours",
                                   "doc": "preenregistrements/classe-reference.md"},
    "m11_grappe": {"ouvert_le": "2026-11-17", "type": "intervalle", "n": 10, "statut": "clos", "clos_le": "2026-11-17",
                   "verdict": "non adopté (δ négatif en exploration, contraire au sens attendu ; rien en confirmation)",
                   "objet": "M11 en grappe (au moins 2 voisins et la moitié en hausse) contre la classe pondérée, GDELT",
                   "doc": "preenregistrements/geo-math.md"},
    "alerte_precoce": {"ouvert_le": "2026-11-17", "type": "intervalle", "n": 10, "statut": "clos", "clos_le": "2026-11-17",
                       "verdict": "non adopté (δ positif en exploration, comme attendu, mais pire que B en confirmation "
                                  "sur les manifestations, intervalle [+0,002 ; +0,053])",
                       "objet": "signes avant-coureurs (variance et autocorrélation en hausse) sur les questions "
                                "d'escalade, contre la classe pondérée, GDELT",
                       "doc": "preenregistrements/geo-math.md"},
    "richardson": {"ouvert_le": "2026-11-17", "type": "intervalle", "n": 30, "statut": "clos", "clos_le": "2026-11-17",
                   "verdict": "non adopté : la lognormale fait moins bien que le taux du bot (+0,015, [−0,006 ; +0,037]), "
                              "la binomiale négative aussi ; le comptage des fenêtres passées reste le meilleur",
                   "objet": "lognormale (queue lourde) contre le taux du bot, morts UCDP au-dessus du quantile 90 %",
                   "doc": "preenregistrements/geo-math.md"},
    "front_diffusion": {"ouvert_le": "2026-11-17", "type": "intervalle", "n": 10, "statut": "clos", "clos_le": "2026-11-17",
                        "verdict": "non adopté (front présent 31 % du temps ; δ −0,06 en exploration, écart −0,002, "
                                   "[−0,009 ; +0,005] en confirmation)",
                        "objet": "front de diffusion entre carreaux PRIO-GRID (UCDP) contre la classe pondérée, par pays",
                        "doc": "preenregistrements/front-diffusion.md"},
    "richardson_evenements": {"ouvert_le": "2026-11-17", "type": "intervalle", "n": 30, "statut": "clos",
                              "clos_le": "2026-11-17",
                              "verdict": "non adopté (α de Hill 1,27, loi de puissance bien présente ; mais +0,008, "
                                         "[−0,034 ; +0,050] contre le taux du bot à 100 morts ; piste a posteriori : "
                                         "gain là où le pays a déjà connu de grands événements, perte ailleurs)",
                              "objet": "Richardson à la bonne échelle : taille des événements universelle (Pareto, tous "
                                       "pays) × fréquence locale, contre le taux du bot, « au moins un événement de 100 morts »",
                              "doc": "preenregistrements/geo-math.md"},
    "jugement_semblables": {"ouvert_le": "2026-11-17", "type": "intervalle", "n": 30, "statut": "ouvert",
                            "objet": "questions de jugement (ForecastBench) : 50 questions semblables résolues contre le "
                                     "statu quo par plateforme, forme et horizon",
                            "doc": "preenregistrements/jugement-semblables.md"},
    "jugement_alphabet": {"ouvert_le": "2026-11-17", "type": "intervalle", "n": 150, "statut": "clos", "clos_le": "2026-11-18",
                          "verdict": "non adopté : second regard à 300 (309 valides), M − A = −0,019, intervalle 90 % "
                                     "[−0,049 ; +0,009], corrigé [−0,075 ; +0,031] ; M devant A à chaque regard (0,362 contre "
                                     "0,381), foule 0,384 en repère après coup ; cartes démontrées : PROPORTION et HIÉRARCHIE "
                                     "(décideurs) sur l'ensemble, TENDANCE sur les échéances",
                          "objet": "questions de jugement Metaculus : bot standard (A) contre le même passé par l'alphabet "
                                   "en matriochka (M), départ des semblables",
                          "doc": "preenregistrements/jugement-alphabet.md"},
    "jugement_sens": {"ouvert_le": "2026-11-18", "type": "intervalle", "n": 1, "statut": "ouvert",
                      "objet": "questions semblables trouvées par le sens (embeddings bge-small) contre par les mots "
                               "(TF-IDF) ; un seul regard, réplique 2025 exigée",
                      "doc": "preenregistrements/jugement-sens.md"},
    "avocat_oui": {"ouvert_le": "2026-11-18", "type": "intervalle", "n": 150, "statut": "ouvert", "lecteur": "gpt-5-mini",
                   "objet": "M avec un « avocat du OUI » avant le jugement final, contre M refait sur la même recherche",
                   "doc": "preenregistrements/jugement-variantes.md"},
    "formulation_neutre": {"ouvert_le": "2026-11-18", "type": "intervalle", "n": 150, "statut": "ouvert",
                           "lecteur": "gpt-5-mini",
                           "objet": "jugement final de M posé en deux issues symétriques, contre M refait (oui/non)",
                           "doc": "preenregistrements/jugement-variantes.md"},
    "replique_haiku": {"ouvert_le": "2026-11-18", "type": "intervalle", "n": 150, "statut": "ouvert",
                       "lecteur": "claude-haiku-4-5",
                       "objet": "réplique du banc jugement_alphabet sur un second lecteur : M contre A, Claude Haiku 4.5",
                       "doc": "preenregistrements/jugement-variantes.md"},
    "m_officiel": {"ouvert_le": "2026-11-18", "type": "seuil", "n": 100, "statut": "ouvert", "depuis_version": "0.10.253",
                   "objet": "bras M (matriochka) POSTÉ en compétition par décision d'auteur (2026-11-18 5 h 55), A en "
                            "ombre ; règle d'arrêt : après 100 questions résolues, retour en arrière si M − A > +0,03",
                   "doc": "preenregistrements/m-officiel.md"},
    "jugement_doublons": {"ouvert_le": "2026-11-18", "type": "intervalle", "n": 30, "statut": "clos", "clos_le": "2026-11-18",
                          "verdict": "non adopté, de justesse : −0,015, intervalle corrigé [−0,034 ; +0,001] ; gain surtout "
                                     "sur Polymarket et INFER, rien sur Metaculus (0,455 → 0,452) ; réplication sur Polymarket et INFER, jeux de 2025 : NON reproduite (+0,006, "
                                     "[−0,007 ; +0,014]) : gain de 2026 tenu pour du hasard",
                          "objet": "questions semblables sans doublons (une voisine par question, cosinus ≤ 0,8 entre "
                                   "voisines) contre les semblables actuelles",
                          "doc": "preenregistrements/jugement-doublons.md"},
    "sans_matrice": {"ouvert_le": "2026-11-14", "type": "seuil", "n": 50, "statut": "ouvert", "depuis_version": "0.10.99",
                     "lecteur": "mistral-medium",
                     "objet": "plan et lecture sans la matrice",
                     "doc": "preenregistrements/sans-matrice.md"},
}


def k_intervalle() -> int:
    return max(1, sum(1 for e in ESSAIS.values() if e["statut"] == "ouvert" and e["type"] == "intervalle"))


def risque_corrige(regard: int = 1) -> float:
    """Risque unilatéral corrigé pour un essai « intervalle » : 5 % / k, partagé en deux si un second regard existe."""
    return RISQUE / k_intervalle() / (2 if regard == 2 else 1)


def bornes(tirages_tries: list[float], risque: float) -> tuple[float, float]:
    """Intervalle bilatéral au niveau 1 − 2·risque, lu sur des tirages bootstrap déjà triés."""
    n = len(tirages_tries)
    i = max(0, min(n - 1, int(risque * n)))
    j = max(0, min(n - 1, int((1 - risque) * n) - 1))
    return tirages_tries[i], tirages_tries[j]


def regard(n_disponible: int, n: int) -> int:
    """0 : pas encore de regard ; 1 : premier regard (N premières lignes) ; 2 : second regard (2N premières)."""
    return 0 if n_disponible < n else (1 if n_disponible < 2 * n else 2)


def resume() -> dict:
    ouverts = {k: v for k, v in ESSAIS.items() if v["statut"] == "ouvert"}
    return {"ouverts": len(ouverts), "intervalle": k_intervalle(), "risque_corrige_premier_regard": risque_corrige(1),
            "niveau_intervalle_corrige": round(1 - 2 * risque_corrige(1), 4), "essais": ouverts}
