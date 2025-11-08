#!/usr/bin/env python3
import csv
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
cfg = BASE / "config" / "asia"
outdir = BASE / "out" / "universe" / "latest"
outcsv = outdir / "universe.csv"

fields = ["isin","ticker","name","ccy","bucket","mktcap"]

def read_csv(p):
    rows = []
    if p.exists():
        with p.open() as f:
            r = csv.DictReader(f)
            for row in r:
                rows.append([row.get(k,"") for k in fields])
    return rows

def main():
    outdir.mkdir(parents=True, exist_ok=True)

    # ensure base file exists
    if not outcsv.exists():
        with outcsv.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(fields)

    # load what’s already there
    with outcsv.open() as f:
        existing = list(csv.reader(f))
    header, data = existing[0], existing[1:]

    # collect asia rows
    asia_files = ["nikkei225.csv","hsi.csv","asx200.csv","sensex.csv","additions.csv"]
    new_rows = []
    for name in asia_files:
        new_rows += read_csv(cfg / name)

    # append
    with outcsv.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for row in new_rows:
            w.writerow(row)

    print(f"Appended {len(new_rows)} Asia rows into {outcsv}")

if __name__ == "__main__":
    main()
