"""0.10.314 : inventaire des thèmes (sans réseau)."""
import inventaire_themes as it


def test_themes_connus_incluent_fiches_et_ponts():
    c = it.themes_connus()
    assert "ormuz" in c and "energie-mondiale" in c


def test_identifiants_propres():
    assert it.propre("Sécurité Nucléaire civile!") == "securite-nucleaire-civile"
    assert it.propre("faillites_entreprises") == "faillites-entreprises"


def test_resume_ordonne_les_fiches_non_ecrites_d_abord():
    ls = [{"question_id": "1", "titre": "Brent above $100?", "themes": [{"id": "energie-mondiale", "nom": "Énergie"}]},
          {"question_id": "2", "titre": "Hormuz traffic?", "themes": [{"id": "ormuz", "nom": "Ormuz"}]},
          {"question_id": "3", "titre": "Ir-192 stolen?", "themes": [{"id": "securite-radiologique", "nom": "Sources radioactives", "nouveau": True}]},
          {"question_id": "4", "titre": "Mexico packages?", "themes": [{"id": "securite-radiologique", "nom": "Sources radioactives"}]}]
    r = it.resumer(ls, it.themes_connus())
    ordre = [x["theme"] for x in r["ordre"]]
    assert ordre[0] == "securite-radiologique" and ordre[-1] == "ormuz"
    assert next(x for x in r["ordre"] if x["theme"] == "energie-mondiale")["ponts_qui_l_appellent"] == 1
