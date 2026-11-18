import unittest

import collecte_telegram as ct

PAGE = """<html><div class="tgme_widget_message_wrap js-widget_message_wrap">
<div class="tgme_widget_message" data-post="DeepStateUA/101">
<a class="tgme_widget_message_forwarded_from_name" href="https://t.me/rybar/555"><span dir="auto">Rybar</span></a>
<div class="tgme_widget_message_text">TEXTE A NE JAMAIS GARDER <a href="https://t.me/warmonitors/9">x</a> <a href="https://t.me/share/url?u=a">p</a></div>
<span class="tgme_widget_message_views">189K</span>
<a class="tgme_widget_message_date" href="https://t.me/DeepStateUA/101"><time datetime="2026-11-18T02:10:00+02:00" class="time">02:10</time></a>
</div></div>
<div class="tgme_widget_message_wrap js-widget_message_wrap">
<div class="tgme_widget_message" data-post="DeepStateUA/102">
<span class="tgme_widget_message_forwarded_from_name">Chaîne privée</span>
<span class="tgme_widget_message_views">1.2M</span>
<time datetime="2026-11-18T03:00:00+00:00" class="time">03:00</time>
</div></div></html>"""


class TLecture(unittest.TestCase):
    def test_vues(self):
        self.assertEqual(ct.vues("189K"), 189000)
        self.assertEqual(ct.vues("1.2M"), 1200000)
        self.assertEqual(ct.vues("742"), 742)
        self.assertIsNone(ct.vues("abc"))

    def test_page(self):
        ms = ct.lire_page(PAGE, "DeepStateUA")
        self.assertEqual(len(ms), 2)
        a, b = ms
        self.assertEqual((a["id"], a["heure"], a["vues"], a["relaye_de"], a["cite"]),
                         (101, "2026-11-18T00:10:00Z", 189000, "rybar", "warmonitors"))
        self.assertEqual((b["relaye_de"], b["cite"], b["vues"]), ("~", "", 1200000))

    def test_aucun_texte(self):
        for m in ct.lire_page(PAGE, "DeepStateUA"):
            self.assertEqual(set(m), set(ct.MS_C))
            self.assertNotIn("TEXTE", " ".join(map(str, m.values())))


def msg(ch, i, jour, relaye="", cite=""):
    return {"chaine": ch, "id": str(i), "heure": f"{jour}T12:00:00Z", "vues": "", "relaye_de": relaye, "cite": cite}


class TListe(unittest.TestCase):
    def chaines(self):
        return [{"chaine": c, "groupe": g, "origine": "cheyenne", "ajoutee_le": "2026-09-01", "statut": "active"}
                for c, g in (("a_chaine", "UKRAINE"), ("b_chaine", "UKRAINE"), ("c_chaine", "MOYEN-ORIENT"), ("d_muette", "ASIE"))]

    def test_entree_muette_disparue(self):
        ch = self.chaines()
        ms = [msg("a_chaine", i, "2026-11-10", relaye="nouvelle1") for i in range(4)]
        ms += [msg("b_chaine", 10, "2026-11-11", cite="nouvelle1")]
        ms += [msg("a_chaine", 20 + i, "2026-11-12", cite="solo_cite") for i in range(6)]   # 1 seule chaîne citante
        ms += [msg("c_chaine", 30, "2026-11-12"), msg("d_muette", 1, "2026-09-02")]
        rel = [{"releve": f"2026-11-{j:02d}T22:00Z", "chaine": "c_chaine", "statut_http": "404", "messages_lus": "0"}
               for j in range(1, 8)]
        mv = ct.mettre_a_jour(ch, ms, rel, "2026-12-01")
        par = {m["chaine"]: m["mouvement"] for m in mv}
        self.assertEqual(par, {"nouvelle1": "entrée", "c_chaine": "disparue", "d_muette": "muette"})
        n = next(x for x in ch if x["chaine"] == "nouvelle1")
        self.assertEqual((n["groupe"], n["origine"]), ("UKRAINE", "relais"))

    def test_plafond_entrees(self):
        ch = self.chaines()
        ms = []
        for k in range(15):
            for c in ("a_chaine", "b_chaine"):
                ms += [msg(c, 100 * k + i + (50 if c == "b_chaine" else 0), "2026-11-20", relaye=f"cand_{k:02d}") for i in range(3)]
        mv = ct.mettre_a_jour(ch, ms, [], "2026-12-01")
        self.assertEqual(sum(m["mouvement"] == "entrée" for m in mv), ct.ENTREES_MAX)


