#!/usr/bin/env python3
"""
Build out/data/equity_overview.csv from canonical equity input CSVs.

Inputs (under project root):
- in/equity/prices.csv
    Columns: date,ticker,exchange,close,volume,currency,source
- in/equity/dividends.csv
    Columns: ticker,exchange,ex_date,pay_date,amount,currency,source
- data/stock.csv
    At least: ticker,exchange,isin,name,country,sector,currency

Output:
- out/data/equity_overview.csv
    Columns (exact order, as per DATA_SCHEMA_2025-11-14 Section 9.3):
    ticker,exchange,isin,name,country,sector,currency,
    price_today,price_d1,price_w1,price_m1,price_m3,price_m6,price_y1,
    ret_d1,ret_w1,ret_m1,ret_m3,ret_m6,ret_y1,
    hi_52w,lo_52w,drawdown_from_hi_pct,
    div_trailing_12m,div_yield_trailing_12m,
    next_div_ex_date,next_div_pay_date,next_div_amount,next_div_currency,
    notes_flag,watchlist_flag

Notes:
- Joins are on (ticker, exchange).
- Lookbacks are trailing *trading days* by index:
  d1=1, w1=5, m1=21, m3=63, m6=126, y1=252.
- 52-week hi/low and div_trailing_12m are based on the last price date per key.
"""

from __future__ import annotations

import csv
import datetime as dt
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, List, Tuple, Optional


PROJECT_ROOT = Path("/opt/daily-report")
IN_EQUITY_DIR = PROJECT_ROOT / "in" / "equity"
DATA_DIR = PROJECT_ROOT / "data"
OUT_DATA_DIR = PROJECT_ROOT / "out" / "data"

PRICES_CSV = IN_EQUITY_DIR / "prices.csv"
DIVIDENDS_CSV = IN_EQUITY_DIR / "dividends.csv"
STOCK_CSV = DATA_DIR / "stock.csv"
EQUITY_OVERVIEW_CSV = OUT_DATA_DIR / "equity_overview.csv"

WINDOW_OFFSETS = {
    "d1": 1,
    "w1": 5,
    "m1": 21,
    "m3": 63,
    "m6": 126,
    "y1": 252,
}


@dataclass
class PriceRow:
    date: dt.date
    close: Decimal


@dataclass
class DividendRow:
    ex_date: dt.date
    pay_date: Optional[dt.date]
    amount: Decimal
    currency: str


Key = Tuple[str, str]  # (ticker, exchange)


def parse_date(value: str) -> dt.date:
    value = value.strip()
    if not value:
        raise ValueError("Empty date string where ISO date expected")
    return dt.date.fromisoformat(value)


def parse_optional_date(value: str) -> Optional[dt.date]:
    value = value.strip()
    if not value:
        return None
    return dt.date.fromisoformat(value)


def parse_decimal(value: str) -> Optional[Decimal]:
    value = value.strip()
    if not value:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        raise ValueError(f"Invalid decimal: {value!r}")


def load_prices(path: Path) -> Dict[Key, List[PriceRow]]:
    prices_by_key: Dict[Key, List[PriceRow]] = defaultdict(list)
    if not path.exists():
        raise FileNotFoundError(f"Missing prices.csv at {path}")

    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        required = {"date", "ticker", "exchange", "close"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"prices.csv missing columns: {sorted(missing)}")

        for row in reader:
            ticker = row["ticker"].strip()
            exchange = row["exchange"].strip()
            if not ticker or not exchange:
                continue
            key: Key = (ticker, exchange)
            date = parse_date(row["date"])
            close = parse_decimal(row["close"])
            if close is None:
                continue
            prices_by_key[key].append(PriceRow(date=date, close=close))

    # Sort each key by date ascending
    for key, rows in prices_by_key.items():
        rows.sort(key=lambda r: r.date)

    return prices_by_key


