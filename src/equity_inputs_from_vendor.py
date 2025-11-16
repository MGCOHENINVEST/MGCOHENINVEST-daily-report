#!/usr/bin/env python3
"""
Fetch canonical equity inputs (prices.csv, dividends.csv) from EODHD for the
current stock universe in data/stock.csv.

- Requires EODHD_API_TOKEN in environment.
- Writes:
    in/equity/prices.csv
    in/equity/dividends.csv
in the schemas defined in DATA_SCHEMA_2025-11-14 Section 9.
"""

import csv
import os
import sys
import time
import datetime as dt
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple, Optional

import requests


PROJECT_ROOT = Path("/opt/daily-report")
DATA_DIR = PROJECT_ROOT / "data"
IN_EQUITY_DIR = PROJECT_ROOT / "in" / "equity"

STOCK_CSV = DATA_DIR / "stock.csv"
PRICES_CSV = IN_EQUITY_DIR / "prices.csv"
DIVIDENDS_CSV = IN_EQUITY_DIR / "dividends.csv"

EOD_BASE_URL = "https://eodhd.com/api"

# Defaults – can be overridden via env if needed
DEFAULT_DAYS_BACK = int(os.environ.get("EQUITY_VENDOR_DAYS_BACK", "400"))
DEFAULT_MAX_TICKERS = int(os.environ.get("EQUITY_VENDOR_MAX_TICKERS", "0"))  # 0 = no limit


