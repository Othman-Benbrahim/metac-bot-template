"""Lecteur générique des cartes publiées — bot 0.10.470 (0.10.472 : champs de lecture étendus, agrégat pays-année,
fichiers complémentaires, relecture quand la façon de lire change), hors cadre.

Décision de l'auteur, 2026-11-23, 7 h 38 - 7 h 53 : « comme un flux RSS, mais pour les cartes ». Chaque carte a son
fichier de lecture dans cartes/*.yaml (le « standard de lecture ») : où trouver les fichiers, comment les lire, quoi en
tirer. Ce programme ne contient rien de propre à une carte. Pour chacune :
1. il lit la page de l'émetteur (robots.txt respecté) et y trouve, par motif, la version la plus récente de chaque
   fichier ;
2. il ne retélécharge un fichier que si son adresse a changé depuis le dernier passage ;
3. il en tire des AGRÉGATS par pays et par mois (nombre d'événements, par catégorie, et somme), jamais les lignes ni le
   texte ;
4. il garde la référence (adresse, date de lecture, taille, empreinte SHA-256, nombre de lignes) et supprime le fichier.

Registres : registre/cartes/<id>-pays-mois.csv (agrégats), registre/cartes/references.csv (une ligne par lecture,
ajout seul). Les pays sont rattachés à notre table (ecosystemes/codes-pays-fips.csv) par leur nom anglais ; ceux qui
ne se rattachent pas gardent leur nom d'origine et sont signalés dans le journal.
"""
from __future__ import annotations

import csv
import hashlib
import io
import os
import re
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import yaml

DOSSIER = Path("cartes")
REG = Path(os.environ.get("ALPHABET_REGISTRE", "registre")) / "cartes"
REFS = REG / "references.csv"
CODES = Path("ecosystemes/codes-pays-fips.csv")
COLS_REF = ["carte", "role", "url", "lu_le", "octets", "sha256", "lignes"]
csv.field_size_limit(10 ** 8)

# noms de l'UCDP (et d'autres émetteurs) qui ne correspondent pas aux noms courants de notre table
ALIAS = {"dr congo": "COD", "congo": "COG", "russia": "RUS", "ivory coast": "CIV", "cote d'ivoire": "CIV",
         "yemen": "YEM", "myanmar": "MMR", "burma": "MMR", "cambodia": "KHM", "kingdom of eswatini": "SWZ",
         "swaziland": "SWZ", "united states of america": "USA", "united states": "USA", "united kingdom": "GBR",
         "iran": "IRN", "syria": "SYR", "laos": "LAO", "vietnam": "VNM", "south korea": "KOR", "north korea": "PRK",
         "bosnia-herzegovina": "BIH", "bosnia and herzegovina": "BIH", "macedonia, fyr": "MKD", "north macedonia": "MKD",
         "macedonia": "MKD", "serbia": "SRB", "yugoslavia": "SRB", "kosovo": "XKX", "moldova": "MDA", "tanzania": "TZA",
         "venezuela": "VEN", "bolivia": "BOL", "east timor": "TLS", "timor-leste": "TLS", "gambia": "GMB",
         "cape verde": "CPV", "zimbabwe": "ZWE", "madagascar": "MDG", "palestine": "PSE", "turkey": "TUR",
         "czech republic": "CZE", "brunei": "BRN", "taiwan": "TWN", "guinea-bissau": "GNB", "sudan": "SDN",
         "south sudan": "SSD", "comoros": "COM", "solomon islands": "SLB", "papua new guinea": "PNG",
         "trinidad and tobago": "TTO", "kyrgyzstan": "KGZ", "azerbaijan": "AZE", "georgia": "GEO", "ukraine": "UKR",
         "lebanon": "LBN", "libya": "LBY", "egypt": "EGY", "algeria": "DZA", "morocco": "MAR", "western sahara": "ESH"}


def nom_cle(n: str) -> str:
    """« Russia (Soviet Union) » → « russia » : on retire la parenthèse historique de l'UCDP."""
    return re.sub(r"\s*\(.*?\)\s*", "", n or "").strip().lower()


