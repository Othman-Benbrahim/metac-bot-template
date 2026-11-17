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
    "conflictforecast": {"ouvert_le": "2026-11-17", "type": "intervalle", "n": 10, "statut": "ouvert",
                         "objet": "ConflictForecast lu comme indicateur (escalade prévue, toute violence probable) : δ par "
                                  "état fixé avant 2026, jugé sur 2026 ; version utilisable le 25 du mois suivant ses données",
                         "doc": "preenregistrements/conflictforecast.md"},
    "classe_reference": {"ouvert_le": "2026-11-17", "type": "intervalle", "n": 30, "statut": "ouvert",
                         "objet": "B par classe de référence pondérée par la ressemblance (tous pays, noyau fixé d'avance) "
                                  "contre B, questions fabriquées GDELT",
                         "doc": "preenregistrements/classe-reference.md"},
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
