"""0.10.369 : registre des briques (tranches d'échelle, statuts)."""
import registre_briques as rb


def test_tranches():
    assert rb.tranche_course("Will X win the 2026 Michigan Democratic Primary?") == "primaire"
    assert rb.tranche_course("Will X win the 2026 Bahia gubernatorial election?") == "infranational"
    assert rb.tranche_course("Will X win the 2026 Brazilian presidential election?") == "national"
    x = {"question_id": "fb:2026-07-05:fred:X:2026-07-12", "jeu": "2026-07-05", "ombre_b_echeance": {"ecart_median_jours": 1}}
    assert rb.tranche_seuil(x) == "quotidienne|h<=7"


def test_statut_insuffisant():
    assert rb.statut([{"id": "a", "issue": 1, "p_brique": 0.6, "p_ref": 0.5}], 0.05)["statut"] == "insuffisant"
