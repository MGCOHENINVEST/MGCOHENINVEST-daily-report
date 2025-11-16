#!/usr/bin/env python3
"""
Build canonical data/stock.csv from out/data/equity_universe_raw.csv.

Input:
    out/data/equity_universe_raw.csv
        bucket,exchange,code,name,country,sector,industry,currency,isin,market_capitalization

Output:
    data/stock.csv
        ticker,exchange,isin,name,country,sector,currency

Rules:
    - One row per (ticker, exchange).
    - Prefer the first occurrence per (exchange, code) in the universe file.
    - Sector taken from 'sector' (fall back to empty string if missing).
    - Leaves synthetic TEST row out (unless added manually later).
"""

import csv
from pathlib import Path
from typing import Dict, Tuple

PROJECT_ROOT = Path("/opt/daily-report")
OUT_DATA_DIR = PROJECT_ROOT / "out" / "data"
DATA_DIR = PROJECT_ROOT / "data"

UNIVERSE_CSV = OUT_DATA_DIR / "equity_universe_raw.csv"
STOCK_CSV = DATA_DIR / "stock.csv"


def load_universe() -> Dict[Tuple[str, str], Dict[str, str]]:
    universe: Dict[Tuple[str, str], Dict[str, str]] = {}

    if not UNIVERSE_CSV.exists():
        raise SystemExit(f"Missing universe file: {UNIVERSE_CSV}")

    with UNIVERSE_CSV.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = (row.get("code") or "").strip()
            exch = (row.get("exchange") or "").strip()

            if not code or not exch:
                continue

            key = (code, exch)
            if key in universe:
                # Already have a row for this (ticker, exchange); keep the first.
                continue

            universe[key] = {
                "ticker": code,
                "exchange": exch,
                "isin": (row.get("isin") or "").strip(),
                "name": (row.get("name") or "").strip(),
                "country": (row.get("country") or "").strip(),
                "sector": (row.get("sector") or "").strip(),
                "currency": (row.get("currency") or "").strip(),
            }

    return universe


def write_stock(universe: Dict[Tuple[str, str], Dict[str, str]]) -> None:
    STOCK_CSV.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "ticker",
        "exchange",
        "isin",
        "name",
        "country",
        "sector",
        "currency",
    ]

    with STOCK_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for key in sorted(universe.keys(), key=lambda k: (k[1], k[0])):
            writer.writerow(universe[key])

    print(f"Wrote {len(universe)} rows to {STOCK_CSV}")


def main() -> None:
    universe = load_universe()
    print(f"Loaded {len(universe)} unique (ticker, exchange) from universe")
    write_stock(universe)


if __name__ == "__main__":
    main()
