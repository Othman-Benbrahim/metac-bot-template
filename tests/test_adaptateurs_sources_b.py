"""0.10.323 : adaptateurs des sources dormantes, lot B (données synthétiques et vrai registre)."""
import gzip
import json
from pathlib import Path

import adaptateurs as ad
import adaptateurs_sources_b as b

REG = Path("registre")


def _ecrire(tmp: Path, nom: str, texte: str):
    (tmp / nom).write_text(texte, encoding="utf-8")


def test_hostilites_et_zeros(tmp_path):
    _ecrire(tmp_path, "gdelt-hostilites-ru.csv", "pays,jour,agressions,combats,violence_masse\nUA,2026-01-02,1,2,0\nPL,2026-01-02,1,0,0\n")
    _ecrire(tmp_path, "gdelt-hostilites-jours.txt", "2026-01-01\n2026-01-02\n2026-01-03\n")
    assert b.hostilites(tmp_path, "UA") == [("2026-01-01", 0.0), ("2026-01-02", 3.0), ("2026-01-03", 0.0)]
    assert b.hostilites(tmp_path, "UA", "combats")[1] == ("2026-01-02", 2.0)


def test_manifestations(tmp_path):
    _ecrire(tmp_path, "gdelt-manifestations.csv", "pays,jour,manifestations,emeutes,articles\nIR,2026-01-01,4,1,30\n")
    _ecrire(tmp_path, "gdelt-jours.txt", "2026-01-01\n2026-01-02\n")
    assert b.manifestations(tmp_path, "IR") == [("2026-01-01", 4.0), ("2026-01-02", 0.0)]
    assert b.manifestations(tmp_path, "IR", "emeutes")[0] == ("2026-01-01", 1.0)


def test_paire_et_paire_mois(tmp_path):
    _ecrire(tmp_path, "gdelt-paires-jour.csv", "jour,a,b,coop_mil,force\n2026-01-01,CN,TW,0,9\n2026-01-01,TW,CN,0,1\n")
    _ecrire(tmp_path, "gdelt-paires-jours.txt", "2026-01-01\n2026-01-02\n")
    assert b.paire(tmp_path, "CN", "TW") == [("2026-01-01", 9.0), ("2026-01-02", 0.0)]
    _ecrire(tmp_path, "gdelt-paires-mois.csv", "mois,a,b,evenements,conflit\n2026-01,RU,UA,100,60\n")
    assert b.paire_mois(tmp_path, "UA", "RU") == [("2026-01-01", 60.0)]          # paire non orientée


def test_sanctions_chine(tmp_path):
    _ecrire(tmp_path, "gdelt-chine-sanctions.csv", "pays,jour,evenements\nUS,2026-01-02,3\nUS,2026-01-02,1\n")
    _ecrire(tmp_path, "gdelt-chine-jours.txt", "2026-01-01\n2026-01-02\n")
    assert b.sanctions_chine(tmp_path, "US") == [("2026-01-01", 0.0), ("2026-01-02", 4.0)]


def test_ucdp(tmp_path):
    with gzip.open(tmp_path / "ucdp-cellules.csv.gz", "wt", encoding="utf-8") as h:
        h.write("pays,jour,cellule,evenements,morts,max_morts\nSudan,2026-01-01,1,2,10,8\nSudan,2026-01-01,2,1,5,5\nChad,2026-01-03,3,1,1,1\n")
    assert b.ucdp(tmp_path, "Sudan") == [("2026-01-01", 15.0), ("2026-01-02", 0.0), ("2026-01-03", 0.0)]
    assert b.ucdp(tmp_path, "Mali") == []


def test_voisins(tmp_path):
    _ecrire(tmp_path, "voisins.json", json.dumps({"IR": ["IQ", "TR"]}))
    _ecrire(tmp_path, "gdelt-manifestations.csv", "pays,jour,manifestations,emeutes,articles\nIQ,2026-01-01,2,0,1\nTR,2026-01-01,3,0,1\n")
    _ecrire(tmp_path, "gdelt-jours.txt", "2026-01-01\n")
    assert b.voisins(tmp_path, "IR") == [("2026-01-01", 5.0)]


def test_conflictforecast(tmp_path):
    _ecrire(tmp_path, "conflictforecast.csv", "version,isocode,periode,cible,horizon,p_all,p_text,p_hist,actuel\n"
            "2026-01,IRN,202601,anyviolence,12,40.5,1,,\n2026-01,IRN,202601,armedconf,3,9,1,,\n2026-02,IRN,202602,anyviolence,12,,1,,\n")
    assert b.conflictforecast(tmp_path, "IRN") == [("2026-01-01", 40.5)]


def test_prix_alimentaires_derniere_version(tmp_path):
    _ecrire(tmp_path, "prix-alimentaires.csv", "version,pays,mois,close,inflation\n2026-01-01,LB,2025-12,1.0,10\n2026-02-01,LB,2025-12,1.1,12\n")
    assert b.prix_alimentaires(tmp_path, "LB") == [("2025-12-01", 12.0)]
    assert b.prix_alimentaires(tmp_path, "LB", "close") == [("2025-12-01", 1.1)]


