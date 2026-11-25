"""Règles du dossier interne et de la force de la preuve (preenregistrements/dossier-interne.md)."""
import datetime as dt

import dossier_interne as di
import sources_preuve as sp

CLES = ["schema", "question", "briques", "prix", "carte", "questionneur", "sondes", "a_chercher", "mention", "empreinte"]
J = dt.date(2026, 11, 24)


def test_schema_complet_et_ordonne():
    D = di.construire("Will Senegal's National Assembly be dissolved before January 1, 2027?", "2027-01-01", J)
    assert list(D) == CLES
    assert D["schema"] == "dossier-1"
    assert D["empreinte"] == di.empreinte(D)


def test_pays_seul_ne_rattache_rien():
    D = di.construire("Will Senegal's National Assembly be dissolved before January 1, 2027?", "2027-01-01", J)
    assert D["carte"].get("silence") == "rattachement_insuffisant"
    D = di.construire("Will any of these high-ranking U.S. officials leave office before January 1, 2027?", "2026-12-16", J)
    assert D["carte"].get("silence") == "rattachement_insuffisant"


def test_gentile_ne_rattache_pas():
    D = di.construire("Will Russian Foreign Minister Sergey Lavrov visit Florida in December 2026?", "2027-01-01", J)
    assert all(not c.startswith("information-cyber") for c in D["carte"].get("compartiments", []))


def test_sans_famille_mention_et_silences_codes():
    D = di.construire("Will Senegal's National Assembly be dissolved before January 1, 2027?", "2027-01-01", J)
    assert D["question"]["famille"] == "sans_famille" and D["mention"] == di.MENTION_SANS_FAMILLE
    for k in ("briques", "prix", "carte", "sondes"):
        v = D[k]
        if isinstance(v, dict) and "silence" in v:
            assert v["silence"] in di.SILENCES


def test_recherche_ne_voit_aucune_valeur_interne():
    D = di.construire("Will Brent crude oil close above $100 per barrel on November 27, 2026?", "2026-11-27", J)
    R = di.pour_recherche(D)
    assert set(R) == {"question", "a_chercher"} and set(R["question"]) == {"titre", "echeance"}


def _lecteur(pages):
    return lambda u: pages.get(u)


def test_force_primaire_corroboree():
    rec = "https://www.federalreserve.gov/a https://www.lemonde.fr/b"
    pr = [{"url": "https://www.federalreserve.gov/a", "date": "2026-11-20"}, {"url": "https://www.lemonde.fr/b", "date": "2026-11-21"}]
    f = sp.force(pr, rec, "Will the Fed cut?", J, _lecteur({pr[0]["url"]: "x", pr[1]["url"]: "y"}))
    assert f["force"] == "forte" and f["marge"] == 0.10


def test_primaire_seule_insuffisante():
    rec = "https://www.federalreserve.gov/a"
    pr = [{"url": rec, "date": "2026-11-20"}]
    assert sp.force(pr, rec, "Fed", J, _lecteur({rec: "x"}))["force"] == "insuffisante"


def test_meme_depeche_compte_une_fois():
    a, b = "https://www.lemonde.fr/a", "https://www.lefigaro.fr/b"
    pr = [{"url": a, "date": "2026-11-20"}, {"url": b, "date": "2026-11-20"}]
    f = sp.force(pr, f"{a} {b}", "x", J, _lecteur({a: "Paris (AFP) - ...", b: "... (AFP) ..."}))
    assert f["independantes"] == 1 and f["force"] == "insuffisante"


def test_absente_de_la_recherche_ou_future_rejetee():
    a = "https://www.reuters.com/a"
    f = sp.force([{"url": a, "date": "2026-11-20"}], "", "x", J, _lecteur({a: "t"}))
    assert f["sources"][0]["rejet"] == "absente_de_la_recherche"
    f = sp.force([{"url": a, "date": "2026-12-20"}], a, "x", J, _lecteur({a: "t"}))
    assert f["sources"][0]["rejet"] == "date_absente_ou_future"


