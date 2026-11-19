import collecte_opencheck as oc

BODS = {"bods": [
    {"recordId": "e1", "recordType": "entity", "recordDetails": {"name": "Groupe Média SA"}},
    {"recordId": "e2", "recordType": "entity", "recordDetails": {"name": "Holding Familiale SAS"}},
    {"recordId": "p1", "recordType": "person", "recordDetails": {"names": [{"fullName": "Vincent Bolloré"}]}},
    {"recordId": "p2", "recordType": "person", "recordDetails": {"names": [{"fullName": "Jean Privé"}]}},
    {"recordId": "r1", "recordType": "relationship", "recordDetails": {"subject": "e1", "interestedParty": "e2",
                                                                       "interests": [{"share": {"exact": 60}}]}},
    {"recordId": "r2", "recordType": "relationship", "recordDetails": {"subject": "e2", "interestedParty": "p1", "interests": []}},
    {"recordId": "r3", "recordType": "relationship", "recordDetails": {"subject": "e1", "interestedParty": "p2", "interests": []}},
]}


def test_detenteurs_sans_personne_privee():
    d = oc.detenteurs(oc.enregistrements(BODS), {"vincent bolloré"})
    assert d["societes"] == [{"nom": "Holding Familiale SAS", "part": 60}]
    assert d["personnes_publiques"] == [{"nom": "Vincent Bolloré", "part": None}]
    assert d["autres_personnes"] == 1                                  # la personne privée n'est que comptée


def test_noms_publics_viennent_de_nos_tables():
    p = oc.noms_publics()
    assert "vincent bolloré" in p and "bernard arnault" in p