def load_dividends(path: Path) -> Dict[Key, List[DividendRow]]:
    divs_by_key: Dict[Key, List[DividendRow]] = defaultdict(list)
    if not path.exists():
        # It is valid to have no dividends file; treat as empty.
        return divs_by_key

    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        required = {"ticker", "exchange", "ex_date", "amount", "currency"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"dividends.csv missing columns: {sorted(missing)}")

        for row in reader:
            ticker = row["ticker"].strip()
            exchange = row["exchange"].strip()
            if not ticker or not exchange:
                continue
            key: Key = (ticker, exchange)
            ex_date = parse_date(row["ex_date"])
            pay_date = parse_optional_date(row.get("pay_date", "").strip())
            amount = parse_decimal(row["amount"])
            if amount is None:
                continue
            currency = row["currency"].strip()
            divs_by_key[key].append(
                DividendRow(ex_date=ex_date, pay_date=pay_date, amount=amount, currency=currency)
            )

    # Sort each key by ex_date ascending
    for key, rows in divs_by_key.items():
        rows.sort(key=lambda r: r.ex_date)

    return divs_by_key


def load_stock_meta(path: Path) -> Dict[Key, dict]:
    if not path.exists():
        raise FileNotFoundError(f"Missing stock.csv at {path}")

    meta: Dict[Key, dict] = {}
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        required = {"ticker", "exchange", "isin", "name", "country", "sector", "currency"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"stock.csv missing columns: {sorted(missing)}")

        for row in reader:
            ticker = row["ticker"].strip()
            exchange = row["exchange"].strip()
            if not ticker or not exchange:
                continue
            key: Key = (ticker, exchange)
            meta[key] = row

    return meta


def _price_at_offset(prices: List[PriceRow], offset: int) -> Optional[Decimal]:
    if not prices:
        return None
    if len(prices) <= offset:
        return None
    return prices[-1 - offset].close


def _ret(today: Optional[Decimal], ref: Optional[Decimal]) -> Optional[Decimal]:
    if today is None or ref is None:
        return None
    if ref == 0:
        return None
    return (today / ref) - Decimal("1")


def _format_decimal(value: Optional[Decimal]) -> str:
    if value is None:
        return ""
    # Normalize for cleaner CSV; adjust quantize if you want fixed dp.
    return str(value.normalize())


def _format_percent(value: Optional[Decimal]) -> str:
    if value is None:
        return ""
    pct = value * Decimal("100")
    return str(pct.normalize())


