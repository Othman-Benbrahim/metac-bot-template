"""2026-11-25 : réunions des eurodéputés avec les représentants d'intérêts (collecte_lobbying.py)."""
import collecte_lobbying as cl


def test_agreger():
    R = [{"date": "23-01-2024", "epid": "1", "dossier": "2023/0001(COD)", "committees": ["ENVI"], "lobbyistsArray": ["Bayer", "ONG X"]},
         {"date": "25-01-2024", "epid": "2", "dossier": "", "committees": [], "lobbyistsArray": ["Bayer"]},
         {"date": "02-02-2024 Cancelled", "epid": "3", "dossier": "", "committees": [], "lobbyistsArray": ["Y"]},
         {"date": "03-02-2024", "epid": "1", "dossier": "2023/0001(COD)", "procedure": "2024/0002(COD)", "committees": ["ENVI", "AGRI"], "lobbyistsArray": ["Z"]}]
    lignes, dos, derniere = cl.agreger(R, {"Bayer": "123-45", "ONG X": ""})
    t = {(m, mes, c): v for m, mes, c, v in lignes}
    assert t[("2024-01", "reunions", "")] == 2 and t[("2024-01", "deputes", "")] == 2
    assert t[("2024-01", "part_dossier", "")] == 50.0 and t[("2024-01", "part_registre", "")] == 66.7
    assert t[("2024-02", "reunions", "")] == 1 and t[("2024-02", "commission", "AGRI")] == 1
    assert derniere == "2024-02-03" and dos[0] == {"dossier": "2023/0001(COD)", "reunions": 2, "deputes": 1,
                                                    "representants": 3, "debut": "2024-01-23", "fin": "2024-02-03"}
    assert cl.date_iso("x") is None
