import sonde_webamon as sw


def test_forme_sans_valeurs():
    f = sw.forme({"total": 1234, "hits": [{"domain": "mauvais.example", "ip": "1.2.3.4", "score": 9}], "q": "x"})
    assert f == {"total": 1234, "hits": [{"domain": "str", "ip": "str", "score": "int"}], "q": "str"}
    assert "infostealers" not in sw.INDEX
