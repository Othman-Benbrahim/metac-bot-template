"""Confiance dans l'actualité par pays (Reuters Institute, Digital News Report 2026) → ecosystemes/confiance-actualite.csv.
Source validée par l'auteur le 2026-11-25 à 10 h 26. Lit le texte du PDF (pdftotext -layout), page pays par page pays :
le graphique « OVERALL TRUST IN NEWS <début>–26 » donne la valeur de la première année et celle de 2026 avec son écart
à 2025, d'où trois points par pays : première année, 2025, 2026. Les pages à plusieurs courbes (Belgique, Suisse,
Canada) ne gardent que 2025 et 2026. Mesure : part des sondés qui font confiance « à la plupart des informations la
plupart du temps ». Le PDF n'est pas conservé ; seuls les chiffres le sont.
    pdftotext -layout DNR_2026.pdf dnr.txt && python -I mise_au_point/dnr_confiance.py dnr.txt"""
import re
import sys
from pathlib import Path

ISO = {"United Kingdom": "GBR", "Austria": "AUT", "Belgium": "BEL", "Bulgaria": "BGR", "Croatia": "HRV", "Czech Republic": "CZE",
       "Denmark": "DNK", "Finland": "FIN", "France": "FRA", "Germany": "DEU", "Greece": "GRC", "Hungary": "HUN", "Ireland": "IRL",
       "Italy": "ITA", "Netherlands": "NLD", "Norway": "NOR", "Poland": "POL", "Portugal": "PRT", "Romania": "ROU", "Serbia": "SRB",
       "Slovakia": "SVK", "Spain": "ESP", "Sweden": "SWE", "Switzerland": "CHE", "Turkey": "TUR", "United States": "USA",
       "Argentina": "ARG", "Brazil": "BRA", "Canada": "CAN", "Chile": "CHL", "Colombia": "COL", "Mexico": "MEX", "Peru": "PER",
       "Australia": "AUS", "Hong Kong": "HKG", "India": "IND", "Indonesia": "IDN", "Japan": "JPN", "Malaysia": "MYS",
       "Philippines": "PHL", "Singapore": "SGP", "South Korea": "KOR", "Taiwan": "TWN", "Thailand": "THA", "Kenya": "KEN",
       "Morocco": "MAR", "Nigeria": "NGA", "South Africa": "ZAF"}


def lire(texte: str) -> list[tuple[str, int, int]]:
    out = []
    for p in texte.split("\f"):
        if "OVERALL TRUST IN NEWS" not in p:
            continue
        m = re.search(r"2026 \| ([A-Z][A-Za-z .&'()-]+?)(?:\s{2,}|\s*\d+\s*$|$)", p, re.M)
        iso = ISO.get(m.group(1).strip()) if m else None
        if not iso:
            continue
        t = re.search(r"OVERALL TRUST IN NEWS (\d{4})–(\d{2})", p)
        lignes = p.splitlines()
        i0 = next(i for i, l in enumerate(lignes) if "OVERALL TRUST IN NEWS" in l)
        bloc = lignes[i0 + 1:i0 + 40]
        c = re.search(r"(\d+)%\s*\(([-+]?\d+|=|-|–)\)", "\n".join(l[:125] for l in bloc))
        if not c:
            continue
        cur = int(c.group(1))
        d = 0 if c.group(2) in ("=", "-", "–") else int(c.group(2))
        out += [(iso, 2025, cur - d), (iso, 2026, cur)]
        fin = next((k for k, l in enumerate(bloc) if re.search(r"^\s+(19|20)\d\d\s+20\d\d", l)), 20)
        gauche = [int(x.group(1)) for l in bloc[:fin] for x in re.finditer(r"(\d+)%", l[:90]) if 5 <= x.start() <= 30]
        if t and len(gauche) == 1 and "All" not in lignes[i0 + 1][:100] and int(t.group(1)) < 2025:
            out.append((iso, int(t.group(1)), gauche[0]))
    return sorted(out)


if __name__ == "__main__":
    lignes = lire(Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace"))
    f = Path(__file__).resolve().parent.parent / "ecosystemes" / "confiance-actualite.csv"
    with f.open("w", encoding="utf-8") as h:
        h.write("# Confiance dans l'actualité (% qui font confiance à la plupart des informations la plupart du temps), "
                "Reuters Institute, Digital News Report 2026 ; mise_au_point/dnr_confiance.py\n")
        h.write("pays,annee,confiance\n")
        for l in lignes:
            h.write(",".join(map(str, l)) + "\n")
    print(len(lignes), "lignes,", len({l[0] for l in lignes}), "pays ->", f)
