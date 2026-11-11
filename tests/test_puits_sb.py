"""Bot 0.10.27 : quatre puits repérés dans ShadowBroker (front en Ukraine, coupures d'Internet, lancements, sanctions US)."""
from __future__ import annotations

import asyncio
import io
import json
import sys
import tarfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import alphabet_puits as pz  # noqa: E402


def archive(jours: dict[str, list]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for j, poly in jours.items():
            b = json.dumps({"type": "FeatureCollection", "features": [
                {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [poly]}}]}).encode()
            ti = tarfile.TarInfo(f"depot-main/data/deepstatemap_data_{j.replace('-', '')}.geojson")
            ti.size = len(b)
            tf.addfile(ti, io.BytesIO(b))
    return buf.getvalue()


class Tests(unittest.TestCase):
    def setUp(self):
        pz._FRONT.clear()

    def test_front(self):
        carre = lambda e: [[37.0, 48.0], [37.0 + e, 48.0], [37.0 + e, 48.0 + e], [37.0, 48.0 + e], [37.0, 48.0]]
        donnees = archive({"2026-01-01": carre(0.1), "2026-01-02": carre(0.2), "2026-01-03": carre(0.3)})

        async def octets(url):
            return donnees
        ancien = pz._get_octets
        pz._get_octets = octets
        try:
            r = asyncio.run(pz.front_ukraine(avant=date(2026, 1, 3)))           # publication le lendemain
            self.assertEqual([p["date"] for p in r["points"]], ["2026-01-01", "2026-01-02"])
            self.assertTrue(70 < r["points"][0]["valeur"] < 90)                    # 0,1° × 0,1° vers 48° N ≈ 82 km²
            pz._FRONT.clear()
            r = asyncio.run(pz.front_ukraine("X", 48.25, 37.25, avant=date(2026, 1, 10)))
            v = [p["valeur"] for p in r["points"]]
            self.assertGreater(v[0], v[1])                                         # le front se rapproche
            self.assertEqual(v[2], 0.0)                                            # puis la localité est dedans
        finally:
            pz._get_octets = ancien

    def test_coupures_lancements_sanctions(self):
        async def faux(url, params=None, headers=None, json_=True):
            if "ioda" in url:
                return {"data": [{"time": 1735689600, "level": "critical", "datasource": "bgp"},
                                 {"time": 1735693200, "level": "critical", "datasource": "ping-slash24"},
                                 {"time": 1738368000, "level": "warning", "datasource": "bgp"}]}
            if "celestrak" in url:
                return ("OBJECT_NAME,OBJECT_ID,OWNER,LAUNCH_DATE,LAUNCH_SITE\n"
                        "STARLINK-1,2025-001A,US,2025-01-03,AFETR\nSTARLINK-2,2025-001B,US,2025-01-03,AFETR\n"
                        "TIANHE,2025-002A,PRC,2025-01-05,TSC\n")
            return ("id,schema,name,aliases,countries,sanctions,first_seen\n"
                    "a,Person,Ancien,,ru,RUSSIA-EO14024,2021-09-01T00:00:00\n"
                    "b,Company,Nouvelle SARL,,ru,RUSSIA-EO14024,2025-03-02T00:00:00\n"
                    "c,Person,Autre,,ir,IRAN,2025-04-01T00:00:00\n")
        ancien = pz._get
        pz._get = faux
        try:
            r = asyncio.run(pz.coupures_internet("ir", "2025-01-01", avant=date(2025, 12, 31)))
            self.assertEqual([p["date"] for p in r["points"]], ["2025-01-01"])     # deux alertes, un seul jour
            r = asyncio.run(pz.lancements(nom="STARLINK", avant=date(2025, 12, 31)))
            self.assertEqual(len(r["points"]), 1)                                  # deux objets, un lancement
            self.assertEqual(len(asyncio.run(pz.lancements(avant=date(2025, 12, 31)))["points"]), 2)
            r = asyncio.run(pz.sanctions_us(programme="RUSSIA", avant=date(2025, 12, 31)))
            self.assertEqual([p["date"] for p in r["points"]], ["2025-03-02"])     # stock initial du 2021-09-01 retiré
        finally:
            pz._get = ancien
        self.assertTrue(all(k in pz.CATALOGUE for k in ("front_ukraine", "coupures_internet", "lancements", "sanctions_us")))


if __name__ == "__main__":
    unittest.main()
