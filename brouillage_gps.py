"""Brouillage GPS par pays et par jour, d'après gpsjam.org (0.10.153, décision d'auteur du 2026-11-15, 21 h 35).

gpsjam.org (John Wiseman) agrège chaque jour (UTC), depuis le 2022-02-14, les positions d'avions (ADS-B Exchange,
airplanes.live) par zones hexagonales et compte les avions dont la précision de navigation (NACp) est dégradée.
Une zone est « rouge » quand 100 × (mauvais − 1) / (bons + mauvais) > 10 (seuil de gpsjam). Le brouillage précède ou
accompagne souvent les opérations militaires : signal de niche AVEC historique, testable sur les questions passées.

Mesure : pour un pays et une date D, part moyenne des zones rouges du pays sur les 14 jours avant D (et sur les 14
jours précédents). Zones rattachées au pays par leur centre (frontières Natural Earth, échelle 1:110 M). Les fichiers
quotidiens ne sont pas documentés par gpsjam : lecture tolérante des colonnes, vérification au démarrage.
"""
from __future__ import annotations

import csv
import io
from datetime import date, timedelta

URL_JOUR = "https://gpsjam.org/data/{d}-h3_4.csv"
FRONTIERES = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson"
DEBUT = date(2022, 2, 14)


def lire_jour(texte: str) -> list[tuple[str, int, int]]:
    """(zone, bons, mauvais) ; colonnes reconnues par leur nom (hex…, …good…, …bad…)."""
    r = csv.DictReader(io.StringIO(texte))
    cols = r.fieldnames or []
    c_hex = next((c for c in cols if "hex" in c.lower()), None)
    c_bon = next((c for c in cols if "good" in c.lower()), None)
    c_mau = next((c for c in cols if "bad" in c.lower()), None)
    if not (c_hex and c_bon and c_mau):
        raise ValueError(f"colonnes inattendues : {cols}")
    out = []
    for x in r:
        try:
            out.append((x[c_hex], int(float(x[c_bon])), int(float(x[c_mau]))))
        except (ValueError, TypeError):
            continue
    return out


def rouge(bons: int, mauvais: int) -> bool:
    return bons + mauvais > 0 and 100 * (mauvais - 1) / (bons + mauvais) > 10


def centre(zone: str) -> tuple[float, float]:
    import h3
    if hasattr(h3, "cell_to_latlng"):
        return h3.cell_to_latlng(zone)
    return h3.h3_to_geo(zone)


def _dans_anneau(lon: float, lat: float, anneau: list) -> bool:
    dedans = False
    j = len(anneau) - 1
    for i in range(len(anneau)):
        xi, yi = anneau[i][0], anneau[i][1]
        xj, yj = anneau[j][0], anneau[j][1]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi:
            dedans = not dedans
        j = i
    return dedans


def charger_frontieres(geojson: dict) -> list[tuple[str, tuple, list]]:
    """(code ISO 2, boîte englobante, polygones [anneau extérieur, trous…])."""
    pays = []
    for f in geojson.get("features", []):
        pr = f.get("properties") or {}
        code = pr.get("ISO_A2_EH") if pr.get("ISO_A2") in (None, "-99") else pr.get("ISO_A2")
        g = f.get("geometry") or {}
        polys = g.get("coordinates") or []
        if g.get("type") == "Polygon":
            polys = [polys]
        if not code or code == "-99" or not polys:
            continue
        xs = [p[0] for poly in polys for p in poly[0]]
        ys = [p[1] for poly in polys for p in poly[0]]
        pays.append((code, (min(xs), min(ys), max(xs), max(ys)), polys))
    return pays


def pays_du_point(lat: float, lon: float, frontieres: list) -> str | None:
    for code, (x0, y0, x1, y1), polys in frontieres:
        if not (x0 <= lon <= x1 and y0 <= lat <= y1):
            continue
        for poly in polys:
            if _dans_anneau(lon, lat, poly[0]) and not any(_dans_anneau(lon, lat, t) for t in poly[1:]):
                return code
    return None


class Brouillage:
    def __init__(self, obtenir):
        self.obtenir = obtenir                     # fonction asynchrone (client, url) -> réponse ou None
        self.jours: dict[str, dict[str, tuple[int, int]] | None] = {}
        self.zone_pays: dict[str, str | None] = {}
        self.frontieres: list | None = None
        self.erreur = ""

    async def preparer(self, c) -> bool:
        if self.frontieres is None:
            r = await self.obtenir(c, FRONTIERES)
            self.frontieres = charger_frontieres(r.json()) if r is not None else []
        return bool(self.frontieres)

    async def jour(self, c, d: date) -> dict[str, tuple[int, int]] | None:
        """Par pays : (zones observées, zones rouges) ce jour-là."""
        k = d.isoformat()
        if k not in self.jours:
            r = await self.obtenir(c, URL_JOUR.format(d=k))
            if r is None:
                self.jours[k] = None
            else:
                try:
                    lignes = lire_jour(r.text)
                except ValueError as e:
                    self.erreur, self.jours[k] = str(e)[:200], None
                    return None
                par = {}
                for z, b, m in lignes:
                    if z not in self.zone_pays:
                        try:
                            la, lo = centre(z)
                            self.zone_pays[z] = pays_du_point(la, lo, self.frontieres or [])
                        except Exception as e:
                            self.erreur = f"{type(e).__name__}: {e}"[:200]
                            self.zone_pays[z] = None
                    p = self.zone_pays[z]
                    if p:
                        n, rr = par.get(p, (0, 0))
                        par[p] = (n + 1, rr + rouge(b, m))
                self.jours[k] = par
        return self.jours[k]

    async def mesure(self, c, cca2: str | None, d0: date) -> dict:
        if not cca2 or d0 - timedelta(days=28) < DEBUT:
            return {"present": False, "raison": "pays inconnu ou période non couverte"}
        if not await self.preparer(c):
            return {"present": False, "raison": "frontières indisponibles"}
        parts = {"recent": [], "avant": []}
        for i in range(1, 29):
            j = await self.jour(c, d0 - timedelta(days=i))
            if j is None or cca2 not in j or j[cca2][0] == 0:
                continue
            n, rr = j[cca2]
            parts["recent" if i <= 14 else "avant"].append(rr / n)
        if len(parts["recent"]) < 10:
            return {"present": False, "raison": "trop peu de jours observés (couverture des avions)", "detail": self.erreur}
        moy = lambda v: sum(v) / len(v) if v else None
        return {"present": True, "valeur": round(moy(parts["recent"]), 4),
                "avant": round(moy(parts["avant"]), 4) if parts["avant"] else None, "jours": len(parts["recent"])}