def build_equity_overview() -> None:
    OUT_DATA_DIR.mkdir(parents=True, exist_ok=True)

    stock_meta = load_stock_meta(STOCK_CSV)
    prices_by_key = load_prices(PRICES_CSV)
    divs_by_key = load_dividends(DIVIDENDS_CSV)

    fieldnames = [
        "ticker",
        "exchange",
        "isin",
        "name",
        "country",
        "sector",
        "currency",
        "price_today",
        "price_d1",
        "price_w1",
        "price_m1",
        "price_m3",
        "price_m6",
        "price_y1",
        "ret_d1",
        "ret_w1",
        "ret_m1",
        "ret_m3",
        "ret_m6",
        "ret_y1",
        "hi_52w",
        "lo_52w",
        "drawdown_from_hi_pct",
        "div_trailing_12m",
        "div_yield_trailing_12m",
        "next_div_ex_date",
        "next_div_pay_date",
        "next_div_amount",
        "next_div_currency",
        "notes_flag",
        "watchlist_flag",
    ]

    count_written = 0
    count_missing_prices = 0

    with EQUITY_OVERVIEW_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for key in sorted(stock_meta.keys()):
            ticker, exchange = key
            meta = stock_meta[key]

            prices = prices_by_key.get(key, [])
            divs = divs_by_key.get(key, [])

            if prices:
                latest_price_row = prices[-1]
                today_date = latest_price_row.date
                price_today = latest_price_row.close
            else:
                today_date = None
                price_today = None
                count_missing_prices += 1

            # Price history lookbacks by index (trading days)
            price_d = {name: _price_at_offset(prices, offset) for name, offset in WINDOW_OFFSETS.items()}

            # Returns
            ret_d = {name: _ret(price_today, price_d[name]) for name in WINDOW_OFFSETS.keys()}

            # 52-week hi/low & drawdown
            hi_52w: Optional[Decimal] = None
            lo_52w: Optional[Decimal] = None
            drawdown_from_hi_pct: Optional[Decimal] = None

            if prices and today_date is not None:
                cutoff_52w = today_date - dt.timedelta(days=365)
                window_prices = [p.close for p in prices if cutoff_52w <= p.date <= today_date]
                if window_prices:
                    hi_52w = max(window_prices)
                    lo_52w = min(window_prices)
                    if hi_52w and price_today:
                        drawdown_from_hi_pct = (price_today / hi_52w) - Decimal("1")

            # Dividends: trailing 12m & next div
            div_trailing_12m: Optional[Decimal] = None
            div_yield_trailing_12m: Optional[Decimal] = None
            next_div_ex_date: str = ""
            next_div_pay_date: str = ""
            next_div_amount: str = ""
            next_div_currency: str = ""

            if divs and today_date is not None:
                cutoff_div = today_date - dt.timedelta(days=365)
                trailing_amount = Decimal("0")
                have_trailing = False

                future_divs: List[DividendRow] = []

                for d in divs:
                    if cutoff_div < d.ex_date <= today_date:
                        trailing_amount += d.amount
                        have_trailing = True
                    if d.ex_date > today_date:
                        future_divs.append(d)

                if have_trailing:
                    div_trailing_12m = trailing_amount
                    if price_today and price_today != 0:
                        div_yield_trailing_12m = trailing_amount / price_today

                if future_divs:
                    future_divs.sort(key=lambda r: r.ex_date)
                    nxt = future_divs[0]
                    next_div_ex_date = nxt.ex_date.isoformat()
                    if nxt.pay_date:
                        next_div_pay_date = nxt.pay_date.isoformat()
                    next_div_amount = _format_decimal(nxt.amount)
                    next_div_currency = nxt.currency

            # Output row
            row = {
                "ticker": ticker,
                "exchange": exchange,
                "isin": meta.get("isin", "").strip(),
                "name": meta.get("name", "").strip(),
                "country": meta.get("country", "").strip(),
                "sector": meta.get("sector", "").strip(),
                "currency": meta.get("currency", "").strip(),
                "price_today": _format_decimal(price_today),
                "price_d1": _format_decimal(price_d["d1"]),
                "price_w1": _format_decimal(price_d["w1"]),
                "price_m1": _format_decimal(price_d["m1"]),
                "price_m3": _format_decimal(price_d["m3"]),
                "price_m6": _format_decimal(price_d["m6"]),
                "price_y1": _format_decimal(price_d["y1"]),
                "ret_d1": _format_decimal(ret_d["d1"]),
                "ret_w1": _format_decimal(ret_d["w1"]),
                "ret_m1": _format_decimal(ret_d["m1"]),
                "ret_m3": _format_decimal(ret_d["m3"]),
                "ret_m6": _format_decimal(ret_d["m6"]),
                "ret_y1": _format_decimal(ret_d["y1"]),
                "hi_52w": _format_decimal(hi_52w),
                "lo_52w": _format_decimal(lo_52w),
                "drawdown_from_hi_pct": _format_percent(drawdown_from_hi_pct),
                "div_trailing_12m": _format_decimal(div_trailing_12m),
                "div_yield_trailing_12m": _format_decimal(div_yield_trailing_12m),
                "next_div_ex_date": next_div_ex_date,
                "next_div_pay_date": next_div_pay_date,
                "next_div_amount": next_div_amount,
                "next_div_currency": next_div_currency,
                "notes_flag": "",     # reserved for EX_DIV_TODAY / NEW_HIGH etc. later
                "watchlist_flag": "0",  # default off; can be updated from another source later
            }

            writer.writerow(row)
            count_written += 1

    print(
        f"equity_overview: wrote {count_written} rows to {EQUITY_OVERVIEW_CSV} "
        f"(stock entries: {len(stock_meta)}, missing prices: {count_missing_prices})"
    )


def main() -> None:
    build_equity_overview()


if __name__ == "__main__":
    main()
