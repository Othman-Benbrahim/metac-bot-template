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


def test_regles_compartiments_valides():
    import regles_coutumieres as rc
    assert rc.valider() == []
    faux = [{"id": "x", "structure": "procedure", "echelle": {"axe": "temps"}, "statut": "source",
             "sources": [{"url": "https://a"}], "compartiments": ["politique-americaine:lune"]}]
    assert any("compartiment inconnu" in e for e in rc.valider(faux))


def test_catalogue_regles_sans_2026():
    import re
    import couverture_regles as cr
    cat = cr.catalogue()
    assert cat and not any(re.search(r"\b20(2[6-9]|[3-9]\d)\b", v["texte"]) for v in cat.values())
    assert "us_congres_productivite" not in cat          # cite le 119e Congrès en 2026 : exclue en entier
