#!/usr/bin/env python3
import csv
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
cfg = BASE / "config" / "uk"
outdir = BASE / "out" / "universe" / "latest"
outdir.mkdir(parents=True, exist_ok=True)

fields = ["isin","ticker","name","ccy","bucket","mktcap"]
rows = []

# Look for additions.csv under config/uk
fpath = cfg / "additions.csv"
if fpath.exists():
    with fpath.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append([row.get(k,"") for k in fields])

outf = outdir / "universe.csv"
if not outf.exists():
    print("[WARN] universe.csv not found — did you run merge_us_indices.py and merge_euro_into_universe.py first?")
else:
    # Append UK rows
    with outf.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    print(f"Appended {len(rows)} UK rows to {outf}")
