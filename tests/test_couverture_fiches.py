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


def test_v4_objet_perimetre_et_fautes_de_frappe():
    import couverture_regles as cr
    cat = cr.catalogue()
    assert all(v["objet"] and v["perimetre"] for v in cat.values())
    assert cr.corriger_id("effect_d_echeance_negociation", cat) == "effet_d_echeance_negociation"
    assert cr.corriger_id("regle_inventee", cat) is None
    o, si = cat["us_fed_calendrier"]["objet"], cat["us_fed_calendrier"]["situation"]
    bon = lambda **k: [{"id": "us_fed_calendrier", "objet": o, "situation": si, "est_l_objet": True, "est_la_situation": True, **k}]
    ok, rej = cr.valider({"pays": ["États-Unis"], "regles": bon()}, cat)
    assert ok == ["us_fed_calendrier"] and not rej
    _, rej = cr.valider({"pays": ["États-Unis"], "regles": bon(objet="autre chose")}, cat)
    assert rej[0]["motif"] == "objet mal recopié"
    _, rej = cr.valider({"pays": ["États-Unis"], "regles": bon(situation="autre chose")}, cat)
    assert rej[0]["motif"] == "situation mal recopiée"
    _, rej = cr.valider({"pays": ["États-Unis"], "regles": bon(est_l_objet=False)}, cat)
    assert "n'est pas l'objet" in rej[0]["motif"]
    _, rej = cr.valider({"pays": ["États-Unis"], "regles": bon(est_la_situation=False)}, cat)
    assert "situation de départ" in rej[0]["motif"]
    _, rej = cr.valider({"pays": [], "regions": ["afrique"], "regles": bon()}, cat)
    assert rej[0]["motif"].startswith("hors périmètre")
    c = cat["coups_d_etat_frequence"]
    ok, _ = cr.valider({"pays": ["Brésil"], "regles": [{"id": "coups_d_etat_frequence", "objet": c["objet"],
                         "situation": c["situation"], "est_l_objet": True, "est_la_situation": True}]}, cat)
    assert ok == ["coups_d_etat_frequence"]                  # périmètre monde
    assert cr.dans_perimetre(["amerique_du_nord"], ["Canada"], [])


def test_regles_sourcees_ont_objet_et_perimetre():
    import regles_coutumieres as rc
    faux = [{"id": "x", "structure": next(iter(rc.STRUCTURES)), "echelle": {"axe": "temps"}, "statut": "source",
             "sources": [{"url": "u"}], "perimetre": ["Atlantide"]}]
    err = rc.valider(faux, {})
    assert any("sans objet" in e for e in err) and any("périmètre" in e for e in err)
