"""Risques annuels de départ par ancienneté (Archigos 4.1, 1990-2015) → ecosystemes/archigos-risques.csv.
    python -I mise_au_point/archigos_risques.py chemin/vers/peacesciencer/data/archigos.rda
(décision de l'auteur, 2026-11-24, 15 h 23 : source validée)."""
import sys
import pandas as pd
import pyreadr

df = list(pyreadr.read_r(sys.argv[1]).values())[0]
df["s"], df["e"] = pd.to_datetime(df.startdate), pd.to_datetime(df.enddate)
D0, D1 = pd.Timestamp("1990-01-01"), pd.Timestamp("2015-12-31")
seg = {"0-2": (0, 2), "2-5": (2, 5), "5-10": (5, 10), "10+": (10, 99)}
expo = {k: 0.0 for k in seg}
ev = {k: {"irr": 0, "reg": 0, "mort": 0} for k in seg}
for _, r in df.iterrows():
    a, b = max(r.s, D0), min(r.e, D1)
    if b <= a:
        continue
    for k, (lo, hi) in seg.items():
        u, v = max(a, r.s + pd.Timedelta(days=365.25 * lo)), min(b, r.s + pd.Timedelta(days=365.25 * hi))
        if v > u:
            expo[k] += (v - u).days / 365.25
    if D0 <= r.e <= D1 and r.exit != "Still in Office":
        t = (r.e - r.s).days / 365.25
        k = next(k for k, (lo, hi) in seg.items() if lo <= t < hi)
        c = "irr" if r.exit in ("Irregular", "Foreign") else ("mort" if r.exit in ("Natural Death", "Retired Due to Ill Health", "Suicide") else "reg")
        ev[k][c] += 1
for k in seg:
    print(f"{k},{round(expo[k])},{ev[k]['irr'] / expo[k]:.4f},{ev[k]['reg'] / expo[k]:.4f},{ev[k]['mort'] / expo[k]:.4f}")
