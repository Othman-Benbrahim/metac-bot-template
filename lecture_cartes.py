"""Lecteur générique des cartes publiées — bot 0.10.470, hors cadre.

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


def agreger(lignes, lecture: dict, role: str, pays_iso: dict[str, str], agg: dict, inconnus: set) -> int:
    """Ajoute à agg[(pays, mois)][role] les comptes et la somme ; renvoie le nombre de lignes lues."""
    n = 0
    for r in lignes:
        n += 1
        mois = (r.get(lecture["date"]) or "")[:7]
        if not re.fullmatch(r"\d{4}-\d{2}", mois):
            continue
        p = r.get(lecture["pays"]) or ""
        iso = pays_iso.get(nom_cle(p), "")
        if not iso:
            inconnus.add(p)
        cle = (p, iso, r.get(lecture.get("code_pays", ""), "") or "", mois)
        d = agg.setdefault(cle, {}).setdefault(role, {"evenements": 0, "somme": 0.0, "categories": {}})
        d["evenements"] += 1
        try:
            d["somme"] += float(r.get(lecture["somme"]) or 0)
        except ValueError:
            pass
        c = r.get(lecture.get("categorie", ""), "") or ""
        d["categories"][c] = d["categories"].get(c, 0) + 1
    return n


def ecrire_agregats(spec: dict, agg: dict, sortie: Path) -> int:
    """Une ligne par pays et par mois ; pour un même mois, la source prioritaire (la plus récente) l'emporte."""
    prio = spec.get("priorite") or [f["role"] for f in spec["fichiers"]]
    cats = sorted({c for v in agg.values() for d in v.values() for c in d["categories"]})
    sortie.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with sortie.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pays_source", "iso3", "code_pays", "mois", "source", "evenements", "somme"] +
                   [f"categorie_{c}" for c in cats])
        for (p, iso, code, mois), v in sorted(agg.items(), key=lambda kv: (kv[0][3], kv[0][0])):
            role = next(r for r in prio if r in v)
            d = v[role]
            w.writerow([p, iso, code, mois, role, d["evenements"], round(d["somme"], 1)] +
                       [d["categories"].get(c, 0) for c in cats])
            n += 1
    return n


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
            sortie = REG / f"{cid}-pays-mois.csv"
            if not nouveau and sortie.exists():
                print(f"{cid} : aucune version nouvelle ; rien à relire.")
                continue
            agg, inconnus = {}, set()
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
                    n = agreger(lignes_csv(contenu, fmt[role]), spec["lecture"], role, pays_iso, agg, inconnus)
                    neuves.append({"carte": cid, "role": role, "url": url,
                                   "lu_le": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
                                   "octets": len(contenu), "sha256": hashlib.sha256(contenu).hexdigest(), "lignes": n})
                    print(f"{cid} : {role} lu, {n} lignes, {len(contenu) // 1024} Ko", flush=True)
                    del contenu
            if agg:
                k = ecrire_agregats(spec, agg, sortie)
                print(f"{cid} : {k} lignes pays-mois → {sortie} ; pays non rattachés : {sorted(x for x in inconnus if x)}")
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