def load_universe(limit: Optional[int] = None) -> List[Tuple[str, str]]:
    """
    Load canonical equity universe from data/stock.csv.

    Returns a de-duplicated list of (ticker, exchange) pairs.
    """
    if not STOCK_CSV.exists():
        raise SystemExit(f"ERROR: stock file not found: {STOCK_CSV}")

    pairs: List[Tuple[str, str]] = []
    with STOCK_CSV.open(newline="") as f:
        reader = csv.DictReader(f)
        required = {"ticker", "exchange"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(f"ERROR: stock.csv missing columns: {sorted(missing)}")

        for row in reader:
            ticker = (row.get("ticker") or "").strip()
            exchange = (row.get("exchange") or "").strip()
            if not ticker or not exchange:
                continue
            pairs.append((ticker, exchange))

    # De-duplicate in order
    seen = set()
    uniq: List[Tuple[str, str]] = []
    for t, e in pairs:
        key = (t, e)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(key)

    if limit and limit > 0 and len(uniq) > limit:
        uniq = uniq[:limit]

    return uniq


def _safe_decimal(value) -> Optional[str]:
    if value is None or value == "":
        return None
    try:
        return str(Decimal(str(value)))
    except InvalidOperation:
        return None


def fetch_prices(symbol: str, from_date: str, to_date: str, token: str) -> List[Dict]:
    """Fetch historical daily prices for symbol from EODHD."""
    url = f"{EOD_BASE_URL}/eod/{symbol}"
    params = {
        "api_token": token,
        "from": from_date,
        "to": to_date,
        "fmt": "json",
    }
    r = requests.get(url, params=params, timeout=30)
    if r.status_code != 200:
        print(f"[prices] {symbol}: HTTP {r.status_code} – {r.text[:200]}", file=sys.stderr)
        return []
    try:
        data = r.json()
    except Exception as exc:  # noqa: BLE001
        print(f"[prices] {symbol}: JSON decode error: {exc}", file=sys.stderr)
        return []
    if not isinstance(data, list):
        print(f"[prices] {symbol}: unexpected payload type {type(data)}", file=sys.stderr)
        return []
    return data


def fetch_dividends(symbol: str, from_date: str, to_date: str, token: str) -> List[Dict]:
    """Fetch dividends history for symbol from EODHD."""
    url = f"{EOD_BASE_URL}/div/{symbol}"
    params = {
        "api_token": token,
        "from": from_date,
        "to": to_date,
        "fmt": "json",
    }
    r = requests.get(url, params=params, timeout=30)
    if r.status_code != 200:
        # 404 / no-data is not necessarily fatal – just log and move on
        if r.status_code != 404:
            print(f"[div] {symbol}: HTTP {r.status_code} – {r.text[:200]}", file=sys.stderr)
        return []
    try:
        data = r.json()
    except Exception as exc:  # noqa: BLE001
        print(f"[div] {symbol}: JSON decode error: {exc}", file=sys.stderr)
        return []
    if not isinstance(data, list):
        print(f"[div] {symbol}: unexpected payload type {type(data)}", file=sys.stderr)
        return []
    return data


def build_inputs(days_back: int, max_tickers: int) -> None:
    token = os.environ.get("EODHD_API_TOKEN")
    if not token:
        raise SystemExit("ERROR: EODHD_API_TOKEN not set in environment")

    IN_EQUITY_DIR.mkdir(parents=True, exist_ok=True)

    today = dt.date.today()
    from_date = today - dt.timedelta(days=days_back)
    from_str = from_date.isoformat()
    to_str = today.isoformat()

    universe = load_universe(limit=max_tickers if max_tickers > 0 else None)
    total = len(universe)
    print(f"[universe] {total} tickers in scope (limit={max_tickers or 'none'})")

    # Open outputs
    prices_rows = 0
    div_rows = 0

    with PRICES_CSV.open("w", newline="") as f_prices, DIVIDENDS_CSV.open("w", newline="") as f_divs:
        prices_writer = csv.writer(f_prices)
        div_writer = csv.writer(f_divs)

        # Canonical headers
        prices_writer.writerow(["date", "ticker", "exchange", "close", "volume", "currency", "source"])
        div_writer.writerow(["ticker", "exchange", "ex_date", "pay_date", "amount", "currency", "source"])

        for idx, (ticker, exchange) in enumerate(universe, start=1):
            symbol = f"{ticker}.{exchange}"
            print(f"[vendor] {idx}/{total} {symbol}: fetching", flush=True)

            # Prices
            try:
                prices = fetch_prices(symbol, from_str, to_str, token)
            except Exception as exc:  # noqa: BLE001
                print(f"[vendor] {symbol}: ERROR fetching prices: {exc}", file=sys.stderr)
                prices = []

            for row in prices:
                date = row.get("date")
                if not date:
                    continue

                # Prefer adjusted_close if present, fall back to close
                close_raw = row.get("adjusted_close", row.get("close"))
                close_str = _safe_decimal(close_raw)
                if close_str is None:
                    continue

                volume = row.get("volume") or ""
                currency = row.get("currency") or ""

                prices_writer.writerow(
                    [date, ticker, exchange, close_str, volume, currency, "EODHD"]
                )
                prices_rows += 1

            # Dividends
            try:
                divs = fetch_dividends(symbol, from_str, to_str, token)
            except Exception as exc:  # noqa: BLE001
                print(f"[vendor] {symbol}: ERROR fetching dividends: {exc}", file=sys.stderr)
                divs = []

            for d in divs:
                ex_date = d.get("date")
                if not ex_date:
                    continue

                pay_date = d.get("payment_date") or d.get("paymentdate") or ""
                # Prefer adjusted value; fall back to unadjusted if that's all we have
                amount_raw = d.get("value") or d.get("unadjusted_value")
                amount_str = _safe_decimal(amount_raw)
                if amount_str is None:
                    continue

                currency = d.get("currency") or ""

                div_writer.writerow(
                    [ticker, exchange, ex_date, pay_date, amount_str, currency, "EODHD"]
                )
                div_rows += 1

            # Tiny sleep to avoid hammering the API unnecessarily
            time.sleep(0.15)

    print(f"[done] Wrote {prices_rows} price rows to {PRICES_CSV}")
    print(f"[done] Wrote {div_rows} dividend rows to {DIVIDENDS_CSV}")
    print(f"[done] Date range: {from_str} → {to_str}")


def main(argv: Optional[Sequence[str]] = None) -> None:
    argv = list(argv or sys.argv[1:])

    # Very light CLI parsing to keep things simple
    days_back = DEFAULT_DAYS_BACK
    max_tickers = DEFAULT_MAX_TICKERS

    for arg in argv:
        if arg.startswith("--days-back="):
            try:
                days_back = int(arg.split("=", 1)[1])
            except ValueError:
                raise SystemExit(f"Invalid --days-back value: {arg}")
        elif arg.startswith("--max-tickers="):
            try:
                max_tickers = int(arg.split("=", 1)[1])
            except ValueError:
                raise SystemExit(f"Invalid --max-tickers value: {arg}")
        else:
            raise SystemExit(f"Unknown argument: {arg}")

    build_inputs(days_back, max_tickers)


if __name__ == "__main__":
    main()
