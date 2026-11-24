import collecte_annonces_tarifs as a


def test_versions_triees_numeriquement():
    html = '<a href="/datasets/tirade/v1.2">x</a><a href="/datasets/tirade/v1.11">y</a><a href="/datasets/tirade/v1.9">'
    assert a.versions(html) == ["v1.11", "v1.9", "v1.2"]


def test_lien_csv_relatif():
    html = '<a href="tirade-v1.11-rate-statements.csv">CSV</a>'
    assert a.lien_csv(html, "https://www.globallinkages.org/datasets/tirade/v1.11/") == \
        "https://www.globallinkages.org/datasets/tirade/v1.11/tirade-v1.11-rate-statements.csv"


def test_planificateur_mardi():
    from datetime import datetime, timezone
    import planificateur as p
    assert p.permise("mardi", datetime(2026, 11, 24, 2, 0, tzinfo=timezone.utc))
    assert not p.permise("mardi", datetime(2026, 11, 23, 2, 0, tzinfo=timezone.utc))
    assert ("collecte_annonces_tarifs.yaml", "mardi") in p.COLLECTES
