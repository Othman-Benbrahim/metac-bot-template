"""0.10.187 : pilote des mécanismes tirés des revues (lecture OAI-PMH, filtre)."""
import os
import tempfile
import unittest

os.environ["ALPHABET_REGISTRE"] = tempfile.mkdtemp(prefix="registre-")
import mecanismes_revues as mr

XML = b"""<?xml version="1.0"?><OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"><ListRecords>
<record><header><identifier>oai:x:1</identifier></header><metadata>
<oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/" xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:title>La soudure et les tensions pastorales au Sahel</dc:title><dc:date>2019-06-01</dc:date>
<dc:description>Pendant la soudure, les conflits entre agriculteurs et \xc3\xa9leveurs augmentent...</dc:description>
<dc:identifier>https://journals.openedition.org/echogeo/1</dc:identifier><dc:coverage>Niger</dc:coverage>
<dc:type>article</dc:type></oai_dc:dc></metadata></record>
<resumptionToken>abc</resumptionToken></ListRecords></OAI-PMH>"""


class TestRevues(unittest.TestCase):
    def test_page(self):
        arts, tok, err = mr.lire_page(XML)
        self.assertEqual((len(arts), tok, err), (1, "abc", None))
        self.assertEqual(arts[0]["lieux"], ["Niger"])
        self.assertTrue(mr.pertinent(arts[0]))
        self.assertFalse(mr.pertinent(dict(arts[0], date="1998-01-01")))

    def test_erreur(self):
        x = b'<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"><error code="badArgument">set</error></OAI-PMH>'
        self.assertEqual(mr.lire_page(x)[2], "badArgument: set")


class TestVerifier(unittest.TestCase):
    def test_verifier_sans_reseau(self):
        from unittest import mock

        class R:
            status_code = 200
            content = XML
            text = ""

        class C:
            def __init__(self, **k): pass
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def get(self, *a, **k): return R()

        with mock.patch.object(mr.httpx, "Client", C), mock.patch.object(mr.time, "sleep", lambda s: None):
            self.assertEqual(mr.verifier(), 0)


if __name__ == "__main__":
    unittest.main()