def table_pays() -> dict[str, str]:
    lignes = [l for l in CODES.read_text(encoding="utf-8").splitlines() if l and not l.startswith("#")]
    out = {}
    for r in csv.DictReader(lignes):
        for n in (r.get("nom"), r.get("nom_fr")):
            if n:
                out[nom_cle(n)] = r["iso3"]
    out.update(ALIAS)
    return out


def specs(dossier: Path = DOSSIER) -> list[dict]:
    return [yaml.safe_load(f.read_text(encoding="utf-8")) for f in sorted(dossier.glob("*.yaml"))]


def choisir_liens(html: str, spec: dict, base: str) -> dict[str, str]:
    """Pour chaque rôle, le lien de la page qui suit le motif, version la plus récente (nombres comparés dans l'ordre)."""
    from urllib.parse import urljoin
    liens = set(re.findall(r'href="([^"]+)"', html))
    out = {}
    for f in spec["fichiers"]:
        cand = []
        for l in liens:
            m = re.search(f["motif"], l)
            if m:
                cand.append((tuple(int(x) for x in m.groups()), urljoin(base, l)))
        if cand:
            out[f["role"]] = max(cand)[1]
    return out


def lignes_csv(contenu: bytes, format_: str):
    if format_ == "csv_zip":
        z = zipfile.ZipFile(io.BytesIO(contenu))
        nom = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        with z.open(nom) as f:
            yield from csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig", errors="replace"))
    else:
        yield from csv.DictReader(io.StringIO(contenu.decode("utf-8-sig", errors="replace")))


def periode(valeur: str, agregat: str) -> str:
    """« 2025-03-02 00:00 » → « 2025-03 » (pays_mois) ; « 2021 » → « 2021 » (pays_annee) ; sinon chaîne vide."""
    v = (valeur or "").strip()
    if agregat == "pays_annee":
        return v[:4] if re.fullmatch(r"\d{4}", v[:4]) else ""
    return v[:7] if re.fullmatch(r"\d{4}-\d{2}", v[:7]) else ""


def nombre(v) -> float:
    try:
        return float(v or 0)
    except ValueError:
        return 0.0


def agreger(lignes, lecture: dict, role: str, pays_iso: dict[str, str], agg: dict, inconnus: set) -> int:
    """Ajoute à agg[(pays, iso, code, période)][role] les comptes et les sommes ; renvoie le nombre de lignes lues.

    Champs de lecture (0.10.472, tous facultatifs sauf date et pays) : somme (colonne principale), categorie,
    somme_par_categorie (somme principale ventilée par catégorie), sommes ({nom: colonne}), distincts ({nom: colonne},
    nombre de valeurs différentes, par ex. régions touchées), principaux ({colonnes: [...], nombre: n}, les valeurs qui
    pèsent le plus dans la somme principale, par ex. les acteurs), agregat (pays_mois ou pays_annee). Une colonne absente
    du fichier est ignorée (lue comme vide)."""
    n = 0
    agregat = lecture.get("agregat", "pays_mois")
    princ = lecture.get("principaux") or {}
    for r in lignes:
        n += 1
        per = periode(r.get(lecture["date"]), agregat)
        if not per:
            continue
        p = r.get(lecture["pays"]) or ""
        iso = pays_iso.get(nom_cle(p), "")
        if not iso:
            inconnus.add(p)
        cle = (p, iso, r.get(lecture.get("code_pays", ""), "") or "", per)
        d = agg.setdefault(cle, {}).setdefault(role, {"evenements": 0, "somme": 0.0, "categories": {}, "sommes_cat": {},
                                                      "sommes": {}, "distincts": {}, "principaux": {}})
        d["evenements"] += 1
        v = nombre(r.get(lecture["somme"])) if lecture.get("somme") else 0.0
        d["somme"] += v
        c = r.get(lecture.get("categorie", ""), "") or ""
        if lecture.get("categorie"):
            d["categories"][c] = d["categories"].get(c, 0) + 1
            if lecture.get("somme_par_categorie"):
                d["sommes_cat"][c] = d["sommes_cat"].get(c, 0.0) + v
        for nom, col in (lecture.get("sommes") or {}).items():
            d["sommes"][nom] = d["sommes"].get(nom, 0.0) + nombre(r.get(col))
        for nom, col in (lecture.get("distincts") or {}).items():
            x = (r.get(col) or "").strip()
            if x:
                d["distincts"].setdefault(nom, set()).add(x)
        for col in princ.get("colonnes", []):
            x = (r.get(col) or "").strip()
            if x:
                d["principaux"][x] = d["principaux"].get(x, 0.0) + (v if lecture.get("somme") else 1)
    return n


