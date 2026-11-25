"""2026-11-25 (source validée par l'auteur : GHS-UCDB R2024A, JRC, CC BY 4.0) : agrégats par pays des centres urbains.

Lit registre/ucdb/<thème>.csv.gz (collecte_ucdb.py) et écrit ecosystemes/ucdb-pays.csv, format long
iso2,variable,annee,valeur ; « WLD » = ensemble des centres urbains du monde.

Définitions lues dans la documentation officielle de chaque thème (registre/ucdb/doc/*.pdf), pas devinées d'après les codes :
- pop_centres : GH_POP_TOT, population totale des centres urbains (GHS-POP R2023A ; 2025 = estimation du modèle).
- part_crue_fluviale_100 : EX_100_POP / GH_POP_TOT, part exposée aux crues de période de retour 100 ans. La part est
  recalculée ici parce que les libellés des colonnes EX_010_SHP et EX_100_SHP sont intervertis dans la documentation.
- part_submersion_100 : EX_CF1_POP / GH_POP_TOT (submersion côtière, période de retour 100 ans).
- part_lecz_10 : (EX_L05_POP + EX_L10_POP) / GH_POP_TOT, part vivant à moins de 10 m d'altitude près des côtes (LECZ).
- part_seisme_6 : somme EX_E06..E10_POP / GH_POP_TOT (intensité MMI ≥ 6).
- jours_utci32 : CL_UTC_T32, jours par an où l'indice de chaleur ressentie UTCI dépasse 32 °C (moyenne de la décennie,
  ERA5) ; moyenne pondérée par la population 2020 de chaque centre, poids fixes pour isoler le climat du peuplement.
- pm25 : EM_PM2_CON (concentration de PM2,5 pondérée par la population, µg/m³ ; la documentation écrit « g/m3 »),
  moyenne pondérée par la population de la même année.
- deces_pm25 : EM_PM2_MOR, décès prématurés attribués aux PM2,5 (somme).
- morts_ucdp : HZ_CON_FAT, morts de la violence organisée dans les centres urbains (UCDP GED, fenêtre de trois ans
  centrée sur l'année ; somme). HZ_CON_TOT n'est pas gardé : la documentation le dit tiré de l'UCDP, mais le même groupe
  compte manifestations et émeutes (ACLED) et ses valeurs (7 728 événements en France en 2020) ne sont pas celles de l'UCDP.
- part_seisme_6 : aléa de la carte GEM 2023.1, pas un séisme observé.
Les années 2030 (projections) ne sont pas gardées.
"""
from __future__ import annotations

import csv
import gzip
from collections import defaultdict
from pathlib import Path

ICI = Path(__file__).resolve().parent.parent
REG = ICI / "registre" / "ucdb"
SORTIE = ICI / "ecosystemes" / "ucdb-pays.csv"
# noms GADM absents de GeoNames ; Chypre du Nord n'est pas rattaché
EXTRA = {"México": "MX", "Netherlands": "NL", "Côte d'Ivoire": "CI", "Palestine": "PS", "Réunion": "RE", "Curaçao": "CW",
         "São Tomé and Príncipe": "ST", "Swaziland": "SZ", "Timor-Leste": "TL"}


def lire(theme: str) -> dict[str, dict]:
    with gzip.open(REG / f"{theme}.csv.gz", "rt", encoding="utf-8-sig") as h:
        return {x["ID_UC_G0"]: x for x in csv.DictReader(h)}


def f(x: dict, c: str) -> float | None:
    try:
        v = float(x.get(c) or "nan")
    except ValueError:
        return None
    return None if v != v or v < 0 else v


def main() -> None:
    import geonamescache
    noms = {v["name"]: k for k, v in geonamescache.GeonamesCache().get_countries().items()} | EXTRA
    gen, gh, ex, cl, em, hz = (lire(t) for t in ("general_characteristics", "ghsl", "exposure", "climate", "emissions", "hazard_risk"))
    pays = {i: noms.get(x["GC_CNT_GAD_2025"]) for i, x in gen.items()}
    acc: dict = defaultdict(lambda: [0.0, 0.0])   # (iso, variable, année) -> [numérateur, dénominateur]

    def ajoute(i, var, an, num, den=1.0):
        for p in (pays[i], "WLD"):
            if p:
                acc[(p, var, an)][0] += num
                acc[(p, var, an)][1] += den

    ans = [str(a) for a in range(1975, 2026, 5)]
    for i in gen:
        for a in ans:
            pop = f(gh.get(i, {}), f"GH_POP_TOT_{a}")
            if not pop:
                continue
            ajoute(i, "pop_centres", a, pop, 0.0)
            e = ex.get(i, {})
            for var, cols in (("part_crue_fluviale_100", ["EX_100_POP"]), ("part_submersion_100", ["EX_CF1_POP"]),
                              ("part_lecz_10", ["EX_L05_POP", "EX_L10_POP"]),
                              ("part_seisme_6", [f"EX_E{k:02d}_POP" for k in range(6, 11)])):
                vs = [f(e, f"{c}_{a}") for c in cols]
                if all(v is not None for v in vs):
                    ajoute(i, var, a, sum(vs), pop)
            if a in ("2000", "2005", "2010", "2015", "2020"):
                m = em.get(i, {})
                c = f(m, f"EM_PM2_CON_{a}")
                if c is not None:
                    ajoute(i, "pm25", a, c * pop, pop)
                d = f(m, f"EM_PM2_MOR_{a}")
                if d is not None:
                    ajoute(i, "deces_pm25", a, d, 0.0)
                for var, col in (("morts_ucdp", "HZ_CON_FAT"),):
                    v = f(hz.get(i, {}), f"{col}_{a}")
                    if v is not None:
                        ajoute(i, var, a, v, 0.0)
        p20 = f(gh.get(i, {}), "GH_POP_TOT_2020")
        if p20:
            for a in ("1970", "1980", "1990", "2000", "2010", "2020"):
                v = f(cl.get(i, {}), f"CL_UTC_T32_{a}")
                if v is not None:
                    ajoute(i, "jours_utci32", a, v * p20, p20)
    with SORTIE.open("w", encoding="utf-8", newline="") as h:
        h.write("# GHS-UCDB R2024A (JRC, CC BY 4.0), agrégé par pays sur les centres urbains ; mise_au_point/ucdb_pays.py\n")
        w = csv.writer(h)
        w.writerow(["iso2", "variable", "annee", "valeur"])
        for (p, var, a), (n, d) in sorted(acc.items()):
            if var.startswith("part_"):
                v = round(100 * n / d, 2) if d else None
            elif var in ("pm25", "jours_utci32"):
                v = round(n / d, 2) if d else None
            else:
                v = round(n)
            if v is not None:
                w.writerow([p, var, a, v])
    print(len(acc), "lignes ;", len({k[0] for k in acc}), "pays")


if __name__ == "__main__":
    main()
