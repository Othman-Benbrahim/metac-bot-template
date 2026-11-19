"""0.10.323 : adaptateurs des sources dormantes, lot A (fichiers synthétiques au format réel, puis le vrai registre)."""
import json
from pathlib import Path

import pytest

import adaptateurs as ad
import adaptateurs_sources_a as sa


def _ecrire(tmp: Path, nom: str, texte: str):
    (tmp / nom).write_text(texte, encoding="utf-8")


def _jsonl(tmp: Path, nom: str, lignes: list[dict]):
    _ecrire(tmp, nom, "\n".join(json.dumps(x) for x in lignes) + "\n")


def test_inscrits():
    for n in ("avions", "tfr", "violations", "radar", "certificats", "federal_register", "congres", "tribunaux",
              "elections", "memoire", "feries_chine", "publications_nbs", "calendrier_nbs"):
        assert n in ad.ADAPTATEURS


def test_avions_moyenne_par_jour_et_zero_si_absent(tmp_path):
    _ecrire(tmp_path, "militaires-adsbfi.csv", "releve,pays,appareils\n2026-11-17T08:00Z,US,10\n2026-11-17T20:00Z,US,20\n"
                                                "2026-11-17T20:00Z,FR,2\n2026-11-18T08:00Z,FR,4\n")
    assert ad.lire("avions:US", tmp_path) == [("2026-11-17", 15.0), ("2026-11-18", 0.0)]
    assert ad.lire("avions", tmp_path) == [("2026-11-17", 16.0), ("2026-11-18", 4.0)]


def test_tfr_par_creation_depuis_le_premier_releve(tmp_path):
    _jsonl(tmp_path, "faa-tfr.jsonl", [
        {"notam": "1", "type": "SECURITY", "cree_le": "11/17/2026", "vu_le": "2026-11-19"},
        {"notam": "2", "type": "SPECIAL", "cree_le": "11/18/2026", "vu_le": "2026-11-19"},
        {"notam": "3", "type": "VIP", "cree_le": "10/08/2015", "vu_le": "2026-11-19"}])
    s = dict(ad.lire("tfr", tmp_path))
    assert s["2026-11-17"] == 1.0 and s["2026-11-18"] == 1.0 and min(s) == "2026-10-20"
    assert sum(dict(ad.lire("tfr:SECURITY", tmp_path)).values()) == 1.0


def test_violations(tmp_path):
    _ecrire(tmp_path, "violationswatch-comptes.csv", "pays,jour,gravite,incidents\nUkraine,2026-11-06,High,2\n"
                                                      "Yemen,2026-11-08,Critical,1\n")
    assert ad.lire("violations:Ukraine", tmp_path) == [("2026-11-06", 2.0), ("2026-11-07", 0.0), ("2026-11-08", 0.0)]
    assert ad.lire("violations:tous:Critical", tmp_path)[-1] == ("2026-11-08", 1.0)


def test_radar_coupures_en_cours(tmp_path):
    _ecrire(tmp_path, "radar-coupures.csv", "id,pays,debut,fin,cause,type,portee,motif\n1,IQ,2026-06-02,2026-06-03,"
                                            "GOVERNMENT_DIRECTED,REGIONAL,,examens\n2,LC,2026-06-03,2026-06-03,CABLE_CUT,NETWORK,,\n")
    _ecrire(tmp_path, "radar-couverture.txt", "2026-06-01\n")
    assert ad.lire("radar", tmp_path) == [("2026-06-01", 0.0), ("2026-06-02", 1.0), ("2026-06-03", 2.0)]
    assert ad.lire("radar:IQ", tmp_path)[2] == ("2026-06-03", 1.0)


def test_certificats(tmp_path):
    _jsonl(tmp_path, "certificats.jsonl", [{"domaine": "openai.com", "nom": "a", "vu_le": "2026-01-01"},
                                           {"domaine": "x.ai", "nom": "b", "vu_le": "2026-01-03"}])
    assert ad.lire("certificats:openai.com", tmp_path) == [("2026-01-01", 1.0)]
    assert len(ad.lire("certificats", tmp_path)) == 3


