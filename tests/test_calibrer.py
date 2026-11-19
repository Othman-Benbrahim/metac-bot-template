"""0.10.325 : calibration mesurée, modulation de seuil (Behave), fiche humain."""
import json
import math
import random
from datetime import date, timedelta
from pathlib import Path

import calibrer as cb
import carte as ca
import ecosystemes as ec


def _serie(valeurs, debut=date(2024, 1, 1), pas=7):
    return [((debut + timedelta(days=pas * i)).isoformat(), float(v)) for i, v in enumerate(valeurs)]


def test_retard_et_signe_retrouves():
    random.seed(1)
    x = [random.gauss(0, 1) for _ in range(120)]
    cx = [sum(x[: i + 1]) for i in range(120)]                      # niveau = somme des chocs
    y = [0.0, 0.0, 0.0] + [-v + random.gauss(0, 0.3) for v in x[:-3]]
    cy = [sum(y[: i + 1]) for i in range(120)]
    a, b, pas = cb.aligner(_serie(cx), _serie(cy))
    m = cb.mesurer(a, b, pas)
    assert pas == "semaine" and m["verdict"] == "significatif"
    assert m["retard"] == 3 and m["signe"] == "-" and m["delai_jours"] == 21 and m["poids"] == 1.0


def test_bruit_non_significatif_et_chevauchement():
    random.seed(2)
    x = [random.gauss(0, 1) for _ in range(100)]
    y = [random.gauss(0, 1) for _ in range(100)]
    a, b, pas = cb.aligner(_serie(x), _serie(y))
    assert cb.mesurer(a, b, pas)["verdict"] == "non_significatif"
    a, b, pas = cb.aligner(_serie(x[:10]), _serie(y[:10]))
    assert cb.mesurer(a, b, pas)["verdict"] == "chevauchement_insuffisant"


def test_pas_mensuel_si_une_serie_est_mensuelle():
    q = _serie(range(400), pas=1)
    m = _serie(range(14), pas=30)
    assert cb.aligner(q, m)[2] == "mois"


def test_regle_seuil_detectee():
    random.seed(3)
    x = [random.gauss(0, 1) for _ in range(300)]
    y = [(3 * v if abs(v) > 1.5 else 0.1 * v) + random.gauss(0, 0.2) for v in x]
    m = cb.mesurer(cb.reduire(x), cb.reduire(y), "semaine")
    assert m["regle"] in ("seuil", "masse_critique") and m["seuil"] == cb.SEUIL_REGLE   # le S explique mieux : Schelling
    assert m["regle"] == "masse_critique" and m["delta_bic"] > 2


def test_modulation_mesuree():
    random.seed(4)
    mod = [random.gauss(0, 1) for _ in range(400)]
    x = [random.gauss(0, 1) for _ in range(400)]
    y = [(1.0 if abs(mm) > 0.7 else 0.1) * v + random.gauss(0, 0.3) for mm, v in zip(mod, x)]
    r = cb.mesurer_modulation(mod, x, y, 0)
    assert r["verdict"] == "significatif" and r["r_haut"] > r["r_bas"] and r["gain"] > 0


def test_comptes_a_rebours_exclus(tmp_path: Path):
    assert cb.lire_serie("elections:US", tmp_path) == [] and cb.lire_serie("memoire:RU", tmp_path) == []


def test_fiche_humain_valide_et_modulations():
    f = ec.charger(ec.DOSSIER)
    assert "humain" in f and ec.valider(f["humain"]) == []
    assert "corps" in ec.niveaux()["niveaux"]
    c = ca.Carte(calibration=None)
    mods = dict(c.modulateurs)
    assert ("humain:hormones", 0.5) in mods["humain:instant>humain:passage_acte"]
    assert all(r["vers"] != "humain:instant" or r.get("module") is None for r in c.sortants.get("humain:hormones", []))


