import couverture_fiches as c


def test_sans_dates_recentes():
    assert "2026" not in c.sans_dates_recentes("règle ancienne ; trêve de juin 2026 rompue")
    assert c.sans_dates_recentes("crises de 1987 et 2019").startswith("crises de 1987")


def test_valider_rejette_les_faux_compartiments():
    cat = {"politique-americaine": {"texte": "x", "compartiments": {"congres": "Congrès"}}}
    g, r = c.valider({"choix": [
        {"fiche": "politique-americaine", "compartiment": "congres", "regle": "majorité simple au Sénat pour la réconciliation"},
        {"fiche": "politique-americaine", "compartiment": "lune", "regle": "une règle assez longue pour passer"},
        {"fiche": "inconnue", "compartiment": "congres", "regle": "une règle assez longue pour passer"},
        {"fiche": "politique-americaine", "compartiment": "congres", "regle": "court"}]}, cat)
    assert len(g) == 1 and len(r) == 1          # au plus deux choix lus ; le second est rejeté
    assert c.valider({"choix": []}, cat) == ([], [])
