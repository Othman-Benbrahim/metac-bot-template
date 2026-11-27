import couches as c


def r(j, u, t, d="ex.org", n=(), p=(), m=()):
    return {"j": j, "u": u, "t": t, "d": d, "n": list(n), "p": list(p), "m": list(m)}


def test_nuage_exclut_les_articles_traites():
    rows = [r("2026-12-01", "https://a/1", "Titre un", n=["Pezeshkian"]),
            r("2026-12-01", "https://a/2", "Titre deux", n=["Pezeshkian"]),
            r("2026-12-01", "https://a/3", "Titre trois", n=["Pezeshkian"])]
    nu = c.nuage(rows, {"https://a/3"})
    assert nu[0]["terme"] == "Pezeshkian" and nu[0]["n"] == 2
    assert {x["lien"] for x in nu[0]["articles"]} == {"https://a/1", "https://a/2"}


def test_montee_respecte_la_chauffe_et_les_seuils():
    jour = [r("2026-12-15", f"https://a/{i}", f"Titre {i}", n=["Mamdani"]) for i in range(4)]
    histo_court = [r(f"2026-12-0{k}", f"https://h/{k}", "x") for k in range(1, 6)]   # 5 jours < 7
    assert c.montee(jour, histo_court, "2026-12-15") == []
    histo = [r(f"2026-12-{k:02d}", f"https://h/{k}", "x") for k in range(1, 15)]
    a = c.montee(jour, histo, "2026-12-15")
    assert a and a[0]["terme"] == "Mamdani" and a[0]["n_jour"] == 4
    habituel = histo + [r(f"2026-12-{k:02d}", f"https://m/{k}", "y", n=["Mamdani"]) for k in range(1, 15)]
    assert c.montee(jour, habituel, "2026-12-15")            # 1 par jour d'habitude : 4 >= 4 x 1, seuil inclusif
    habituel2 = habituel + [r(f"2026-12-{k:02d}", f"https://m2/{k}", "z", n=["Mamdani"]) for k in range(1, 15)]
    assert c.montee(jour, habituel2, "2026-12-15") == []


def test_inattendue():
    histo = [r("2026-12-01", f"https://n/{i}", "NASA launches Artemis mission", d="nasa.gov") for i in range(25)]
    jour = [r("2026-12-02", "https://n/x", "Will Israel and Hamas agree to a ceasefire?", d="nasa.gov")]
    fam_h, fam_j = c._famille(histo[0]["t"]), c._famille(jour[0]["t"])
    a = c.inattendue(jour, histo)
    if fam_j and fam_j != fam_h:
        assert a and a[0]["source"] == "nasa.gov"


def test_classement_une_histoire_une_fois_et_source_primaire():
    et = {"fda.gov": {"type": "primaire_officielle", "proprietaire_ou_financeur": "FDA"},
          "cnn.com": {"type": "presse_generaliste", "proprietaire_ou_financeur": "WBD"}}
    rows = [r("2026-12-01", "https://cnn.com/x", "FDA approves Leqembi Iqlik", d="cnn.com", n=["FDA", "Leqembi Iqlik"]),
            r("2026-12-01", "https://fda.gov/y", "FDA approves Leqembi Iqlik injection", d="fda.gov",
              n=["FDA", "Leqembi Iqlik"])]
    out = c.classement(rows, set(), set(), et, 5)
    assert len(out) == 1 and out[0]["source"] == "fda.gov" and out[0]["sources_independantes"] == 2
