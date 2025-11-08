#!/usr/bin/env python3
import csv
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
cfg = BASE / "config" / "us"
outdir = BASE / "out" / "universe" / "latest"
outdir.mkdir(parents=True, exist_ok=True)

fields = ["isin","ticker","name","ccy","bucket","mktcap"]
rows = []

for fname in ["sp500.csv", "nasdaq100.csv", "dow30.csv"]:
    fpath = cfg / fname
    if fpath.exists():
        with fpath.open() as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append([row.get(k,"") for k in fields])

outf = outdir / "universe.csv"
with outf.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(fields)
    writer.writerows(rows)

print(f"Wrote {len(rows)} US rows to {outf}")