def test_acaps(tmp_path):
    _ecrire(tmp_path, "acaps-inform.csv", "instantane,crisis_id,pays,indice,categorie,derniere_maj\n2026-11-16,SDN1,SD,9.7,Very High,x\n2026-11-16,SDN2,SD,6,High,x\n2026-11-16,SDN3,SD,,,x\n")
    assert b.acaps(tmp_path, "SD") == [("2026-11-16", 9.7)]
    _ecrire(tmp_path, "acaps-risques.csv", "risk_id,pays,date_entered,last_risk_update,probability,impact,risk_level,status,risk_type,geographic_level,risk_title\n"
            "R1,UA,2026-01-01,2026-03-01,Low,3,Medium,Materialised,t,National,x\nR2,UA,2026-02-01,,Low,3,Medium,Active,t,National,x\n")
    assert b.acaps_risques(tmp_path, "UA") == [("2026-01-01", 1.0), ("2026-02-01", 2.0), ("2026-03-01", 1.0)]


def test_telegram_comptes_seulement(tmp_path):
    _ecrire(tmp_path, "telegram-messages.csv", "chaine,id,heure,vues,relaye_de,cite\nA,1,2026-01-01T10:00:00Z,5,,\nB,2,2026-01-03T10:00:00Z,5,,\n")
    assert b.telegram(tmp_path) == [("2026-01-01", 1.0), ("2026-01-02", 0.0), ("2026-01-03", 1.0)]
    assert b.telegram(tmp_path, "a") == [("2026-01-01", 1.0)]


def test_recit_russe(tmp_path):
    _ecrire(tmp_path, "recit-russe.csv", "pays,jour,articles,alibi,total_surveille\nMD,2026-01-01,3,,10\nAM,2026-01-02,1,,10\n")
    assert b.recit_russe(tmp_path, "MD") == [("2026-01-01", 3.0), ("2026-01-02", 0.0)]
    assert b.recit_russe(tmp_path, "UA") == []                                   # hors de la liste surveillée


def test_rss_routines(tmp_path):
    _ecrire(tmp_path, "rss-comptes.csv", "pays,jour,famille,articles\nCD,2026-01-01,sante,2\nCD,2026-01-01,verification,1\n")
    assert b.rss(tmp_path, "CD") == [("2026-01-01", 3.0)] and b.rss(tmp_path, "CD", "sante") == [("2026-01-01", 2.0)]
    _ecrire(tmp_path, "rss-regions.csv", "region,jour,famille,articles\nREG_X,2026-01-01,enquete,1\n")
    assert b.rss_region(tmp_path, "REG_X") == [("2026-01-01", 1.0)]
    _ecrire(tmp_path, "routines-comptes.csv", "source,jour,n\nmaison_blanche,2026-01-01,6\nkremlin,2026-01-03,1\n")
    assert b.routines(tmp_path, "maison_blanche") == [("2026-01-01", 6.0), ("2026-01-02", 0.0), ("2026-01-03", 0.0)]


def test_wikipedia(tmp_path):
    _ecrire(tmp_path, "wikipedia-comptes.json", json.dumps({
        "q1": {"articles": ["Iran"], "jours": {"2026-01-01": 10, "2026-01-02": 12}},
        "q2": {"articles": ["Iran"], "jours": {"2026-01-02": 15}},
        "q3": {"articles": ["Iran", "Israel"], "jours": {"2026-01-01": 99}}}))
    assert b.wikipedia(tmp_path, "Iran") == [("2026-01-01", 10.0), ("2026-01-02", 15.0)]


def test_inscrits_et_vrai_registre():
    noms = ["hostilites:UA", "manifestations:IR", "paire:CN:TW", "paire_mois:RU:UA", "sanctions_chine:US", "ucdp:Sudan",
            "voisins:IR", "conflictforecast:IRN", "prix_alimentaires:LB", "acaps:SD", "acaps_risques:UA", "telegram:tout",
            "recit_russe:MD", "rss:UA", "rss_region:REG_ORG_EUR_EU", "routines:maison_blanche", "wikipedia:Iran"]
    for n in noms:
        s = ad.lire(n, REG)
        assert isinstance(s, list) and all(isinstance(j, str) and isinstance(v, float) for j, v in s), n
        assert [j for j, _ in s] == sorted(j for j, _ in s), n


def test_branchements_visent_des_compartiments_existants():
    import yaml
    import ecosystemes as ec
    fiches = ec.charger()
    for x in yaml.safe_load(Path("ecosystemes/branchements-b.yml").read_text(encoding="utf-8"))["branchements"]:
        assert x["adaptateur"].split(":")[0] in ad.ADAPTATEURS, x
        if x["compartiment"] != "a_definir":
            assert any(c["id"] == x["compartiment"] for c in fiches[x["fiche"]]["compartiments"]), x
