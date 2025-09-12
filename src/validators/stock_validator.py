#!/usr/bin/env python3
import csv, sys, os, json

REQUIRED = ["ticker","isin","name","exchange","country","sector","currency"]
CANDIDATES = ["stock.csv","data/stock.csv","stock.sample.csv","data/stock.sample.csv"]

def find_csv():
    for p in CANDIDATES:
        if os.path.isfile(p):
            return p
    return None

def main():
    csv_path = find_csv()
    if not csv_path:
        print("NOTE: no stock CSV found; skipping validation gracefully.")
        return 0  # don't fail CI just because the sample isn't present

    with open(csv_path, newline='', encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        missing = [c for c in REQUIRED if c not in header]
        if missing:
            print(f"ERROR: {csv_path} missing required columns: {missing}")
            return 2

        seen = set()
        dupes = set()
        for row in reader:
            key = (row.get("ticker","").strip(), row.get("isin","").strip())
            if key in seen: dupes.add(key)
            seen.add(key)

        if dupes:
            print(f"ERROR: duplicate rows by (ticker, isin): {sorted(list(dupes))[:10]}")
            return 3

    print(f"OK: {csv_path} passed schema sanity.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