def test_federal_register(tmp_path):
    _jsonl(tmp_path, "federal-register.jsonl", [
        {"numero": "1", "type": "Rule", "agences": ["Treasury Department"], "depose_le": "2026-11-16"},
        {"numero": "2", "type": "Notice", "agences": ["Energy Department"], "depose_le": "2026-11-18"}])
    assert ad.lire("federal_register", tmp_path) == [("2026-11-16", 1.0), ("2026-11-17", 0.0), ("2026-11-18", 1.0)]
    assert ad.lire("federal_register:Rule", tmp_path) == [("2026-11-16", 1.0)]
    assert ad.lire("federal_register:tous:energy", tmp_path) == [("2026-11-18", 1.0)]


def test_congres_et_tribunaux_sans_noms(tmp_path):
    _jsonl(tmp_path, "congres-reunions.jsonl", [{"id": "1", "chambre": "House", "date": "2026-11-19"},
                                                {"id": "2", "chambre": "Senate", "date": "2026-11-19"}])
    _jsonl(tmp_path, "congres-nominations.jsonl", [{"id": "n1", "description": "X", "recue_le": "2026-02-11"}])
    _jsonl(tmp_path, "tribunaux-dossiers.jsonl", [{"id": "d", "tribunal": "scotus", "affaire": "A v. B", "depot": "2026-11-12"}])
    assert ad.lire("congres", tmp_path) == [("2026-11-19", 2.0)]
    assert ad.lire("congres:reunions:Senate", tmp_path) == [("2026-11-19", 1.0)]
    assert ad.lire("congres:nominations", tmp_path) == [("2026-02-11", 1.0)]
    assert ad.lire("tribunaux:scotus", tmp_path) == [("2026-11-12", 1.0)]


def test_elections_jours_avant(tmp_path):
    _ecrire(tmp_path, "elections.csv", "qid,pays,date,type,nom\nQ1,FR,2026-01-03,election,a\nQ2,DE,2026-01-01,election,b\n")
    assert ad.lire("elections:FR", tmp_path) == [("2026-01-01", 2.0), ("2026-01-02", 1.0), ("2026-01-03", 0.0)]
    assert ad.lire("elections:XX", tmp_path) == []


def test_memoire_annuelle(tmp_path, monkeypatch):
    from datetime import date
    monkeypatch.setattr(sa, "_aujourdhui", lambda: date(2026, 5, 1))
    _ecrire(tmp_path, "dates-memoire.csv", "pays,mois_jour,libelle\nRU,05-09,Jour de la Victoire\n")
    s = dict(ad.lire("memoire:RU", tmp_path))
    assert s["2026-05-01"] == 8.0 and s["2026-05-09"] == 0.0 and s["2026-05-10"] == 364.0


def test_feries_chine(tmp_path):
    _ecrire(tmp_path, "jours-feries-chine.csv", "debut,fin,fete\n2026-10-01,2026-10-07,Fête nationale\n")
    s = dict(ad.lire("feries_chine", tmp_path))
    assert len(s) == 365 and s["2026-10-03"] == 1.0 and s["2026-10-08"] == 0.0


def test_nbs_paru_et_prevu(tmp_path):
    _ecrire(tmp_path, "publications-nbs.csv", "jour,publication,titre,url\n2026-01-09,ipc,t,u\n2026-01-09,ipp,t,u\n")
    _ecrire(tmp_path, "calendrier-nbs.csv", "publication,date_prevue\nipc,2026-01-09\nipc,2026-02-11\n")
    assert ad.lire("publications_nbs", tmp_path) == [("2026-01-09", 2.0)]
    s = dict(ad.lire("calendrier_nbs:ipc", tmp_path))
    assert s["2026-01-01"] == 8.0 and s["2026-01-09"] == 0.0 and s["2026-01-10"] == 32.0


@pytest.mark.parametrize("nom", ["avions", "avions:US", "tfr", "tfr:SECURITY", "violations", "radar", "radar:IR",
                                 "certificats", "federal_register", "congres", "congres:nominations", "tribunaux:scotus",
                                 "elections:US", "memoire:RU", "feries_chine", "publications_nbs", "calendrier_nbs"])
def test_vrai_registre(nom):
    s = ad.lire(nom)
    assert isinstance(s, list)
    assert all(isinstance(j, str) and isinstance(v, float) for j, v in s)
    assert [j for j, _ in s] == sorted(j for j, _ in s)