def test_modulation_abaisse_le_seuil():
    c = ca.Carte(calibration=None)
    r = next(x for x in c.sortants["humain:nous_eux"] if x["vers"] == "humain:passage_acte")
    z = abs(c.intensite("humain:stress_chronique"))                 # l'état observé du jour abaisse déjà le seuil
    sans = c.seuil_effectif(r, {})
    avec = c.seuil_effectif(r, {"humain:stress_chronique": {"ampleur": 1.0}})
    assert abs(sans - max(ca.SEUIL_PLANCHER, 2.0 - 0.4 * z)) < 1e-9
    assert abs(avec - max(ca.SEUIL_PLANCHER, 2.0 - 0.4 * max(z, 2.0))) < 1e-9
    assert c.seuil_effectif(r, {"humain:stress_chronique": {"ampleur": 9.0}}) == ca.SEUIL_PLANCHER
    assert ca.multiplicateur("seuil", 1.8, 2.0) == 0.3 and ca.multiplicateur("seuil", 1.8, avec) == 1.5


def test_validation_module_et_series():
    base = {"theme": "t", "nom": "T", "declaration": {k: "x" for k in ("but", "limites", "observateur", "date") + ec.AXES},
            "compartiments": [{"id": i, "niveau": {"espace": "x", "temps": "x", "vitesse": "jours", "taille": "micro"},
                               "traces": [{"source": "s", "statut": "collecte", "adaptateur": f"fred:{i}"}]} for i in "abc"],
            "relations": [{"de": "a", "vers": "b", "effet": "+", "statut": "a_verifier", "intensite": {"mesure": "m", "regle": "proportionnelle"}},
                          {"de": "c", "vers": "a", "effet": "0", "statut": "a_verifier", "module": "a>b"},
                          {"de": "a", "vers": "c", "effet": "+", "statut": "a_verifier", "series": ["fred:a", "fred:b"],
                           "parametres": {"seuil": "haut"}}], "ponts": []}
    e = " | ".join(ec.valider(base))
    assert "sans règle « seuil »" in e and "series" in e and "parametres" in e


def test_calibration_lue_par_la_carte(tmp_path: Path):
    cal = {"relations": {
        "humain:stress_chronique>humain:attente": {"verdict": "significatif", "poids": 0.8, "delai_jours": 60, "signe": "-",
                                                    "concorde": True},
        "humain:attente>humain:hierarchie": {"verdict": "significatif", "poids": 0.9, "delai_jours": 5, "signe": "+",
                                             "concorde": False}}}
    p = tmp_path / "cal.json"
    p.write_text(json.dumps(cal), encoding="utf-8")
    c = ca.Carte(calibration=p)
    r = next(x for x in c.sortants["humain:stress_chronique"] if x["vers"] == "humain:attente")
    assert r["mesure"] and r["poids_mesure"] == 0.8 and r["delai_mesure"] == 60
    r2 = next(x for x in c.sortants["humain:attente"] if x["vers"] == "humain:hierarchie")
    assert r2.get("contredite") and not r2.get("mesure") and r2["effet"] == "-"


def test_un_effet_fort_tardif_n_est_plus_masque():
    c = ca.Carte(calibration=None)
    e = {x["compartiment"]: x for x in c.propager({"humain:stress_chronique": 1.0}, 400)}
    assert e["humain:passage_acte"]["ampleur"] >= 1.0                 # par l'attente déçue, plus tard que par l'empathie
    assert "politique-americaine:elections" in e and "russie-ukraine:front" not in {
        k for k, v in e.items() if "humain:passage_acte → russie-ukraine:front" in v["chemin"]}


# --- 0.10.326 : Schelling ---
def test_masse_critique_equilibres_et_bascule():
    e = ca.equilibres(0.4, 0.15, 0.05)
    assert e["bascule"] is not None and 0.2 < e["bascule"] < 0.45 and e["stables"][0] < 0.1 and e["part_haute"] == 1.0
    assert ca.equilibres(0.8, 0.1, 0.0)["part_haute"] == 0.0              # le séminaire qui meurt : pas de masse critique
    assert ca.multiplicateur("masse_critique", 5, mu=2, sigma=0.5) > 1.49
    assert ca.multiplicateur("masse_critique", 0, mu=2, sigma=0.5) < 0.31
    assert abs(ca.repartition(2.0, 2.0, 0.0) - 1.0) < 1e-9                 # sigma → 0 : le seuil net


