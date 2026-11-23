"""0.10.480 : veille de la carte (liens et flux RSS des fiches et des compartiments). Sans réseau."""
from pathlib import Path

import ecosystemes as eco
import veille as v


def test_catalogue_coherent():
    cat = v.catalogue()
    ids = set(cat["flux"])
    for f in cat["flux"].values():
        assert f["url"].startswith("http") and f["titre"]
    for groupe in ("regions", "organisations"):
        for k, l in cat[groupe].items():
            assert set(l) <= ids, (groupe, k, set(l) - ids)
    fiches = eco.charger(Path("ecosystemes"))
    assert set(fiches) <= set(cat["fiches"]), set(fiches) - set(cat["fiches"])     # chaque fiche a sa veille
    for t, fi in cat["fiches"].items():
        assert t in fiches, t
        assert fi["region"] in cat["regions"], t
        assert fi.get("liens") and all(l["titre"] and l["url"].startswith("http") for l in fi["liens"]), t
        assert set(fi.get("flux") or []) <= ids, (t, set(fi["flux"]) - ids)
        comps = {c["id"] for c in fiches[t]["compartiments"]}
        for c, l in (fi.get("compartiments") or {}).items():
            assert c in comps and set(l) <= ids, (t, c)
    orgs = {c.get("organisation") for x in fiches.values() for c in x["compartiments"]}
    assert orgs - {None} <= set(cat["organisations"]), orgs - set(cat["organisations"])


def test_resolution_compartiment():
    cat = v.catalogue()
    t = v.regions_pays()
    assert v.flux_compartiment(cat, "inde", {"id": "mousson", "organisation": "climat"}, t) == ["carbon_brief", "the_hindu"]
    l = v.flux_compartiment(cat, "transport-maritime", {"id": "detroit_bab_el_mandeb", "organisation": "relief",
                                                         "geopolitique": {"pays": ["YEM", "DJI", "ERI"]}}, t)
    assert l[0] == "nasa_eo" and l[1] in cat["regions"]["afrique"]           # région majoritaire des riverains (Djibouti, Érythrée)
    l2 = v.flux_compartiment(cat, "afrique", {"id": "x", "organisation": "economie"}, t)
    assert l2[:2] == ["lm_economie", "lm_afrique"] and len(l2) == 3


def test_lire_flux_rss_et_atom():
    rss = b"""<?xml version="1.0"?><rss><channel><item><title>Un</title><link>https://a.org/1</link>
      <pubDate>Mon, 23 Nov 2026 10:00:00 GMT</pubDate><description>texte long</description></item>
      <item><title>Deux</title><link>https://a.org/2</link><pubDate>Tue, 24 Nov 2026 10:00:00 GMT</pubDate></item></channel></rss>"""
    a = v.lire_flux(rss)
    assert [x["titre"] for x in a] == ["Deux", "Un"] and set(a[0]) == {"titre", "lien", "date"}
    atom = b"""<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>A</title><link href="https://b.org/a"/>
      <updated>2026-11-22T08:00:00Z</updated></entry></feed>"""
    assert v.lire_flux(atom) == [{"titre": "A", "lien": "https://b.org/a", "date": "2026-11-22T08:00Z"}]


def test_candidats_principal_puis_secours():
    import veille
    f = {"titre": "A", "url": "https://a/x", "secours": ["https://a/y", {"url": "https://b/z", "titre": "B"}]}
    assert veille.candidats(f) == [{"url": "https://a/x", "titre": "A"}, {"url": "https://a/y", "titre": "A"},
                                   {"url": "https://b/z", "titre": "B"}]
    assert veille.candidats({"titre": "A", "url": "u"}) == [{"url": "u", "titre": "A"}]


def test_catalogue_secours_bien_formes():
    import veille
    for fid, f in veille.catalogue()["flux"].items():
        for c in veille.candidats(f):
            assert c["url"].startswith("https://"), fid
