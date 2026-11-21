from datetime import date

import collecte_cyber as cc


def test_kev_et_mois():
    js = {"vulnerabilities": [{"cveID": "CVE-2026-1", "dateAdded": "2026-03-02", "vendorProject": "X",
                               "knownRansomwareCampaignUse": "Known"},
                              {"cveID": "CVE-2025-9", "dateAdded": "2025-12-30", "vendorProject": "Y",
                               "knownRansomwareCampaignUse": "Unknown"}]}
    assert cc.lire_kev(js) == [["CVE-2025-9", "2025-12-30", "Y", "non"], ["CVE-2026-1", "2026-03-02", "X", "oui"]]
    assert cc.mois_entre((2025, 11), date(2026, 2, 3)) == [(2025, 11), (2025, 12), (2026, 1), (2026, 2)]
    assert cc.bornes(2024, 2) == ("2024-02-01T00:00:00.000", "2024-02-29T23:59:59.999")