def test_ajustement_masse_critique():
    random.seed(5)
    x = [random.gauss(0, 1.2) for _ in range(400)]
    y = [v * (0.3 + 1.2 * ca.repartition(abs(v), 1.5, 0.25)) + random.gauss(0, 0.1) for v in x]
    m = cb.ajuster_masse_critique(x, y)
    assert m["delta_bic"] > 2 and abs(m["mu"] - 1.5) <= 0.25


def test_simulation_pas_a_pas_bascule_selon_l_ampleur(tmp_path: Path):
    c = ca.Carte(reg=tmp_path, calibration=None)                          # aucun état observé : seuils intacts
    petit = c.simuler({"humain:stress_chronique": 0.2}, 365, 7)
    grand = c.simuler({"humain:stress_chronique": 1.0}, 365, 7)
    assert abs((petit.get("humain:passage_acte") or {"pic": 0})["pic"]) < 0.3      # pas de bascule (pertes ×2 : une trace)
    assert grand["humain:passage_acte"]["pic"] > 1.0
    assert len(grand["humain:passage_acte"]["trajectoire"]) == 365 // 7 + 1


def test_simulation_thermostat_oscille(tmp_path: Path):
    import yaml
    d = tmp_path / "eco"
    d.mkdir()
    (d / "niveaux.yaml").write_text((ec.DOSSIER / "niveaux.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    niv = {"espace": "site", "temps": "jours", "vitesse": "jours", "taille": "micro"}
    f = {"theme": "th", "nom": "thermostat", "declaration": {k: "x" for k in ("but", "limites", "observateur", "date") + ec.AXES},
         "compartiments": [{"id": "temperature", "niveau": niv}, {"id": "chauffage", "niveau": niv}],
         "relations": [{"de": "temperature", "vers": "chauffage", "effet": "-", "force": "forte", "delai": "mois", "statut": "a_verifier"},
                       {"de": "chauffage", "vers": "temperature", "effet": "+", "force": "forte", "delai": "jours", "statut": "a_verifier"}]}
    (d / "th.yaml").write_text(yaml.safe_dump(f, allow_unicode=True), encoding="utf-8")
    c = ca.Carte(dossier=d, reg=tmp_path, calibration=None)
    r = c.simuler({"th:temperature": 1.0}, 365, 7)
    assert r["th:temperature"]["inversions"] >= 2                         # rappel avec retard : dépasse et oscille


def test_identite_comptable():
    c = ca.Carte(calibration=None)
    v = c.verifier_identites([{"compartiment": "energie-mondiale:production", "sens": "baisse"},
                              {"compartiment": "energie-mondiale:demande", "sens": "hausse"},
                              {"compartiment": "energie-mondiale:stocks", "sens": "hausse"}])
    assert v and v[0]["verdict"] == "incoherent"
    v = c.verifier_identites([{"compartiment": "energie-mondiale:production", "sens": "baisse"}])
    assert v[0]["verdict"] == "implique" and v[0]["sens"] == "baisse"


def test_fiche_humain_schelling():
    f = ec.charger(ec.DOSSIER)["humain"]
    ids = {c["id"] for c in f["compartiments"]}
    assert {"tri", "conventions", "dilemme"} <= ids
    r = next(x for x in f["relations"] if x["de"] == x["vers"] == "passage_acte")
    assert r["intensite"]["regle"] == "masse_critique" and set(r["parametres"]) == {"mu", "sigma"}


# --- 0.10.327 : Kuran ---
def test_fiche_humain_kuran_et_cascade(tmp_path: Path):
    f = ec.charger(ec.DOSSIER)["humain"]
    assert {"opinion_privee", "falsification", "opinion_publique"} <= {c["id"] for c in f["compartiments"]}
    c = ca.Carte(reg=tmp_path, calibration=None)
    calme = c.simuler({"humain:opinion_privee": 0.5}, 365, 7, maintenu=True)
    cascade = c.simuler({"humain:opinion_privee": 1.5}, 365, 7, maintenu=True)
    assert "humain:opinion_publique" not in calme                          # le mécontentement reste muet
    assert cascade["humain:opinion_publique"]["pic"] > 1.0 and cascade["humain:falsification"]["pic"] < 0


def test_marges_de_bascule():
    c = ca.Carte(calibration=None)
    m = c.marges_de_bascule(500)
    connues = [x["marge"] for x in m if x["marge"] is not None]
    assert connues == sorted(connues) and all(x["regle"] in ("seuil", "masse_critique") for x in m)
    assert not any(x["relation"].startswith("humain:symboles>") and x["marge"] is not None for x in m)   # memoire = calendrier


# --- 0.10.328 : Kahneman ---
def test_asymetrie_des_pertes():
    r = {"lambda_pertes": 2.0, "sens_perte": "-"}
    assert ca.asymetrie(r, -1.0) == 2.0 and ca.asymetrie(r, 1.0) == 1.0 and ca.asymetrie({}, -1.0) == 1.0
    random.seed(6)
    x = [random.gauss(0, 1) for _ in range(500)]
    y = [(2.0 if v < 0 else 1.0) * v + random.gauss(0, 0.3) for v in x]
    m = cb.mesurer_asymetrie(x, y, 0, -1)
    assert m["lambda_significatif"] and abs(m["lambda_pertes"] - 2.0) < 0.3


def test_persistance_retour_vers_la_moyenne():
    random.seed(7)
    v, e = [], 0.0
    for _ in range(300):
        e = 0.8 * e + random.gauss(0, 1)
        v.append(e)
    p = cb.persistance(_serie(v))
    assert abs(p["phi"] - 0.8) < 0.1 and abs(p["tau_jours"] - (-7 / math.log(0.8))) < 15


def test_fiche_humain_kahneman():
    f = ec.charger(ec.DOSSIER)["humain"]
    assert {"disponibilite", "risque_percu"} <= {c["id"] for c in f["compartiments"]}
    c = ca.Carte(calibration=None)
    r = next(x for x in c.sortants["humain:attente"] if x["vers"] == "humain:passage_acte")
    assert r["lambda_pertes"] == 2.0 and r["sens_perte"] == "-"


# --- 0.10.329 : Simon ---
def test_fiche_humain_simon_et_insatisfaction(tmp_path: Path):
    f = ec.charger(ec.DOSSIER)["humain"]
    assert {"aspiration", "agenda"} <= {c["id"] for c in f["compartiments"]}
    c = ca.Carte(reg=tmp_path, calibration=None)
    r = c.simuler({"humain:attente": -1.0}, 730, 7)                     # chute de l'attente, impulsion
    asp = r["humain:aspiration"]
    assert asp["pic"] < 0 and asp["jour_pic"] > 7                        # l'aspiration suit, avec retard


def test_pont_calibre_donne_le_sens(tmp_path: Path):
    cal = {"relations": {"pont:humain:agenda>politique-americaine:executif": {
        "verdict": "significatif", "poids": 0.7, "delai_jours": 14, "signe": "+"}}}
    p = tmp_path / "cal.json"
    p.write_text(json.dumps(cal), encoding="utf-8")
    c = ca.Carte(calibration=p)
    lien = next(x for x in c.sortants["humain:agenda"] if x["vers"] == "politique-americaine:executif")
    assert lien["effet"] == "+" and lien["mesure"] and lien["delai_mesure"] == 14
    c2 = ca.Carte(calibration=None)
    assert next(x for x in c2.sortants["humain:agenda"] if x["vers"] == "politique-americaine:executif")["effet"] == "±"
