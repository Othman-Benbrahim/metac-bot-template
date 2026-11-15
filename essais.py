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
    "a_plus_b": {"ouvert_le": "2026-11-15", "type": "intervalle", "n": 100, "statut": "ouvert",
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
    "aiguillage": {"ouvert_le": "2026-11-15", "type": "intervalle", "n": 100, "statut": "ouvert",
                   "objet": "A sur les questions ACLED (événements humains), B ailleurs",
                   "doc": "preenregistrements/aiguillage.md"},
    "classes_signature": {"ouvert_le": "2026-11-15", "type": "intervalle", "n": 100, "statut": "ouvert",
                          "objet": "classe de référence par signature de l'alphabet (B_sig) à la place de B",
                          "doc": "preenregistrements/classes-par-signature.md"},
    "langage_acte": {"ouvert_le": "2026-11-15", "type": "intervalle", "n": 100, "statut": "ouvert",
                     "objet": "A corrigé par les actes de langage (engagements) des sources, conflits",
                     "doc": "preenregistrements/langage.md"},
    "desaccord": {"ouvert_le": "2026-11-15", "type": "intervalle", "n": 100, "statut": "ouvert",
                  "objet": "A rapproché de B selon le désaccord entre sources, conflits",
                  "doc": "preenregistrements/langage.md"},
    "regimes_causaux": {"ouvert_le": "2026-11-15", "type": "intervalle", "n": 100, "statut": "ouvert",
                        "objet": "méthode choisie selon le régime causal mesuré (saison, inertie) à la place de B, séries",
                        "doc": "preenregistrements/regimes-causaux.md"},
    "signaux_couteux": {"ouvert_le": "2026-11-15", "type": "intervalle", "n": 100, "statut": "ouvert",
                        "objet": "A corrigé par les actes gratuits et coûteux séparément, conflits",
                        "doc": "preenregistrements/signaux-couteux.md"},
    "indicateurs": {"ouvert_le": "2026-11-15", "type": "intervalle", "n": 100, "statut": "ouvert",
                    "objet": "A recalibré plus indicateurs indirects (Wikipedia, IODA, conseils aux voyageurs, pluie), conflits",
                    "doc": "preenregistrements/indicateurs.md"},
    "recalibrage_conflits": {"ouvert_le": "2026-11-15", "type": "intervalle", "n": 100, "statut": "ouvert",
                             "objet": "A recalibré (Platt figé) à la place de A, conflits",
                             "doc": "preenregistrements/silence-et-calibrage.md"},
    "silence": {"ouvert_le": "2026-11-15", "type": "intervalle", "n": 100, "statut": "ouvert",
                "objet": "A recalibré corrigé par le silence de la presse (aucun extrait), conflits",
                "doc": "preenregistrements/silence-et-calibrage.md"},
    "jugements_intermediaires": {"ouvert_le": "2026-11-15", "type": "intervalle", "n": 100, "statut": "ouvert",
                                 "objet": "jugement final après sept notes séparées (cartes) à la place de A, conflits",
                                 "doc": "preenregistrements/jugements-intermediaires.md"},
    "ombre_absence": {"ouvert_le": "2026-11-13", "type": "intervalle", "n": 30, "statut": "ouvert",
                      "objet": "cote de B divisée par 2 pour les états nuls d'absence",
                      "doc": "preenregistrements/ombre-absence.md"},
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
