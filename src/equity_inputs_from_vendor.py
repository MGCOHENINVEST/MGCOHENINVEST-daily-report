#!/usr/bin/env python3
"""
Transform vendor equity data into canonical CSVs.

Outputs:
- in/equity/prices.csv
- in/equity/dividends.csv

This is the only place that knows about vendor formats.
"""

from pathlib import Path

PROJECT_ROOT = Path("/opt/daily-report")
IN_DIR = PROJECT_ROOT / "in"
OUT_EQUITY_DIR = PROJECT_ROOT / "in" / "equity"


def build_prices_and_dividends_from_vendor() -> None:
    OUT_EQUITY_DIR.mkdir(parents=True, exist_ok=True)
    # TODO:
    # - Read your real vendor equity files from IN_DIR
    # - Write:
    #     OUT_EQUITY_DIR / "prices.csv"
    #     OUT_EQUITY_DIR / "dividends.csv"
    raise NotImplementedError("Wire vendor → canonical equity inputs here")


if __name__ == "__main__":
    build_prices_and_dividends_from_vendor()
