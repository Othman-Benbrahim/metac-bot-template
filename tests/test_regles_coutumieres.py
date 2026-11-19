"""0.10.371 : base des règles coutumières (validation)."""
import regles_coutumieres as rc


def test_base_valide():
    assert rc.valider() == []


def test_garde_fous():
    assert rc.valider([{"id": "x", "structure": "course", "echelle": {"axe": "taille"}, "statut": "source", "sources": []}])
    assert rc.valider([{"id": "y", "structure": "course", "echelle": {"axe": "taille"}, "statut": "absence",
                        "parametres": {"a": 1}, "aide": "z"}])


# 0.10.372 : brique coutumière et socle du programme écosystémique
def test_brique_lit_les_regles():
    import brique_coutumiere as bc
    assert bc.multiplicateur(0) == 2.0 and bc.multiplicateur(50) == 3.0 and bc.multiplicateur(400) == 4.0
    f = {"election": "2026 Colombian presidential election", "evenement": "gagne", "rang": 1, "classe": "S1", "titre": ""}
    r = bc.rattacher(f)
    assert r["mode"] == "deux_tours" and r["retournement"] == 0.24 and abs(r["sigma"] - 2.70 / 0.8) < 1e-9
    assert "absence" in bc.rattacher({**f, "election": "2026 Texas Republican primary"})["motif"]
    assert bc.rattacher({**f, "election": "2026 Gangwon Province gubernatorial election"}).get("motif")
    g = bc.rattacher({**f, "election": "2026 Mongolian presidential election"})
    assert g["region"] == "monde"                          # Asie : moins de 30 seconds tours → chiffre mondial
    # le premier du premier tour sous 50 % gagne avec 1 − retournement ; le deuxième avec le retournement
    p1 = bc.probabilite({"A": 45, "B": 30, "C": 25, "__sujet__": "A"}, f, r, 0)
    p2 = bc.probabilite({"A": 45, "B": 30, "C": 25, "__sujet__": "B"}, f, r, 0)
    assert 0.70 < p1 < 0.80 and 0.15 < p2 < 0.26


def test_socle():
    import socle_ecosystemique as so
    s = so.assembler()
    assert len(s["mecanismes"]) == 11 and all(m["garde"] for m in s["mecanismes"])
    assert "politique-americaine" in s["fiches"] and "amerique_du_nord" in s["fiches"]["politique-americaine"]["espaces"]
    assert "us_erreur_primaires_d_etat" in s["fiches"]["politique-americaine"]["abstentions"]
