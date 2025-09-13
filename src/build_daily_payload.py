#!/usr/bin/env python3
import csv
import json
import os
import sys
from statistics import mean
from datetime import datetime

DATA_DIR = "data"

def load_csv(path, required_fields=None):
    if not os.path.exists(path):
        return []
    with open(path, newline='', encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = [row for row in reader]
        if required_fields:
            for i, row in enumerate(rows, start=2):
                for field in required_fields:
                    if field not in row or not row[field]:
                        raise ValueError(f"{path}: line {i} missing field {field}")
        return rows

def build_payload():
    payload = {}

    # --- Stocks ---
    stocks = load_csv(os.path.join(DATA_DIR, "stock.csv"))
    payload["stocks"] = stocks

    # --- Bonds + analytics ---
    bonds = load_csv(
        os.path.join(DATA_DIR, "bonds.csv"),
        required_fields=["isin", "issuer", "maturity", "price"]
    )
    payload["bonds"] = bonds

    if bonds:
        prices = [float(b["price"]) for b in bonds if b.get("price")]
        ytms = [float(b["ytm"]) for b in bonds if b.get("ytm")]
        runs = [float(b["running_yield"]) for b in bonds if b.get("running_yield")]
        durs = [float(b["duration_mod"]) for b in bonds if b.get("duration_mod")]

        payload["bond_analytics"] = {
            "count": len(bonds),
            "avg_price": mean(prices) if prices else None,
            "avg_ytm": mean(ytms) if ytms else None,
            "avg_running_yield": mean(runs) if runs else None,
            "avg_duration_mod": mean(durs) if durs else None,
        }

    # --- Dividend Radar ---
    dividends = load_csv(os.path.join(DATA_DIR, "dividends.csv"))
    for d in dividends:
        # normalize ex-date
        if "ex_date" in d and d["ex_date"]:
            try:
                dt = datetime.strptime(d["ex_date"], "%Y-%m-%d")
                d["ex_date"] = dt.strftime("%d %b %Y")
            except ValueError:
                pass
        if "yield" in d and d["yield"]:
            d["yield"] = float(d["yield"])
    payload["dividend_upcoming"] = dividends

    return payload

if __name__ == "__main__":
    json.dump(build_payload(), fp=sys.stdout, ensure_ascii=False, indent=2)