def champs(d: dict, cats: list, scats: list, noms_s: list, noms_d: list, k_princ: int) -> list:
    princ = sorted(d["principaux"].items(), key=lambda kv: -kv[1])[:k_princ]
    return ([d["evenements"], round(d["somme"], 1)] + [d["categories"].get(c, 0) for c in cats] +
            [round(d["sommes_cat"].get(c, 0.0), 1) for c in scats] + [round(d["sommes"].get(x, 0.0), 1) for x in noms_s] +
            [len(d["distincts"].get(x, ())) for x in noms_d] +
            ([" ; ".join(p for p, _ in princ)] if k_princ else []))


def ecrire_agregats(spec: dict, agg: dict, sortie: Path) -> int:
    """Une ligne par pays et par période. combiner: priorite (défaut) — pour une même période, la source prioritaire (la
    plus récente) l'emporte ; combiner: roles — les fichiers se complètent (par ex. conflits internes et entre États) et
    chacun a ses colonnes, préfixées par son rôle."""
    lec = spec["lecture"]
    prio = spec.get("priorite") or [f["role"] for f in spec["fichiers"]]
    vals = [d for v in agg.values() for d in v.values()]
    cats = sorted({c for d in vals for c in d["categories"]})
    scats = sorted({c for d in vals for c in d["sommes_cat"]})
    noms_s = list((lec.get("sommes") or {}).keys())
    noms_d = list((lec.get("distincts") or {}).keys())
    k_princ = int((lec.get("principaux") or {}).get("nombre", 0))
    tete = (["evenements", "somme"] + [f"categorie_{c}" for c in cats] + [f"somme_categorie_{c}" for c in scats] +
            noms_s + [f"distincts_{x}" for x in noms_d] + (["principaux"] if k_princ else []))
    col_per = "annee" if lec.get("agregat") == "pays_annee" else "mois"
    roles = [f["role"] for f in spec["fichiers"]]
    combiner = spec.get("combiner", "priorite")
    sortie.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with sortie.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if combiner == "roles":
            w.writerow(["pays_source", "iso3", "code_pays", col_per] + [f"{r}_{t}" for r in roles for t in tete])
        else:
            w.writerow(["pays_source", "iso3", "code_pays", col_per, "source"] + tete)
        vide = {"evenements": 0, "somme": 0.0, "categories": {}, "sommes_cat": {}, "sommes": {}, "distincts": {},
                "principaux": {}}
        for (p, iso, code, per), v in sorted(agg.items(), key=lambda kv: (kv[0][3], kv[0][0])):
            if combiner == "roles":
                ligne = [p, iso, code, per]
                for r in roles:
                    ligne += champs(v.get(r, vide), cats, scats, noms_s, noms_d, k_princ)
                w.writerow(ligne)
            else:
                role = next(r for r in prio if r in v)
                w.writerow([p, iso, code, per, role] + champs(v[role], cats, scats, noms_s, noms_d, k_princ))
            n += 1
    return n


