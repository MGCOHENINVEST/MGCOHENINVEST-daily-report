#!/usr/bin/env python3
"""
Build a raw equity universe using the EODHD Screener API
(covered by the All-In-One plan).

Output: out/data/equity_universe_raw.csv

Columns:
    bucket,exchange,code,name,country,sector,industry,currency,isin,market_capitalization

Buckets (approximate the spec):
    - UK_FTSE_LARGE_100        → top 100 by mkt cap on LSE
    - FR_CAC_LARGE_50          → top 50 on Paris
    - DE_DAX_LARGE_100         → top 100 on XETRA
    - US_LARGE_250             → top 250 on US (NYSE+NASDAQ combined)
    - US_NASDAQ_LARGE_150      → top 150 on NASDAQ
    - SG_LARGE_50              → top 50 on Singapore
    - HK_LARGE_50              → top 50 on Hong Kong
    - ES_IBEX_LARGE_50         → top 50 on Madrid
    - CH_SWISS_LARGE_50        → top 50 on Swiss (SW)
    - GLOBAL_URANIUM_LARGE_25  → top 25 globally by mkt cap where industry = "Uranium"
"""

import csv
import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

import requests


PROJECT_ROOT = Path("/opt/daily-report")
OUT_DATA_DIR = PROJECT_ROOT / "out" / "data"
OUT_DATA_DIR.mkdir(parents=True, exist_ok=True)

OUT_UNIVERSE_CSV = OUT_DATA_DIR / "equity_universe_raw.csv"

API_TOKEN = os.environ.get("EODHD_API_TOKEN")
BASE_URL = "https://eodhd.com/api/screener"

# Buckets are dicts so we can mix exchange-based and industry-based filters.
#   name      = bucket label
#   exchange  = EODHD exchange code or None for global
#   count     = target number of names
#   filters   = extra screener filters, in Screener JSON syntax
BUCKETS: List[Dict[str, Any]] = [
    {"name": "UK_FTSE_LARGE_100",       "exchange": "LSE",    "count": 100, "filters": []},
    {"name": "FR_CAC_LARGE_50",         "exchange": "PA",     "count": 50,  "filters": []},
    {"name": "DE_DAX_LARGE_100",        "exchange": "XETRA",  "count": 100, "filters": []},
    {"name": "US_LARGE_250",            "exchange": "US",     "count": 250, "filters": []},
    {"name": "US_NASDAQ_LARGE_150",     "exchange": "NASDAQ", "count": 150, "filters": []},
    {"name": "SG_LARGE_50",             "exchange": "SGX",    "count": 50,  "filters": []},
    {"name": "HK_LARGE_50",             "exchange": "HK",     "count": 50,  "filters": []},
    {"name": "ES_IBEX_LARGE_50",        "exchange": "MC",     "count": 50,  "filters": []},
    {"name": "CH_SWISS_LARGE_50",       "exchange": "SW",     "count": 50,  "filters": []},
    # Global uranium / nuclear bucket: industry = "Uranium", no exchange filter.
    {"name": "GLOBAL_URANIUM_LARGE_25", "exchange": None,     "count": 25,
     "filters": [["industry", "=", "Uranium"]]},
]


def require_token() -> str:
    if not API_TOKEN:
        raise SystemExit("EODHD_API_TOKEN is not set in the environment.")
    return API_TOKEN


def build_filters(exchange: Optional[str], extra_filters: List[List[str]]) -> Optional[str]:
    """
    Build Screener 'filters' parameter as JSON-encoded list of [field, op, value].
    """
    clauses: List[List[str]] = []

    if exchange:
        clauses.append(["exchange", "=", exchange])

    if extra_filters:
        # Trust caller to give well-formed [field, op, value] triples.
        clauses.extend(extra_filters)

    if not clauses:
        return None

    return json.dumps(clauses)


def screener_top_n(
    bucket_name: str,
    exchange: Optional[str],
    n: int,
    extra_filters: List[List[str]],
) -> List[Dict[str, Any]]:
    """
    Use Screener API to get top N by market_capitalization.

    For exchange-driven buckets we filter on 'exchange = <code>'.
    For thematic buckets (e.g. uranium) we use industry/sector filters only.
    """
    require_token()
    rows: List[Dict[str, Any]] = []

    remaining = n
    offset = 0

    while remaining > 0:
        limit = min(remaining, 100)

        filters_param = build_filters(exchange, extra_filters)

        params: Dict[str, Any] = {
            "api_token": API_TOKEN,
            "sort": "market_capitalization.desc",
            "limit": limit,
            "offset": offset,
        }
        if filters_param:
            params["filters"] = filters_param

        r = requests.get(BASE_URL, params=params, timeout=60)
        r.raise_for_status()
        payload = r.json()

        # Screener returns either {"data":[...], "total": ...} or a bare list.
        if isinstance(payload, dict):
            items = payload.get("data") or []
        elif isinstance(payload, list):
            items = payload
        else:
            items = []

        if not items:
            break

        for item in items:
            rows.append(
                {
                    "exchange": item.get("exchange") or exchange or "",
                    "code": item.get("code") or "",
                    "name": item.get("name") or "",
                    "country": item.get("country") or "",
                    "sector": item.get("sector") or "",
                    "industry": item.get("industry") or "",
                    "currency": item.get("currency") or item.get("currency_symbol") or "",
                    "isin": item.get("isin") or "",
                    "market_capitalization": item.get("market_capitalization") or 0.0,
                }
            )

        pulled = len(items)
        remaining -= pulled
        offset += pulled

        if pulled < limit:
            # Hit end of list before we reached requested N.
            break

    print(
        f"[screener] bucket={bucket_name} exchange={exchange or '*'} "
        f"requested={n} got={len(rows)}"
    )
    return rows


def build_universe() -> None:
    out_rows: List[Dict[str, Any]] = []

    for bucket in BUCKETS:
        name = bucket["name"]
        ex = bucket.get("exchange")
        count = int(bucket["count"])
        extra = bucket.get("filters") or []

        try:
            pool = screener_top_n(name, ex, count, extra)
        except Exception as e:
            print(f"ERROR: screener for bucket {name} (exchange={ex}) failed: {e}")
            continue

        if not pool:
            print(f"WARNING: no data returned for bucket {name} (exchange={ex})")
            continue

        for r in pool:
            row = {
                "bucket": name,
                "exchange": r.get("exchange", ex or ""),
                "code": r.get("code", ""),
                "name": r.get("name", ""),
                "country": r.get("country", ""),
                "sector": r.get("sector", ""),
                "industry": r.get("industry", ""),
                "currency": r.get("currency", ""),
                "isin": r.get("isin", ""),
                "market_capitalization": r.get("market_capitalization", 0.0),
            }
            out_rows.append(row)

    fieldnames = [
        "bucket",
        "exchange",
        "code",
        "name",
        "country",
        "sector",
        "industry",
        "currency",
        "isin",
        "market_capitalization",
    ]

    OUT_UNIVERSE_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_UNIVERSE_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"Wrote {len(out_rows)} rows to {OUT_UNIVERSE_CSV}")


def main() -> None:
    require_token()
    build_universe()


if __name__ == "__main__":
    main()

