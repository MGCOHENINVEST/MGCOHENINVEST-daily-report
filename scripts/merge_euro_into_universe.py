#!/usr/bin/env python3
import csv
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
cfg = BASE / "config" / "euro"
outdir = BASE / "out" / "universe" / "latest"
outcsv = outdir / "universe.csv"

fields = ["isin","ticker","name","ccy","bucket","mktcap"]

def read_any(path: Path):
    rows = []
    if path.exists():
        with path.open() as f:
            r = csv.DictReader(f)
            for row in r:
                # Normalise and FORCE EZ/EUR if missing
                isin = (row.get("isin","") or "").strip()
                ticker = (row.get("ticker","") or "").strip()
                name = (row.get("name","") or "").strip()
                ccy = (row.get("ccy","") or "EUR").strip() or "EUR"
                bucket = (row.get("bucket","") or "EZ").strip() or "EZ"
                mktcap = (row.get("mktcap","") or "").strip()
                rows.append([isin,ticker,name,ccy,bucket,mktcap])
    return rows

def main():
    outdir.mkdir(parents=True, exist_ok=True)

    # Ensure base file exists with header
    if not outcsv.exists():
        with outcsv.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(fields)

    # Load existing to check header only
    with outcsv.open() as f:
        existing = list(csv.reader(f))
    if not existing or existing[0] != fields:
        # Re-write header if a surprise file format appears
        with outcsv.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(fields)

    # Read all euro lists present
    euro_files = ["dax.csv","cac.csv","aex.csv","ibex.csv","mib.csv","bel.csv","psi.csv"]
    new_rows = []
    for name in euro_files:
        new_rows += read_any(cfg / name)

    # Append
    with outcsv.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerows(new_rows)

    print(f"merged euro -> out/universe/latest/universe.csv (added {len(new_rows)})")

if __name__ == "__main__":
    main()