def empreinte_lecture(spec: dict) -> str:
    """Empreinte de la façon de lire (fichiers et champs) : si elle change, on relit même sans version nouvelle."""
    import json
    return hashlib.sha256(json.dumps([spec["fichiers"], spec["lecture"], spec.get("combiner"), spec.get("priorite")],
                                     sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def _colonnes_lecture(lec: dict) -> set:
    cols = {lec.get(k) for k in ("date", "pays", "code_pays", "categorie", "somme")}
    cols |= set((lec.get("sommes") or {}).values()) | set((lec.get("distincts") or {}).values())
    cols |= set((lec.get("principaux") or {}).get("colonnes", []))
    return {c for c in cols if c}


def deja_lus() -> dict[tuple[str, str], dict]:
    if not REFS.exists():
        return {}
    return {(r["carte"], r["url"]): r for r in csv.DictReader(REFS.open(encoding="utf-8"))}


def principal() -> int:
    import httpx
    import politesse
    pays_iso = table_pays()
    refs = deja_lus()
    neuves = []
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=300, follow_redirects=True) as c:
        for spec in specs():
            cid = spec["id"]
            if not politesse.autorise(c, spec["page"]):
                print(f"::warning::{cid} : page refusée par robots.txt ; rien lu.")
                continue
            p = c.get(spec["page"])
            if p.status_code != 200:
                print(f"::warning::{cid} : la page répond {p.status_code} ; rien lu (aucun contournement).")
                continue
            liens = choisir_liens(p.text, spec, spec["page"])
            print(f"{cid} : fichiers trouvés {liens}", flush=True)
            nouveau = [r for r, u in liens.items() if (cid, u) not in refs]
            per = "annee" if spec["lecture"].get("agregat") == "pays_annee" else "mois"
            sortie = REG / f"{cid}-pays-{per}.csv"
            fe = REG / f"{cid}-lecture.txt"
            emp = empreinte_lecture(spec)
            meme_lecture = fe.exists() and fe.read_text(encoding="utf-8").strip() == emp
            if not nouveau and sortie.exists() and meme_lecture:
                print(f"{cid} : aucune version nouvelle ; rien à relire.")
                continue
            if not nouveau:
                print(f"{cid} : la façon de lire a changé ; relecture des mêmes fichiers.")
            agg, inconnus, colonnes_vues = {}, set(), {}
            fmt = {f["role"]: f["format"] for f in spec["fichiers"]}
            for role, url in liens.items():
                if not politesse.autorise(c, url):
                    print(f"::warning::{cid} : {url} refusé par robots.txt.")
                    continue
                with tempfile.TemporaryDirectory() as tmp:          # le fichier ne survit pas à la lecture
                    r = c.get(url)
                    if r.status_code != 200:
                        print(f"::warning::{cid} : {url} répond {r.status_code} (aucun contournement).")
                        continue
                    contenu = r.content
                    (Path(tmp) / "f").write_bytes(contenu)
                    lignes = lignes_csv(contenu, fmt[role])
                    premiere = next(lignes, None)
                    colonnes_vues[url] = list(premiere or {})
                    print(f"{cid} : {role}, colonnes {colonnes_vues[url]}", flush=True)
                    import itertools
                    n = agreger(itertools.chain([premiere] if premiere else [], lignes), spec["lecture"], role,
                                pays_iso, agg, inconnus)
                    neuves.append({"carte": cid, "role": role, "url": url,
                                   "lu_le": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
                                   "octets": len(contenu), "sha256": hashlib.sha256(contenu).hexdigest(), "lignes": n})
                    print(f"{cid} : {role} lu, {n} lignes, {len(contenu) // 1024} Ko", flush=True)
                    del contenu
            if agg:
                k = ecrire_agregats(spec, agg, sortie)
                fe.write_text(emp + "\n", encoding="utf-8")
                print(f"{cid} : {k} lignes pays-{per} → {sortie} ; pays non rattachés : {sorted(x for x in inconnus if x)}")
                entetes = {c for u in liens.values() for c in colonnes_vues.get(u, [])}
                manquantes = sorted(_colonnes_lecture(spec["lecture"]) - entetes)
                if manquantes:
                    print(f"::warning::{cid} : colonnes de lecture absentes des fichiers : {manquantes}")
    if neuves:
        REG.mkdir(parents=True, exist_ok=True)
        neuf = not REFS.exists()
        with REFS.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=COLS_REF)
            if neuf:
                w.writeheader()
            w.writerows(neuves)
    return 0


if __name__ == "__main__":
    sys.exit(principal())
