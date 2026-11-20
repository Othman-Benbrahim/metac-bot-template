"""EDGAR (0.10.405) : trimestres et quatrième trimestre déduit."""
import collecte_edgar as ce


def faits(vals):
    return {"facts": {"us-gaap": {"Revenues": {"units": {"USD": vals}}}}}


def test_t4_deduit_de_l_annee():
    q = [{"form": "10-Q", "start": s, "end": e, "val": v, "filed": "2025-01-01"} for s, e, v in
         [("2024-01-01", "2024-03-31", 10), ("2024-04-01", "2024-06-30", 11), ("2024-07-01", "2024-09-30", 12)]]
    a = [{"form": "10-K", "start": "2024-01-01", "end": "2024-12-31", "val": 46, "filed": "2025-02-01"}]
    f = faits(q + a)
    t = ce.avec_t4(ce.trimestres(f, "chiffre_affaires", "USD"), ce.annuels(f, "chiffre_affaires", "USD"))
    assert t[-1][1:] == ("2024-12-31", 13)


def test_contact_jamais_dans_le_code():
    import pathlib
    assert "@" not in pathlib.Path("collecte_edgar.py").read_text(encoding="utf-8").split('"""')[2]