class Faux:
    """Client factice : trois pages de 2 messages, ids décroissants."""
    def __init__(self):
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        avant = int(url.split("before=")[1]) if "before=" in url else 107
        corps = "".join(f'<div class="tgme_widget_message_wrap"><div data-post="x_chaine/{i}">'
                        f'<time datetime="2026-11-18T0{i - 100}:00:00+00:00"></time></div></div>'
                        for i in (avant - 2, avant - 1) if i > 100)
        return type("R", (), {"status_code": 200, "text": corps})()


class TRemonter(unittest.TestCase):
    def setUp(self):
        ct.time.sleep = lambda s: None

    def test_jusqu_au_connu(self):
        f = Faux()
        code, ms, pages, complet = ct.remonter(f, "x_chaine", 103, "2000-01-01", 15)
        self.assertEqual((code, pages, complet), ("200", 2, True))
        self.assertEqual(sorted(m["id"] for m in ms), [103, 104, 105, 106])

    def test_plafond(self):
        code, ms, pages, complet = ct.remonter(Faux(), "x_chaine", 0, "2000-01-01", 2)
        self.assertEqual((pages, complet), (2, False))

    def test_debut_de_chaine(self):
        code, ms, pages, complet = ct.remonter(Faux(), "x_chaine", 0, "2000-01-01", 15)
        self.assertTrue(complet)
        self.assertEqual(min(m["id"] for m in ms), 101)

    def test_bots_exclus(self):
        page = PAGE.replace("https://t.me/warmonitors/9", "https://t.me/newsDeepStatebot")
        self.assertEqual(ct.lire_page(page, "DeepStateUA")[0]["cite"], "")


if __name__ == "__main__":
    unittest.main()


class TRelaisFormes(unittest.TestCase):
    def test_formes_de_relais(self):
        formes = [
            '<div class="tgme_widget_message_forwarded_from accent_color">Forwarded from <a class="tgme_widget_message_forwarded_from_name" href="https://t.me/rybar/77"><span dir="auto">R</span></a></div>',
            '<div class="tgme_widget_message_forwarded_from accent_color">Forwarded from <a href="https://t.me/rybar/77" class="tgme_widget_message_forwarded_from_name">R</a></div>',
            '<div class="tgme_widget_message_forwarded_from"><a class="tgme_widget_message_forwarded_from_name" href="https://t.me/rybar"><span>R</span></a> <a class="tgme_widget_message_forwarded_from_author">auteur</a></div>',
        ]
        for f in formes:
            page = ('<div class="tgme_widget_message_wrap"><div data-post="x_chaine/5">' + f +
                    '<time datetime="2026-11-18T03:00:00+00:00"></time></div></div>')
            self.assertEqual(ct.lire_page(page, "x_chaine")[0]["relaye_de"], "rybar", f)


class TRelaisSansLien(unittest.TestCase):
    def test_relais_sans_lien_aucun_nom(self):
        f = ('<div class="tgme_widget_message_forwarded_from accent_color"><span class="tgme_widget_message_forwarded_from_name">'
             '<span dir="auto">Jean Dupont</span></span><span class="tgme_widget_message_forwarded_from_author" dir="auto">J. D.</span></div>')
        page = ('<div class="tgme_widget_message_wrap"><div data-post="x_chaine/5">' + f +
                '<time datetime="2026-11-18T03:00:00+00:00"></time></div></div>')
        m = ct.lire_page(page, "x_chaine")[0]
        self.assertEqual(m["relaye_de"], "~")
        self.assertNotIn("Dupont", " ".join(map(str, m.values())))
        self.assertEqual(ct.mettre_a_jour([], [dict(m, id="5")] * 9, [], "2026-12-01"), [])
