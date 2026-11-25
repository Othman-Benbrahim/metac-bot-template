"""2026-11-25 : briefs standardisés (brief.py) — contrôles par le code, relais, rendu."""
import json
import re

import brief as b

TEXTE = ("Selon le SIPRI, les stocks d'ogives nucléaires atteignent 9 745 en 2026. La Chine a ajouté une centaine d'ogives "
         "en un an, d'après le rapport annuel publié lundi à Stockholm par l'institut.")
ROUTAGE = [(re.compile(r"nucl[ée]aire", re.I), {"militaire:arsenaux_nucleaires"})]
NOMS = {"militaire:arsenaux_nucleaires": "Arsenaux nucléaires"}


def test_chiffre_present():
    assert b.chiffre_present("9 745", TEXTE) and b.chiffre_present("9745", TEXTE)
    assert not b.chiffre_present("12 241", TEXTE)
    assert b.chiffre_present("", TEXTE)


def test_recopie_retiree():
    copie = "les stocks d'ogives nucléaires atteignent 9 745 en 2026 La Chine a ajouté une centaine"
    assert b.recopie(copie, TEXTE) and not b.recopie("Le SIPRI compte 9 745 ogives en stock.", TEXTE)


def test_controler():
    d = {"titre": "Ogives", "faits": [
        {"fait": "Le SIPRI estime le stock mondial à 9 745 ogives.", "chiffre": "9 745", "origine": "SIPRI"},
        {"fait": "Un chiffre inventé.", "chiffre": "12 241", "origine": "SIPRI"},
        {"fait": "les stocks d'ogives nucléaires atteignent 9 745 en 2026 La Chine a ajouté une centaine", "chiffre": "", "origine": ""}],
        "ce_que_ca_change": " ".join(["mot"] * 80), "compartiments": ["militaire:arsenaux_nucleaires", "inventé:x"], "limites": ["a", "b", "c"]}
    r = b.controler(d, TEXTE, "exemple.com", ["militaire:arsenaux_nucleaires"])
    assert [f["statut"] for f in r["faits"]] == ["relayé (attribué à SIPRI)", "chiffre non retrouvé dans la source"]
    assert r["compartiments"] == ["militaire:arsenaux_nucleaires"] and len(r["ce_que_ca_change"].split()) == b.MOTS_MAX_CHANGE
    assert len(r["limites"]) == 2


def test_relais_saute_et_bascule(monkeypatch):
    monkeypatch.setenv("CLE_B", "x")
    monkeypatch.setenv("CLE_C", "x")
    vus = []

    def appel(m, msgs):
        vus.append(m)
        if m == "b":
            raise TimeoutError("quota")
        return '{"titre": "t", "faits": []}'
    t, m = b.appeler([], relais=[("a", "CLE_ABSENTE"), ("b", "CLE_B"), ("c", "CLE_C")], appel=appel)
    assert m == "c" and vus == ["b", "c"]


def test_traiter_bout_en_bout(tmp_path, monkeypatch):
    monkeypatch.setattr(b, "DOSSIER", tmp_path)
    rep = json.dumps({"titre": "Arsenaux nucléaires en hausse", "faits": [
        {"fait": "Le SIPRI estime le stock mondial à 9 745 ogives.", "chiffre": "9 745", "origine": "SIPRI"}],
        "ce_que_ca_change": "Confirme la hausse des arsenaux.", "compartiments": ["militaire:arsenaux_nucleaires"], "limites": ["Estimation."]})
    item = {"url": "https://exemple.com/a", "titre": "Le nucléaire militaire progresse", "resume": ""}
    r = b.traiter(item, ROUTAGE, NOMS, "2026-11-25", appel=lambda m, msgs: rep, lecteur=lambda u: f"<p>{TEXTE}</p>",
                  relais=[("modele-test", None)])
    assert r["statut"] == "ok" and r["compartiments"] == ["militaire:arsenaux_nucleaires"]
    md = (tmp_path / r["fichier"]).read_text(encoding="utf-8")
    assert "relayé (attribué à SIPRI)" in md and "Arsenaux nucléaires" in md and r["mots"] < 200
    assert b.traiter({"url": "https://fr.news-pravda.com/x", "titre": "nucléaire", "resume": ""}, ROUTAGE, NOMS, "2026-11-25")["statut"] == "domaine_de_manipulation"
    assert b.traiter({"url": "https://exemple.com/b", "titre": "météo", "resume": ""}, ROUTAGE, NOMS, "2026-11-25")["statut"] == "filtre_aucun_terme"


def test_meme_media():
    assert b._meme_media("Le Grand Continent", "legrandcontinent.eu") and b._meme_media("Atlantic Council", "atlanticcouncil.org")
    assert b._meme_media("le média", "x.com") and not b._meme_media("Reuters", "atlanticcouncil.org")
