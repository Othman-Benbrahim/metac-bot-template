"""2026-11-25 : lecture des pages pays du Digital News Report (mise_au_point/dnr_confiance.py)."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("dnr", Path(__file__).resolve().parent.parent / "mise_au_point" / "dnr_confiance.py")
dnr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dnr)

PAGE = """Digital News Report 2026 | France
OVERALL TRUST IN NEWS 2015–26
100%
                                                                                                OVERALL TRUST
                                                                                                29% (-)
 50%
       38%
                                                                                   29%
  0%                                                                                            GLOBAL AVERAGE 37%
            2015                                                              2026
"""


def test_page_pays():
    assert dnr.lire(PAGE) == [("FRA", 2015, 38), ("FRA", 2025, 29), ("FRA", 2026, 29)]


def test_ecart_negatif():
    p = PAGE.replace("29% (-)", "30% (-5)").replace("France", "United Kingdom").replace("       38%", " 50% 51%").replace(" 50%\n 50% 51%", " 50% 51%")
    assert ("GBR", 2025, 35) in dnr.lire(p) and ("GBR", 2026, 30) in dnr.lire(p)