def test_deux_agences_differentes_moyenne():
    a, b = "https://www.reuters.com/a", "https://apnews.com/b"
    pr = [{"url": a, "date": "2026-11-20"}, {"url": b, "date": "2026-11-20"}]
    assert sp.force(pr, f"{a} {b}", "x", J, _lecteur({a: "t", b: "t"}))["force"] == "moyenne"


import juge as jg

D0 = {"question": {"titre": "Will the Fed cut rates at its December 2026 meeting?"}, "briques": [{"famille": "banque_centrale"}]}


def test_juge_mesure_et_reponse_illisible():
    assert jg.analyser('{"decision": "mesure"}', D0, "", 0.3, "", J)["p_poste"] == 0.3
    r = jg.analyser("je pense 60 %", D0, "", 0.3, "", J)
    assert r["p_poste"] == 0.3 and r["rejet"] == "reponse_illisible"


def test_juge_motif_hors_liste_rejete():
    r = jg.analyser('{"decision": "ecart", "motif": "intuition", "p_juge": 0.9}', D0, "", 0.3, "", J)
    assert r["p_poste"] == 0.3 and r["rejet"] == "motif_hors_liste"


def test_juge_critere_cite_borne_a_10_points():
    crit = "Resolves Yes only if the target range upper bound is lowered at the December meeting."
    rep = '{"decision": "ecart", "motif": "critere_resolution", "preuve": "the target range upper bound is lowered", "p_juge": 0.9}'
    r = jg.analyser(rep, D0, "", 0.3, crit, J)
    assert r["decision"] == "ecart" and abs(r["p_poste"] - 0.4) < 1e-9


def test_juge_citation_inventee_rejetee():
    rep = '{"decision": "ecart", "motif": "critere_resolution", "preuve": "any cut announced by Powell counts", "p_juge": 0.9}'
    assert jg.analyser(rep, D0, "", 0.3, "Resolves on the FOMC statement.", J)["rejet"] == "citation_introuvable"


def test_juge_source_unique_rejetee_moyenne_5_points():
    a, b = "https://www.reuters.com/x", "https://apnews.com/y"
    rep1 = '{"decision": "ecart", "motif": "fait_nouveau_source", "preuve": [{"url": "%s", "date": "2026-11-23"}], "p_juge": 0.9}' % a
    r = jg.analyser(rep1, D0, a, 0.3, "", J, lambda u: "t")
    assert r["p_poste"] == 0.3 and r["rejet"] == "preuve_insuffisante"
    rep2 = ('{"decision": "ecart", "motif": "fait_nouveau_source", "preuve": [{"url": "%s", "date": "2026-11-23"}, '
            '{"url": "%s", "date": "2026-11-23"}], "p_juge": 0.9}') % (a, b)
    r = jg.analyser(rep2, D0, f"{a} {b}", 0.3, "", J, lambda u: "t")
    assert abs(r["p_poste"] - 0.35) < 1e-9


def test_juge_hors_domaine_exige_une_brique():
    D = {"question": {"titre": "Will the Fed cut rates at its December 2026 meeting?"}, "briques": {"silence": "aucune_brique"}}
    rep = '{"decision": "ecart", "motif": "brique_hors_domaine", "preuve": "cut rates at its December 2026 meeting", "p_juge": 0.9}'
    assert jg.analyser(rep, D, "", 0.3, "", J)["rejet"] == "aucune_brique"


def test_domaine_de_manipulation_rejete():
    """2026-11-25 : un domaine Portal Kombat (Viginum) n'est jamais une preuve, sous-domaine compris."""
    a, b = "https://fr.news-pravda.com/x", "https://www.reuters.com/y"
    f = sp.force([{"url": a, "date": "2026-11-20"}, {"url": b, "date": "2026-11-20"}], f"{a} {b}", "x", J, _lecteur({a: "t", b: "t"}))
    assert f["sources"][0]["rejet"] == "domaine_de_manipulation" and f["independantes"] == 1
