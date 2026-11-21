"""Test de lecture des pages de sondages pour TOUS les pays qui tiennent des élections nationales (démocraties et
régimes à élections encadrées), décision de l'auteur du 2026-11-21, 18 h 02 : « recommence les tests d'inclusion avec la
mise en forme uniquement, pour ces pays-là ». Aucune issue, aucun score, aucun modèle : on vérifie seulement que le
robot lit les bons chiffres au bon endroit.

Pour chaque pays :
1. la page anglaise de sondages de la prochaine élection nationale (recherche « Opinion polling for the next … »),
   retenue si son titre porte le pays et une année de 2025 ou plus (ou « next ») ;
2. lecture HTML (le lecteur du bot) : tableaux, lignes, dates lisibles, colonnes ;
3. relecture « Lead » : part des lignes dont l'écart écrit par les rédacteurs est retrouvé ;
4. seconde lecture par le wikitexte : moyennes des 5 derniers sondages, colonne par colonne, comparées à la lecture
   HTML (même page : l'écart doit être nul, tolérance 0,5 point) ;
5. page dans la langue du pays (liens interlangues) : mêmes colonnes retrouvées (sigles, noms), moyennes sur la même
   fenêtre de dates (30 jours finissant au plus ancien des deux derniers sondages), tolérance 2 points.

Débit : l'API anonyme de Wikimedia est limitée (environ 500 requêtes par heure) ; une requête toutes les 7,5 s et deux
lots (paramètre `lot` : 1 ou 2). Sorties : registre/mise-au-point/formats-sondages-pays-lot{N}.json et .md.

    python mise_au_point/formats_sondages_pays.py 1
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import collecte_sondages as cs

SORTIE = Path("registre") / "mise-au-point"
PAUSE = 7.5

# (pays en français, nom anglais, adjectif anglais, langue locale de Wikipédia ou None si l'anglais est la langue du pays)
PAYS = [
    ("Afrique du Sud", "South Africa", "South African", None), ("Albanie", "Albania", "Albanian", "sq"),
    ("Algérie", "Algeria", "Algerian", "ar"), ("Allemagne", "Germany", "German", "de"),
    ("Argentine", "Argentina", "Argentine", "es"), ("Arménie", "Armenia", "Armenian", "hy"),
    ("Australie", "Australia", "Australian", None), ("Autriche", "Austria", "Austrian", "de"),
    ("Azerbaïdjan", "Azerbaijan", "Azerbaijani", "az"), ("Bangladesh", "Bangladesh", "Bangladeshi", "bn"),
    ("Belgique", "Belgium", "Belgian", "nl"), ("Bénin", "Benin", "Beninese", "fr"),
    ("Biélorussie", "Belarus", "Belarusian", "ru"), ("Bolivie", "Bolivia", "Bolivian", "es"),
    ("Bosnie-Herzégovine", "Bosnia and Herzegovina", "Bosnian", "bs"), ("Botswana", "Botswana", "Botswana", None),
    ("Brésil", "Brazil", "Brazilian", "pt"), ("Bulgarie", "Bulgaria", "Bulgarian", "bg"),
    ("Cameroun", "Cameroon", "Cameroonian", "fr"), ("Canada", "Canada", "Canadian", None),
    ("Cap-Vert", "Cape Verde", "Cape Verdean", "pt"), ("Chili", "Chile", "Chilean", "es"),
    ("Chypre", "Cyprus", "Cypriot", "el"), ("Colombie", "Colombia", "Colombian", "es"),
    ("Corée du Sud", "South Korea", "South Korean", "ko"), ("Costa Rica", "Costa Rica", "Costa Rican", "es"),
    ("Côte d'Ivoire", "Ivory Coast", "Ivorian", "fr"), ("Croatie", "Croatia", "Croatian", "hr"),
    ("Danemark", "Denmark", "Danish", "da"), ("Égypte", "Egypt", "Egyptian", "ar"),
    ("Équateur", "Ecuador", "Ecuadorian", "es"), ("Espagne", "Spain", "Spanish", "es"),
    ("Estonie", "Estonia", "Estonian", "et"), ("États-Unis", "United States", "United States", None),
    ("Éthiopie", "Ethiopia", "Ethiopian", None), ("Finlande", "Finland", "Finnish", "fi"),
    ("France", "France", "French", "fr"), ("Géorgie", "Georgia", "Georgian", "ka"),
    ("Ghana", "Ghana", "Ghanaian", None), ("Grèce", "Greece", "Greek", "el"),
    ("Guatemala", "Guatemala", "Guatemalan", "es"), ("Honduras", "Honduras", "Honduran", "es"),
    ("Hongrie", "Hungary", "Hungarian", "hu"), ("Inde", "India", "Indian", None),
    ("Indonésie", "Indonesia", "Indonesian", "id"), ("Irak", "Iraq", "Iraqi", "ar"),
    ("Iran", "Iran", "Iranian", "fa"), ("Irlande", "Ireland", "Irish", None),
    ("Islande", "Iceland", "Icelandic", "is"), ("Israël", "Israel", "Israeli", "he"),
    ("Italie", "Italy", "Italian", "it"), ("Jamaïque", "Jamaica", "Jamaican", None),
    ("Japon", "Japan", "Japanese", "ja"), ("Kazakhstan", "Kazakhstan", "Kazakh", "ru"),
    ("Kenya", "Kenya", "Kenyan", None), ("Kosovo", "Kosovo", "Kosovan", "sq"),
    ("Lettonie", "Latvia", "Latvian", "lv"), ("Liban", "Lebanon", "Lebanese", "ar"),
    ("Lituanie", "Lithuania", "Lithuanian", "lt"), ("Luxembourg", "Luxembourg", "Luxembourg", "fr"),
    ("Macédoine du Nord", "North Macedonia", "North Macedonian", "mk"), ("Malaisie", "Malaysia", "Malaysian", "ms"),
    ("Malawi", "Malawi", "Malawian", None), ("Malte", "Malta", "Maltese", None),
    ("Maroc", "Morocco", "Moroccan", "fr"), ("Maurice", "Mauritius", "Mauritian", None),
    ("Mexique", "Mexico", "Mexican", "es"), ("Moldavie", "Moldova", "Moldovan", "ro"),
    ("Mongolie", "Mongolia", "Mongolian", "mn"), ("Monténégro", "Montenegro", "Montenegrin", "sr"),
    ("Namibie", "Namibia", "Namibian", None), ("Népal", "Nepal", "Nepalese", "ne"),
    ("Nicaragua", "Nicaragua", "Nicaraguan", "es"), ("Nigeria", "Nigeria", "Nigerian", None),
    ("Norvège", "Norway", "Norwegian", "no"), ("Nouvelle-Zélande", "New Zealand", "New Zealand", None),
    ("Pakistan", "Pakistan", "Pakistani", "ur"), ("Panama", "Panama", "Panamanian", "es"),
    ("Paraguay", "Paraguay", "Paraguayan", "es"), ("Pays-Bas", "Netherlands", "Dutch", "nl"),
    ("Pérou", "Peru", "Peruvian", "es"), ("Philippines", "Philippines", "Philippine", "tl"),
    ("Pologne", "Poland", "Polish", "pl"), ("Portugal", "Portugal", "Portuguese", "pt"),
    ("République dominicaine", "Dominican Republic", "Dominican", "es"), ("République tchèque", "Czech Republic", "Czech", "cs"),
    ("Roumanie", "Romania", "Romanian", "ro"), ("Royaume-Uni", "United Kingdom", "United Kingdom", None),
    ("Russie", "Russia", "Russian", "ru"), ("Salvador", "El Salvador", "Salvadoran", "es"),
    ("Sénégal", "Senegal", "Senegalese", "fr"), ("Serbie", "Serbia", "Serbian", "sr"),
    ("Singapour", "Singapore", "Singaporean", None), ("Slovaquie", "Slovakia", "Slovak", "sk"),
    ("Slovénie", "Slovenia", "Slovenian", "sl"), ("Sri Lanka", "Sri Lanka", "Sri Lankan", "si"),
    ("Suède", "Sweden", "Swedish", "sv"), ("Suisse", "Switzerland", "Swiss", "de"),
    ("Taïwan", "Taiwan", "Taiwanese", "zh"), ("Tanzanie", "Tanzania", "Tanzanian", "sw"),
    ("Thaïlande", "Thailand", "Thai", "th"), ("Tunisie", "Tunisia", "Tunisian", "ar"),
    ("Turquie", "Turkey", "Turkish", "tr"), ("Ukraine", "Ukraine", "Ukrainian", "uk"),
    ("Uruguay", "Uruguay", "Uruguayan", "es"), ("Venezuela", "Venezuela", "Venezuelan", "es"),
    ("Zambie", "Zambia", "Zambian", None), ("Zimbabwe", "Zimbabwe", "Zimbabwean", None),
]


class Client:
    def __init__(self):
        import httpx
        import politesse
        self.c = httpx.Client(headers={"User-Agent": politesse.UA}, timeout=60, follow_redirects=True)
        self.pol, self.n = politesse, 0

    def get(self, url, **kw):
        time.sleep(PAUSE)
        self.n += 1
        r = self.c.get(url, **kw)
        if r.status_code == 429:                               # limite atteinte : on attend ce que dit le serveur, une fois
            time.sleep(min(900, int(r.headers.get("Retry-After", "120") or 120)))
            r = self.c.get(url, **kw)
        return r


def page_anglaise(cl: Client, nom: str, adj: str, vus: list) -> dict | None:
    # mots du pays sans la liste des mots vides (« United States », « United Kingdom » y perdaient tout)
    racines = {w[:5] for w in re.findall(r"[a-z]{4,}", cs.norm(f"{nom} {adj}"))} - {"repub", "democ"}
    for q in (f"Opinion polling for the next {adj} election", f"Opinion polling {adj} election 2026",
              f"Opinion polling {nom} 2027 election", f"Nationwide opinion polling {nom} election"):
        r = cl.get(f"{cs.API}/search/page", params={"q": q, "limit": 20})
        if r.status_code != 200:
            continue
        cands = []
        for p in r.json().get("pages", []):
            t = p.get("title", "")
            nt = cs.norm(t)
            if "polling" in nt and len(vus) < 12:
                vus.append(t)                                  # titres vus (diagnostic des pages introuvables)
            if "polling" not in nt or re.search(r"leadership|european parliament|referendum|approval|local|municipal|"
                                                r"mayor|regional|state election|provincial|by-election", nt):
                continue
            if not racines & {w[:5] for w in re.findall(r"[a-z]{4,}", nt)}:
                continue
            ans = [int(a) for a in re.findall(r"\b(20\d\d)\b", t)]
            if "next" in nt or (ans and max(ans) >= 2025):
                cands.append(("next" in nt, max(ans) if ans else 9999, p))
        if cands:
            return max(cands, key=lambda c: (c[0], c[1]))[2]
    return None


def derniers(lignes: list[dict], fin_max=None, debut_min=None) -> dict[str, float]:
    par: dict[str, list] = {}
    for l in lignes:
        if (fin_max and l["fin"] > fin_max) or (debut_min and l["fin"] < debut_min):
            continue
        for k, v in l["valeurs"].items():
            par.setdefault(k, []).append((l["fin"], v))
    return {k: round(sum(x for _, x in sorted(v)[-5:]) / len(sorted(v)[-5:]), 2) for k, v in par.items()}


PERSONNE_PARTI = re.compile(r"^\S+(\s+\S+)+\s*\([^)]+\)\s*$")     # « Magdalena Andersson (S) »


def tableau_recent(lignes: list[dict]) -> int | None:
    """Le tableau principal d'intentions de vote, avec les leçons des passages précédents : pas de duel (deux colonnes),
    pas de tableau dont les moyennes sortent de 30-110 % (scénarios mêlés), pas de tableau de chefs « Personne (Parti) »
    quand un autre tableau convient (Suède) ; puis le plus récent (à 60 jours près du plus récent de la page), puis le
    plus fourni. Les lignes elles-mêmes ont déjà passé les filtres du lecteur (agrégateurs, résultats, lignes > 110 %,
    matrices de duels)."""
    ts: dict = {}
    for l in lignes:
        ts.setdefault(l["table"], []).append(l)
    cands = []
    for t, ls in ts.items():
        m = derniers(ls)
        if len(m) < 3 or not 30 <= sum(m.values()) <= 110:
            continue
        if any(re.search(r"\b(approve|disapprove|direction|wrong track|satisf|favou?rable|unfavou?rable|"
                         r"aprueba|desaprueba)\b", cs.norm(k)) for k in m):
            continue                                           # popularité ou « bonne direction » : pas un vote
        chefs = sum(bool(PERSONNE_PARTI.match(k)) for k in m) / len(m)
        cands.append((t, chefs < 0.5, max(l["fin"] for l in ls), ls))
    if not cands:
        return None
    plus_recent = max(c[2] for c in cands)
    an = lambda ls: sum(1 for l in ls if l["fin"] >= plus_recent - timedelta(days=365))
    return max(cands, key=lambda c: (c[1], an(c[3]), c[2]))[0]   # le plus de sondages dans l'année, puis le plus récent


def examiner(cl: Client, fr: str, nom: str, adj: str, lang: str | None) -> dict:
    out = {"pays": fr}
    vus: list = []
    p = page_anglaise(cl, nom, adj, vus)
    if not p:
        return {**out, "statut": "page anglaise introuvable", "titres_vus": vus}
    out["page"] = p["title"]
    h = cl.get(f"{cs.API}/page/{p['key']}/html")
    if h.status_code != 200:
        return {**out, "statut": f"page illisible (HTTP {h.status_code})"}
    gs = cs.grilles(h.text)
    ls = cs.sondages_grilles(gs, 2026)
    out.update({"tableaux_html": len(gs), "lignes_lues": len(ls)})
    if not ls:
        return {**out, "statut": "aucun tableau de sondages lisible"}
    t = tableau_recent(ls)
    if t is None:
        return {**out, "statut": "aucun tableau principal (duels, scénarios ou tableaux de chefs seulement)"}
    lt = [l for l in ls if l["table"] == t]
    m_html = derniers(lt)
    nv, acc = cs.accord_lead(lt)
    out.update({"dernier_sondage": max(l["fin"] for l in lt).isoformat(), "colonnes": list(m_html)[:12],
                "total_moyennes": round(sum(m_html.values()), 1), "lead": {"lignes": nv, "accord": acc}})
    # seconde lecture : wikitexte, tableau aux mêmes colonnes
    w = cl.get(f"{cs.API}/page/{p['key']}")
    if w.status_code == 200 and (src := w.json().get("source")):
        lw = cs.sondages_grilles(cs.grilles_wikitexte(src), 2026)
        best, score = None, 0.0
        for tw in {l["table"] for l in lw}:
            mw_ = derniers([l for l in lw if l["table"] == tw])
            if len(mw_) < 3 or not 30 <= sum(mw_.values()) <= 110:     # mêmes refus que pour la lecture HTML
                continue
            cols = set(mw_)
            j = len(cols & set(m_html)) / max(1, len(cols | set(m_html)))
            if j > score:
                best, score = tw, j
        if best is not None and score >= 0.5:
            m_w = derniers([l for l in lw if l["table"] == best], max(l["fin"] for l in lt))   # même date de fin
            communs = [k for k in m_html if k in m_w]
            ok = [k for k in communs if abs(m_w[k] - m_html[k]) <= 0.5]
            out["wikitexte"] = {"colonnes_communes": len(communs), "concordantes": len(ok),
                                "divergentes": {k: [m_html[k], m_w[k]] for k in communs if k not in ok}}
        else:
            out["wikitexte"] = {"tableau_correspondant": False, "lignes_lues": len(lw)}
    else:
        out["wikitexte"] = {"tableau_correspondant": False, "lignes_lues": 0, "motif": f"source illisible (HTTP {w.status_code})"}
    # langue du pays
    if lang:
        r = cl.get(f"{cs.API}/page/{p['key']}/links/language")
        lien = next((x for x in (r.json() if r.status_code == 200 else []) if x.get("code") == lang), None)
        if not lien:
            out["langue_locale"] = {"langue": lang, "statut": "pas de page liée"}
        else:
            base = cs.API.rsplit("/", 1)[0] + f"/{lang}"
            hl = cl.get(f"{base}/page/{lien['key']}/html")
            gl = cs.grilles(hl.text) if hl.status_code == 200 else []
            ll = cs.sondages_grilles(gl, 2026)
            if not ll:                                          # journal seulement : premières lignes d'en-tête
                for g in [g for g in gl if len(g) >= 3][:3]:
                    print(f"  [{fr} {lang}] en-tête : {[c[:20] for c in g[0][:8]]} | {[c[:20] for c in g[1][:8]]}")
            loc = {"langue": lang, "page": lien["title"], "lignes_lues": len(ll)}
            tl = tableau_recent(ll) if ll else None
            if ll and tl is None:
                loc["statut"] = "aucun tableau principal (duels, scénarios ou tableaux de chefs seulement)"
            if tl is not None:
                lt2 = [l for l in ll if l["table"] == tl]
                fin = min(max(l["fin"] for l in lt), max(l["fin"] for l in lt2))
                deb = fin - timedelta(days=30)
                a, b = derniers(lt, fin, deb), derniers(lt2, fin, deb)
                if not a or not b:
                    loc["statut"] = "pas de période commune (30 jours) entre les deux pages"
                    a, b = {}, {}
                paires = {k: c for k in a if (c := cs.colonne(k, list(b)))}
                ok = [k for k, c in paires.items() if abs(a[k] - b[c]) <= 2]
                loc.update({"dernier_sondage": max(l["fin"] for l in lt2).isoformat(), "colonnes": list(b)[:12],
                            "colonnes_appariees": len(paires), "concordantes": len(ok),
                            "divergentes": {k: [a[k], b[c]] for k, c in paires.items() if k not in ok}})
            out["langue_locale"] = loc
    pb = []
    if not 30 <= out["total_moyennes"] <= 110:
        pb.append("total des moyennes aberrant")
    if nv >= 3 and acc < 0.8:
        pb.append("relecture « Lead » en échec")
    wt = out.get("wikitexte") or {}
    if wt.get("divergentes"):
        pb.append("wikitexte divergent")
    if wt.get("tableau_correspondant") is False:
        pb.append("wikitexte : pas de tableau correspondant")
    ll_ = out.get("langue_locale") or {}
    if ll_.get("divergentes"):
        pb.append("langue locale divergente")
    if ll_.get("lignes_lues") == 0:
        pb.append("langue locale : aucun tableau lisible")
    if lang and ll_.get("lignes_lues") and not ll_.get("colonnes_appariees") and not ll_.get("statut"):
        pb.append("langue locale : aucune colonne appariée")
    out["problemes"] = pb
    out["statut"] = "lu" if not pb else "à corriger"
    return out


def principal(lot: int) -> int:
    pays = PAYS[: len(PAYS) // 2] if lot == 1 else PAYS[len(PAYS) // 2:]
    cl = Client()
    res = []
    for fr, nom, adj, lang in pays:
        try:
            r = examiner(cl, fr, nom, adj, lang)
        except Exception as e:
            r = {"pays": fr, "statut": "erreur", "motif": f"{type(e).__name__}: {e}"[:300]}
        res.append(r)
        print(f"{fr} : {r['statut']} {r.get('problemes', '')}", flush=True)
    SORTIE.mkdir(parents=True, exist_ok=True)
    base = SORTIE / f"formats-sondages-pays-lot{lot}"
    base.with_suffix(".json").write_text(json.dumps({"lot": lot, "requetes": cl.n, "pays": res}, ensure_ascii=False,
                                                    indent=1, default=str), encoding="utf-8")
    import collections
    md = [f"# Lecture des pages de sondages, lot {lot} ({len(res)} pays, {cl.n} requêtes)", "",
          "Statuts : " + ", ".join(f"{k} {v}" for k, v in collections.Counter(r["statut"] for r in res).items()), ""]
    for r in sorted(res, key=lambda r: (r["statut"] == "lu", r["pays"])):
        md.append(f"- **{r['pays']}** : {r['statut']}" + (f" — {', '.join(r['problemes'])}" if r.get("problemes") else ""))
        if r.get("page"):
            md.append(f"  - page : {r['page']} ; dernier sondage {r.get('dernier_sondage')} ; colonnes "
                      f"{r.get('colonnes')} ; total {r.get('total_moyennes')} ; Lead {r.get('lead')}")
        if r.get("wikitexte"):
            md.append(f"  - wikitexte : {r['wikitexte']}")
        if r.get("langue_locale"):
            md.append(f"  - langue locale : {r['langue_locale']}")
    base.with_suffix(".md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(principal(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
