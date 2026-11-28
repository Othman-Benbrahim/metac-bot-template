import contradicteur_brique as cb
import dossier_interne as di

T = "Will Donald Trump and Vladimir Putin meet in person or talk on the phone before January 1, 2027?"


def test_hors_domaine_citation_verifiee():
    r = cb.analyser('{"verdict": "hors_domaine", "citation": "or talk on the phone"}', T)
    assert r["verdict"] == "hors_domaine"
    r = cb.analyser('{"verdict": "hors_domaine", "citation": "video call"}', T)
    assert r["verdict"] == "rejete"


def test_terrain_exige_des_sources():
    assert cb.analyser('{"verdict": "contre_terrain", "sources": []}', T)["verdict"] == "rejete"
    assert cb.analyser("pas de json", T)["verdict"] == "illisible"


def test_chaque_brique_a_un_domaine():
    import inspect
    src = inspect.getsource(di._briques)
    import re
    fams = re.findall(r'\("([a-z_]+)", "', src)
    assert fams and all(f in di.DOMAINES for f in fams)


def test_contradicteur_juge_la_brique_appliquee(monkeypatch):
    """2026-11-28 (relecture indépendante) : le contradicteur juge la brique appliquée par le bot, pas la première du
    dossier interne ; il ne juge pas les sondes."""
    import asyncio
    import alphabet_bot as ab
    import dossier_interne as di
    vus = []
    monkeypatch.setenv("ALPHABET_CONTRADICTEUR", "x")
    monkeypatch.setattr(di, "_briques", lambda titre, j, fin: [("sommets", "m", 0.3), ("rencontres", "m", 0.4),
                                                                ("tenue", "m", 0.5)])
    import contradicteur_brique as cb
    monkeypatch.setattr(cb, "consigne", lambda titre, crit, fam, dom, p, r: vus.append(fam) or "c")
    monkeypatch.setattr(cb, "analyser", lambda rep, titre, crit: {"verdict": "dans_domaine"})
    bot = ab.AlphabetBot.__new__(ab.AlphabetBot)

    async def crit(c):
        return "{}"
    bot._critique = crit
    monkeypatch.setattr(ab, "open", lambda *a, **k: __import__("io").StringIO(), raising=False)

    class Q:
        id, url, titre, criteres = "1", "u", "t", ""
        resolution = __import__("datetime").date(2027, 1, 1)
    for fam, attendu in [("tenue", "tenue"), ("accords", "sommets"), ("sondes", None)]:
        vus.clear()
        asyncio.run(bot._contradicteur_brique(None, Q(), "", 0.5, 0.5, fam))
        assert (vus[0] if vus else None) == attendu, fam
